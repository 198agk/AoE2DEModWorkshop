//! `tech.effect`: write one field of one command inside a technology's effect.
//!
//! An effect is a debug string + i16 count + N commands of
//! `(u8 type, i16 a, i16 b, i16 c, f32 d)` = 11 bytes each.
//!
//! The two things this CANNOT do are as important as what it can:
//!
//!   * it cannot change the NAME or the COUNT of commands. Either changes the
//!     record's LENGTH, which shifts every following effect and invalidates
//!     `effect_id` everywhere -- the variable-width trap this project has paid
//!     for once already (991,273 mismatches from one 3-byte string).
//!   * it cannot add or remove a command, for the same reason.
//!
//! So a caller names an existing `(tech, command index, field)` and gets a
//! refusal for anything else.

use serde_json::Value;
use std::collections::HashMap;
use std::path::Path;

pub struct EffectTable {
    /// `effect index -> commands`, each command being `field -> absolute offset`.
    pub effects: HashMap<i32, Vec<HashMap<String, usize>>>,
}

impl EffectTable {
    pub fn load(path: &Path) -> std::io::Result<EffectTable> {
        let text = std::fs::read_to_string(path)?;
        let v: Value = serde_json::from_str(text.trim_start_matches('\u{feff}'))
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        let mut effects = HashMap::new();
        if let Some(obj) = v.get("effects").and_then(|x| x.as_object()) {
            for (k, val) in obj {
                let idx: i32 = match k.parse() {
                    Ok(i) => i,
                    Err(_) => continue,
                };
                let mut cmds = Vec::new();
                if let Some(arr) = val.get("commands").and_then(|x| x.as_array()) {
                    for c in arr {
                        let mut m = HashMap::new();
                        if let Some(fields) = c.as_object() {
                            for (fk, fv) in fields {
                                if let Some(off) = fv.as_u64() {
                                    m.insert(fk.clone(), off as usize);
                                }
                            }
                        }
                        cmds.push(m);
                    }
                }
                effects.insert(idx, cmds);
            }
        }
        Ok(EffectTable { effects })
    }

    pub fn command(&self, effect: i32, index: usize) -> Option<&HashMap<String, usize>> {
        self.effects.get(&effect)?.get(index)
    }
}

/// The width and interpretation of each command field.
///
/// `t` is the command TYPE and is a u8; the rest are two-byte / four-byte. A
/// caller that names `t` is changing what the command MEANS, which is legal and
/// sometimes intended -- but the response says which field moved so a wrong one
/// is visible.
pub fn field_kind(field: &str) -> Option<(&'static str, u8)> {
    Some(match field {
        "t" => ("u8", 1),
        "a" | "b" | "c" => ("i16", 2),
        "d" => ("f32", 4),
        _ => return None,
    })
}

pub fn table_path() -> std::path::PathBuf {
    for p in crate::sentences::table_paths("AOE2MOD_EFFECT_OFFSETS", "effect_offsets.json") {
        if p.is_file() {
            return p;
        }
    }
    std::path::PathBuf::from("_golden/effect_offsets.json")
}
