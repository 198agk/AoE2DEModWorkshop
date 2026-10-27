//! `unit.sprite` in RENAME mode: decide which records to re-point, then do it.
//!
//! The previous version walked one frozen pair table (villager -> sheep) no
//! matter what the sentence asked, so "让弓兵的样子换成长弓兵" moved the
//! villager's pictures.  The number in the preview was right and the bytes
//! belonged to somebody else -- the failure this project keeps paying for.
//!
//! The decision is the reference's (`aoe2mod/intent/retarget.py:plan` over
//! `aoe2mod/game/sprites.py:plan_swap` + `swap_files`):
//!
//!   for each civilization in scope, take that civilization's art for the target
//!   unit and for the donor unit; pair each target animation token with the donor
//!   animation token of the SAME NAME; a token the donor has no picture for keeps
//!   the shipped art (`fill=False`, which is what rename does) and is reported.
//!   Each pair yields the `_x1` name and its derived `_x2` sibling, because the
//!   engine asks for `_x2` in high resolution and a rename that covers only `_x1`
//!   would half-apply by resolution.
//!
//! The exported table (`_golden/sprite_art.json`) carries the DECISION INPUTS --
//! arts with their tokens and frame grids, and which art each unit uses in each
//! civilization -- not an answer.  The answer depends on the (target, donor) pair
//! the sentence names, so precomputing it would be 2,281 x 2,281 rows of mostly
//! identical data.

use serde_json::Value;
use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::Path;

/// One loose art: the animation token -> file stem map, plus frame grids.
pub struct Art {
    pub stem: String,
    /// `animation -> file stem` (the stem has no extension; the engine appends
    /// `_x1`/`_x2` itself for the two resolutions, so a record only ever names
    /// the `_x1` form -- measured: no record in the shipped data names `_x2`).
    pub tokens: BTreeMap<String, String>,
    /// `animation -> [[frames, directions]]` for the grid-mismatch report.
    pub grids: HashMap<String, Vec<Vec<i64>>>,
}

pub struct SpriteArt {
    /// `unit id -> [(civ index, art index)]`, in civilization order.
    pub units: HashMap<i16, Vec<(usize, usize)>>,
    pub arts: Vec<Art>,
    /// `civ index -> .dat name`, index-aligned with the `units` civ numbers.
    pub civ_names: Vec<String>,
}

/// The outcome of the decision, before any bytes move.
pub struct Retarget {
    /// `target file stem (no extension) -> donor file stem`.  Keys include the
    /// derived `_x2` siblings.
    pub want: BTreeMap<String, String>,
    /// Distinct art stems involved, for the description.
    pub target_stems: Vec<String>,
    pub donor_stems: Vec<String>,
    /// Civilizations that contributed at least one pair.
    pub civs: usize,
    /// Animation tokens the donor had no picture for: these keep the original
    /// art, and the user is told rather than left to find out in game.
    pub unmapped: Vec<(String, String)>,
    /// `animation, target grid, donor grid` where the frame layout differs.  Not
    /// a refusal: the engine plays the wrong rows silently, so it is a warning.
    pub grid_mismatches: Vec<(String, Vec<Vec<i64>>, Vec<Vec<i64>>)>,
}

