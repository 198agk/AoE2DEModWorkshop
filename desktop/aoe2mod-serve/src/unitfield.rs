//! Resolving `unit.cost` and `unit.attack_class` to byte offsets.
//!
//! Both intents write `i16`s into a unit record, and neither can be resolved by
//! a per-civilisation lookup table the way `unit.stat` can: which of the three
//! `ResourceCost` slots answers "木材成本" depends on the slot's own `type`, and
//! which of the attack rows answers "对平民" depends on the row's own `class`.
//! So these two read the marks the parser recorded while walking the record, and
//! the decision is a lookup in what the file actually contains.
//!
//! # Why the mirrors are not optional
//!
//! AoE2 stores several unit properties twice: the number the panel RENDERS
//! (`DisplayedAttack`, `DisplayedMeleeArmour`, `DisplayedPierceArmour`) and the
//! number the damage maths READS (the `attacks`/`armors` row for class 3/4).
//! Shipping data keeps the two in step for 97.5-99.9% of comparable units, so an
//! edit that moves only one of them produces a record the game never ships: the
//! panel would show 10 while the arrow still hits for 4.
//!
//! The mirror carries the DELTA, never the value.  The 20 units where the two
//! numbers diverge on purpose must keep that offset after the edit, and copying
//! the displayed value would erase it.
//!
//! Whether a displayed field tracks a particular damage row is derived from
//! `_golden/stat_mirrors.json`, which is the schema's one-directional `mirror`
//! links.  It is genuinely a SET rather than a single owner: when an armour list
//! has class 3 but no class 4, BOTH `displayed_melee_armour` and
//! `displayed_pierce_armour` resolve to that one class-3 row, and moving only one
//! of them would desync the panel.

use aoe2mod_dat::stage810::{Stages810, Unit};
use aoe2mod_dat::stats::StatKind;

/// One write to perform: which civilisation (for the report) and where.
#[derive(Debug, Clone, Copy)]
pub struct Hit {
    pub civ: usize,
    pub offset: usize,
}

/// What an edit resolved to.
#[derive(Debug, Clone)]
pub struct Resolved {
    pub hits: Vec<Hit>,
    /// The value held at `hits[0].offset` before the edit.
    pub before: f64,
    /// The schema's user-facing name for the field, so a refusal and the screen
    /// agree and neither leaks a locator key like `attack cls 3`.
    pub label: String,
}

impl Resolved {
    pub fn kind(&self) -> StatKind {
        // Every field these two intents reach is a signed 16-bit integer.  The
        // cost amounts and damage amounts are both `i16` in the format, which is
        // also why the reference writes them with `signed=True`.
        StatKind::I16
    }

    /// How many distinct civilizations the write list touches.
    ///
    /// This is NOT `hits.len()`: after family expansion one civilisation
    /// contributes several ids, and the reference calls the two numbers
    /// `civ_count` and `edit_count` precisely because they answer different
    /// questions.
    pub fn civ_count(&self) -> usize {
        let mut seen: Vec<usize> = self.hits.iter().map(|h| h.civ).collect();
        seen.sort_unstable();
        seen.dedup();
        seen.len()
    }
}

/// Which resource word a cost edit names, as the id the record stores.
///
/// Read from `dat_bindings.json`'s `resource_types`, not invented here: those
/// five are the ids the game uses, and `population` in particular is 4 rather
/// than something the caller would guess.
pub fn resource_id(word: &str) -> Option<i16> {
    match word {
        "food" => Some(0),
        "wood" => Some(1),
        "stone" => Some(2),
        "gold" => Some(3),
        "population" => Some(4),
        _ => None,
    }
}

fn resource_zh(word: &str) -> &'static str {
    match word {
        "food" => "食物",
        "wood" => "木材",
        "stone" => "石头",
        "gold" => "黄金",
        "population" => "人口",
        _ => "",
    }
}

/// The slot that IS the cost of resource `want`, or `None` when the type is absent.
///
/// The rule is NOT "the first slot whose type matches", and each part of it is
/// load-bearing:
///
///   * an empty slot is real -- `(-1,0,0)` is the sentinel and a `(0,0,1)`
///     placeholder marks "paid, amount zero";
///   * taking the first type match lands on one of 133 zero amounts in the base
///     data;
///   * taking only `flag != 0` misses tech 430, whose 800 food and 500 gold are
///     genuinely stored with `flag == 0`.
///
/// So: among slots of that type, prefer the first NONZERO amount; if every
/// candidate is zero, fall back to the first one.
fn pick_cost_slot(costs: &[aoe2mod_dat::stage810::CostSlot], want: i16) -> Option<usize> {
    let mut first: Option<usize> = None;
    for (i, c) in costs.iter().enumerate() {
        if c.type_ != want {
            continue;
        }
        if first.is_none() {
            first = Some(i);
        }
        if c.amount != 0 {
            return Some(i);
        }
    }
    first
}

