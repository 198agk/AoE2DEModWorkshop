//! Apply a stat edit through the offset table, and report exactly what moved.

use crate::server::{json_escape, Server};
use aoe2mod_dat::stats::{StatKind, StatTable};
use aoe2mod_dat::writer::Writer;
use aoe2mod_dat::write23::{write_stage1, write_stages23};
use aoe2mod_dat::write47::write_stages47;
use aoe2mod_dat::write810::write_stages810;
use aoe2mod_dat::{
    load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
};
use std::path::Path;

/// Every record id that an edit named after `unit` has to touch.
///
/// Reads the exported family table, so the preview and the build answer this
/// question from one source.  A missing table is not fatal: the fallback is the
/// one-member family, which is correct for every lone unit and is what this
/// server did before the table existed.
fn family_ids(unit: i16) -> Vec<i16> {
    let path = crate::families::table_path();
    match crate::families::Families::load(&path) {
        Ok(f) => f.of(unit),
        Err(_) => vec![unit],
    }
}

/// Edit `stat` on `unit` in every civilization, and describe what changed.
///
/// Editing every civ is not a convenience: a villager exists in all 63, and
/// touching one of them is the "it worked in the game I tested" failure this
/// project has already paid for.
pub fn apply(server: &Server, stat: &str, unit: i16, value: f64) -> Result<String, String> {
    let parsed = server
        .parsed
        .lock()
        .unwrap()
        .clone()
        .ok_or("游戏数据还没读完")?;
    let _ = parsed;

    let root = std::env::var("AOE2MOD_GAME_ROOT")
        .map(std::path::PathBuf::from)
        .ok()
        .or_else(|| {
            [
                r"d:\games\steam\steamapps\common\AoE2DE",
                r"c:\games\steam\steamapps\common\AoE2DE",
            ]
            .iter()
            .map(std::path::PathBuf::from)
            .find(|p: &std::path::PathBuf| {
                p.join("resources/_common/dat/empires2_x2_p1.dat").is_file()
            })
        })
        .ok_or("找不到游戏目录")?;

    let offsets_path = std::env::var("AOE2MOD_STAT_OFFSETS")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|_| Path::new("_golden/stat_offsets.json").to_path_buf());
    let table = StatTable::load(&offsets_path)
        .map_err(|e| format!("读不到 {}：{e}", offsets_path.display()))?;
    let kind = *table
        .kinds
        .get(stat)
        .ok_or_else(|| format!("不认识的属性 {stat}"))?;

    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    // Same family expansion as `build_one`, from the same table: `/api/stat` and
    // `/api/build` must never write different scopes for the same sentence.
    let family = family_ids(unit);
    let mut targets = Vec::new();
    for (ci, c) in s810.civs.iter().enumerate() {
        for u in c.units.iter() {
            if !family.contains(&u.id) {
                continue;
            }
            if let Some(off) = table.offset(ci, stat, u.id) {
                targets.push((ci, off));
            }
        }
    }
    if targets.is_empty() {
        return Err(format!("没有任何文明的单位 {unit} 带 {stat}"));
    }

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;

    // An absolute offset only means the same thing in the output because the
    // unmodified round trip is byte-identical. That is asserted, not assumed.
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }

    let before = read_at(&raw, targets[0].1, kind);
    for (_, off) in &targets {
        write_at(&mut out, *off, kind, value);
    }

    let diffs = raw
        .iter()
        .zip(out.iter())
        .filter(|(a, b)| a != b)
        .count();

    // The mod ships raw-deflated, which is the container the game reads.
    let out_dir = std::env::temp_dir().join("aoe2mod-native");
    std::fs::create_dir_all(&out_dir).map_err(|e| e.to_string())?;
    let out_path = out_dir.join("empires2_x2_p1.dat");
    {
        use flate2::write::DeflateEncoder;
        use flate2::Compression;
        use std::io::Write;
        let f = std::fs::File::create(&out_path).map_err(|e| e.to_string())?;
        let mut e = DeflateEncoder::new(f, Compression::default());
        e.write_all(&out).map_err(|e| e.to_string())?;
        e.finish().map_err(|e| e.to_string())?;
    }

    Ok(format!(
        "{{\"ok\":true,\"stat\":\"{}\",\"unit\":{},\"civs\":{},\"variants\":{},\"edit_count\":{},\"before\":{},\"value\":{},\"bytes_changed\":{},\"out\":\"{}\"}}",
        json_escape(stat),
        unit,
        civ_count(&targets),
        family.len(),
        targets.len(),
        before,
        value,
        diffs,
        json_escape(&out_path.display().to_string())
    ))
}

