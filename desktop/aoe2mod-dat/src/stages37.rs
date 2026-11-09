//! Stages 4-7: terrain block, effects, and unit headers.
//!
//! Split from `lib.rs` because these readers are mostly "read N bytes of a
//! structure nobody inspects", and keeping them next to the logic that matters
//! would bury it.
//!
//! Every field order here is transcribed from `aoe2mod/dat/parser.py`, not from
//! the format's documentation: the C++ names are not always in the order they
//! are written, and `read_task` alone has four run of same-width fields where
//! getting the order wrong still yields a readable parse.

use crate::Reader;
use std::io;

pub const TILE_TYPE_COUNT: usize = 19;
pub const TERRAIN_COUNT_FOR_TERRAINBLOCK: usize = 200;
pub const TERRAIN_UNITS_SIZE: usize = 30;

#[derive(Debug, Clone, Default)]
pub struct Terrain {
    pub enabled: u8,
    pub random: u8,
    pub is_water: u8,
    pub hide_in_editor: u8,
    pub string_id: i32,
    pub name: String,
    pub name2: String,
    /// Markers + stored widths for the three strings.  See `Graphic`: the
    /// marker is not constant, and a re-emit needs the INPUT width.
    pub name_marker: u16,
    pub name_len: u16,
    pub name2_marker: u16,
    pub name2_len: u16,
    pub slp: i32,
    pub sound_id: i32,
    pub blend_priority: i32,
    pub blend_type: i32,
    pub overlay_mask_name: String,
    pub overlay_marker: u16,
    pub overlay_len: u16,
    pub passable_terrain: u8,
    pub impassable_terrain: u8,
    pub is_animated: u8,
    /// Terrain.cpp:196 `if (gv < GV_SWGB) serialize<int16_t>(Phantom)`.
    /// GV_C32 (54) < GV_SWGB (55) is TRUE, so DE dats DO carry it -- reading
    /// this as absent shifts the rest of the file by 2 bytes.
    pub phantom: i16,
}

pub fn read_terrain(r: &mut Reader<'_>) -> io::Result<Terrain> {
    let mut t = Terrain::default();
    t.enabled = r.u8()?;
    t.random = r.u8()?;
    t.is_water = r.u8()?;
    t.hide_in_editor = r.u8()?;
    t.string_id = r.i32()?;
    let (name_marker, name, name_len) = r.debug_string()?;
    t.name = name;
    t.name_marker = name_marker;
    t.name_len = name_len;
    let (name2_marker, name2, name2_len) = r.debug_string()?;
    t.name2 = name2;
    t.name2_marker = name2_marker;
    t.name2_len = name2_len;
    t.slp = r.i32()?;
    let _shape_ptr = r.i32()?;
    t.sound_id = r.i32()?;
    let _wwise = r.u32()?;
    let _wwise_stop = r.u32()?;
    t.blend_priority = r.i32()?;
    t.blend_type = r.i32()?;
    let (overlay_marker, overlay, overlay_len) = r.debug_string()?;
    t.overlay_mask_name = overlay;
    t.overlay_marker = overlay_marker;
    t.overlay_len = overlay_len;
    r.skip(3)?; // Colors[3]
    r.skip(2)?; // CliffColors
    t.passable_terrain = r.u8()?;
    t.impassable_terrain = r.u8()?;
    t.is_animated = r.u8()?;
    r.skip(2)?; // AnimationFrames
    r.skip(2)?; // PauseFrames
    r.skip(4)?; // Interval
    r.skip(4)?; // PauseBetweenLoops
    r.skip(2)?; // Frame
    r.skip(2)?; // DrawFrame
    r.skip(4)?; // AnimateLast
    r.skip(1)?; // FrameChanged
    r.skip(1)?; // Drawn
    for _ in 0..TILE_TYPE_COUNT {
        r.skip(6)?; // FrameData: i16,i16,i16
    }
    r.skip(2)?; // TerrainToDraw
    r.skip(4)?; // TerrainDimensions i16[2]
    r.skip(2 * TERRAIN_UNITS_SIZE)?; // MaskedDensity
    r.skip(2 * TERRAIN_UNITS_SIZE)?; // UnitID
    r.skip(2 * TERRAIN_UNITS_SIZE)?; // Density
    r.skip(TERRAIN_UNITS_SIZE)?; // Centering (u8)
    r.skip(2)?; // NumberOfTerrainUnitsUsed
    t.phantom = r.i16()?;
    Ok(t)
}

#[derive(Debug, Clone, Default)]
pub struct TerrainBlock {
    pub map_width: i32,
    pub map_height: i32,
    pub world_width: i32,
    pub world_height: i32,
    pub terrains: Vec<Terrain>,
    pub map_min_x: f32,
    pub map_max_x: f32,
    pub terrains_used2: i16,
    pub borders_used: i16,
    pub max_terrain: i16,
    pub tile_width: i16,
    pub tile_height: i16,
    pub any_frame_change: u8,
    pub fog_flag: u8,
}

