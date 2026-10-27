//! Full parse: every stage, comparing against the offsets the baseline pins.
use aoe2mod_dat::{load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader};
use std::path::Path;

fn main() {
    let path = std::env::args().nth(1).expect("dat path");
    let t0 = std::time::Instant::now();
    let (raw, _how) = load_dat(Path::new(&path)).expect("load");
    let t_load = t0.elapsed();

    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).expect("stage1");
    let gv = s1.game_version;
    let _ = read_stages23(&mut r).expect("stages23");
    let pos3 = r.pos;
    let _ = read_stages47(&mut r, gv).expect("stages47");
    let pos7 = r.pos;
    let s = read_stages810(&mut r, gv).expect("stages810");
    let pos10 = r.pos;
    let total = t0.elapsed();

    println!("gv          : {}", gv);
    println!("after_s3    : {}", pos3);
    println!("after_s7    : {}", pos7);
    println!("after_s10   : {}", pos10);
    println!("raw bytes   : {}", raw.len());
    println!("eof clean   : {}", pos10 == raw.len());
    println!("civs        : {}", s.civs.len());
    println!("techs       : {}", s.techs.len());
    println!("time_slice  : {}", s.time_slice);
    println!("techtree    : ages={} buildings={} units={} research={} groups={}",
             s.tech_tree.ages, s.tech_tree.buildings, s.tech_tree.units,
             s.tech_tree.research, s.tech_tree.total_unit_tech_groups);
    println!("load ms     : {}", t_load.as_millis());
    println!("total ms    : {}", total.as_millis());

    for c in s.civs.iter().take(3) {
        println!("civ         : {:<10} units={:<5} ptrs={}/{} ttree={}",
                 c.name, c.units.len(), c.unit_pointers_nonzero,
                 c.unit_pointers_total, c.tech_tree_id);
    }
    if let Some(c) = s.civs.first() {
        println!("gaia unit[0]: id={} type={} hp={} name={:?} tsg={}",
                 c.units.first().map(|u| u.id).unwrap_or(-1),
                 c.units.first().map(|u| u.unit_type).unwrap_or(0),
                 c.units.first().map(|u| u.hit_points).unwrap_or(0),
                 c.units.first().map(|u| u.name.as_str()).unwrap_or(""),
                 c.units.first().map(|u| u.task_swap_group).unwrap_or(0));
        let vil = c.units.iter().find(|u| u.name.contains("Villager"));
        if let Some(v) = vil {
            println!("gaia villager: id={} hp={} name={:?} tsg={}",
                     v.id, v.hit_points, v.name, v.task_swap_group);
        }
    }
    if let Some(t) = s.techs.first() {
        println!("tech[0]     : civ={} name={:?} effect={}", t.civ, t.name, t.effect_id);
    }
    if let Some(t) = s.techs.last() {
        println!("tech[last]  : civ={} name={:?}", t.civ, t.name);
    }
}
