//! Per-sub-block spans for unit 0, to diff against the Python trace.
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

    let _ = r.i16().expect("civ_count");
    let _ = r.u8().expect("pt");
    let _ = r.debug_string().expect("name");
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
    println!("unit0 start {}", r.pos);
    let u0 = r.pos;

    match aoe2mod_dat::read_unit(&mut r, gv) {
        Ok(u) => {
            println!("type {}", u.unit_type);
            println!("unit0 end {} SPAN {}", r.pos, r.pos - u0);
            println!("id={} hp={} name={:?} tsg={}", u.id, u.hit_points, u.name, u.task_swap_group);
        }
        Err(e) => println!("FAILED: {e}"),
    }
    println!("python says SPAN 484 (common 156 / dead_fish 41 / bird 28 / type50 86 / creatable 126)");
}
