//! Stage 8-10 writers.
//!
//! A unit record is not written field by field, and that is a deliberate
//! decision copied from `aoe2mod/dat/writer.py`:
//!
//! > A unit record's tail is type-dependent (Type50 / Projectile / Creatable /
//! > Building, each with its own version guards), so rebuilding it from zeros
//! > would be one guess per field.
//!
//! So a record carries the BYTES it was read from (`Unit.image`) and those are
//! emitted verbatim.  A clone of an existing record is exactly right by
//! construction; a reconstruction is right only if every one of ~40
//! version-guarded guesses is right.
//!
//! The same applies to a civilization, whose 2,693 unit records are 89 MB of
//! the file.
//!
//! What this means for editing: changing a field means changing the bytes at a
//! known offset inside `image`, which is precise and testable.  It does NOT mean
//! this writer cannot express an edit -- it means an edit must name its offset,
//! and the round trip proves the offset bookkeeping before any edit touches it.

use crate::writer::Writer;
use crate::Stages810;
use std::io;

/// Emit one unit record from its captured bytes.
fn write_unit(w: &mut Writer<'_>, u: &crate::Unit) -> io::Result<()> {
    match &u.image {
        Some(bytes) => {
            w.push_bytes(bytes);
            // The push advanced the OUTPUT only; the input cursor must advance
            // by the same span so the verbatim replay stays aligned.
            w.advance_raw(bytes.len())
        }
        None => Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!(
                "unit id={} has no byte image; stage 8 cannot re-emit it",
                u.id
            ),
        )),
    }
}

fn write_civ(w: &mut Writer<'_>, c: &crate::Civ) -> io::Result<()> {
    w.u8(c.player_type);
    w.debug_string(c.name_marker, &c.name, Some(c.name_len))?;
    w.i16(c.resources.len() as i16);
    w.i16(c.tech_tree_id);
    w.i16(c.team_bonus_id);
    for &v in &c.resources {
        w.f32(v);
    }
    w.u8(c.icon_set);
    w.i16(c.unit_pointers_total);
    // The pointer array's VALUES are not modeled (only how many are non-zero),
    // so it is copied: `8,857 unit records` depends on the exact pattern of
    // which slots are empty, and a rebuilt array that got one slot wrong would
    // shift every following record.
    w.op(4 * c.unit_pointers_total.max(0) as usize)?;
    for u in &c.units {
        write_unit(w, u)?;
    }
    Ok(())
}

fn write_tech(w: &mut Writer<'_>, t: &crate::Tech) -> io::Result<()> {
    match &t.image {
        Some(bytes) => {
            w.push_bytes(bytes);
            w.advance_raw(bytes.len())
        }
        None => Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!("tech {:?} has no byte image", t.name),
        )),
    }
}

pub fn write_stages810(w: &mut Writer<'_>, s: &Stages810) -> io::Result<()> {
    w.i16(s.civs.len() as i16);
    for c in &s.civs {
        write_civ(w, c)?;
    }
    w.i16(s.techs.len() as i16);
    for t in &s.techs {
        write_tech(w, t)?;
    }
    w.i32(s.time_slice);
    w.op(4 * 6)?; // unit_kill_rate .. razing_kill_total
    match &s.tech_tree_image {
        Some(bytes) => {
            w.push_bytes(bytes);
            w.advance_raw(bytes.len())
        }
        None => Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "tech tree has no byte image",
        )),
    }
}
