//! Whole-file round trip: every stage re-emitted, then compared.
use aoe2mod_dat::writer::{RoundTrip, Writer};
use aoe2mod_dat::write23::{write_stage1, write_stages23};
use aoe2mod_dat::write47::write_stages47;
use aoe2mod_dat::write810::write_stages810;
use aoe2mod_dat::{
    load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
};
use std::path::Path;

fn main() {
    let path = std::env::args().nth(1).expect("dat path");
    let (raw, _how) = load_dat(Path::new(&path)).expect("load");

    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).expect("s1");
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).expect("s23");
    let s47 = read_stages47(&mut r, gv).expect("s47");
    let s810 = read_stages810(&mut r, gv).expect("s810");
    let parsed = r.pos;

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).expect("w1");
    write_stages23(&mut w, &s23, &raw).expect("w23");
    write_stages47(&mut w, &s47, gv).expect("w47");
    write_stages810(&mut w, &s810).expect("w810");

    let rt = RoundTrip {
        out_len: w.out.len(),
        raw_len: raw.len(),
        mismatches: w.mismatches,
        first_mismatch: w.first_mismatch,
        identical: w.out == raw,
    };
    println!("parsed   : {} / {}", parsed, raw.len());
    println!("written  : {}", w.out.len());
    println!("round trip: {}", rt.report());
    if !rt.identical {
        std::process::exit(1);
    }
}
