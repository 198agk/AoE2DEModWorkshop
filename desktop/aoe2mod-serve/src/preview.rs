//! What a sentence would do, computed by RUNNING the build instead of describing it.
//!
//! The page shows "1,701 处改动" before the player presses 生成.  A preview that
//! counted those places its own way would eventually disagree with the builder,
//! and the disagreement would show up as a promise broken after the mod is
//! installed -- the shape this project has paid for repeatedly (`edit_count` was
//! 1701 in the build and 1 in an earlier preview attempt; `unit.stat` wrote the
//! panel number and not the mirror, so the preview said "editable" about an edit
//! that changed nothing the game reads).
//!
//! So this module does not count anything.  It turns the clause's `Intent` back
//! into the request the builder expects, calls the builder with `"dry": true`,
//! and reads the numbers out of the builder's own report.  `stat_edit::is_dry`
//! makes every builder stop at exactly one place: the line before it creates the
//! mod folder.  Resolution, family expansion, mirror lookup and the refusal
//! reasons are all the real ones.
//!
//! The consequence that matters: a sentence the builder refuses cannot preview
//! as buildable, because there is only one decision.

use serde_json::{json, Value};

use crate::sentences::{names, Intent, STAT_WORDS};

/// `stat -> the Chinese noun for it`, from the reference's `_FIELD_ZH`
/// (`aoe2mod/intent/compiler.py:2623`).  The plan's `description` is read by a
/// person, and "displayed_attack" is not a word anyone says.
fn field_zh(stat: &str) -> &'static str {
    match stat {
        "hit_points" => "生命值",
        "displayed_attack" => "攻击力",
        "displayed_melee_armour" => "近战护甲",
        "displayed_pierce_armour" => "远程护甲",
        "displayed_range" => "射程",
        "movement_speed" => "移动速度",
        "research_time" => "研究时间",
        "attack" => "攻击",
        "melee_armour" => "近战护甲",
        "pierce_armour" => "远程护甲",
        "line_of_sight" => "视野",
        "garrison_capacity" => "驻扎上限",
        "creation_time" => "训练时间",
        "max_range" => "射程",
        "min_range" => "最小射程",
        "reload_time" => "装填时间",
        "displayed_reload_time" => "面板装填时间",
        "accuracy" => "命中率",
        _ => "数值",
    }
}

/// `resource -> the Chinese word`, from `_RESOURCE_ZH` (`compiler.py:2635`).
fn resource_zh(r: &str) -> &'static str {
    match r {
        "food" => "食物",
        "wood" => "木材",
        "gold" => "黄金",
        "stone" => "石头",
        "population" | "pop" => "人口",
        "build_time" => "建造时间",
        "research_time" => "研究时间",
        "trade_goods" => "贸易品",
        "relics" => "圣物",
        _ => "成本",
    }
}

/// How the sentence said to change the number.
fn op_zh(it: &Intent) -> String {
    match (it.value, it.delta) {
        (Some(v), _) => format!(" ={v}"),
        (None, Some(d)) if d >= 0.0 => format!(" +{d}"),
        (None, Some(d)) => format!(" {d}"),
        _ => String::new(),
    }
}

/// The entity the sentence is about, for the plan's description.
fn entity(it: &Intent, kind: &str) -> String {
    let id = if kind == "tech" { it.tech } else { it.unit };
    match id {
        Some(v) => entity_of(&names(), kind, v),
        None => "它".into(),
    }
}

/// The name of one record, given the table.  Split out from `entity` so a
/// preview can name an id that is not the clause's primary target -- the sprite
/// donor being the case that made this necessary (`#8` in the description).
fn entity_of(table: &Option<crate::sentences::Names>, kind: &str, id: i16) -> String {
    if let Some(n) = table.as_ref() {
        let map = if kind == "tech" { &n.techs } else { &n.units };
        if let Some(list) = map.get(&id) {
            // The FIRST alias is the game's own primary name; the rest are
            // alternative spellings players use.  Printing the second one back
            // would rename the thing the player asked about.
            if let Some(first) = list.first() {
                return first.clone();
            }
        }
    }
    format!("#{id}")
}

