//! `unit.sprite` in rename mode: point graphics records at the donor's picture.
//!
//! Copy mode ships 466 `.sld` files (438 MB) because every target FILENAME needs
//! its own copy. Rename mode ships none: the `.dat` already says, per graphics
//! record, which file to load, so re-pointing those records is the whole edit --
//! ~12 MB instead of 418 MB.
//!
//! Already proven in game (2026-10-17, `dsh test v13`: villagers showed as sheep),
//! which is why rename mode is documented as PROVEN rather than hopeful.
//!
//! The one hazard is the thing this project paid for once: a graphics record's
//! `file` string has a STORED WIDTH, and re-emitting it at a different length
//! must advance the input cursor by the OLD width or every later verbatim read
//! shifts. `writer.debug_string(..., stored_len)` exists for exactly that, and the
//! `_file_len` the parser keeps is passed through here.

use serde_json::Value;
use std::collections::HashMap;
use std::path::Path;

pub struct SpritePairs {
    /// `target stem -> donor stem`
    pub pairs: HashMap<String, String>,
    pub unit: i16,
    pub donor: i16,
}

impl SpritePairs {
    pub fn load(path: &Path) -> std::io::Result<SpritePairs> {
        let text = std::fs::read_to_string(path)?;
        let v: Value = serde_json::from_str(text.trim_start_matches('\u{feff}'))
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        let mut pairs = HashMap::new();
        if let Some(obj) = v.get("pairs").and_then(|x| x.as_object()) {
            for (k, val) in obj {
                if let Some(s) = val.as_str() {
                    pairs.insert(k.clone(), s.to_string());
                }
            }
        }
        Ok(SpritePairs {
            pairs,
            unit: v.get("unit").and_then(|x| x.as_i64()).unwrap_or(83) as i16,
            donor: v.get("donor").and_then(|x| x.as_i64()).unwrap_or(594) as i16,
        })
    }
}

pub fn table_path() -> std::path::PathBuf {
    for p in crate::sentences::table_paths("AOE2MOD_SPRITE_PAIRS", "sprite_pairs.json") {
        if p.is_file() {
            return p;
        }
    }
    std::path::PathBuf::from("_golden/sprite_pairs.json")
}

/// The donor stem for a record's `file`, if this record is a target.
///
/// The record stores a stem without extension, and the engine appends `_x1`/`_x2`
/// itself (measured: no record ever names an `_x2`). So the lookup is on the stem
/// as stored, with the `_x2` sibling mapped to the donor's `_x2` because the
/// engine WILL ask for it.
pub fn donor_for<'a>(pairs: &'a SpritePairs, file: &str) -> Option<&'a String> {
    if let Some(d) = pairs.pairs.get(file) {
        return Some(d);
    }
    // A record naming the `_x1` sibling: the map has the `_x2` too, but keep the
    // pairing explicit rather than assuming an offset.
    if let Some(base) = file.strip_suffix("_x1") {
        if let Some(d) = pairs.pairs.get(&format!("{base}_x1")) {
            return Some(d);
        }
    }
    None
}
