//! First real edit: change a villager's hit points, then prove the bytes moved
//! exactly where intended and nowhere else.
//!
//! The gate is not "it built".  A `.dat` write that changes the wrong byte is
//! indistinguishable from one that changed nothing, because the game silently
//! ignores a record it cannot resolve.  So this asserts three things:
//!
//!  1. the output differs from the input in EXACTLY the bytes it should;
//!  2. parsing the output shows the new hit points on the intended record and
//!     the old value everywhere else;
//!  3. the output still parses to its own length (nothing shifted).
use aoe2mod_dat::writer::Writer;
use aoe2mod_dat::write23::{write_stage1, write_stages23};
use aoe2mod_dat::write47::write_stages47;
use aoe2mod_dat::write810::write_stages810;
use aoe2mod_dat::{
    load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
};
use std::path::Path;

const VILLAGER: i16 = 83;

fn main() {
    let path = std::env::args().nth(1).expect("dat path");
    let new_hp: i16 = std::env::args()
        .nth(2)
        .and_then(|s| s.parse().ok())
        .unwrap_or(1000);
    let (raw, _how) = load_dat(Path::new(&path)).expect("load");

    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).expect("s1");
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).expect("s23");
    let s47 = read_stages47(&mut r, gv).expect("s47");
    let mut s810 = read_stages810(&mut r, gv).expect("s810");

    // Find the intended record in Gaia, and record where it lives in the stream.
    let mut hit: Option<(usize, usize, i16)> = None; // (civ, index, old_hp)
    for (ci, c) in s810.civs.iter().enumerate() {
        for (ui, u) in c.units.iter().enumerate() {
            if u.id == VILLAGER {
                hit = Some((ci, ui, u.hit_points));
                break;
            }
        }
        if hit.is_some() {
            break;
        }
    }
    let (ci, ui, old_hp) = match hit {
        Some(v) => v,
        None => {
            eprintln!("unit {VILLAGER} not found");
            std::process::exit(1);
        }
    };
    let off = s810.civs[ci].units[ui].hit_points_offset;
    println!(
        "unit {}: civ {} ({}) old hp {} at offset {} -> {}",
        VILLAGER, ci, s810.civs[ci].name, old_hp, off, new_hp
    );

    // THE EDIT: write the new value into the captured record image.
    let img = s810.civs[ci].units[ui]
        .image
        .as_mut()
        .expect("record image");
    img[off..off + 2].copy_from_slice(&new_hp.to_le_bytes());
    s810.civs[ci].units[ui].hit_points = new_hp;

    // Re-emit everything.
    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).expect("w1");
    write_stages23(&mut w, &s23, &raw).expect("w23");
    write_stages47(&mut w, &s47, gv).expect("w47");
    write_stages810(&mut w, &s810).expect("w810");
    let out = w.out.clone();

    // ---- 1. exactly which bytes differ -----------------------------------
    assert_eq!(out.len(), raw.len(), "length changed");
    let mut diffs = Vec::new();
    for (i, (a, b)) in raw.iter().zip(out.iter()).enumerate() {
        if a != b {
            diffs.push((i, *a, *b));
        }
    }
    println!("bytes differing: {} -> {:?}", diffs.len(), &diffs[..diffs.len().min(8)]);

    // ---- 2. re-parse the OUTPUT ------------------------------------------
    let mut r2 = Reader::new(&out);
    let o1 = read_stage1(&mut r2).expect("o1");
    let o23 = read_stages23(&mut r2).expect("o23");
    let o47 = read_stages47(&mut r2, o1.game_version).expect("o47");
    let o810 = read_stages810(&mut r2, o1.game_version).expect("o810");

    // ---- 3. nothing shifted ----------------------------------------------
    let clean = r2.pos == out.len();
    println!("reparse clean: {}", clean);
    let _ = (&o23, &o47);

    let got = o810.civs[ci].units[ui].hit_points;
    let mut others_changed = 0;
    for (c2, c1) in o810.civs.iter().zip(s810.civs.iter()) {
        for (u2, u1) in c2.units.iter().zip(c1.units.iter()) {
            if u2.id == VILLAGER && std::ptr::eq(c2, &o810.civs[ci]) {
                continue;
            }
            if u2.hit_points != u1.hit_points {
                others_changed += 1;
            }
        }
    }
    println!("reparsed hp   : {} (want {})", got, new_hp);
    println!("other records changed: {}", others_changed);

    let ok = diffs.len() == 2 && got == new_hp && clean && others_changed == 0;
    println!("{}", if ok { "EDIT OK" } else { "EDIT FAILED" });

    // Save the modified stream raw-deflated, which is what a mod ships.
    if ok {
        let dst = std::env::args().nth(3);
        if let Some(dst) = dst {
            use flate2::write::DeflateEncoder;
            use flate2::Compression;
            use std::io::Write;
            let f = std::fs::File::create(&dst).expect("create");
            let mut e = DeflateEncoder::new(f, Compression::default());
            e.write_all(&out).expect("deflate");
            e.finish().expect("finish");
            println!("wrote {}", dst);
        }
    }
    if !ok {
        std::process::exit(1);
    }
}