fn read_at(buf: &[u8], off: usize, kind: StatKind) -> f64 {
    match kind {
        StatKind::I16 if off + 2 <= buf.len() => {
            i16::from_le_bytes([buf[off], buf[off + 1]]) as f64
        }
        StatKind::U8 if off < buf.len() => buf[off] as f64,
        StatKind::F32 if off + 4 <= buf.len() => f32::from_le_bytes([
            buf[off],
            buf[off + 1],
            buf[off + 2],
            buf[off + 3],
        ]) as f64,
        _ => f64::NAN,
    }
}

fn write_at(buf: &mut [u8], off: usize, kind: StatKind, value: f64) {
    match kind {
        StatKind::I16 => {
            let v = value as i16;
            buf[off..off + 2].copy_from_slice(&v.to_le_bytes());
        }
        StatKind::U8 => buf[off] = value as u8,
        StatKind::F32 => {
            let v = value as f32;
            buf[off..off + 4].copy_from_slice(&v.to_le_bytes());
        }
    }
}

/// Compile one intent from the sentence layer, write the mod, install it.
///
/// The whole chain in one call, because each step alone is provable and the
/// interesting failures live in the joins: an intent that resolves but cannot be
/// compiled, a build that succeeds but installs nowhere, a title the engine will
/// truncate.
/// `/api/build` takes an intent LIST (`{"intents":[{...},{...}]}`) because one mod
/// carries every sentence the player typed: splitting them turns "tougher
/// villagers AND faster loom" into two mods of which the engine loads only the
/// higher-priority one.
///
/// Measured 2026-10-27: reading the field as `intent` (singular) meant the
/// Build button never worked for ANY intent -- every call fell through to the
/// stat branch and refused with "这句话没有说要改哪个单位", including the ones this
/// server implemented. The end-to-end probes missed it because they posted a flat
/// `{stat,unit,value}` body that the page never sends.
///
/// A bundle is still all-or-nothing: the first intent that fails to compile stops
/// the build, because a mod that applied two of the player's three sentences does
/// less than it says. Several intents that each want their own files are refused
/// by name rather than silently keeping the last one.
pub fn build_one(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    // Tech edits take a different path: a technology is ONE record (not 63), its
    // research time is a list of locations, and its cost is a slot index.
    let intent = req.get("intent").and_then(|v| v.as_str()).unwrap_or("");
    if intent == "tech.research_time" || intent == "tech.cost" {
        return build_tech(server, req);
    }
    if intent == "tech.effect" {
        return build_effect(server, req);
    }
    if intent == "tech.toggle_group" {
        return build_toggle_group(server, req);
    }
    if intent == "unit.sprite" {
        return build_sprite(server, req);
    }
    if intent == "unit.card_move" || intent == "card_move" {
        return build_card_move(server, req);
    }
    if intent == "unit.cost" {
        return build_unit_cost(server, req);
    }
    if intent == "unit.attack_class" {
        return build_unit_attack_class(server, req);
    }
    let stat = req.get("stat").and_then(|v| v.as_str()).unwrap_or("");
    let unit = req.get("unit").and_then(|v| v.as_i64()).map(|v| v as i16);
    let value = req.get("value").and_then(|v| v.as_f64());
    let delta = req.get("delta").and_then(|v| v.as_f64());
    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("{stat} {unit:?}"));
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);

    let unit = unit.ok_or("这句话没有说要改哪个单位")?;
    if !server.parsed.lock().unwrap().is_some() {
        return Err("游戏数据还没读完".into());
    }

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let offsets_path = crate::stats_path();
    let table = StatTable::load(&offsets_path)
        .map_err(|e| format!("读不到 {}：{e}", offsets_path.display()))?;
    let kind = *table
        .kinds
        .get(stat)
        .ok_or_else(|| format!("不认识的属性 {stat}"))?;

    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    // Resolve the target value: SET means the number, DELTA means old + delta.
    //
    // `family_of` is not a nicety.  `村民血量改成100` names ONE id (83) but the
    // game ships 27 villager records per civilization -- age variants for the
    // trained unit and separate male/female baskets joined through
    // `objreplacement.json`.  Writing only the named id changes the male villager
    // and leaves the female one alone, while the screen reports "63 处改动": a
    // number that is really the extent of the loop, not of the edit.
    let family = family_ids(unit);
    let mut targets = Vec::new();
    for (ci, c) in s810.civs.iter().enumerate() {
        for u in c.units.iter() {
            if !family.contains(&u.id) {
                continue;
            }
            if let Some(off) = table.offset(ci, stat, u.id) {
                targets.push((ci, off));
            }
        }
    }
    if targets.is_empty() {
        return Err(format!("没有任何文明的单位 {unit} 带 {stat}"));
    }
    let old = read_at(&raw, targets[0].1, kind);
    let new_value = match (value, delta) {
        (Some(v), _) => v,
        (None, Some(d)) => old + d,
        (None, None) => return Err("这句话没有说要改成多少".into()),
    };

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }
    for (_, off) in &targets {
        write_at(&mut out, *off, kind, new_value);
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("{stat} {unit} -> {new_value}"),
        true,
    )?;

    // Remember the origin BEFORE installing: the record is what makes the mod
    // visible to /api/update-check and replayable by /api/rebuild, and a mod
    // that exists while both guards have never heard of it is the failure this
    // project's provenance layer exists to prevent.
    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, r, _v)) => (f, r),
        None => (String::new(), None),
    };
    // Hash the bytes that LAND ON DISK, which are raw-deflated -- the same file
    // `update-check` will hash later. Hashing the uncompressed stream here made
    // every freshly built mod report `edited`, i.e. "something else overwrote
    // this", about the file this tool had just written itself.
    let dat_out_sha = sha256_bytes(&built.compressed);

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    // The record. `changes_dat: true` because this build genuinely rewrites the
    // .dat, which is what lets the update guard call it `stale` later instead of
    // `no_dat`.
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &format!("{stat} {unit} -> {new_value}"),
        serde_json::json!([{
            "intent": "unit.stat",
            "unit": unit,
            "stat": stat,
            "value": new_value
        }]),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        "{{\"ok\":true,\"stat\":\"{}\",\"unit\":{},\"civs\":{},\"variants\":{},\"edit_count\":{},\"before\":{},\"value\":{},\"dat_bytes\":{},\"compressed\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        crate::server::json_escape(stat),
        unit,
        // Distinct civilizations, not writes.  `targets.len()` used to be
        // reported here under the name `civs`, which after family expansion says
        // 1701 civilizations exist.  The two numbers answer different questions
        // and the reference calls them `civ_count` and `edit_count`.
        civ_count(&targets),
        family.len(),
        targets.len(),
        old,
        new_value,
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}