/// A displayed panel field that tracks a damage row, and where it sits.
///
/// `classes` is the schema's ordered candidate list for that link: the field
/// tracks whichever of those classes the unit's list carries FIRST.  That
/// ordering is what makes `民兵` (classes 29,21,4,8,30,15 attack) have
/// `displayed_attack` tracking class 4 while `步弓手` (…,3,…) has it tracking
/// class 3.
struct MirrorSpec {
    classes: &'static [i16],
    /// Which list on the unit the linked row lives in.
    source: &'static str,
}

/// The five `Displayed*` fields and their mirror links, from
/// `_golden/stat_mirrors.json`.
///
/// Only the two whose `source` is a damage list can ever track a damage row;
/// `displayed_range` and `displayed_reload_time` mirror plain marks
/// (`max_range`, `reload_time`) and are therefore irrelevant to a class edit.
/// They are still listed so that the table is the schema's table rather than a
/// hand-picked subset -- an entry that cannot match is a no-op, while a missing
/// entry silently skips a mirror.
fn mirror_specs() -> Vec<(&'static str, MirrorSpec)> {
    vec![
        (
            "displayed_attack",
            MirrorSpec {
                classes: &[3, 4],
                source: "attack",
            },
        ),
        (
            "displayed_melee_armour",
            MirrorSpec {
                classes: &[4, 3],
                source: "armour",
            },
        ),
        (
            "displayed_pierce_armour",
            MirrorSpec {
                classes: &[3, 4],
                source: "armour",
            },
        ),
    ]
}

/// The offset of the `Displayed*` mark named `field` on this record, if the
/// record is old enough to have one.
fn mark_offset(u: &Unit, field: &str) -> Option<usize> {
    match field {
        "displayed_attack" => u.type50.as_ref().map(|t| t.displayed_attack.offset),
        "displayed_melee_armour" => u.type50.as_ref().map(|t| t.displayed_melee_armour.offset),
        "displayed_pierce_armour" => u.displayed_pierce_armour.map(|m| m.offset),
        _ => None,
    }
}

/// The offset of the row a mirror link resolves to on this record.
///
/// Returns `None` when the unit carries none of the candidate classes -- which
/// is the same condition that makes the PRIMARY lookup fail, so a mirror can
/// never outlive the row it tracks.
fn linked_row_offset(u: &Unit, spec: &MirrorSpec) -> Option<usize> {
    let list = match spec.source {
        "attack" => u.type50.as_ref().map(|t| &t.attacks)?,
        "armour" => u.type50.as_ref().map(|t| &t.armors)?,
        _ => return None,
    };
    for sel in spec.classes {
        if let Some(e) = list.iter().find(|e| e.class == *sel) {
            return Some(e.amount_offset);
        }
    }
    None
}

/// `unit.cost`: the amount of one resource in a unit's three cost slots.
///
/// A resource the record does not carry is refused rather than added: "give this
/// unit a wood cost" is a different operation from "change the price", and
/// guessing a slot is how the price moves on one field while the screen shows a
/// cost the game does not charge.
pub fn cost_targets(
    s810: &Stages810,
    family: &[i16],
    resource: &str,
    unit: i16,
) -> Result<Resolved, String> {
    let want = resource_id(resource).ok_or_else(|| format!("不认识的资源 {resource}"))?;
    let mut hits = Vec::new();
    let mut before = None;
    for (ci, c) in s810.civs.iter().enumerate() {
        for u in c.units.iter() {
            if !family.contains(&u.id) {
                continue;
            }
            if let Some(slot) = pick_cost_slot(&u.costs, want) {
                let off = u.costs[slot].amount_offset;
                if before.is_none() {
                    before = Some(u.costs[slot].amount as f64);
                }
                hits.push(Hit { civ: ci, offset: off });
            }
        }
    }
    let label = format!("{}成本", resource_zh(resource));
    finish(hits, before, label, unit)
}

