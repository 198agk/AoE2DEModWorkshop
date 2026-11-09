//! `tech.toggle_group`: make several technologies mutually exclusive.
//!
//! The engine's rule lives in `resources/_common/dat/linkedTechs.json`, not in
//! the `.dat`: an entry with `Type: "MutuallyExclusive"` and a `Techs` list means
//! researching one greys out the rest. Measured on this install: the factory file
//! has 20 entries, and adding `{NameId: 424021, Type: "MutuallyExclusive",
//! Techs: [22, 23]}` is the whole edit (Loom + Coinage).
//!
//! This file is ONLY the label.  The mechanism -- the `type 102` ban commands in
//! each member's own effect record -- is in `crate::groupdat`, and for
//! `MutuallyExclusive`/`Toggleable` the label alone does nothing on screen
//! (measured in game 2026-10-22: the user researched Forging and read 「不变灰」,
//! then 「研究后依旧能接着研究第二个」).  The `.dat` is still always shipped even
//! when it is a byte copy of the factory one, because a mod writing under
//! `resources/_common/dat/` without one makes the game fail to start: the DAT
//! storage point is resolved as a unit, not per file.
//!
//! What this refuses
//! -----------------
//! A group of fewer than two technologies (nothing to be exclusive with), and a
//! technology id that does not exist. Both would produce a file the game loads
//! and ignores, which reads on screen as "it worked".

use serde_json::{json, Value};
use std::path::Path;

/// The next `NameId` the factory file has not used.
///
/// The factory ids run 424001..424020; a new entry takes one past the highest so
/// two mods adding a group do not collide.
pub fn next_name_id(doc: &Value) -> i64 {
    let mut hi = 424000i64;
    if let Some(arr) = doc.get("LinkedTechs").and_then(|v| v.as_array()) {
        for e in arr {
            if let Some(n) = e.get("NameId").and_then(|v| v.as_i64()) {
                if n > hi {
                    hi = n;
                }
            }
        }
    }
    hi + 1
}

/// Append one `MutuallyExclusive` entry. Returns the entry that was added.
pub fn add_group(doc: &mut Value, techs: &[i16]) -> Result<Value, String> {
    if techs.len() < 2 {
        return Err("互斥至少要两项科技：只有一项没有可以互斥的对象。".into());
    }
    let mut clean: Vec<i64> = Vec::new();
    for t in techs {
        if *t < 0 {
            return Err(format!("科技编号 {t} 不存在"));
        }
        if !clean.contains(&(*t as i64)) {
            clean.push(*t as i64);
        }
    }
    if clean.len() < 2 {
        return Err("互斥至少要两项不同的科技。".into());
    }
    // Compute the id BEFORE taking the mutable borrow: it reads the same array.
    let id = next_name_id(doc);
    let arr = doc
        .get_mut("LinkedTechs")
        .and_then(|v| v.as_array_mut())
        .ok_or("linkedTechs.json 里没有 LinkedTechs 数组")?;
    // Already exclusive? Say so instead of appending a duplicate -- two entries
    // naming the same pair is a state the factory file never contains.
    for e in arr.iter() {
        if e.get("Type").and_then(|v| v.as_str()) != Some("MutuallyExclusive") {
            continue;
        }
        let listed: Vec<i64> = e
            .get("Techs")
            .and_then(|v| v.as_array())
            .map(|a| a.iter().filter_map(|x| x.as_i64()).collect())
            .unwrap_or_default();
        if clean.iter().all(|c| listed.contains(c)) {
            return Err(format!(
                "这几项科技已经是互斥的了（{listed:?}），再写一遍不会有变化"
            ));
        }
    }
    let entry = json!({
        "NameId": id,
        "Comment": "",
        "Local": true,
        "Type": "MutuallyExclusive",
        "Techs": clean,
    });
    arr.push(entry.clone());
    Ok(entry)
}

/// Load the factory file, apply the group, and write the mod's copy.
pub fn build(
    game_dat_dir: &Path,
    out_dir: &Path,
    techs: &[i16],
) -> Result<(Value, usize), String> {
    let src = game_dat_dir.join("linkedTechs.json");
    let text = std::fs::read_to_string(&src)
        .map_err(|e| format!("读不到 {}：{e}", src.display()))?;
    let mut doc: Value = serde_json::from_str(text.trim_start_matches('\u{feff}'))
        .map_err(|e| format!("{} 不是合法 JSON：{e}", src.display()))?;
    let entry = add_group(&mut doc, techs)?;
    let target = out_dir.join("resources/_common/dat/linkedTechs.json");
    if let Some(parent) = target.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let body = serde_json::to_string_pretty(&doc).map_err(|e| e.to_string())?;
    std::fs::write(&target, body).map_err(|e| e.to_string())?;
    let n = doc
        .get("LinkedTechs")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    Ok((entry, n))
}