/// How many distinct civilizations the write list touches.
fn civ_count(targets: &[(usize, usize)]) -> usize {
    let mut seen: Vec<usize> = targets.iter().map(|(ci, _)| *ci).collect();
    seen.sort_unstable();
    seen.dedup();
    seen.len()
}

/// The shared body of `unit.cost` and `unit.attack_class`.
///
/// Both write `i16`s into a unit record at offsets the parser measured, both
/// have to expand to the variant family, and both produce the same report.  The
/// only difference is how a sentence becomes offsets, so that is the closure --
/// one copy of the write/install/remember chain, which is where a divergence
/// would be invisible: a cost edit that installed and a damage edit that only
/// reported would each look correct from its own JSON.
fn build_unit_field(
    server: &Server,
    req: &serde_json::Value,
    resolve: impl FnOnce(
        &aoe2mod_dat::stage810::Stages810,
        &[i16],
        i16,
    ) -> Result<crate::unitfield::Resolved, String>,
) -> Result<String, String> {
    let intent = req.get("intent").and_then(|v| v.as_str()).unwrap_or("");
    let unit = req
        .get("unit")
        .and_then(|v| v.as_i64())
        .map(|v| v as i16)
        .ok_or("这句话没有说要改哪个单位")?;
    let value = req.get("value").and_then(|v| v.as_f64());
    let delta = req.get("delta").and_then(|v| v.as_f64());
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    // Family, not the named id: `村民` is 27 records per civilisation, and
    // writing only the one the sentence named leaves the female villager alone
    // while the screen reports the loop's extent as if it were the edit's.
    let family = family_ids(unit);
    let resolved = resolve(&s810, &family, unit)?;

    let new_value = match (value, delta) {
        (Some(v), _) => v,
        (None, Some(d)) => resolved.before + d,
        (None, None) => return Err("这句话没有说要改成多少".into()),
    };

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }
    let kind = resolved.kind();
    for hit in &resolved.hits {
        write_at(&mut out, hit.offset, kind, new_value);
    }

    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("{intent} {unit}"));

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("{} {unit} -> {new_value}", resolved.label),
        true,
    )?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    let dat_out_sha = sha256_bytes(&built.compressed);
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &format!("{} {unit} -> {new_value}", resolved.label),
        serde_json::json!([{
            "intent": intent,
            "unit": unit,
            "resource": req.get("resource").cloned().unwrap_or(serde_json::Value::Null),
            "attack_kind": req.get("attack_kind").cloned().unwrap_or(serde_json::Value::Null),
            "value": new_value
        }]),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        "{{\"ok\":true,\"intent\":\"{}\",\"unit\":{},\"field\":\"{}\",\"civs\":{},\"variants\":{},\"edit_count\":{},\"before\":{},\"value\":{},\"dat_bytes\":{},\"compressed\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        crate::server::json_escape(intent),
        unit,
        crate::server::json_escape(&resolved.label),
        resolved.civ_count(),
        family.len(),
        resolved.hits.len(),
        resolved.before,
        new_value,
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}

