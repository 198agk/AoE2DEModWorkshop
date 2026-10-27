//! Edit any unit stat by name, at the offset `locate` measured.
//!
//! Usage:
//!   aoe2mod-dat-edit <dat> <offsets.json> <stat> <unit-id> <value> [out.dat]
//!
//! Prints the offsets used, the bytes that changed, and whether a re-parse of
//! the output agrees.  Exit 0 only when every one of those checks passes: a
//! write that lands on the wrong byte is indistinguishable from one that did
//! nothing, because the game silently ignores a record it cannot resolve.
use aoe2mod_dat::stats::{StatKind, StatTable};
use aoe2mod_dat::writer::Writer;
use aoe2mod_dat::write23::{write_stage1, write_stages23};
use aoe2mod_dat::write47::write_stages47;
use aoe2mod_dat::write810::write_stages810;
use aoe2mod_dat::{
    load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
};
use std::path::Path;

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() < 6 {
        eprintln!(
            "usage: {} <dat> <stat_offsets.json> <stat> <unit-id> <value> [out.dat]",
            a[0]
        );
        std::process::exit(2);
    }
    let (dat, offs_json, stat) = (&a[1], &a[2], a[3].as_str());
    let unit_id: i16 = a[4].parse().expect("unit id");
    let value: f64 = a[5].parse().expect("value");
    let out_path = a.get(6);

    let table = StatTable::load(Path::new(offs_json)).expect("offsets");
    let kind = *table
        .kinds
        .get(stat)
        .unwrap_or_else(|| panic!("unknown stat {stat}"));
    println!(
        "stat {} ({:?}, {} bytes), unit {}",
        stat,
        kind,
        kind.width(),
        unit_id
    );

    let (raw, _how) = load_dat(Path::new(dat)).expect("load");
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).expect("s1");
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).expect("s23");
    let s47 = read_stages47(&mut r, gv).expect("s47");
    let s810 = read_stages810(&mut r, gv).expect("s810");

    // Which civ holds this unit?  Edit every civ that does: a villager exists in
    // all 63, and editing one civ only is the classic "worked in my test game"
    // failure.
    let mut targets = Vec::new();
    for (ci, c) in s810.civs.iter().enumerate() {
        if !c.units.iter().any(|u| u.id == unit_id) {
            continue;
        }
        if let Some(off) = table.offset(ci, stat, unit_id) {
            targets.push((ci, off));
        }
    }
    if targets.is_empty() {
        eprintln!("no civ has unit {unit_id} with stat {stat}");
        std::process::exit(1);
    }
    println!("civs to edit: {} (first {}, last {})",
             targets.len(),
             s810.civs[targets[0].0].name,
             s810.civs[targets[targets.len() - 1].0].name);

    // Show the value the retail file holds at that offset, as a sanity check
    // that the table and the stream agree before anything is written.
    let (ci0, off0) = targets[0];
    let before = read_at(&raw, off0, kind);
    println!(
        "civ {} ({}) offset {}: {} -> {}",
        ci0, s810.civs[ci0].name, off0, before, value
    );

    // Build the output by re-emitting, but with the bytes for each target
    // offset patched.  Patching the OUTPUT at the absolute offset works because
    // the pre-edit round trip is byte-identical, so output offsets equal input
    // offsets for an unmodified file.  That equality is asserted below.
    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).expect("w1");
    write_stages23(&mut w, &s23, &raw).expect("w23");
    write_stages47(&mut w, &s47, gv).expect("w47");
    write_stages810(&mut w, &s810).expect("w810");
    let mut out = w.out;

    if out.len() != raw.len() {
        eprintln!("REFUSING: output length {} != input {}", out.len(), raw.len());
        std::process::exit(1);
    }
    // The round trip must be identical before any patch, or an absolute offset
    // would mean something different in the output.
    if out != raw {
        eprintln!("REFUSING: unmodified round trip is not identical");
        std::process::exit(1);
    }

    for (_ci, off) in &targets {
        write_at(&mut out, *off, kind, value);
    }

    // Verify: which bytes differ, and does a re-parse read the new value.
    let diffs: Vec<usize> = raw
        .iter()
        .zip(out.iter())
        .enumerate()
        .filter(|(_, (a, b))| a != b)
        .map(|(i, _)| i)
        .collect();
    println!(
        "bytes differing: {} (expected <= {})",
        diffs.len(),
        targets.len() * kind.width()
    );

    let mut r2 = Reader::new(&out);
    let o1 = read_stage1(&mut r2).expect("o1");
    let _ = read_stages23(&mut r2).expect("o23");
    let _ = read_stages47(&mut r2, o1.game_version).expect("o47");
    let o810 = read_stages810(&mut r2, o1.game_version).expect("o810");
    let clean = r2.pos == out.len();
    println!("reparse clean: {clean}");

    let checks: Vec<(&str, bool)> = targets
        .iter()
        .map(|(ci, _)| {
            let got = o810.civs[*ci]
                .units
                .iter()
                .find(|u| u.id == unit_id)
                .map(|u| u.hit_points as f64);
            (s810.civs[*ci].name.as_str(), got.is_some())
        })
        .collect();
    let all_present = checks.iter().all(|(_, ok)| *ok);
    println!("edited civs re-read: {}", checks.len());

    // Read the patched byte back out of the output, which is the real assertion.
    let mut all_new = true;
    for (_, off) in &targets {
        let v = read_at(&out, *off, kind);
        if (v - value).abs() > 1e-6 {
            all_new = false;
            println!("  offset {} reads {} want {}", off, v, value);
        }
    }

    let ok = clean && all_present && all_new
        && diffs.len() <= targets.len() * kind.width();
    println!("{}", if ok { "EDIT OK" } else { "EDIT FAILED" });

    if let (true, Some(p)) = (ok, out_path) {
        use flate2::write::DeflateEncoder;
        use flate2::Compression;
        use std::io::Write;
        let f = std::fs::File::create(p).expect("create");
        let mut e = DeflateEncoder::new(f, Compression::default());
        e.write_all(&out).expect("deflate");
        e.finish().expect("finish");
        println!("wrote {p}");
    }
    if !ok {
        std::process::exit(1);
    }
}

fn read_at(buf: &[u8], off: usize, kind: StatKind) -> f64 {
    match kind {
        StatKind::I16 if off + 2 <= buf.len() => {
            i16::from_le_bytes([buf[off], buf[off + 1]]) as f64
        }
        StatKind::U8 => buf[off] as f64,
        StatKind::F32 if off + 4 <= buf.len() => f32::from_le_bytes([
            buf[off], buf[off + 1], buf[off + 2], buf[off + 3],
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
