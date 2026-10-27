//! Stage 2-3 writers: sounds and graphics, re-emitted rather than copied.
//!
//! Everything the model carries is written from the model; everything it does
//! not carry is copied from the input with `op()`.  The 13 bytes between
//! `angle_count` and `id` are the clearest example of why: they are
//! SpeedMultiplier, FrameDuration, ReplayDelay and SequenceType, the engine
//! rewrites FrameDuration, and a reconstructed value could never be trusted.
//! Copying them keeps a round trip exact while leaving them unmodeled.

use crate::writer::Writer;
use crate::{
    read_sound, read_stages23, read_stage1, Reader, Stage1, Stages23,
};
use std::io;

pub fn write_stage1(w: &mut Writer<'_>, s1: &Stage1) -> io::Result<()> {
    w.fixed_string(s1.file_version.trim_end_matches('\u{0}'), 8)?;
    w.i16(s1.terrain_restriction_count);
    w.i16(s1.terrains_used1);
    for &v in &s1.float_ptr_terrain_tables {
        w.i32(v);
    }
    for &v in &s1.terrain_pass_graphic_pointers {
        w.i32(v);
    }
    for t in &s1.terrain_restrictions {
        for &m in &t.mult {
            w.f32(m);
        }
        for &(a, b, c, f) in &t.pass {
            w.i32(a);
            w.i32(b);
            w.i32(c);
            w.f32(f);
        }
    }
    w.i16(s1.player_colour_count);
    for c in &s1.player_colours {
        for &v in c {
            w.i32(v);
        }
    }
    Ok(())
}

fn write_sound(w: &mut Writer<'_>, snd: &crate::Sound) -> io::Result<()> {
    w.i16(snd.id);
    w.i16(snd.play_delay);
    w.i16(snd.items.len() as i16);
    w.i32(snd.cache_time);
    w.i16(snd.total_probability);
    for it in &snd.items {
        // `debug_string` writes the marker AND the length itself, and advances
        // the input cursor by `4 + stored_len`.  An earlier version copied those
        // 4 bytes with `op(4)` first and then called `debug_string`, which
        // emitted marker+len a second time: 4 extra bytes per sound item,
        // 20,504 bytes of drift by the end of stage 3, and 2,377,056 mismatches.
        w.debug_string(it.marker, &it.file, Some(it.file_len))?;
        w.i32(it.resource_id);
        w.i16(it.probability);
        w.i16(it.civilization);
        w.i16(it.iconset);
    }
    Ok(())
}

fn write_graphic(w: &mut Writer<'_>, g: &crate::Graphic) -> io::Result<()> {
    w.debug_string(g.name_marker, &g.name, Some(g.name_len))?;
    // `file_len` is the width the INPUT used.  Passing it is what lets a reskin
    // point the record at a longer filename while every later verbatim read
    // stays aligned; without it the input cursor lands inside the next field.
    w.debug_string(g.file_marker, &g.file, Some(g.file_len))?;
    w.debug_string(g.particle_marker, &g.particle_effect, Some(g.particle_len))?;
    w.i32(g.slp);
    w.u8(g.is_loaded);
    w.u8(g.old_color_flag);
    w.u8(g.layer);
    w.i16(g.player_color);
    w.u8(g.transparent_selection);
    for &v in &g.coordinates {
        w.i16(v);
    }
    w.i16(g.deltas.len() as i16);
    w.i16(g.sound_id);
    w.u32(g.wwise_sound_id);
    w.u8(g.angle_sounds_used);
    w.i16(g.frame_count);
    w.i16(g.angle_count);
    // NOT modeled on purpose: SpeedMultiplier, FrameDuration, ReplayDelay
    // (3 x f32) and SequenceType (u8) -- 13 bytes, copied verbatim.
    w.op(13)?;
    w.i16(g.id);
    w.u8(g.mirroring_mode);
    w.u8(g.editor_flag);
    for d in &g.deltas {
        w.i16(d.0);
        w.i16(d.1);
        w.i32(d.2);
        w.i16(d.3);
        w.i16(d.4);
        w.i16(d.5);
        w.i16(d.6);
    }
    if g.angle_sounds_used != 0 {
        for trio in &g.angle_sounds {
            for &(a, b, c) in trio.iter() {
                w.i16(a);
                w.i16(b);
                w.u32(c);
            }
        }
    }
    Ok(())
}

pub fn write_stages23(w: &mut Writer<'_>, s: &Stages23, raw: &[u8]) -> io::Result<()> {
    w.i16(s.sounds.len() as i16);
    for snd in &s.sounds {
        write_sound(w, snd)?;
    }
    // The graphics pointer array is a presence flag per slot; its values are
    // not modeled, so it is copied.  The record count is derived from it, which
    // is why `graphic_count` (slots) and `graphics.len()` (records) differ.
    let slots = s.graphic_pointers_nonzero + (s.graphics.len() - s.graphic_pointers_nonzero);
    let _ = slots;
    w.i16(s.graphic_count);
    w.op(4 * s.graphic_count as usize)?;
    for g in &s.graphics {
        write_graphic(w, g)?;
    }
    let _ = raw;
    Ok(())
}

/// Parse and re-emit stages 1-3, then leave the rest to the caller.
pub fn reemit_13(raw: &[u8]) -> io::Result<(Writer<'_>, Stage1, usize)> {
    let mut r = Reader::new(raw);
    let s1 = read_stage1(&mut r)?;
    let s23 = read_stages23(&mut r)?;
    let pos = r.pos;
    let mut w = Writer::new(raw);
    write_stage1(&mut w, &s1)?;
    write_stages23(&mut w, &s23, raw)?;
    Ok((w, s1, pos))
}

/// Kept so the crate does not warn while the API settles.
pub fn _unused(r: &mut Reader<'_>) -> io::Result<()> {
    let _ = read_sound(r)?;
    Ok(())
}
