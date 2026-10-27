//! Unit-class names for `unit.attack_class`, and the bonus-row offsets.
//!
//! `nl._class_in` requires the class name to sit IMMEDIATELY AFTER 对, and that
//! position rule is load-bearing: matching a class name anywhere would fire on
//! "骑兵的血量改成1000", where the class is the ENTITY rather than the target of a
//! bonus. It also takes the longest name, so 攻城武器 does not lose to a prefix.
//!
//! The names come from `_golden/class_names.json`, exported from the reader
//! (`_probe/make_class_names.py`) rather than re-derived, because which words a
//! player uses for a class is the reader's knowledge, not the format's.

use std::collections::HashMap;
use std::sync::OnceLock;

/// `class id -> names`.
pub fn class_names() -> &'static HashMap<u32, Vec<String>> {
    static T: OnceLock<HashMap<u32, Vec<String>>> = OnceLock::new();
    T.get_or_init(|| {
        let mut out = HashMap::new();
        for p in crate::sentences::table_paths("AOE2MOD_CLASS_NAMES", "class_names.json") {
            let text = match std::fs::read_to_string(&p) {
                Ok(t) => t,
                Err(_) => continue,
            };
            let v: serde_json::Value = match serde_json::from_str(text.trim_start_matches('\u{feff}')) {
                Ok(v) => v,
                Err(_) => continue,
            };
            if let Some(obj) = v.as_object() {
                for (k, val) in obj {
                    let id: u32 = match k.parse() {
                        Ok(i) => i,
                        Err(_) => continue,
                    };
                    let names: Vec<String> = val
                        .as_array()
                        .map(|a| a.iter().filter_map(|x| x.as_str().map(|s| s.to_string())).collect())
                        .unwrap_or_default();
                    if !names.is_empty() {
                        out.insert(id, names);
                    }
                }
            }
            if !out.is_empty() {
                break;
            }
        }
        out
    })
}
