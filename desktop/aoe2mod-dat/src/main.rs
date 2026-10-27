//! Read the retail `.dat` stage 1 and print what the baseline expects.
//!
//! Usage:
//!   cargo run --release -- <path to empires2_x2_p1.dat>
//!
//! The point is to compare with `_golden/dat_baseline.json`.  Printing "it
//! parsed" is not evidence; printing the same counts and the same end offset is.

use aoe2mod_dat::{load_dat, read_stage1, Reader};
use std::path::Path;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let path = match args.get(1) {
        Some(p) => p.clone(),
        None => {
            eprintln!("usage: aoe2mod-dat <empires2_x2_p1.dat> [--json]");
            std::process::exit(2);
        }
    };
    let as_json = args.iter().any(|a| a == "--json");

    let (raw, how) = match load_dat(Path::new(&path)) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("load failed: {e}");
            std::process::exit(1);
        }
    };

    let mut r = Reader::new(&raw);
    let s1 = match read_stage1(&mut r) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("stage1 failed at {}: {e}", r.pos);
            std::process::exit(1);
        }
    };

    if as_json {
        // Emitted by hand rather than via serde: the shape is small, and a
        // comparison probe needs the exact field names the Python side uses.
        let mut out = String::new();
        out.push('{');
        out.push_str(&format!("\"end_pos\":{},", r.pos));
        out.push_str(&format!(
            "\"file_version\":\"{}\",",
            s1.file_version.trim_end_matches('\u{0}')
        ));
        out.push_str(&format!("\"game_version\":{},", s1.game_version));
        out.push_str(&format!(
            "\"terrain_restriction_count\":{},",
            s1.terrain_restriction_count
        ));
        out.push_str(&format!("\"terrains_used1\":{},", s1.terrains_used1));
        out.push_str(&format!(
            "\"float_ptr\":{:?},",
            s1.float_ptr_terrain_tables
        ));
        out.push_str(&format!(
            "\"pass_ptr\":{:?},",
            s1.terrain_pass_graphic_pointers
        ));
        out.push_str("\"restrictions\":[");
        for (i, t) in s1.terrain_restrictions.iter().enumerate() {
            if i > 0 {
                out.push(',');
            }
            out.push_str("{\"mult\":[");
            for (j, m) in t.mult.iter().enumerate() {
                if j > 0 {
                    out.push(',');
                }
                // 6 decimal places, matching the Python probe's rounding, so
                // float formatting differences cannot masquerade as a bug.
                out.push_str(&format!("{:.6}", m));
            }
            out.push_str("],\"pass\":[");
            for (j, (a, b, c, f)) in t.pass.iter().enumerate() {
                if j > 0 {
                    out.push(',');
                }
                out.push_str(&format!("[{},{},{},{:.6}]", a, b, c, f));
            }
            out.push_str("]}");
        }
        out.push_str("],");
        out.push_str(&format!(
            "\"player_colour_count\":{},",
            s1.player_colour_count
        ));
        out.push_str("\"player_colours\":[");
        for (i, c) in s1.player_colours.iter().enumerate() {
            if i > 0 {
                out.push(',');
            }
            out.push_str(&format!("{:?}", c));
        }
        out.push_str("]}");
        println!("{out}");
        return;
    }

    println!("load      : {how}");
    println!("raw bytes : {}", raw.len());
    println!("head      : {:?}", String::from_utf8_lossy(&raw[..8]));
    println!("version   : {:?}", s1.file_version.trim_end_matches('\u{0}'));
    println!("game_ver  : {}", s1.game_version);
    println!("terr_restr: {}", s1.terrain_restriction_count);
    println!("terr_used : {}", s1.terrains_used1);
    println!("colours   : {}", s1.player_colour_count);
    println!("after S1  : {} (0x{:X})", r.pos, r.pos);
    if let Some(t) = s1.terrain_restrictions.first() {
        println!("  restr[0].mult  : {:?}", &t.mult[..t.mult.len().min(6)]);
        println!("  restr[0].pass0 : {:?}", t.pass.first());
    }
    if let Some(c) = s1.player_colours.first() {
        println!("  colour[0]      : {c:?}");
    }
}
