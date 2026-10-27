//! Dumps every byte mark the reader now records, for one civilisations' units.
//!
//! The marks exist so that `unit.cost` and `unit.attack_class` can be written
//! as "write this value at this measured offset".  A mark that is off by one
//! byte still produces a plausible number, so this binary exists to be diffed
//! against `aoe2mod/dat/locate.py`, which measures the same bytes by walking
//! them a different way.
//!
//! Usage: `marks <dat> <civ-index> <unit-id,...>`
//!
//! Output is one line per mark, sorted, so `diff` against the Python dump is a
//! straight comparison rather than a visual one.

use aoe2mod_dat::{load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader};
use std::env;
use std::path::Path;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    let path = args.get(1).cloned().unwrap_or_else(|| {
        "d:/games/steam/steamapps/common/AoE2DE/resources/_common/dat/empires2_x2_p1.dat"
            .to_string()
    });
    let civ_index: usize = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(1);
    let want: Vec<i16> = args
        .get(3)
        .map(|s| s.split(',').filter_map(|x| x.parse().ok()).collect())
        .unwrap_or_else(|| vec![4, 74, 82, 83]);

    let buf = load_dat(Path::new(&path))?.0;
    let mut r = Reader::new(&buf);
    let gv = read_stage1(&mut r)?.game_version;
    read_stages23(&mut r)?;
    read_stages47(&mut r, gv)?;
    let s = read_stages810(&mut r, gv)?;
    let civ = s
        .civs
        .get(civ_index)
        .ok_or_else(|| format!("no civ at index {civ_index}"))?;

    for u in &civ.units {
        if !want.contains(&u.id) {
            continue;
        }
        println!("unit {}  type {}", u.id, u.unit_type);
        for c in &u.costs {
            println!(
                "  cost     {:>3} amount {:>7} @ {}",
                c.type_, c.amount, c.amount_offset
            );
        }
        if let Some(t) = &u.type50 {
            for a in &t.attacks {
                println!(
                    "  attack   {:>3} amount {:>7} @ {}",
                    a.class, a.amount, a.amount_offset
                );
            }
            for a in &t.armors {
                println!(
                    "  armour   {:>3} amount {:>7} @ {}",
                    a.class, a.amount, a.amount_offset
                );
            }
            println!("  displayed_attack        @ {}", t.displayed_attack.offset);
            println!(
                "  displayed_melee_armour  @ {}",
                t.displayed_melee_armour.offset
            );
            println!("  max_range               @ {}", t.max_range.offset);
            println!("  reload_time             @ {}", t.reload_time.offset);
        }
        if let Some(m) = &u.displayed_pierce_armour {
            println!("  displayed_pierce_armour @ {}", m.offset);
        }
    }
    Ok(())
}