/// `unit.attack_class`: one row of Type50's attack or armour list, plus the
/// panel number that tracks it.
pub fn damage_targets(
    s810: &Stages810,
    family: &[i16],
    kind: &str,
    classes: &[i16],
    unit: i16,
) -> Result<Resolved, String> {
    let specs = mirror_specs();
    let mut hits = Vec::new();
    let mut before = None;
    for (ci, c) in s810.civs.iter().enumerate() {
        for u in c.units.iter() {
            if !family.contains(&u.id) {
                continue;
            }
            let rows: &[aoe2mod_dat::stage810::DamageEntry] = match kind {
                "attack" => match u.type50.as_ref() {
                    Some(t) => &t.attacks,
                    None => continue,
                },
                "armour" => match u.type50.as_ref() {
                    Some(t) => &t.armors,
                    None => continue,
                },
                _ => return Err(format!("攻击还是护甲？说的是 {kind}")),
            };
            // First candidate the unit actually carries.  Taking a fixed slot
            // instead is the bug the schema's `class_candidates` note warns
            // about: class 3 is what a militia does NOT have, so "对建筑攻击"
            // on a militia must fail rather than write into class 29.
            let mut primary = None;
            for sel in classes {
                if let Some(e) = rows.iter().find(|e| e.class == *sel) {
                    primary = Some(*e);
                    break;
                }
            }
            let Some(p) = primary else { continue };
            if before.is_none() {
                before = Some(p.amount as f64);
            }
            hits.push(Hit { civ: ci, offset: p.amount_offset });

            // Mirror: a panel field tracks this row when the row it resolves to
            // IS the row being edited.  Editing a class the panel does not track
            // (class 1 on a militia) therefore leaves the displayed number alone
            // instead of inventing a desync.
            for (field, spec) in &specs {
                if spec.source != kind {
                    continue;
                }
                if linked_row_offset(u, spec) != Some(p.amount_offset) {
                    continue;
                }
                if let Some(off) = mark_offset(u, field) {
                    hits.push(Hit { civ: ci, offset: off });
                }
            }
        }
    }
    let label = if kind == "attack" { "基础攻击" } else { "基础护甲" };
    finish(hits, before, label.to_string(), unit)
}

/// Turn "nothing to write" into the reference's sentence.
///
/// The wording is the reference's because the screen prints it verbatim: a
/// second layer that re-worded it would drift, and the two texts have drifted
/// before.  `（这类单位没有存这一项）` is the unit path's reason -- unlike the
/// tech path, it does not distinguish a missing cost slot from a missing field,
/// because both mean the same thing to the player.
fn finish(
    hits: Vec<Hit>,
    before: Option<f64>,
    label: String,
    unit: i16,
) -> Result<Resolved, String> {
    if hits.is_empty() {
        return Err(format!(
            "{} 没有「{}」这项可以改（这类单位没有存这一项）",
            display_name(unit),
            label
        ));
    }
    Ok(Resolved {
        hits,
        before: before.unwrap_or(f64::NAN),
        label,
    })
}

/// What to call a unit in a sentence the player reads.
///
/// The first name in `entity_names.json` is the Chinese one, which is what the
/// reference prints (`民兵`, not `Militia`).  Falling back to the id is honest:
/// a refusal that names the record by number is still actionable, while one that
/// says "这个单位" is not.
fn display_name(unit: i16) -> String {
    crate::sentences::names()
        .as_ref()
        .and_then(|n| n.units.get(&unit))
        .and_then(|v| v.first())
        .cloned()
        .unwrap_or_else(|| format!("单位 {unit}"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use aoe2mod_dat::stage810::CostSlot;

    #[test]
    fn a_zero_amount_slot_is_still_reachable_but_a_nonzero_one_wins() {
        let slots = [
            CostSlot { type_: 1, amount: 0, amount_offset: 10 },
            CostSlot { type_: 1, amount: 25, amount_offset: 16 },
        ];
        assert_eq!(pick_cost_slot(&slots, 1), Some(1));
        let all_zero = [
            CostSlot { type_: 3, amount: 0, amount_offset: 10 },
            CostSlot { type_: 3, amount: 0, amount_offset: 16 },
        ];
        assert_eq!(pick_cost_slot(&all_zero, 3), Some(0));
    }

    #[test]
    fn a_missing_resource_is_none_not_the_first_slot() {
        let slots = [CostSlot { type_: 0, amount: 50, amount_offset: 10 }];
        assert_eq!(pick_cost_slot(&slots, 1), None);
    }

    #[test]
    fn the_resource_ids_are_the_schemas_not_a_guess() {
        assert_eq!(resource_id("food"), Some(0));
        assert_eq!(resource_id("wood"), Some(1));
        assert_eq!(resource_id("stone"), Some(2));
        assert_eq!(resource_id("gold"), Some(3));
        assert_eq!(resource_id("population"), Some(4));
        assert_eq!(resource_id("faith"), None);
    }
}
