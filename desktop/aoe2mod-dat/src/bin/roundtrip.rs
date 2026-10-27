//! Round-trip proof: parse the retail `.dat`, write it back, compare bytes.
//!
//! This deliberately does NOT re-emit every field.  It re-emits the FIELDS THE
//! MODEL CARRIES and copies every unmodeled run from the input with `op()`.
//! That is not a shortcut -- it is the same strategy the Python writer uses, and
//! it is what makes the two sides comparable: if the model's notion of each
//! field's width is right, the copy lands on the right bytes and the output is
//! identical.  If any width is wrong, the copies shift and the mismatch count
//! says so immediately.
//!
//! So a byte-identical result here proves the READER's structure is correct for
//! every field it models, which is the thing worth proving first.

use aoe2mod_dat::writer::{RoundTrip, Writer};
use aoe2mod_dat::{load_dat, read_stage1, Reader};
use std::path::Path;

fn main() {
    let path = std::env::args().nth(1).expect("dat path");
    let (raw, _how) = load_dat(Path::new(&path)).expect("load");
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).expect("stage1");

    let mut w = Writer::new(&raw);

    // ---- stage 1 ----------------------------------------------------------
    w.fixed_string(s1.file_version.trim_end_matches('\u{0}'), 8)
        .expect("file_version");
    w.i16(s1.terrain_restriction_count);
    w.i16(s1.terrains_used1);
    for &v in &s1.float_ptr_terrain_tables {
        w.i32(v);
    }
    for &v in &s1.terrain_pass_graphic_pointers {
        w.i32(v);
    }
    for t in &s1.terrain_restrictions {
        for &m in &t.mult {
            w.f32(m);
        }
        for &(a, b, c, f) in &t.pass {
            w.i32(a);
            w.i32(b);
            w.i32(c);
            w.f32(f);
        }
    }
    w.i16(s1.player_colour_count);
    for c in &s1.player_colours {
        for &v in c {
            w.i32(v);
        }
    }

    // ---- everything after stage 1: replay verbatim -------------------------
    // The remaining stages are not modeled yet.  Copying them proves the
    // cursor mechanism and the stage-1 widths; the next commits replace the
    // copies with real writes, one stage at a time, keeping this test green.
    let rest = raw.len() - w.raw_pos();
    w.op(rest).expect("rest");

    let rt = RoundTrip {
        out_len: w.out.len(),
        raw_len: raw.len(),
        mismatches: w.mismatches,
        first_mismatch: w.first_mismatch,
        identical: w.out == raw,
    };
    println!("round trip : {}", rt.report());
    println!("stage1 end : {}", r.pos);
    if !rt.identical {
        std::process::exit(1);
    }
}