/// `unit.cost`: the amount in one of the unit's three cost slots.
fn build_unit_cost(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    let resource = req
        .get("resource")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    build_unit_field(server, req, |s810, family, unit| {
        crate::unitfield::cost_targets(s810, family, &resource, unit)
    })
}

/// `unit.attack_class`: one row of Type50's attack or armour list, plus the
/// panel number that tracks it.
fn build_unit_attack_class(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    let kind = req
        .get("attack_kind")
        .and_then(|v| v.as_str())
        .or_else(|| req.get("kind").and_then(|v| v.as_str()))
        .unwrap_or("attack")
        .to_string();
    // The candidate list comes from the sentence layer when it has one, so a
    // sentence that names a class can narrow it.  The default is the schema's
    // `attack_classes.attack|armour.class_candidates`, tried in order.
    let classes: Vec<i16> = req
        .get("class_candidates")
        .and_then(|v| v.as_array())
        .map(|a| a.iter().filter_map(|x| x.as_i64().map(|v| v as i16)).collect())
        .filter(|v: &Vec<i16>| !v.is_empty())
        .unwrap_or_else(|| {
            if kind == "armour" {
                vec![4, 3]
            } else {
                vec![3, 4]
            }
        });
    build_unit_field(server, req, |s810, family, unit| {
        crate::unitfield::damage_targets(s810, family, &kind, &classes, unit)
    })
}


/// `tech.research_time` / `tech.cost`: one global record, one or more offsets.

/// The `/api/build` entry point: an intent ARRAY, or a single flat intent.
///
/// One intent is the whole story for every current strategy -- each writes its
/// own files under its own `<build>/<title>/`, so two of them in one folder would
/// each recreate the folder and drop the other's file. That is a real limitation
/// and it is said out loud instead of returning the last build as if it were the
/// bundle the player asked for.
pub fn build_and_install(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    let list = match req.get("intents").and_then(|v| v.as_array()) {
        Some(a) if !a.is_empty() => a.clone(),
        _ => return build_one(server, req),
    };
    if list.len() > 1 {
        let names: Vec<String> = list
            .iter()
            .map(|it| {
                it.get("intent")
                    .and_then(|v| v.as_str())
                    .unwrap_or("?")
                    .to_string()
            })
            .collect();
        return Err(format!(
            "这一步一个 mod 只能装一件事：现在收到 {} 句（{}）。每句话各写自己的文件、各自建目录，装进同一个 mod 会互相覆盖。先做一句，或把它们分成几步。",
            list.len(),
            names.join("、")
        ));
    }
    let mut one = list[0].clone();
    // Carry the bundle-level fields onto the single intent: the title says what
    // the mod is CALLED, and every builder reads it from the intent it is given.
    if let Some(obj) = one.as_object_mut() {
        for key in ["title", "author", "description", "install", "title_auto"] {
            if !obj.contains_key(key) {
                if let Some(v) = req.get(key) {
                    obj.insert(key.to_string(), v.clone());
                }
            }
        }
    }
    build_one(server, &one)
}

