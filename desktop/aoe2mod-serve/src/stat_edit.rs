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
    let offsets_path = std::env::var("AOE2MOD_STAT_OFFSETS")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|_| std::path::PathBuf::from("_golden/stat_offsets.json"));
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

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    Ok(format!(
        "{{\"ok\":true,\"stat\":\"{}\",\"unit\":{},\"civs\":{},\"before\":{},\"value\":{},\"dat_bytes\":{},\"compressed\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        crate::server::json_escape(stat),
        unit,
        targets.len(),
        old,
        new_value,
        built.dat_bytes,
        built.compressed_bytes,
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}