impl SpriteArt {
    pub fn load(path: &Path) -> std::io::Result<SpriteArt> {
        let text = std::fs::read_to_string(path)?;
        let v: Value = serde_json::from_str(text.trim_start_matches('\u{feff}'))
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;

        let mut arts = Vec::new();
        if let Some(arr) = v.get("arts").and_then(|x| x.as_array()) {
            for a in arr {
                let mut tokens = BTreeMap::new();
                if let Some(t) = a.get("tokens").and_then(|x| x.as_object()) {
                    for (k, val) in t {
                        if let Some(s) = val.as_str() {
                            tokens.insert(k.clone(), s.to_string());
                        }
                    }
                }
                let mut grids = HashMap::new();
                if let Some(g) = a.get("grids").and_then(|x| x.as_object()) {
                    for (k, val) in g {
                        if let Some(rows) = val.as_array() {
                            let rows: Vec<Vec<i64>> = rows
                                .iter()
                                .filter_map(|r| {
                                    r.as_array().map(|rr| {
                                        rr.iter().filter_map(|n| n.as_i64()).collect::<Vec<i64>>()
                                    })
                                })
                                .collect();
                            grids.insert(k.clone(), rows);
                        }
                    }
                }
                arts.push(Art {
                    stem: a
                        .get("stem")
                        .and_then(|x| x.as_str())
                        .unwrap_or_default()
                        .to_string(),
                    tokens,
                    grids,
                });
            }
        }

        // `units[id]` is a FLAT list `[civ, art, civ, art, ...]`.  Reading it as
        // pairs rather than as two parallel arrays is what the exporter wrote, so
        // an odd length means the table is damaged and must say so.
        let mut units = HashMap::new();
        if let Some(obj) = v.get("units").and_then(|x| x.as_object()) {
            for (k, val) in obj {
                let Ok(id) = k.parse::<i16>() else { continue };
                let Some(flat) = val.as_array() else { continue };
                if flat.len() % 2 != 0 {
                    return Err(std::io::Error::new(
                        std::io::ErrorKind::InvalidData,
                        format!("sprite_art.json 里第 {id} 号单位的 civ/art 列表长度是奇数"),
                    ));
                }
                let mut per = Vec::with_capacity(flat.len() / 2);
                for pair in flat.chunks(2) {
                    let (Some(c), Some(a)) = (pair[0].as_u64(), pair[1].as_u64()) else {
                        continue;
                    };
                    per.push((c as usize, a as usize));
                }
                units.insert(id, per);
            }
        }

        let mut civ_names = Vec::new();
        if let Some(arr) = v.get("civ_names").and_then(|x| x.as_array()) {
            for n in arr {
                civ_names.push(n.as_str().unwrap_or_default().to_string());
            }
        }

        Ok(SpriteArt {
            units,
            arts,
            civ_names,
        })
    }

    fn art_of(&self, unit: i16, civ: usize) -> Option<&Art> {
        let per = self.units.get(&unit)?;
        let idx = per.iter().find(|(c, _a)| *c == civ).map(|(_c, a)| *a)?;
        self.arts.get(idx)
    }

    /// Which civilizations to walk.  `wanted` holds the `.dat` spellings the
    /// sentence named; empty or absent means every civilization.
    fn civs_in_scope(&self, wanted: &Option<Vec<String>>) -> Vec<usize> {
        let all: Vec<usize> = (0..self.civ_names.len()).collect();
        let Some(names) = wanted.as_ref() else {
            return all;
        };
        if names.is_empty() {
            return all;
        }
        all.into_iter()
            .filter(|i| {
                let n = self.civ_names.get(*i).map(|s| s.as_str()).unwrap_or("");
                names.iter().any(|w| w.eq_ignore_ascii_case(n))
            })
            .collect()
    }

