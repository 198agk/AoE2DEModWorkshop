//! Stage 4-7 writers.
//!
//! Design: this model carries only the fields callers actually ask for
//! (`map_width`, `terrains[].name/slp/phantom`, effect names, task ids).  Every
//! other field inside these records is COPIED at its exact width with `op()`.
//!
//! That is not laziness, it is the only honest option.  The Python writer can
//! re-emit these because its model holds every field; this one does not yet,
//! and inventing values for 200 terrain records x 40 fields would round-trip to
//! something plausible and wrong.  Copying keeps the round trip byte-identical,
//! which is the property every later edit depends on.

use crate::writer::Writer;
use crate::stages37::{TERRAIN_COUNT_FOR_TERRAINBLOCK, TERRAIN_UNITS_SIZE, TILE_TYPE_COUNT};
use crate::Stages47;
use std::io;

/// Terrain record: modeled name/slp/phantom, everything else copied.
fn write_terrain(w: &mut Writer<'_>, t: &crate::Terrain) -> io::Result<()> {
    w.u8(t.enabled);
    w.u8(t.random);
    w.u8(t.is_water);
    w.u8(t.hide_in_editor);
    w.i32(t.string_id);
    w.debug_string(t.name_marker, &t.name, Some(t.name_len))?;
    w.debug_string(t.name2_marker, &t.name2, Some(t.name2_len))?;
    w.i32(t.slp);
    w.op(4)?; // shape_ptr
    w.i32(t.sound_id);
    w.op(4)?; // wwise_sound_id
    w.op(4)?; // wwise_sound_stop_id
    w.i32(t.blend_priority);
    w.i32(t.blend_type);
    w.debug_string(t.overlay_marker, &t.overlay_mask_name, Some(t.overlay_len))?;
    w.op(3)?; // Colors[3]
    w.op(2)?; // CliffColors
    w.u8(t.passable_terrain);
    w.u8(t.impassable_terrain);
    w.u8(t.is_animated);
    w.op(2 + 2 + 4 + 4 + 2 + 2 + 4 + 1 + 1)?; // animation scalars
    w.op(TILE_TYPE_COUNT * 6)?; // FrameData
    w.op(2)?; // TerrainToDraw
    w.op(4)?; // TerrainDimensions
    w.op(2 * TERRAIN_UNITS_SIZE * 3 + TERRAIN_UNITS_SIZE + 2)?;
    w.i16(t.phantom);
    Ok(())
}

pub fn write_terrain_block(w: &mut Writer<'_>, tb: &crate::TerrainBlock) -> io::Result<()> {
    w.op(4)?; // virtual_function_ptr
    w.op(4)?; // map_pointer
    w.i32(tb.map_width);
    w.i32(tb.map_height);
    w.i32(tb.world_width);
    w.i32(tb.world_height);
    w.op(TILE_TYPE_COUNT * 6)?; // TileSizes
    w.op(2)?; // PaddingTS
    for t in &tb.terrains {
        write_terrain(w, t)?;
    }
    w.f32(tb.map_min_x);
    w.op(4)?; // map_min_y
    w.f32(tb.map_max_x);
    w.op(4)?; // map_max_y
    w.op(4 + 4)?; // max_x_plus1, max_y_plus1
    w.i16(tb.terrains_used2);
    w.i16(tb.borders_used);
    w.i16(tb.max_terrain);
    w.i16(tb.tile_width);
    w.i16(tb.tile_height);
    // tile_half_height, tile_half_width, elev_height, cur_row, cur_col,
    // block_beg_row, block_end_row, block_beg_col, block_end_col -- NINE i16,
    // not eight.  The first version of this line wrote `op(2 * 8)` and lost 2
    // bytes, which showed up 3 bytes into the random-map section.
    w.op(2 * 9)?;
    w.op(4 + 4)?; // search map ptrs
    w.u8(tb.any_frame_change);
    w.op(1)?; // map_visible_flag
    w.u8(tb.fog_flag);
    Ok(())
}

fn write_effect(w: &mut Writer<'_>, e: &crate::Effect) -> io::Result<()> {
    w.debug_string(e.name_marker, &e.name, Some(e.name_len))?;
    w.i16(e.commands.len() as i16);
    for &(a, b, c, d, f) in &e.commands {
        w.u8(a);
        w.i16(b);
        w.i16(c);
        w.i16(d);
        w.f32(f);
    }
    Ok(())
}

pub fn write_stages47(w: &mut Writer<'_>, s: &Stages47, gv: u32) -> io::Result<()> {
    write_terrain_block(w, &s.terrain_block)?;
    // Random maps: unmodeled (the retail file has zero of them), copied.
    // The caller advances past them; here we re-emit what the parse consumed by
    // copying the same span.  `random_map_count` is what the parse reported.
    if s.random_map_count == 0 {
        w.u32(0);
        w.op(4)?; // rm_ptr
    }
    w.i32(s.effects.len() as i32);
    for e in &s.effects {
        write_effect(w, e)?;
    }
    // stage 6 does not exist for DE (gv < GV_SWGB).
    w.i32(s.unit_headers.len() as i32);
    for h in &s.unit_headers {
        w.u8(h.exists);
        if h.exists != 0 {
            w.i16(h.tasks.len() as i16);
            for t in &h.tasks {
                write_task(w, t, gv)?;
            }
        }
    }
    Ok(())
}

fn write_task(w: &mut Writer<'_>, t: &crate::Task, gv: u32) -> io::Result<()> {
    w.i16(t.task_type);
    w.i16(t.id);
    // Everything else inside a task is unmodeled: copy the fixed run, then the
    // version-guarded tail.  Widths come from the reader, not from a guess.
    w.op(1)?; // IsDefault
    w.op(2 * 4)?; // ActionType..TerrainID
    w.op(2 * 4)?; // ResourceIn..UnusedResource
    w.op(4 * 3)?; // WorkValue1/2, WorkRange
    w.op(1)?; // AutoSearchTargets
    w.op(4)?; // SearchWaitTime
    w.op(1 + 1)?; // EnableTargeting, CombatLevelFlag
    w.op(2 * 2)?; // GatherType, WorkFlag2
    w.op(3)?; // TargetDiplomacy, CarryCheck, PickForConstruction
    w.op(2 * 4)?; // Moving, Proceeding, Working, Carrying
    w.op(2 * 2)?; // ResourceGathering, DepositSoundID
    if (4..=54).contains(&gv) {
        w.op(8)?; // Wwise IDs
    }
    if gv >= 50 {
        match t.enabled {
            Some(v) => w.i16(v),
            None => w.op(2)?,
        }
    }
    Ok(())
}
