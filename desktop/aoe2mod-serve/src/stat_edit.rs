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

    let mut targets = Vec::new();
    for (ci, c) in s810.civs.iter().enumerate() {
        if !c.units.iter().any(|u| u.id == unit) {
            continue;
        }
        if let Some(off) = table.offset(ci, stat, unit) {
            targets.push((ci, off));
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
        "{{\"ok\":true,\"stat\":\"{}\",\"unit\":{},\"civs\":{},\"before\":{},\"value\":{},\"bytes_changed\":{},\"out\":\"{}\"}}",
        json_escape(stat),
        unit,
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
pub fn build_and_install(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    // Tech edits take a different path: a technology is ONE record (not 63), its
    // research time is a list of locations, and its cost is a slot index.
    let intent = req.get("intent").and_then(|v| v.as_str()).unwrap_or("");
    if intent == "tech.research_time" || intent == "tech.cost" {
        return build_tech(server, req);
    }
    if intent == "tech.effect" {
        return build_effect(server, req);
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
    let mut targets = Vec::new();
    for (ci, c) in s810.civs.iter().enumerate() {
        if !c.units.iter().any(|u| u.id == unit) {
            continue;
        }
        if let Some(off) = table.offset(ci, stat, unit) {
            targets.push((ci, off));
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
        "{{\"ok\":true,\"stat\":\"{}\",\"unit\":{},\"civs\":{},\"before\":{},\"value\":{},\"dat_bytes\":{},\"compressed\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        crate::server::json_escape(stat),
        unit,
        targets.len(),
        old,
        new_value,
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}


/// `tech.research_time` / `tech.cost`: one global record, one or more offsets.
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
