//! `/api/describe`: everything a screen shows about one entity.
//!
//! The honesty rule this follows
//! ----------------------------
//! `prose` reports its GAPS, not just its hits. This build ships no unit
//! descriptions at all -- the game's string table has no help text for units in
//! either language -- and a screen that renders an empty box where a description
//! belongs looks like a bug in this product rather than a fact about the game.
//! So the refusal says exactly that.
//!
//! The stat list comes from the offset table, which is measured by the parser.
//! Presenting a value the table does not hold would be inventing one; a field a
//! record does not carry is omitted rather than defaulted.

use serde_json::{json, Value};
use std::path::Path;

use crate::stats::StatKind;

/// What one entity is, and the numbers an edit can reach.
pub fn describe(
    parsed: &crate::server::ParseResult,
    stat_table: &crate::stats::StatTable,
    raw: &[u8],
    names_doc: &Value,
    kind: &str,
    entity_id: i16,
) -> Result<Value, String> {
    let key = if kind == "tech" { "techs" } else { "units" };
    let names = names_doc
        .get(key)
        .and_then(|v| v.get(entity_id.to_string()))
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    if names.is_empty() {
        return Err(format!(
            "找不到编号 {} 的{}",
            entity_id,
            if kind == "tech" { "科技" } else { "单位" }
        ));
    }
    let display = names
        .first()
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let en = names
        .iter()
        .find(|v| {
            v.as_str()
                .map(|s| s.chars().all(|c| !('\u{4e00}'..='\u{9fff}').contains(&c)))
                .unwrap_or(false)
        })
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let mut stats = serde_json::Map::new();
    // Values are read from the raw stream at the offsets `locate` measured, for
    // civ 0 (Gaia). A field the record does not carry is simply absent.
    for (stat, _kind) in stat_table.kinds.clone() {
        if let Some(off) = stat_table.offset(0, &stat, entity_id) {
            let k = *stat_table.kinds.get(&stat).unwrap_or(&StatKind::I16);
            if let Some(v) = read_at(raw, off, k) {
                stats.insert(stat, json!(v));
            }
        }
    }

    Ok(json!({
        "id": entity_id,
        "kind": if kind == "tech" { "tech" } else { "unit" },
        "name": display,
        "en": en,
        "zh": display,
        "resolved": true,
        "civ_variants": Value::Null,
        "civ_count": parsed.civs.len(),
        "record_count": 1,
        // Reported with its reason rather than as an empty object: the game has
        // no unit help text in either language, and an empty box would read as a
        // bug in this tool.
        "prose": {
            "ok": false,
            "fields": {},
            "missing": {},
            "why": "这个版本没有单位描述：游戏的字符串表里没有单位帮助文本（英文和中文都是空的，不是缺翻译）"
        },
        "stats": Value::Object(stats),
    }))
}

fn read_at(buf: &[u8], off: usize, kind: StatKind) -> Option<f64> {
    match kind {
        StatKind::I16 if off + 2 <= buf.len() => {
            Some(i16::from_le_bytes([buf[off], buf[off + 1]]) as f64)
        }
        StatKind::U8 if off < buf.len() => Some(buf[off] as f64),
        StatKind::F32 if off + 4 <= buf.len() => Some(f32::from_le_bytes([
            buf[off],
            buf[off + 1],
            buf[off + 2],
            buf[off + 3],
        ]) as f64),
        _ => None,
    }
}

/// Locate `_golden/entity_names.json` by walking up, same as the grammar table.
pub fn entity_names() -> Value {
    let mut roots: Vec<std::path::PathBuf> = Vec::new();
    if let Ok(cwd) = std::env::current_dir() {
        let mut p = Some(cwd);
        while let Some(d) = p {
            roots.push(d.clone());
            p = d.parent().map(|x| x.to_path_buf());
        }
    }
    for root in roots {
        let path = root.join("_golden/entity_names.json");
        if let Ok(t) = std::fs::read_to_string(&path) {
            if let Ok(v) = serde_json::from_str::<Value>(&t) {
                return v;
            }
        }
    }
    json!({"units": {}, "techs": {}})
}

/// Kept for symmetry with the other loaders.
pub fn _load(path: &Path) -> Option<Value> {
    std::fs::read_to_string(path)
        .ok()
        .and_then(|t| serde_json::from_str(&t).ok())
}
