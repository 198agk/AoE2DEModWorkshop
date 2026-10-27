//! `/api/civ`: what one civilisation can actually build, and why.
//!
//! This is the "narrowing" layer `cards.rs` says it does not answer. Without it
//! the card route reports the `.dat` superset -- Barracks lists 49 units -- and
//! a player asking "can I train a Hand Cannoneer as the Britons?" gets "here are
//! 49 units", which is not an answer.
//!
//! Where the answer lives
//! ----------------------
//! Not in the `.dat`. Measured: 63 civilisations, 2 distinct unit records per
//! unit, 0 differing fields, and only 7 effects in the whole file touch
//! per-civ availability. Hand Cannoneer is 23 civilisations available / 38 not,
//! and no `.dat` field carries that split.
//!
//! The game ships it in `resources/_common/dat/CivTechTrees/<CIV>.json`, one
//! file per civilisation, with a `Node Status` per node:
//!
//!   ResearchedCompleted  available from the start of the match
//!   ResearchRequired     available, but gated behind a technology
//!   NotAvailable         this civilisation cannot have it
//!
//! Three things this module refuses to paper over:
//!
//!   1. `Node ID` is not a global id space. `Use Type` says which one it is:
//!      `Unit` -> unit ids, `Tech` -> tech ids, `Building` -> building ids.
//!      `civ_techs_units` holds all three kinds, and node 93 is Spearman in one
//!      row and Ballistics in another. Looking a unit id up among all rows
//!      returns "Ballistics" for Spearman -- a wrong answer with a plausible
//!      name on it, which is the worst shape a wrong answer takes.
//!   2. The key is `(use, node, building)`. The same unit is listed under several
//!      buildings: MAPUCHE lists Skirmisher under 87 and 2556, BULGARIANS lists
//!      Petard under 82 and 1251. Keying without the building drops 8 rows.
//!   3. "Not in the tree" is not "not available". A missing row means this file
//!      does not describe the node, and the caller must be told `unknown` rather
//!      than be given a confident `no`.

use serde_json::{json, Value};
use std::collections::HashMap;
use std::path::Path;

/// A civilisation's tree: `use letter -> node id -> rows`.
///
/// Rows are `[building id, status letter, age id]`, in the order the file lists
/// them. Order matters because the game draws them in it.
pub struct CivTrees {
    pub civs: HashMap<String, HashMap<String, HashMap<String, Vec<Value>>>>,
    pub status_legend: HashMap<String, String>,
}

impl CivTrees {
    pub fn load(path: &Path) -> std::io::Result<CivTrees> {
        let text = std::fs::read_to_string(path)?;
        let text = text.trim_start_matches('\u{feff}');
        let v: Value = serde_json::from_str(text)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        let mut civs = HashMap::new();
        if let Some(obj) = v.get("civs").and_then(|x| x.as_object()) {
            for (civ, table) in obj {
                let mut per_use: HashMap<String, HashMap<String, Vec<Value>>> = HashMap::new();
                if let Some(t) = table.as_object() {
                    for (use_letter, nodes) in t {
                        let mut per_node = HashMap::new();
                        if let Some(n) = nodes.as_object() {
                            for (node, rows) in n {
                                if let Some(arr) = rows.as_array() {
                                    per_node.insert(node.clone(), arr.clone());
                                }
                            }
                        }
                        per_use.insert(use_letter.clone(), per_node);
                    }
                }
                civs.insert(civ.clone(), per_use);
            }
        }
        let mut legend = HashMap::new();
        if let Some(l) = v.get("status_legend").and_then(|x| x.as_object()) {
            for (k, val) in l {
                if let Some(s) = val.as_str() {
                    legend.insert(k.clone(), s.to_string());
                }
            }
        }
        Ok(CivTrees {
            civs,
            status_legend: legend,
        })
    }

    pub fn has(&self, civ: &str) -> bool {
        self.civs.contains_key(civ)
    }

    /// Civilisation names in file order is not preserved by a HashMap; sorted is
    /// the right order for a picker, and callers render a picker.
    pub fn civ_names(&self) -> Vec<String> {
        let mut v: Vec<String> = self.civs.keys().cloned().collect();
        v.sort();
        v
    }

    /// Every row for one node in one civilisation, across all buildings.
    ///
    /// Returns `None` when the civilisation is not in the table at all, which
    /// the caller must distinguish from `Some(vec![])` -- the first means "this
    /// file has never heard of the civ", the second "the civ has no row here".
    fn rows(&self, civ: &str, use_letter: &str, node: i64) -> Option<Vec<Value>> {
        let table = self.civs.get(civ)?;
        let nodes = table.get(use_letter);
        match nodes.and_then(|n| n.get(&node.to_string())) {
            Some(rows) => Some(rows.clone()),
            None => Some(Vec::new()),
        }
    }

    /// `available` / `gated` / `unavailable` / `unknown`.
    ///
    /// `unknown` is a real answer, not a fallback: a node the file does not
    /// describe is not a node the civilisation lacks.
    pub fn status(&self, civ: &str, use_letter: &str, node: i64) -> &'static str {
        match self.rows(civ, use_letter, node) {
            None => "unknown",
            Some(rows) if rows.is_empty() => "unknown",
            Some(rows) => {
                let mut best = "unavailable";
                for r in &rows {
                    match r.get(1).and_then(|v| v.as_str()) {
                        Some("C") => return "available",
                        Some("R") => best = "gated",
                        _ => {}
                    }
                }
                best
            }
        }
    }
}