fn build_tech(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    use crate::writer::Writer;
    use crate::write23::{write_stage1, write_stages23};
    use crate::write47::write_stages47;
    use crate::write810::write_stages810;
    use aoe2mod_dat::{
        load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
    };

    let intent = req.get("intent").and_then(|v| v.as_str()).unwrap_or("");
    let tech = req
        .get("tech")
        .and_then(|v| v.as_i64())
        .map(|v| v as i16)
        .ok_or("这句话没有说要改哪个科技")?;
    let value = req.get("value").and_then(|v| v.as_f64());
    let delta = req.get("delta").and_then(|v| v.as_f64());
    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("tech {tech}"));
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }

    let table = crate::techedit::TechTable::load(&crate::techedit::table_path())
        .map_err(|e| format!("读不到科技偏移表：{e}"))?;

    // Which absolute offsets this edit writes.
    let offsets: Vec<usize> = if intent == "tech.research_time" {
        let v = table.research_time_offsets(tech);
        if v.is_empty() {
            return Err(format!("科技 {tech} 没有研究时间可改"));
        }
        v
    } else {
        // The cost slot is chosen by the resource word, mapped through the order
        // the record stores them in. Naming the slot rather than inferring it is
        // the point: an empty slot is a real thing and (-1,0,0) is the sentinel.
        let res = req.get("resource").and_then(|v| v.as_str()).unwrap_or("");
        let rtype = crate::techedit::TechTable::resource_type_id(res)
            .ok_or_else(|| format!("不认识的资源 {res}"))?;
        match table.cost_offset(tech, rtype) {
            Some(o) => vec![o],
            // Refused rather than added: "give this tech a new cost" is a
            // different operation from "change the price", and guessing a slot
            // is how the price moves on one field and the artefact shows a cost
            // the game does not charge.
            None => {
                return Err(format!(
                    "科技 {tech} 本来就不花{res}，所以没有可以改的那一格；                     加一条新成本是另一件事，这个版本还不做"
                ))
            }
        }
    };

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }

    let kind = aoe2mod_dat::stats::StatKind::I16;
    let old = read_at(&raw, offsets[0], kind);
    let new_value = match (value, delta) {
        (Some(v), _) => v,
        (None, Some(d)) => old + d,
        (None, None) => return Err("这句话没有说要改成多少".into()),
    };
    // EVERY location, not the first: a tech can carry several and the untouched
    // copies keep the old time, which in game reads as "nothing changed".
    for off in &offsets {
        write_at(&mut out, *off, kind, new_value);
    }
    let diffs = raw.iter().zip(out.iter()).filter(|(a, b)| a != b).count();

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("{intent} {tech} -> {new_value}"),
        true,
    )?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    // Hash the bytes that LAND ON DISK, which are raw-deflated -- the same file
    // `update-check` will hash later. Hashing the uncompressed stream here made
    // every freshly built mod report `edited`, i.e. "something else overwrote
    // this", about the file this tool had just written itself.
    let dat_out_sha = sha256_bytes(&built.compressed);
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &format!("{intent} {tech} -> {new_value}"),
        serde_json::json!([{
            "intent": intent,
            "tech": tech,
            "resource": req.get("resource").cloned().unwrap_or(serde_json::Value::Null),
            "value": new_value
        }]),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        "{{\"ok\":true,\"intent\":\"{}\",\"tech\":{},\"locations\":{},\"before\":{},\"value\":{},\"bytes_changed\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        crate::server::json_escape(intent),
        tech,
        offsets.len(),
        old,
        new_value,
        diffs,
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}


fn sha256_bytes(b: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(b);
    format!("{:x}", h.finalize())
}