    /// Decide the rename for one (target, donor) pair.
    ///
    /// The refusals are the ones a person can act on, in the reference's words:
    /// one target name wanted by two donors (a record holds one filename), a
    /// donor picture missing from disk, and no record naming any target (the
    /// rename would be a no-op dressed as a success).
    pub fn plan(
        &self,
        target: i16,
        donor: i16,
        wanted: &Option<Vec<String>>,
        graphics_dir: Option<&Path>,
    ) -> Result<Retarget, String> {
        let scope = self.civs_in_scope(wanted);
        let mut want: BTreeMap<String, String> = BTreeMap::new();
        let mut clash: BTreeMap<String, HashSet<String>> = BTreeMap::new();
        let mut target_stems: Vec<String> = Vec::new();
        let mut donor_stems: Vec<String> = Vec::new();
        let mut unmapped: Vec<(String, String)> = Vec::new();
        let mut grids: Vec<(String, Vec<Vec<i64>>, Vec<Vec<i64>>)> = Vec::new();
        let mut civs_hit: HashSet<usize> = HashSet::new();
        let mut reasons: Vec<String> = Vec::new();

        for civ in scope {
            let (Some(ta), Some(da)) = (self.art_of(target, civ), self.art_of(donor, civ)) else {
                push_once(
                    &mut reasons,
                    format!(
                        "第 {civ} 个文明没有第 {target} 号或第 {donor} 号单位的散图"
                    ),
                );
                continue;
            };
            push_once(&mut target_stems, ta.stem.clone());
            push_once(&mut donor_stems, da.stem.clone());

            // plan_swap with `fill=false`: same-named animation token only.  A
            // stand-in from a nearby animation is a decision the caller has to
            // ask for, and rename never does -- the villager's "carry" picture is
            // exactly the one no donor supplies.
            let mut pairs: Vec<(String, String)> = Vec::new();
            for (token, tfile) in ta.tokens.iter() {
                match da.tokens.get(token) {
                    Some(dfile) => pairs.push((tfile.clone(), dfile.clone())),
                    None => push_once(&mut unmapped, (token.clone(), tfile.clone())),
                }
            }
            if pairs.is_empty() {
                push_once(
                    &mut reasons,
                    format!(
                        "「{}」和「{}」没有一个同名的动画，改名无从下手",
                        ta.stem, da.stem
                    ),
                );
                continue;
            }
            // The grid report is per ANIMATION, not per civilization: 57
            // civilizations share one set of art, so keying on the civ would say
            // the same thing 57 times and bury it.
            for (token, tfile) in ta.tokens.iter() {
                if !da.tokens.contains_key(token) {
                    continue;
                }
                let _ = tfile;
                let (Some(g1), Some(g2)) = (ta.grids.get(token), da.grids.get(token)) else {
                    continue;
                };
                if g1 != g2
                    && !grids
                        .iter()
                        .any(|(a, x, y)| a == token && x == g1 && y == g2)
                {
                    grids.push((token.clone(), g1.clone(), g2.clone()));
                }
            }

            civs_hit.insert(civ);
            // `swap_files`: both resolutions.  The `_x2` name is derived from the
            // `_x1` name, never stored, so the sibling is added here rather than
            // looked up.
            for (tn, dn) in pairs {
                for (t, d) in siblings(&tn, &dn) {
                    match want.get(&t) {
                        Some(existing) if existing != &d => {
                            clash.entry(t.clone()).or_default().insert(existing.clone());
                            clash.entry(t).or_default().insert(d);
                        }
                        _ => {
                            want.insert(t, d);
                        }
                    }
                }
            }
        }

        if !clash.is_empty() {
            let name = clash.keys().next().cloned().unwrap_or_default();
            let mut donors: Vec<String> = clash[&name].iter().cloned().collect();
            donors.sort();
            return Err(format!(
                "两个文明需要 {name}.sld 这个文件显示不同的图（{}），而一条记录只能写一个文件名",
                donors.join(" 与 ")
            ));
        }
        if want.is_empty() {
            let mut distinct: Vec<String> = Vec::new();
            for r in reasons {
                push_once(&mut distinct, r);
            }
            return Err(if distinct.is_empty() {
                "没有任何文明能把这两个单位配成同一个文件：没有可复制的图".to_string()
            } else {
                format!(
                    "没有任何文明能把这两个单位配成同一个文件：{}",
                    distinct.join("；")
                )
            });
        }

        // A donor picture that is not on disk would be a reference to nothing.
        // Checked, not assumed -- the reference does the same and refuses.
        if let Some(dir) = graphics_dir {
            let mut absent: Vec<String> = want
                .values()
                .filter(|d| !dir.join(format!("{d}.sld")).is_file())
                .cloned()
                .collect();
            absent.sort();
            absent.dedup();
            if !absent.is_empty() {
                return Err(format!(
                    "这次改名要指到的 {} 张捐赠方图片不在盘上，第一张是 {}.sld",
                    absent.len(),
                    absent[0]
                ));
            }
        }

        Ok(Retarget {
            want,
            target_stems,
            donor_stems,
            civs: civs_hit.len(),
            unmapped,
            grid_mismatches: grids,
        })
    }
}

/// The `_x1` pair plus its derived `_x2` sibling.
fn siblings(target: &str, donor: &str) -> Vec<(String, String)> {
    let mut out = vec![(target.to_string(), donor.to_string())];
    if let (Some(t), Some(d)) = (target.strip_suffix("_x1"), donor.strip_suffix("_x1")) {
        out.push((format!("{t}_x2"), format!("{d}_x2")));
    }
    out
}

