//! Per-unit span comparison against `_golden/unit_spans.json`.
//!
//! Prints the FIRST record whose byte span differs, with its type, because the
//! type names which sub-block is mis-sized.  Without this the only symptom is
//! "Gaia is 2 MB too long", which points at nothing.
use aoe2mod_dat::{load_dat, read_stage1, read_stages23, read_stages47, Reader};
use std::path::Path;

fn main() {
    let path = std::env::args().nth(1).expect("dat path");
    let (raw, _how) = load_dat(Path::new(&path)).expect("load");
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).expect("stage1");
    let gv = s1.game_version;
    let _ = read_stages23(&mut r).expect("stages23");
    let _ = read_stages47(&mut r, gv).expect("stages47");
    println!("stage8 start: {}", r.pos);

    let civ_count = r.i16().expect("civ_count");
    for ci in 0..2.min(civ_count) {
        let _ = ci;
        let c_start = r.pos;
        let _player_type = r.u8().expect("pt");
        let name = r.debug_string().expect("name").1;
        let n = r.i16().expect("n");
        let _ = r.i16().expect("tt"); // tech_tree_id
        let _ = r.i16().expect("tb"); // team_bonus_id
        r.skip(4 * n.max(0) as usize).expect("resources");
        let _ = r.u8().expect("iconset");
        let m = r.i16().expect("m");
        let mut ptrs = Vec::with_capacity(m.max(0) as usize);
        for _ in 0..m.max(0) {
            ptrs.push(r.i32().expect("ptr"));
        }
        println!("civ {}: {} ({} ptrs)", ci, name, m);

        let mut spans: Vec<(i16, u8, usize)> = Vec::new();
        for p in ptrs {
            if p == 0 {
                continue;
            }
            let u_start = r.pos;
            match aoe2mod_dat::read_unit(&mut r, gv) {
                Ok(u) => spans.push((u.id, u.unit_type, r.pos - u_start)),
                Err(e) => {
                    println!("  FAILED at unit idx {} pos {}: {}", spans.len(), r.pos, e);
                    return;
                }
            }
        }
        let total = r.pos - c_start;
        println!("  {} units, span {}", spans.len(), total);

        // Aggregate by type, so a systematic error shows as a count mismatch
        // rather than a single offset.
        for t in [10u8, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90] {
            let got: Vec<usize> = spans.iter().filter(|s| s.1 == t).map(|s| s.2).collect();
            if got.is_empty() {
                continue;
            }
            let n = got.len();
            let sum: usize = got.iter().sum();
            println!("  type {:<3} n={:<4} total={:<9} avg={}", t, n, sum, sum / n);
        }
        // First 4 individual spans, to compare with Python's json by hand.
        for s in spans.iter().take(4) {
            println!("    unit id={} type={} span={}", s.0, s.1, s.2);
        }
    }
}
