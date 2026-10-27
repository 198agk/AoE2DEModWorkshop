//! Binary-search the first unit whose span differs from Python's, then dump it.
use aoe2mod_dat::{load_dat, read_stage1, read_stages23, read_stages47, Reader};
use std::path::Path;

fn main() {
    let path = std::env::args().nth(1).expect("dat path");
    // optional: stop after N units to bisect manually
    let limit: usize = std::env::args()
        .nth(2)
        .and_then(|s| s.parse().ok())
        .unwrap_or(usize::MAX);

    let (raw, _how) = load_dat(Path::new(&path)).expect("load");
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).expect("stage1");
    let gv = s1.game_version;
    let _ = read_stages23(&mut r).expect("stages23");
    let _ = read_stages47(&mut r, gv).expect("stages47");

    let _civ_count = r.i16().expect("civ_count");
    let _ = r.u8().expect("pt");
    let name = r.debug_string().expect("name").1;
    let n = r.i16().expect("n");
    let _ = r.i16().expect("tt");
    let _ = r.i16().expect("tb");
    r.skip(4 * n.max(0) as usize).expect("res");
    let _ = r.u8().expect("iconset");
    let m = r.i16().expect("m");
    let mut ptrs = Vec::new();
    for _ in 0..m.max(0) {
        ptrs.push(r.i32().expect("ptr"));
    }
    println!("civ {} ptrs {}", name, m);

    let mut idx = 0usize;
    for p in ptrs {
        if p == 0 {
            continue;
        }
        if idx >= limit {
            println!("stopped at unit idx {} pos {}", idx, r.pos);
            return;
        }
        let u_start = r.pos;
        match aoe2mod_dat::read_unit(&mut r, gv) {
            Ok(u) => {
                let span = r.pos - u_start;
                if idx < 8 || (idx >= 1390 && idx <= 1400) {
                    println!("  idx {:<5} id={:<6} type={:<3} span={:<5} start={}",
                             idx, u.id, u.unit_type, span, u_start);
                }
            }
            Err(e) => {
                println!("  FAILED at idx {} pos {}: {}", idx, r.pos, e);
                return;
            }
        }
        idx += 1;
    }
    println!("all {} units, end {}", idx, r.pos);
}
