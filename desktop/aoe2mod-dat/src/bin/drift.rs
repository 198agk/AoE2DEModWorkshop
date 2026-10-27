//! Isolate where stage 8-10 drifts: feed Python's stage boundaries in as targets.
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
    println!("at stage8 start: {} (python 3899440)", r.pos);

    let civ_count = r.i16().expect("civ_count");
    println!("civ_count: {} (python 63)", civ_count);
    for i in 0..civ_count {
        let before = r.pos;
        match aoe2mod_dat::read_civ(&mut r, gv) {
            Ok(c) => {
                if i < 3 || i == civ_count - 1 {
                    println!("  civ[{}] {:<10} units={:<5} span={}", i, c.name,
                             c.units.len(), r.pos - before);
                }
            }
            Err(e) => {
                println!("  civ[{}] FAILED at {} after {} bytes: {}", i, r.pos,
                         r.pos - before, e);
                return;
            }
        }
    }
    println!("after civs: {} (python 92941571)", r.pos);

    let tech_count = r.i16().expect("tech_count");
    println!("tech_count: {} (python 1510)", tech_count);
    for i in 0..tech_count {
        let before = r.pos;
        match aoe2mod_dat::read_tech(&mut r, gv) {
            Ok(_t) => {
                if i < 2 {
                    println!("  tech[{}] span={}", i, r.pos - before);
                }
            }
            Err(e) => {
                println!("  tech[{}] FAILED at {} after {} bytes: {}", i, r.pos,
                         r.pos - before, e);
                return;
            }
        }
    }
    println!("after techs: {} (python 93154676)", r.pos);
    let ts = r.i32().expect("time_slice");
    println!("time_slice: {} (python 30)", ts);
    let _ = r.skip(4 * 6);
    println!("at techtree: {} (python 93154604?)", r.pos);
    match aoe2mod_dat::read_tech_tree(&mut r, gv) {
        Ok(tt) => println!("techtree ok: ages={} bld={} units={} res={} end={} (python 0x058F28B8 = {})",
                           tt.ages, tt.buildings, tt.units, tt.research, r.pos, 0x058F28B8),
        Err(e) => println!("techtree FAILED at {}: {}", r.pos, e),
    }
}
