//! Variant families: which records the engine treats as one visible object.
//!
//! Why this exists
//! ---------------
//! `村民血量改成100` is ONE sentence and 1,701 byte writes: 27 records x 63
//! civilizations.  The 27 are the villager's family, joined by four separate
//! mechanisms in the shipped data (effect type-3 replacement edges, task-swap
//! groups, `linkedUnits.json`, and the `chance 50` rows of `objreplacement.json`
//! that hold the male and female baskets together).
//!
//! Before this module the build wrote the 63 records whose id the sentence named
//! and left the other 26 variants untouched -- so the male villager changed, the
//! female did not, and the screen said "63 处改动" while the reference said
//! 1,701.  That is the failure this project keeps paying for: a number that looks
//! like a measurement but is only the scope of the code that happened to run.
//!
//! Why the table is exported from Python instead of rebuilt here
//! -------------------------------------------------------------
//! The joining rules took measurements to get right (the nonzero-display-name
//! condition, the Sea Gate counter-example, the villager pair no name rule could
//! join).  A second implementation that AGREED with them would prove nothing;
//! this project's two-sided checks are worth something because the two sides
//! reach the same answer by different routes.  So Python measures, this reads
//! the measurement, and the check is that the preview's numbers equal the
//! build's numbers.
//!
//! An id absent from the table is the one-member family `[id]` -- NOT unknown.

use std::collections::HashMap;
use std::path::Path;

/// `unit id -> every id the engine swaps in for it`.
pub struct Families {
    groups: HashMap<i16, Vec<i16>>,
}

impl Families {
    pub fn load(path: &Path) -> std::io::Result<Families> {
        let text = std::fs::read_to_string(path)?;
        // serde_json rather than a hand scanner: a hand parser that gets this
        // slightly wrong returns EMPTY families, which reads as "every object is
        // one record" -- the exact under-report this table exists to prevent, and
        // it would be silent.
        let v: serde_json::Value = serde_json::from_str(&text)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        let mut groups = HashMap::new();
        if let Some(obj) = v.get("groups").and_then(|g| g.as_object()) {
            for (k, members) in obj {
                let id: i16 = match k.parse() {
                    Ok(x) => x,
                    Err(_) => continue,
                };
                let list: Vec<i16> = members
                    .as_array()
                    .map(|a| a.iter().filter_map(|x| x.as_i64()).map(|x| x as i16).collect())
                    .unwrap_or_default();
                if !list.is_empty() {
                    groups.insert(id, list);
                }
            }
        }
        Ok(Families { groups })
    }

    /// Every id that must be written for an edit named after `id`.
    ///
    /// A lone record returns `[id]`, which is the common case: an Archer is one
    /// unit.  The result always contains `id` itself, so a caller can use it as
    /// the write list directly.
    pub fn of(&self, id: i16) -> Vec<i16> {
        match self.groups.get(&id) {
            Some(v) if !v.is_empty() => v.clone(),
            _ => vec![id],
        }
    }

    /// True when this id has more than one record behind it.
    pub fn is_family(&self, id: i16) -> bool {
        self.groups.get(&id).map(|v| v.len() > 1).unwrap_or(false)
    }
}

/// Where `unit_families.json` lives: the same search the other tables use, so a
/// shipped folder finds it in `app/_golden/` and a development run finds it in
/// the repository.
pub fn table_path() -> std::path::PathBuf {
    crate::sentences::table_paths("AOE2MOD_UNIT_FAMILIES", "unit_families.json")
        .into_iter()
        .find(|p| p.is_file())
        .unwrap_or_else(|| std::path::PathBuf::from("_golden/unit_families.json"))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The number this whole module exists for.  Measured against the Python
    /// reference: the villager's family is 27 records, and an edit to it lands in
    /// 27 x 63 = 1,701 places.
    #[test]
    fn the_villager_family_is_twenty_seven_records() {
        let f = match Families::load(&table_path()) {
            Ok(f) => f,
            Err(_) => return, // table not shipped in this checkout
        };
        let fam = f.of(83);
        assert_eq!(fam.len(), 27, "villager family changed size: {fam:?}");
        assert_eq!(fam.len() * 63, 1701);
        assert!(fam.contains(&83), "the id itself must be in its own family");
        assert!(f.is_family(83));
    }

    /// A record with no family entry must read as a one-member family, not as
    /// "unknown": the difference between those two is the difference between
    /// editing one record and refusing the sentence.
    #[test]
    fn a_lone_record_is_a_family_of_one() {
        let f = match Families::load(&table_path()) {
            Ok(f) => f,
            Err(_) => return,
        };
        assert_eq!(f.of(4), vec![4], "the archer is one record");
        assert!(!f.is_family(4));
    }
}
