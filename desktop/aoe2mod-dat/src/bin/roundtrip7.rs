//! Round-trip stages 1-7, then copy the rest.
use aoe2mod_dat::writer::{RoundTrip, Writer};
use aoe2mod_dat::write23::{write_stage1, write_stages23};
use aoe2mod_dat::write47::write_stages47;
use aoe2mod_dat::{load_dat, read_stage1, read_stages23, read_stages47, Reader};
use std::path::Path;

fn main() {
    let path = std::env::args().nth(1).expect("dat path");
    let (raw, _how) = load_dat(Path::new(&path)).expect("load");

    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).expect("stage1");
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).expect("stages23");
    let pos3 = r.pos;
    let s47 = read_stages47(&mut r, gv).expect("stages47");
    let pos7 = r.pos;

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).expect("w1");
    write_stages23(&mut w, &s23, &raw).expect("w23");
    let w3 = w.raw_pos();
    write_stages47(&mut w, &s47, gv).expect("w47");
    let w7 = w.raw_pos();

    let rest = raw.len() - w7;
    w.op(rest).expect("rest");

    let rt = RoundTrip {
        out_len: w.out.len(),
        raw_len: raw.len(),
        mismatches: w.mismatches,
        first_mismatch: w.first_mismatch,
        identical: w.out == raw,
    };
    println!("parse  s3 {} s7 {}", pos3, pos7);
    println!("write  s3 {} s7 {}", w3, w7);
    println!("round trip  : {}", rt.report());
    if !rt.identical {
        std::process::exit(1);
    }
}
