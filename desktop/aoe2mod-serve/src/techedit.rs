//! Technology edits: research time and cost slots.
//!
//! A technology is GLOBAL -- one record per tech id, not one per civilization --
//! so unlike a unit edit this is not 63 copies of one write.
//!
//! Two shapes that are easy to get wrong, both measured:
//!
//!  * For DE the research time is NOT a field of the tech record. The engine
//!    moved it into `research_locations[]` for `gv >= GV_C31`, and one tech can
//!    carry SEVERAL locations. Writing one entry leaves the tech with a stale
//!    time in the copies that were not touched, which reads in game as "the
//!    research finished at the old speed".
//!  * A cost is three slots of `(type, amount, flag)`, and an EMPTY slot is a
//!    real, load-bearing thing: `(-1, 0, 0)` is the sentinel and `(0, 0, 0)` is
//!    legal. So the caller names the SLOT, and no slot is ever inferred.

use serde_json::Value;
use std::path::Path;

pub struct TechTable {
    /// `tech id -> { "research_time": [abs offsets], "cost": { slot: offset } }`
    pub techs: std::collections::HashMap<i16, Value>,
}

impl TechTable {
    pub fn load(path: &Path) -> std::io::Result<TechTable> {
        let text = std::fs::read_to_string(path)?;
        let v: Value = serde_json::from_str(text.trim_start_matches('\u{feff}'))
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        let mut techs = std::collections::HashMap::new();
        if let Some(obj) = v.get("techs").and_then(|x| x.as_object()) {
            for (k, val) in obj {
                if let Ok(id) = k.parse::<i16>() {
                    techs.insert(id, val.clone());
                }
            }
        }
        Ok(TechTable { techs })
    }

    /// Every absolute offset that carries this tech's research time.
    pub fn research_time_offsets(&self, tech: i16) -> Vec<usize> {
        self.techs
            .get(&tech)
            .and_then(|v| v.get("research_time"))
            .and_then(|v| v.as_array())
            .map(|a| {
                a.iter()
                    .filter_map(|x| x.as_u64().map(|n| n as usize))
                    .collect()
            })
            .unwrap_or_default()
    }

    /// The absolute offset of the slot whose `type` is `resource_type`.
    ///
    /// By TYPE, not by position. A tech's three cost slots are not a fixed
    /// food/wood/gold/stone order: each carries its own `type`, they arrive in
    /// whatever order the record chose, and an unused one is `type -1`. Writing
    /// by position put Loom's gold into an EMPTY slot and produced `(-1, 5, 0)`
    /// -- an amount on a slot that declares no resource, which the game never
    /// writes and which showed up in the artefact as a cost that changed and a
    /// price that did not.
    pub fn cost_offset(&self, tech: i16, resource_type: i32) -> Option<usize> {
        let slots = self.techs.get(&tech)?.get("cost_slots")?.as_array()?;
        for s in slots {
            if s.get("type").and_then(|v| v.as_i64()) == Some(resource_type as i64) {
                return s.get("offset").and_then(|v| v.as_u64()).map(|n| n as usize);
            }
        }
        None
    }

    /// The resource type id the game uses in a cost slot.
    pub fn resource_type_id(name: &str) -> Option<i32> {
        Some(match name {
            "food" => 0,
            "wood" => 1,
            "stone" => 2,
            "gold" => 3,
            _ => return None,
        })
    }
}

/// Where `tech_offsets.json` lives: first candidate that exists.
pub fn table_path() -> std::path::PathBuf {
    for p in crate::sentences::table_paths("AOE2MOD_TECH_OFFSETS", "tech_offsets.json") {
        if p.is_file() {
            return p;
        }
    }
    std::path::PathBuf::from("_golden/tech_offsets.json")
}