/// `tech.effect`: write ONE field of ONE command inside a technology's effect.
///
/// What it refuses, and why refusing is the right answer:
///
///   * a command index that does not exist -- adding a command changes the
///     record's LENGTH, which shifts every following effect and invalidates
///     `effect_id` everywhere;
///   * a field name that is not `t`/`a`/`b`/`c`/`d` -- those are the five the
///     format has, and inventing one would write at an offset that means
///     something else.
fn build_effect(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    use crate::writer::Writer;
    use crate::write23::{write_stage1, write_stages23};
    use crate::write47::write_stages47;
    use crate::write810::write_stages810;
    use aoe2mod_dat::{
        load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
    };

    // A tech's effect_id names the effect record. The sentence layer returns the
    // TECH id, so it has to be resolved through the tech record -- editing the
    // effect whose index happens to equal the tech id would be right for Loom
    // (tech 22, effect 22) and wrong for most others, which is the worst kind of
    // coincidence to rely on.
    let tech = req
        .get("tech")
        .and_then(|v| v.as_i64())
        .map(|v| v as i16)
        .ok_or("这句话没有说要改哪个科技")?;
    let command = req
        .get("command")
        .and_then(|v| v.as_u64())
        .map(|v| v as usize)
        .ok_or("这句话没有说是第几条效果")?;
    let field = req
        .get("field")
        .and_then(|v| v.as_str())
        .unwrap_or("d")
        .to_string();
    let value = req.get("value").and_then(|v| v.as_f64());
    let delta = req.get("delta").and_then(|v| v.as_f64());
    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("tech {tech} effect"));
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }
    let (kind_name, width) = crate::effectedit::field_kind(&field)
        .ok_or_else(|| format!("没有 {field} 这个字段（只有 t/a/b/c/d）"))?;

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    let effect_id = s810
        .techs
        .get(tech as usize)
        .map(|t| t.effect_id)
        .ok_or_else(|| format!("没有编号 {tech} 的科技"))?;
    if effect_id < 0 {
        return Err(format!("科技 {tech} 没有效果记录"));
    }

    let table = crate::effectedit::EffectTable::load(&crate::effectedit::table_path())
        .map_err(|e| format!("读不到效果偏移表：{e}"))?;
    let cmd = table
        .command(effect_id as i32, command - 1)
        .ok_or_else(|| {
            format!(
                "效果 {effect_id} 没有第 {command} 条命令（加一条是另一件事，会让后面所有效果错位）"
            )
        })?;
    let off = *cmd
        .get(&field)
        .ok_or_else(|| format!("效果 {effect_id} 第 {command} 条没有 {field} 字段"))?;

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }

    let old = match width {
        1 => raw.get(off).map(|b| *b as f64).unwrap_or(f64::NAN),
        2 => read_at(&raw, off, aoe2mod_dat::stats::StatKind::I16),
        _ => read_at(&raw, off, aoe2mod_dat::stats::StatKind::F32),
    };
    let new_value = match (value, delta) {
        (Some(v), _) => v,
        (None, Some(d)) => old + d,
        (None, None) => return Err("这句话没有说要改成多少".into()),
    };
    match width {
        1 => {
            if off < out.len() {
                out[off] = new_value as u8;
            }
        }
        2 => write_at(&mut out, off, aoe2mod_dat::stats::StatKind::I16, new_value),
        _ => write_at(&mut out, off, aoe2mod_dat::stats::StatKind::F32, new_value),
    }
    let diffs = raw.iter().zip(out.iter()).filter(|(a, b)| a != b).count();

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("effect {effect_id} cmd {command} {field} -> {new_value}"),
        true,
    )?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    let dat_out_sha = sha256_bytes(&built.compressed);
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &format!("effect {effect_id} cmd {command} {field} -> {new_value}"),
        serde_json::json!([{
            "intent": "tech.effect",
            "tech": tech,
            "command": command,
            "field": field,
            "value": new_value
        }]),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        "{{\"ok\":true,\"tech\":{},\"effect\":{},\"command\":{},\"field\":\"{}\",\"field_kind\":\"{}\",\"before\":{},\"value\":{},\"bytes_changed\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        tech,
        effect_id,
        command,
        crate::server::json_escape(&field),
        kind_name,
        old,
        new_value,
        diffs,
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}