pub fn table_path() -> std::path::PathBuf {
    for p in crate::sentences::table_paths("AOE2MOD_CIV_TREES", "civ_trees.json") {
        if p.is_file() {
            return p;
        }
    }
    std::path::PathBuf::from("_golden/civ_trees.json")
}

/// `/api/civ`: one civilisation's answer for a set of nodes, or its whole tree.
///
/// `units` / `techs` / `buildings` are the ids the caller cares about. Passing
/// none returns every row, which is what a "show me this civilisation" view
/// wants and what a per-unit question must not do (10,734 rows is not an answer
/// to "can I train this one unit").
pub fn civ(
    trees: &CivTrees,
    civ: &str,
    units: &[i64],
    techs: &[i64],
    buildings: &[i64],
    names: &Value,
) -> Value {
    if !trees.has(civ) {
        return json!({
            "ok": false,
            "error": format!("没有这个文明：{civ}"),
            "known": trees.civ_names(),
        });
    }
    let wanted = (units.is_empty() && techs.is_empty() && buildings.is_empty()) == false;

    let mut answers: Vec<Value> = Vec::new();
    let push = |use_letter: &str, ids: &[i64], kind: &str, answers: &mut Vec<Value>| {
        for id in ids {
            let status = trees.status(civ, use_letter, *id);
            let rows = trees.rows(civ, use_letter, *id).unwrap_or_default();
            let buildings_of: Vec<Value> = rows
                .iter()
                .map(|r| {
                    json!({
                        "building": r.get(0).cloned().unwrap_or(Value::Null),
                        "status": r.get(1).cloned().unwrap_or(Value::Null),
                        "age": r.get(2).cloned().unwrap_or(Value::Null),
                    })
                })
                .collect();
            let name = names
                .get(kind_key(kind))
                .and_then(|m| m.get(id.to_string()))
                .and_then(|v| v.as_array())
                .and_then(|a| a.first())
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            answers.push(json!({
                "kind": kind,
                "id": id,
                "name": name,
                "status": status,
                "rows": buildings_of,
            }));
        }
    };
    push("u", units, "unit", &mut answers);
    push("t", techs, "tech", &mut answers);
    push("b", buildings, "building", &mut answers);

    let mut body = json!({
        "ok": true,
        "civ": civ,
        "asked": if wanted { "some" } else { "everything" },
        "answers": answers,
        "note": "状态来自游戏自己的 CivTechTrees/<CIV>.json；available 开局就有，\
                 gated 要先研究科技，unavailable 这个文明没有，unknown 这个文件不描述它",
    });

    if !wanted {
        // Whole-tree shape, kept separate so a per-unit caller is never handed
        // 10,734 rows by accident.
        if let Some(table) = trees.civs.get(civ) {
            let mut dump = serde_json::Map::new();
            for (use_letter, nodes) in table {
                dump.insert(use_letter.clone(), json!(nodes));
            }
            body["tree"] = Value::Object(dump);
        }
    }
    body
}

fn kind_key(kind: &str) -> &'static str {
    match kind {
        "tech" => "techs",
        "building" => "units",
        _ => "units",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn trees() -> CivTrees {
        // A hand-made table: two civs, one unit listed under two buildings, one
        // gated tech, and one civ that does not describe the unit at all.
        let doc = json!({
            "status_legend": {"C": "ResearchedCompleted"},
            "civs": {
                "ALPHA": {
                    "u": {
                        "5": [[87, "R", 4]],
                        "7": [[87, "C", 2], [2556, "C", 2]],
                    },
                    "t": {"93": [[209, "C", 3]]},
                },
                "BETA": {"u": {}},
            }
        });
        let dir = std::env::temp_dir().join("aoe2mod_civ_test");
        std::fs::create_dir_all(&dir).unwrap();
        let p = dir.join("civ_trees.json");
        std::fs::write(&p, doc.to_string()).unwrap();
        CivTrees::load(&p).unwrap()
    }

    #[test]
    fn unit_and_tech_share_a_node_number_and_must_not_be_confused() {
        // Node 5 is a unit, node 93 is a tech. Reading them out of one bucket
        // would answer "Ballistics" for a Spearman question.
        let t = trees();
        assert_eq!(t.status("ALPHA", "u", 5), "gated");
        assert_eq!(t.status("ALPHA", "t", 93), "available");
        // Reading the unit 93 bucket, which this civ does not have, must not fall
        // back to the tech 93 row.
        assert_eq!(t.status("ALPHA", "u", 93), "unknown");
    }

    #[test]
    fn a_missing_row_is_unknown_not_unavailable() {
        // BETA describes no units. "This file does not say" is not "no".
        let t = trees();
        assert_eq!(t.status("BETA", "u", 5), "unknown");
        assert_eq!(t.status("GAMMA", "u", 5), "unknown");
    }

    #[test]
    fn one_node_under_two_buildings_keeps_both_rows() {
        let t = trees();
        let rows = t.rows("ALPHA", "u", 7).unwrap();
        assert_eq!(rows.len(), 2, "both buildings must survive");
        // Available if ANY row says so: the unit is trainable from that civ.
        assert_eq!(t.status("ALPHA", "u", 7), "available");
    }

    #[test]
    fn unknown_civ_lists_what_is_known() {
        let t = trees();
        let v = civ(&t, "NOPE", &[5], &[], &[], &json!({}));
        assert_eq!(v["ok"], false);
        let known: Vec<&str> = v["known"].as_array().unwrap().iter().filter_map(|x| x.as_str()).collect();
        assert!(known.contains(&"ALPHA"));
    }
}