pub fn read_terrain_block(r: &mut Reader<'_>) -> io::Result<TerrainBlock> {
    let mut tb = TerrainBlock::default();
    let _vfn = r.u32()?;
    let _map_ptr = r.u32()?;
    tb.map_width = r.i32()?;
    tb.map_height = r.i32()?;
    tb.world_width = r.i32()?;
    tb.world_height = r.i32()?;
    for _ in 0..TILE_TYPE_COUNT {
        r.skip(6)?; // TileSizes: i16[3]
    }
    r.skip(2)?; // PaddingTS
    let mut terrains = Vec::with_capacity(TERRAIN_COUNT_FOR_TERRAINBLOCK);
    for _ in 0..TERRAIN_COUNT_FOR_TERRAINBLOCK {
        terrains.push(read_terrain(r)?);
    }
    tb.terrains = terrains;
    // gv in [GV_C9, GV_LatestDE2] -> TerrainBorders + MapRowOffset are SKIPPED.
    tb.map_min_x = r.f32()?;
    let _map_min_y = r.f32()?;
    tb.map_max_x = r.f32()?;
    let _map_max_y = r.f32()?;
    let _max_x1 = r.f32()?;
    let _max_y1 = r.f32()?;
    tb.terrains_used2 = r.i16()?;
    tb.borders_used = r.i16()?;
    tb.max_terrain = r.i16()?;
    tb.tile_width = r.i16()?;
    tb.tile_height = r.i16()?;
    let _tile_half_height = r.i16()?;
    let _tile_half_width = r.i16()?;
    let _elev_height = r.i16()?;
    let _cur_row = r.i16()?;
    let _cur_col = r.i16()?;
    let _block_beg_row = r.i16()?;
    let _block_end_row = r.i16()?;
    let _block_beg_col = r.i16()?;
    let _block_end_col = r.i16()?;
    let _search_map_ptr = r.u32()?;
    let _search_map_rows_ptr = r.u32()?;
    tb.any_frame_change = r.u8()?;
    let _map_visible_flag = r.u8()?;
    tb.fog_flag = r.u8()?;
    Ok(tb)
}

// ---------------------------------------------------------------------------
// Stage 4b: random maps
// ---------------------------------------------------------------------------
fn skip_map_land(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(4 + 4 + 4 + 4)?; // LandID, Terrain, LandSpacing, BaseSize
    r.skip(1 + 1 + 2)?; // Zone, PlacementType, Padding1
    r.skip(4 + 4)?; // BaseX, BaseY
    r.skip(1 + 1 + 2)?; // Proportion, ByPlayerFlag, Padding2
    r.skip(4 + 4 + 4)?; // StartAreaRadius, TerrainEdgeFade, Clumpiness
    Ok(()) // 44 B
}

fn skip_map_terrain(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(24) // i32[6]
}

fn skip_map_unit(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(4 + 4 + 1 + 1 + 2)?; // Unit, HostTerrain, GroupPlacing, ScaleFlag, Pad
    r.skip(32) // i32[8]
}

fn skip_map_elevation(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(24) // i32[6]
}

