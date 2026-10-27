//! Compare stages 4-7 against the Python original.
use aoe2mod_dat::{load_dat, read_stage1, read_stages23, read_stages47, Reader};
use std::path::Path;

fn main() {
    let path = std::env::args().nth(1).expect("dat path");
    let (raw, _how) = load_dat(Path::new(&path)).expect("load");
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).expect("stage1");
    let gv = s1.game_version;
    let _s23 = read_stages23(&mut r).expect("stages23");
    let pos_s3 = r.pos;
    let s47 = read_stages47(&mut r, gv).expect("stages47");

    println!("gv           : {}", gv);
    println!("after_s3     : {}", pos_s3);
    println!("after_s7     : {}", r.pos);
    println!("terrains     : {}", s47.terrain_block.terrains.len());
    println!("map_size     : {}x{}", s47.terrain_block.map_width, s47.terrain_block.map_height);
    println!("tile         : {}x{}", s47.terrain_block.tile_width, s47.terrain_block.tile_height);
    println!("terrains_used2: {}", s47.terrain_block.terrains_used2);
    println!("borders_used : {}", s47.terrain_block.borders_used);
    println!("max_terrain  : {}", s47.terrain_block.max_terrain);
    println!("fog_flag     : {}", s47.terrain_block.fog_flag);
    println!("random_maps  : {}", s47.random_map_count);
    println!("effects      : {}", s47.effects.len());
    println!("unit_headers : {}", s47.unit_headers.len());

    if let Some(t) = s47.terrain_block.terrains.first() {
        println!("terrain[0]   : name={:?} slp={} phantom={} passable={}",
                 t.name, t.slp, t.phantom, t.passable_terrain);
    }
    if let Some(e) = s47.effects.first() {
        println!("effect[0]    : name={:?} commands={}", e.name, e.commands.len());
    }
    let with_tasks = s47.unit_headers.iter().filter(|u| !u.tasks.is_empty()).count();
    println!("headers with tasks: {}", with_tasks);
    if let Some(u) = s47.unit_headers.iter().find(|u| !u.tasks.is_empty()) {
        println!("first header : exists={} tasks={} task0={:?}",
                 u.exists, u.tasks.len(), u.tasks.first().map(|t| (t.task_type, t.id, t.enabled)));
    }
}
