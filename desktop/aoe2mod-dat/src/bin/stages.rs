//! Compare stages 1-3 against the Python original.
use aoe2mod_dat::{load_dat, read_stage1, read_stages23, Reader, FILE_VERSION_SIZE};
use std::path::Path;

fn main() {
    let path = std::env::args().nth(1).expect("dat path");
    let (raw, _how) = load_dat(Path::new(&path)).expect("load");
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).expect("stage1");
    let pos_s1 = r.pos;
    let s = read_stages23(&mut r).expect("stages23");

    println!("stage1_end   : {}", pos_s1);
    println!("stage1_ver   : {:?} gv={}", s1.file_version.trim_end_matches('\u{0}'), s1.game_version);
    println!("sounds       : {}", s.sounds.len());
    println!("graphic_ptr  : {} nonzero", s.graphic_pointers_nonzero);
    println!("graphics     : {}", s.graphics.len());
    println!("after_s3     : {}", r.pos);

    // Spot facts the Python side reports, so a diff has somewhere to point.
    if let Some(snd) = s.sounds.first() {
        println!("sound[0]     : id={} items={} cache={}", snd.id, snd.items.len(), snd.cache_time);
        if let Some(it) = snd.items.first() {
            println!("sound[0].it0 : {:?}", it.file);
        }
    }
    if let Some(g) = s.graphics.first() {
        println!("gfx[0]       : id={} name={:?} file={:?}", g.id, g.name, g.file);
        println!("               slp={} frames={} angles={} deltas={}",
                 g.slp, g.frame_count, g.angle_count, g.deltas.len());
        println!("               widths {:?} {:?} {:?}", g.name_len, g.file_len, g.particle_len);
    }
    if let Some(g) = s.graphics.last() {
        println!("gfx[last]    : id={} name={:?} file={:?}", g.id, g.name, g.file);
    }
    let _ = FILE_VERSION_SIZE;
}