/// RandomMap.cpp:62-63 calls `serializeSub<MapInfo>` TWICE over the same vector,
/// so the maps are written in two passes and the second pass only carries the
/// `io_all` flag.  Reading it as one pass doubles or halves the section.
pub fn read_random_maps(r: &mut Reader<'_>) -> io::Result<usize> {
    let count = r.u32()? as usize;
    let _rm_ptr = r.i32()?;
    let mut io_all = vec![false; count];
    for _pass in 0..2 {
        for slot in io_all.iter_mut() {
            if *slot {
                r.i16()?; // map_id (only in the second pass)
            }
            r.skip(9 * 4)?; // 9 x int32 header
            for skipper in [
                skip_map_land as fn(&mut Reader<'_>) -> io::Result<()>,
                skip_map_terrain,
                skip_map_unit,
                skip_map_elevation,
            ] {
                let c = r.u32()?;
                let _ptr = r.i32()?;
                for _ in 0..c {
                    skipper(r)?;
                }
            }
            *slot = !*slot;
        }
    }
    Ok(count)
}

// ---------------------------------------------------------------------------
// Stage 5: effects
// ---------------------------------------------------------------------------
#[derive(Debug, Clone)]
pub struct Effect {
    pub name: String,
    /// Marker + stored width, for the same reason every other string carries
    /// them: the writer must advance by the INPUT width, and the marker is not
    /// constant.
    pub name_marker: u16,
    pub name_len: u16,
    /// `(u8, i16, i16, i16, f32)` -- 11 bytes.
    pub commands: Vec<(u8, i16, i16, i16, f32)>,
    /// True for an effect this session APPENDED, which has no counterpart in
    /// the input stream.  Writing one must freeze the input cursor: appending a
    /// record otherwise shifts every later `op()` read and corrupts the tail
    /// while still producing a syntactically valid file.
    pub is_new: bool,
}

pub fn read_effect(r: &mut Reader<'_>) -> io::Result<Effect> {
    let (name_marker, name, name_len) = r.debug_string()?;
    let n = r.i16()?;
    let mut commands = Vec::with_capacity(n.max(0) as usize);
    for _ in 0..n {
        commands.push((r.u8()?, r.i16()?, r.i16()?, r.i16()?, r.f32()?));
    }
    Ok(Effect {
        name,
        name_marker,
        name_len,
        commands,
        is_new: false,
    })
}

/// An effect record this session created: `aoe2mod/dat/writer.py`'s
/// `{"_new": True}`.  It carries no input counterpart, so the writer freezes
/// the cursor for its whole duration.
///
/// `name_marker` is the marker the shipped records use (`0x0A60`; the format
/// does not treat it as a constant but every record in the retail file carries
/// it) and `name_len` is the length of the name we are about to write, because
/// there is no stored width to preserve.
pub fn new_effect(name: String, commands: Vec<(u8, i16, i16, i16, f32)>) -> Effect {
    let name_len = name.as_bytes().len() as u16;
    Effect {
        name,
        name_marker: DEBUG_STRING_MARKER,
        name_len,
        commands,
        is_new: true,
    }
}

/// `serializeDebugString`'s marker in the retail file (`parse_dat.py:166`,
/// `writer.py:42`).  Not a format constant -- only the value every shipped
/// record happens to carry -- which is why parsed records keep theirs verbatim
/// and only synthesised ones use this.
pub const DEBUG_STRING_MARKER: u16 = 0x0A60;

// ---------------------------------------------------------------------------
// Stage 6: unit lines (skipped for DE - gv < GV_SWGB)
// ---------------------------------------------------------------------------
#[derive(Debug, Clone)]
pub struct UnitLine {
    pub id: i16,
    pub name: String,
    pub unit_ids: Vec<i16>,
}

pub fn read_unit_line(r: &mut Reader<'_>) -> io::Result<UnitLine> {
    let id = r.i16()?;
    let n = r.i16()?;
    let name = r.fixed_string(n.max(0) as usize)?;
    let m = r.i16()?;
    let mut unit_ids = Vec::with_capacity(m.max(0) as usize);
    for _ in 0..m {
        unit_ids.push(r.i16()?);
    }
    Ok(UnitLine { id, name, unit_ids })
}

// ---------------------------------------------------------------------------
// Stage 7: unit headers (tasks)
// ---------------------------------------------------------------------------
#[derive(Debug, Clone)]
pub struct Task {
    pub task_type: i16,
    pub id: i16,
    /// Present only when `gv >= GV_C28` (50); DE always has it.
    pub enabled: Option<i16>,
}

pub fn read_task(r: &mut Reader<'_>, gv: u32) -> io::Result<Task> {
    let task_type = r.i16()?;
    let id = r.i16()?;
    r.skip(1)?; // IsDefault
    r.skip(2 * 4)?; // ActionType..TerrainID
    r.skip(2 * 4)?; // ResourceIn..UnusedResource
    r.skip(4 * 3)?; // WorkValue1, WorkValue2, WorkRange
    r.skip(1)?; // AutoSearchTargets
    r.skip(4)?; // SearchWaitTime
    r.skip(1 + 1)?; // EnableTargeting, CombatLevelFlag
    r.skip(2 * 2)?; // GatherType, WorkFlag2
    r.skip(1 + 1 + 1)?; // TargetDiplomacy, CarryCheck, PickForConstruction
    r.skip(2 * 4)?; // Moving, Proceeding, Working, Carrying
    r.skip(2 * 2)?; // ResourceGathering, DepositSoundID
    if (4..=54).contains(&gv) {
        // GV_C4 <= gv <= GV_LatestDE2 (UnitCommand.cpp:76)
        r.skip(8)?; // Wwise* IDs
    }
    let enabled = if gv >= 50 {
        // GV_C28 (UnitCommand.cpp:81) -- the guard whose absence over-ran a
        // real VER 7.8 mod dat by 1,465,059 bytes.
        Some(r.i16()?)
    } else {
        None
    };
    Ok(Task {
        task_type,
        id,
        enabled,
    })
}

#[derive(Debug, Clone, Default)]
pub struct UnitHeader {
    pub exists: u8,
    pub tasks: Vec<Task>,
}

pub fn read_unit_header(r: &mut Reader<'_>, gv: u32) -> io::Result<UnitHeader> {
    let exists = r.u8()?;
    let mut uh = UnitHeader {
        exists,
        tasks: Vec::new(),
    };
    if exists != 0 {
        let n = r.i16()?;
        for _ in 0..n.max(0) {
            uh.tasks.push(read_task(r, gv)?);
        }
    }
    Ok(uh)
}