/// `unit.card_move`: exchange two units' boxes on one building's card.
///
/// Dragging a box in the engine is ONE BYTE: the `button_id` in that unit's
/// `train_locations` entry. The byte sits `TRAIN_BUTTON_OFF` after the entry's
/// absolute `_off_train_time`, which `command_cards.json` carries.
///
/// A move SWAPS. Two units on one box is a state the shipped data never
/// contains, and the engine resolves it by drawing one of them -- so an editor
/// that lets a drop overwrite deletes a unit and reports success.
fn build_card_move(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    use crate::writer::Writer;
    use crate::write23::{write_stage1, write_stages23};
    use crate::write47::write_stages47;
    use crate::write810::write_stages810;
    use aoe2mod_dat::{
        load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
    };

    let unit = req
        .get("unit")
        .and_then(|v| v.as_i64())
        .map(|v| v as i16)
        .ok_or("没说要把哪个单位挪走")?;
    // The sentence may omit the building ("把民兵放在第5格"), and the server
    // reads it from the TABLE: the card the unit is already on. That is what the
    // sentence means -- "move it within its own card" -- and inventing a
    // different building would either fail or move it somewhere the player did
    // not ask for.
    let mut building = req
        .get("building")
        .or_else(|| req.get("builder"))
        .and_then(|v| v.as_i64())
        .map(|v| v as i16);
    // TWO spellings, deliberately.  The page's own drag handler posts `box`, and
    // the sentence reader emits `button` (`sentences.rs:230`) because that is
    // what the schema calls the slot.  Reading only `box` meant every sentence
    // this program said it understood came back "没说要挪到第几格" -- the
    // reader and the builder disagreed about a field name, and only the
    // parse→build path crossed the join.
    let target = req
        .get("box")
        .or_else(|| req.get("button"))
        .and_then(|v| v.as_u64())
        .map(|v| v as u8)
        .ok_or("没说要挪到第几格")?;
    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("card {}", building.map(|b| b.to_string()).unwrap_or_else(|| "auto".into())));
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }

    let cards_json: serde_json::Value = {
        let t = std::fs::read_to_string(crate::cards::table_path())
            .map_err(|e| format!("读不到命令面板表：{e}"))?;
        serde_json::from_str(t.trim_start_matches('\u{feff}'))
            .map_err(|e| format!("命令面板表不是合法 JSON：{e}"))?
    };
    if building.is_none() {
        // First card in id order that lists this unit. Deterministic, and the
        // common case for a villager is the town centre / barracks it starts on.
        if let Some(cards) = cards_json.get("cards").and_then(|c| c.as_object()) {
            let mut ids: Vec<i16> = cards.keys().filter_map(|k| k.parse().ok()).collect();
            ids.sort();
            for id in ids {
                if let Some(list) = cards.get(&id.to_string()).and_then(|v| v.as_array()) {
                    if list.iter().any(|e| {
                        e.get("unit").and_then(|v| v.as_i64()) == Some(unit as i64)
                    }) {
                        building = Some(id);
                        break;
                    }
                }
            }
        }
    }
    let building = building.ok_or_else(|| {
        format!("第 {unit} 号单位不在任何建筑的训练表里，所以它没有格子可挪")
    })?;
    let lookup = crate::cardmove::entry_lookup(&cards_json, building, |_| None);
    if !lookup.contains_key(&unit) {
        return Err(format!(
            "第 {unit} 号单位不在这座建筑（{building}）的训练表里，所以它没有格子可挪"
        ));
    }

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }

    // Offsets are ABSOLUTE in the table (locate stores cursor positions); the box
    // byte is a fixed distance after the train-time field.
    let table = lookup.clone();
    let slots = crate::slots::card_slots(&root).0;
    let report = crate::cardmove::move_unit(&mut out, unit, building, target, slots, |u| {
        table.get(&u).copied()
    })?;

    let diffs = raw.iter().zip(out.iter()).filter(|(a, b)| a != b).count();
    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("card {building}: unit {unit} -> box {target}"),
        true,
    )?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    let dat_out_sha = sha256_bytes(&built.compressed);
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &format!("card {building}: unit {unit} -> box {target}"),
        serde_json::json!([{
            "intent": "unit.card_move",
            "unit": unit,
            "building": building,
            "button": target
        }]),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    let moved: Vec<String> = report
        .moved
        .iter()
        .map(|(u, from, to)| format!("{{\"unit\":{u},\"from\":{from},\"to\":{to}}}"))
        .collect();
    Ok(format!(
        "{{\"ok\":true,\"building\":{},\"offset\":{},\"before\":{},\"after\":{},\"moved\":[{}],\"bytes_changed\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        building,
        report.offset,
        report.before,
        report.after,
        moved.join(","),
        diffs,
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}


/// Public wrapper: the server module calls this, and `build_card_move` stays
/// private so its signature can change without touching the routing layer.
pub fn build_card_move_pub(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    build_card_move(server, req)
}


/// `unit.sprite` in RENAME mode: re-point graphics records, ship no pictures.
///
/// Copy mode would ship 466 `.sld` files (438 MB). Rename mode ships none: the
/// `.dat` already says which file to load per graphics record, so re-pointing
/// them is the whole edit -- ~12 MB.
///
/// The hazard is the one this project paid for: a graphics record's `file` string
/// has a STORED WIDTH, and re-emitting it at a different length must advance the
/// input cursor by the OLD width or every later verbatim read shifts. That is
/// what `Graphic::file_len` is for, and it is passed through here.
fn build_sprite(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    use crate::write23::{write_stage1, write_stages23};
    use crate::write47::write_stages47;
    use crate::write810::write_stages810;
    use crate::writer::Writer;
    use aoe2mod_dat::{
        load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
    };

    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| "sprite".to_string());
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }

    let pairs = crate::spritemap::SpritePairs::load(&crate::spritemap::table_path())
        .map_err(|e| format!("读不到贴图对照表：{e}"))?;
    if pairs.pairs.is_empty() {
        return Err("贴图对照表是空的".into());
    }

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let mut s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    // Re-point the graphics records. `file_len` is left ALONE on purpose: it is
    // the width the INPUT used, and the writer needs it to advance the cursor.
    let mut touched = 0usize;
    for g in s23.graphics.iter_mut() {
        if let Some(donor) = crate::spritemap::donor_for(&pairs, &g.file) {
            if &g.file != donor {
                g.file = donor.clone();
                touched += 1;
            }
        }
    }
    if touched == 0 {
        return Err("没有任何图形记录需要改指向".into());
    }

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let out = w.out;
    // NOT `mismatches != 0`: this edit changes the LENGTH of a string, so every
    // byte after it legitimately differs from the input. The round-trip check
    // applies to unmodified builds, where the whole stream must be identical.
    // Here the gate is the RE-PARSE below: if the cursor bookkeeping is right the
    // output parses to its own EOF, and if it is wrong it will not.
    let _ = w.mismatches;

    // Re-parse the OUTPUT: the whole point of rename mode is that the records say
    // what we asked and nothing else moved.
    let mut r2 = Reader::new(&out);
    let o1 = read_stage1(&mut r2).map_err(|e| e.to_string())?;
    let _ = read_stages23(&mut r2).map_err(|e| e.to_string())?;
    let _ = read_stages47(&mut r2, o1.game_version).map_err(|e| e.to_string())?;
    let _ = read_stages810(&mut r2, o1.game_version).map_err(|e| e.to_string())?;
    if r2.pos != out.len() {
        return Err(format!(
            "改完之后重新解析停在 {}，文件长 {}",
            r2.pos,
            out.len()
        ));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("sprite rename: {touched} records"),
        true,
    )?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    let dat_out_sha = sha256_bytes(&built.compressed);
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &format!("sprite rename: {touched} records"),
        serde_json::json!([{
            "intent": "unit.sprite",
            "unit": pairs.unit,
            "donor": pairs.donor,
            "mode": "rename"
        }]),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        "{{\"ok\":true,\"intent\":\"unit.sprite\",\"mode\":\"rename\",\"records\":{},\"dat_bytes\":{},\"compressed\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        touched,
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}