fn tech_names(it: &Intent) -> Vec<String> {
    let table = names();
    it.techs
        .clone()
        .unwrap_or_default()
        .iter()
        .map(|id| {
            table
                .as_ref()
                .and_then(|n| n.techs.get(id))
                .and_then(|l| l.first().cloned())
                .unwrap_or_else(|| format!("#{id}"))
        })
        .collect()
}

/// The sentence's own words for what it wants, so the plan reads like it.
fn describe(it: &Intent) -> String {
    let op = op_zh(it);
    match it.intent.as_str() {
        "unit.stat" => {
            let stat = it.stat.as_deref().unwrap_or("");
            format!("{} {}{}", entity(it, "unit"), field_zh(stat), op)
        }
        "tech.research_time" => format!("{} 研究时间{}", entity(it, "tech"), op),
        "tech.cost" => format!(
            "{} {}成本{}",
            entity(it, "tech"),
            resource_zh(it.resource.as_deref().unwrap_or("")),
            op
        ),
        "unit.cost" => format!(
            "{} {}成本{}",
            entity(it, "unit"),
            resource_zh(it.resource.as_deref().unwrap_or("")),
            op
        ),
        "unit.attack_class" => {
            let what = if it.attack_kind.as_deref() == Some("armour") {
                "护甲"
            } else {
                "攻击"
            };
            // The class id the sentence named is a UNIT class (12 = 骑兵); the id
            // an attack entry stores is an ATTACK class (3/4/29).  The table's
            // own words are the only ones that name the stored id, so the label
            // comes from it and not from the sentence's word.
            let cid = it.class_id.unwrap_or(3) as u32;
            let table = crate::attack_class::class_names();
            let cn = table
                .get(&cid)
                .and_then(|l| l.first())
                .cloned()
                .unwrap_or_else(|| format!("类别 {cid}"));
            format!("{} 基础{what}·{cn}{op}", entity(it, "unit"))
        }
        "tech.effect" => {
            // `field` is the command slot letter (t/a/b/c/d), not a name, and the
            // table names fields by letter.  The reference prints the effect's
            // own attribute name instead, which this side does not carry; saying
            // which command it is says the same thing in the player's terms.
            let n = it.command.unwrap_or(0) + 1;
            format!("{} 第 {} 条效果{}", entity(it, "tech"), n, op)
        }
        "tech.toggle_group" => {
            let list = tech_names(it);
            format!(
                "{} 项做成一组：{}",
                list.len(),
                list.join("、")
            )
        }
        "unit.card_move" => format!(
            "{} 放到 {} 的第 {} 格",
            entity(it, "unit"),
            it.building.map(|b| format!("#{b}")).unwrap_or_else(|| "卡".into()),
            it.button.unwrap_or(0) + 1
        ),
        "unit.sprite" => format!(
            "{} 的样子换成 {}",
            entity(it, "unit"),
            // The donor is an entity too: the reader already resolved it to an
            // id, so print the same name the player used.  `#8` was the id
            // leaking through a preview that had the table in hand.
            it.donor
                .map(|d| entity_of(&names(), "unit", d))
                .unwrap_or_else(|| "别的单位".into())
        ),
        other => format!("{other}{op}"),
    }
}

/// Which of the plan's own fields name the kind of record being edited.
fn kind_of(it: &Intent) -> &'static str {
    if it.intent.starts_with("tech.") {
        "tech"
    } else {
        "unit"
    }
}

/// The request the builder expects, reconstructed from the clause.
///
/// This is the ONE place that knows both shapes.  If a builder starts requiring
/// a field the reader does not produce, the dry run fails with the builder's own
/// complaint instead of previewing a different edit.
fn request(it: &Intent) -> Value {
    let mut req = json!({ "intent": it.intent, "dry": true });
    let o = req.as_object_mut().unwrap();
    for (key, val) in [
        ("unit", it.unit.map(|v| json!(v))),
        ("tech", it.tech.map(|v| json!(v))),
        ("stat", it.stat.clone().map(|v| json!(v))),
        ("resource", it.resource.clone().map(|v| json!(v))),
        ("value", it.value.map(|v| json!(v))),
        ("delta", it.delta.map(|v| json!(v))),
        ("field", it.field.clone().map(|v| json!(v))),
        ("command", it.command.map(|v| json!(v))),
        ("building", it.building.map(|v| json!(v))),
        ("button", it.button.map(|v| json!(v))),
        ("donor", it.donor.map(|v| json!(v))),
        ("class_id", it.class_id.map(|v| json!(v))),
        ("class_candidates", it.class_candidates.clone().map(|v| json!(v))),
        ("kind", it.attack_kind.clone().map(|v| json!(v))),
        ("type", it.group_type.clone().map(|v| json!(v))),
        ("techs", it.techs.clone().map(|v| json!(v))),
        ("civs", it.civs.clone().map(|v| json!(v))),
    ] {
        if let Some(v) = val {
            o.insert(key.to_string(), v);
        }
    }
    req
}

