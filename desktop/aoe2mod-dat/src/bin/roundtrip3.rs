//! Round-trip stages 1-3 from the model, then copy the rest.
use aoe2mod_dat::writer::{RoundTrip, Writer};
use aoe2mod_dat::write23::{write_stage1, write_stages23};
use aoe2mod_dat::{load_dat, read_stage1, read_stages23, Reader};
use std::path::Path;

fn main() {
    let path = std::env::args().nth(1).expect("dat path");
    let (raw, _how) = load_dat(Path::new(&path)).expect("load");

    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).expect("stage1");
    let s23 = read_stages23(&mut r).expect("stages23");
    let pos3 = r.pos;

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).expect("write stage1");
    let after1 = w.raw_pos();
    write_stages23(&mut w, &s23, &raw).expect("write stages23");
    let after3 = w.raw_pos();

    // Everything past stage 3 is not modeled yet: replay it verbatim.  This is
    // what isolates a stage-2/3 width error from anything later.
    let rest = raw.len() - after3;
    w.op(rest).expect("rest");

    let rt = RoundTrip {
        out_len: w.out.len(),
        raw_len: raw.len(),
        mismatches: w.mismatches,
        first_mismatch: w.first_mismatch,
        identical: w.out == raw,
    };
    println!("parse stage1 end : {}", after1);
    println!("parse stage3 end : {}", pos3);
    println!("write stage3 end : {}", after3);
    println!("round trip       : {}", rt.report());
    if !rt.identical {
        std::process::exit(1);
    }
}