fn push_once<T: PartialEq>(v: &mut Vec<T>, item: T) {
    if !v.contains(&item) {
        v.push(item);
    }
}

pub fn table_path() -> std::path::PathBuf {
    for p in crate::sentences::table_paths("AOE2MOD_SPRITE_ART", "sprite_art.json") {
        if p.is_file() {
            return p;
        }
    }
    std::path::PathBuf::from("_golden/sprite_art.json")
}

/// `civ index -> .dat name`, for the civilization scope.
///
/// The art table carries its own index-aligned name list because the civ index
/// in `units` is a position in `civs`, not an id the rest of the program has a
/// table for.
pub fn civ_names_of(table: &SpriteArt) -> Vec<String> {
    table.civ_names.clone()
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The `_x2` sibling is DERIVED: a record only ever names `_x1`, and a
    /// rename covering only `_x1` would half-apply by resolution -- the failure
    /// the reference's `swap_files` documents at length.
    #[test]
    fn the_high_resolution_sibling_is_derived_not_looked_up() {
        let got = siblings("u_arc_archer_idleA_x1", "u_arc_longbowman_idleA_x1");
        assert_eq!(got.len(), 2);
        assert_eq!(got[1].0, "u_arc_archer_idleA_x2");
        assert_eq!(got[1].1, "u_arc_longbowman_idleA_x2");
        // An already-`_x2` name has no derivable partner; inventing one would be
        // a filename nobody ships.
        assert_eq!(siblings("a_x2", "b_x2").len(), 1);
    }

    /// A donor without a picture for one of the target's animations leaves that
    /// animation on the shipped art.  That is an answer, and it must be visible.
    #[test]
    fn an_animation_the_donor_lacks_is_reported_not_invented() {
        let ta = Art {
            stem: "T".into(),
            tokens: [("idle".to_string(), "t_idle_x1".to_string()),
                     ("carry".to_string(), "t_carry_x1".to_string())]
                .into_iter()
                .collect(),
            grids: HashMap::new(),
        };
        let da = Art {
            stem: "D".into(),
            tokens: [("idle".to_string(), "d_idle_x1".to_string())]
                .into_iter()
                .collect(),
            grids: HashMap::new(),
        };
        let table = SpriteArt {
            units: [(
                1i16,
                vec![(0usize, 0usize)],
            )]
            .into_iter()
            .collect(),
            arts: vec![ta, da],
            civ_names: vec!["British".into()],
        };
        let mut units = table.units.clone();
        units.insert(2i16, vec![(0usize, 1usize)]);
        let table = SpriteArt {
            units,
            arts: table.arts,
            civ_names: table.civ_names,
        };
        let rep = table.plan(1, 2, &None, None).unwrap();
        assert_eq!(rep.want.len(), 2, "one pair, both resolutions");
        assert_eq!(rep.unmapped.len(), 1);
        assert_eq!(rep.unmapped[0].0, "carry");
        assert_eq!(rep.civs, 1);
    }

    /// One target filename wanted by two different donors cannot be satisfied by
    /// a rename, because a record holds one filename.  Refusing is the answer;
    /// picking one silently would break the other civilization's picture.
    #[test]
    fn two_donors_wanting_one_filename_is_refused() {
        let mk = |stem: &str, file: &str| Art {
            stem: stem.into(),
            tokens: [("idle".to_string(), file.to_string())].into_iter().collect(),
            grids: HashMap::new(),
        };
        let mut units: HashMap<i16, Vec<(usize, usize)>> = HashMap::new();
        units.insert(1, vec![(0, 0), (1, 0)]);
        units.insert(2, vec![(0, 1), (1, 2)]);
        let table = SpriteArt {
            units,
            arts: vec![mk("T", "t_idle_x1"), mk("D1", "d1_idle_x1"), mk("D2", "d2_idle_x1")],
            civ_names: vec!["British".into(), "French".into()],
        };
        let err = table.plan(1, 2, &None, None).unwrap_err();
        assert!(err.contains("t_idle_x1"), "{err}");
        assert!(err.contains("两个文明"), "{err}");
    }
}