/// Which file the edit lands in, in the words the reference uses.
fn writes_of(it: &Intent) -> &'static str {
    match it.intent.as_str() {
        "tech.toggle_group" => "resources/_common/dat/linkedTechs.json",
        "unit.sprite" => "resources/_common/drs/graphics/*.sld",
        _ => "resources/_common/dat/empires2_x2_p1.dat",
    }
}

/// What a clause would do, as the page's `preview.plan`.
///
/// Returns `(buildable, plan)`.  `buildable` is false for a plan the builder
/// refused AND for one it accepted but marked not editable -- both mean "pressing
/// 生成 would not give you this".
pub fn plan(server: &crate::server::Server, it: &Intent) -> (bool, Value) {
    let description = describe(it);
    let kind = kind_of(it);
    let req = request(it);
    let built = crate::stat_edit::build_one(server, &req);
    let report: Result<Value, String> = match &built {
        Ok(s) => serde_json::from_str(s)
            .map_err(|e| format!("构建器返回的不是 JSON（{e}）：{}", &s[..s.len().min(200)])),
        Err(e) => Err(e.clone()),
    };
    let report = match report {
        Ok(v) => v,
        Err(e) => {
            // The builder refused.  That is an answer, not a failure: the page
            // prints it under the sentence instead of a card full of numbers it
            // would not deliver.
            return (
                false,
                json!({
                    "description": description,
                    "kind": kind,
                    "editable": false,
                    "changes_dat": false,
                    "reason": e,
                    "writes": writes_of(it),
                    "shape": it.intent,
                }),
            );
        }
    };
    let num = |k: &str| report.get(k).and_then(|v| v.as_i64());
    let mut plan = json!({
        "description": description,
        "kind": kind,
        "editable": true,
        "changes_dat": true,
        "writes": writes_of(it),
        "shape": it.intent,
        // Which civilization the edit reaches.  `civ_labels` is what the page
        // prints; `civ_count` is the fallback when the server could not name them.
        "civs": it.civs.clone().unwrap_or_default(),
        "civ_count": num("civs").unwrap_or(0),
        "edit_count": num("edit_count").unwrap_or(0),
    });
    if let Some(c) = it.civs.as_ref() {
        let table = names();
        let labels: Vec<String> = c
            .iter()
            .map(|n| {
                table
                    .as_ref()
                    .and_then(|t| t.civ_label(n))
                    .unwrap_or_else(|| n.clone())
            })
            .collect();
        plan["civ_labels"] = json!(labels);
    }
    // Fields only some shapes have: `member_count` is a class edit's reach,
    // `mirror_count` says how much of the edit the game's damage code sees.
    for (from, to) in [
        ("mirror_count", "mirror_count"),
        ("variants", "variants"),
        ("records", "records"),
        ("locations", "locations"),
        ("before", "before"),
        ("value", "value"),
        ("bytes_changed", "bytes_changed"),
    ] {
        if let Some(v) = report.get(from) {
            plan[to] = v.clone();
        }
    }
    if let Some(m) = it.techs.as_ref() {
        plan["member_count"] = json!(m.len());
    }
    // The reference calls the numbers in a `description` "值"; keep the plan's
    // own before/after available because a preview that says "1,701 处改动"
    // without saying from what to what is only half an answer.
    (true, plan)
}

/// STAT_WORDS is public so the page can be told which words it understands; a
/// preview that cannot name the attribute is not usable.
pub fn known_stats() -> Vec<&'static str> {
    STAT_WORDS.iter().map(|(name, _w)| *name).collect()
}