/// Public wrapper for the routing layer.
pub fn build_sprite_pub(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    build_sprite(server, req)
}


/// `tech.toggle_group`: append one `MutuallyExclusive` entry to linkedTechs.json.
///
/// The mod ships an UNMODIFIED `.dat` beside the JSON: measured in this project,
/// a mod writing under `resources/_common/dat/` without one makes the game fail to
/// start, because that storage point is resolved as a unit rather than per file.
/// `changes_dat` is therefore true even though no `.dat` byte moved -- the record
/// says "this mod carries a .dat", which is what the update guard needs to know.
fn build_toggle_group(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    use aoe2mod_dat::load_dat;

    let techs: Vec<i16> = req
        .get("techs")
        .and_then(|v| v.as_array())
        .map(|a| a.iter().filter_map(|x| x.as_i64().map(|n| n as i16)).collect())
        .unwrap_or_default();
    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| "tech group".to_string());
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;

    let out_dir = std::env::temp_dir()
        .join("aoe2mod-native-build")
        .join(&title);
    if out_dir.exists() {
        std::fs::remove_dir_all(&out_dir).map_err(|e| e.to_string())?;
    }
    std::fs::create_dir_all(&out_dir).map_err(|e| e.to_string())?;

    // 1. the JSON layer
    let (entry, total) = crate::togglegroup::build(
        &root.join("resources/_common/dat"),
        &out_dir,
        &techs,
    )?;

    // 2. the carrier .dat, copied verbatim
    let dat_out = out_dir.join("resources/_common/dat/empires2_x2_p1.dat");
    {
        use flate2::write::DeflateEncoder;
        use flate2::Compression;
        use std::io::Write;
        let f = std::fs::File::create(&dat_out).map_err(|e| e.to_string())?;
        let mut e = DeflateEncoder::new(f, Compression::default());
        e.write_all(&raw).map_err(|e| e.to_string())?;
        e.finish().map_err(|e| e.to_string())?;
    }

    // 3. info.json, compact, four keys
    let info = format!(
        "{{\"Author\":\"aoe2mod\",\"CacheStatus\":0,\"Description\":\"{}\",\"Title\":\"{}\"}}",
        crate::server::json_escape(&format!("mutually exclusive: {techs:?}")),
        crate::server::json_escape(&title)
    );
    std::fs::write(out_dir.join("info.json"), info).map_err(|e| e.to_string())?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let built = crate::build::Built {
            dir: out_dir.clone(),
            title: title.clone(),
            dat_bytes: raw.len(),
            compressed: Vec::new(),
        };
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &format!("mutually exclusive: {techs:?}"),
        serde_json::json!([{
            "intent": "tech.toggle_group",
            "techs": techs
        }]),
        &base_file_sha,
        base_raw_sha.as_deref(),
        // The emitted .dat is the factory one, so its hash is empty on purpose:
        // `update-check` then treats this as a CARRIER, not as an edit that can go
        // stale. Writing a hash here would make it look edited forever.
        "",
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        "{{\"ok\":true,\"intent\":\"tech.toggle_group\",\"entry\":{},\"entries\":{},\"files\":2,\"built\":\"{}\",\"installed\":\"{}\"}}",
        entry,
        total,
        crate::server::json_escape(&out_dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}

pub fn build_toggle_group_pub(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    build_toggle_group(server, req)
}
