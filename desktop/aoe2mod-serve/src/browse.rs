//! `/api/browse`: a paged grid of things a player can pick by LOOKING at them.
//!
//! Typing a name only works if you already know the name, and the game's Chinese
//! names are not the ones people use ("弓箭手" is not any unit's name at all;
//! "城堡" is a building AND part of a technology's name). So this route exists so
//! a player can point at a picture instead.
//!
//! Two rules carried over from the reference:
//!
//!   * `total` counts NAMED entities -- the rows this route can return -- never
//!     every record in the `.dat`. The grid is what the player counts, and an
//!     earlier version quoted 2,693 unit records beside a grid listing 1,651.
//!   * `has_icon` is reported per row: many of the game's units ship no icon id,
//!     so a grid that silently rendered holes would look broken.

use serde_json::{json, Value};
use std::collections::HashMap;

/// `kind` is "unit" or "tech"; `q` filters by any of the entity's names.
///
/// `icon_ids` maps an entity id to the icon id its record carries. An id that is
/// absent from the map has NO icon -- reported as `has_icon: false` so the page
/// can draw a labelled cell instead of a hole.
pub fn browse(
    names_doc: &Value,
    icon_ids: &HashMap<i16, i16>,
    kind: &str,
    query: &str,
    limit: usize,
    offset: usize,
) -> Value {
    let key = if kind == "tech" { "techs" } else { "units" };
    let table = names_doc.get(key).and_then(|v| v.as_object());
    let q = query.trim().to_lowercase();

    let mut all: Vec<(i16, Vec<String>)> = Vec::new();
    if let Some(t) = table {
        for (k, v) in t {
            let id: i16 = match k.parse() {
                Ok(i) => i,
                Err(_) => continue,
            };
            let names: Vec<String> = v
                .as_array()
                .map(|a| {
                    a.iter()
                        .filter_map(|x| x.as_str().map(|s| s.to_string()))
                        .collect()
                })
                .unwrap_or_default();
            if names.is_empty() {
                continue;
            }
            if !q.is_empty()
                && !names.iter().any(|n| n.to_lowercase().contains(&q))
            {
                continue;
            }
            all.push((id, names));
        }
    }
    // Stable order by id: two page loads must agree, or a click lands on a
    // different row than the one the player saw.
    all.sort_by_key(|(id, _)| *id);
    let total = all.len();
    let page: Vec<Value> = all
        .into_iter()
        .skip(offset)
        .take(limit)
        .map(|(id, names)| {
            let zh = names.first().cloned().unwrap_or_default();
            let en = names
                .iter()
                .find(|n| n.chars().all(|c| !('\u{4e00}'..='\u{9fff}').contains(&c)))
                .cloned()
                .unwrap_or_default();
            // The icon id is NOT the entity id: unit 83's icon is 15. It comes
            // from the record's own IconID field, via the offset table.
            let icon_id = icon_ids.get(&id).copied().unwrap_or(-1);
            json!({
                "id": id,
                "kind": if kind == "tech" { "tech" } else { "unit" },
                "name": zh,
                "en": en,
                "zh": zh,
                "has_icon": icon_id > 0,
                "icon_id": icon_id,
            })
        })
        .collect();

    json!({
        "ok": true,
        "browse": {
            "ok": true,
            "kind": if kind == "tech" { "tech" } else { "unit" },
            "limit": limit,
            "offset": offset,
            "total": total,
            "rows": page,
        }
    })
}


/// `entity id -> icon id`, read once from the `.dat` unit records.
///
/// The field is `IconID`, a fixed i16 at a known offset in every unit record
/// (it does not depend on the record's type -- it sits before the type-dependent
/// tail). Walking Gaia's records is enough: the icon id is a property of the
/// unit, not of the civilization.
pub fn icon_ids_from_dat(raw: &[u8], table: &crate::stats::StatTable) -> HashMap<i16, i16> {
    let mut out = HashMap::new();
    // The offset table carries absolute positions per (civ, stat, unit). Only
    // `hit_points` and friends are in there, not icon_id, so this falls back to
    // scanning the records through the dat crate.
    for (id, _) in table.civs.first().map(|c| &c.offsets).into_iter().flatten() {
        let _ = id;
    }
    // Read through the crate's own reader: it already knows the record layout.
    let mut r = aoe2mod_dat::Reader::new(raw);
    let Ok(s1) = aoe2mod_dat::read_stage1(&mut r) else {
        return out;
    };
    let gv = s1.game_version;
    if aoe2mod_dat::read_stages23(&mut r).is_err() {
        return out;
    }
    if aoe2mod_dat::read_stages47(&mut r, gv).is_err() {
        return out;
    }
    let Ok(s810) = aoe2mod_dat::read_stages810(&mut r, gv) else {
        return out;
    };
    if let Some(civ) = s810.civs.first() {
        for u in &civ.units {
            if let Some(icon) = u.icon_id {
                out.insert(u.id, icon);
            }
        }
    }
    out
}
