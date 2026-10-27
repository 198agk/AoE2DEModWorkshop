//! A `.dat` reader that must agree with the frozen baseline, byte for byte.
//!
//! Why this crate exists
//! ---------------------
//! `aoe2mod/dat/` is 4,146 lines of Python that took three weeks to get right,
//! and every one of its rules was bought with a mis-parse: a field width that
//! changes when a string gets longer, `count` being a geometry field rather
//! than a record count, `displayed_*` holding a different number from the one
//! stored beside it.  The goal here is NOT to write a better parser.  It is to
//! write a second one that agrees, so the shipped program can be a native
//! binary with no interpreter in it.
//!
//! How agreement is measured
//! -------------------------
//! `_golden/dat_baseline.json` pins three numbers for the retail stream:
//!
//! ```text
//! raw sha256        02a09b48a0fbd2116295cad2ebdd28dfa20b92b44e29b360f8639e5fb73405df
//! structure sha256  6602ee89ba528af1cc1c7c44d877a480c205446e86431ad493da034a452da9c1
//! serialized        identical to the input, delta +0
//! ```
//!
//! A parse is only "done" when it reproduces those.  Anything else is a diff to
//! chase, which is exactly the point: the checks are not a formality, they are
//! the specification.
//!
//! Scope of this file
//! ------------------
//! Stage 1 only for now (file version, terrain restrictions, player colours).
//! That is deliberate: it is the smallest slice that still exercises the file's
//! real hazards -- a version string that selects every later layout, a
//! `count`-driven loop, and a nested struct with a variable-length float array.
//! Once stage 1 lands byte-exact, the same reader shape carries the rest.

use std::fs;
use std::io::{self, Read};
use std::path::Path;

/// Raw-deflate (`zlib` with `window_bits = -15`), the container the game ships.
///
/// The retail file is NOT gzip and NOT zlib-framed; it is a bare deflate stream
/// whose payload starts with `VER `.  `aoe2mod/dat/parser.py::load_dat` accepts
/// either form, so this does too, and reports which one it saw rather than
/// guessing silently.
pub fn load_dat(path: &Path) -> io::Result<(Vec<u8>, &'static str)> {
    let blob = fs::read(path)?;
    if blob.len() >= 4 && &blob[..4] == b"VER " {
        return Ok((blob, "already-decompressed"));
    }
    let mut out = Vec::with_capacity(96 * 1024 * 1024);
    let mut d = flate2::read::DeflateDecoder::new(&blob[..]);
    d.read_to_end(&mut out)?;
    Ok((out, "raw-deflate(window_bits=-15)"))
}

/// A bounds-checked little-endian cursor.
///
/// Every read returns `Result` instead of panicking: this file's whole job is
/// to be handed a stream that might be a mod, an old version, or corrupt, and
/// the Python original raises rather than returning garbage.  Panicking in
/// Rust would abort the process that is supposed to show an error page.
pub struct Reader<'a> {
    pub buf: &'a [u8],
    pub pos: usize,
}

impl<'a> Reader<'a> {
    pub fn new(buf: &'a [u8]) -> Self {
        Reader { buf, pos: 0 }
    }

    fn take(&mut self, n: usize) -> io::Result<&'a [u8]> {
        let end = self
            .pos
            .checked_add(n)
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "offset overflow"))?;
        if end > self.buf.len() {
            return Err(io::Error::new(
                io::ErrorKind::UnexpectedEof,
                format!(
                    "wanted {} bytes at {}, only {} left",
                    n,
                    self.pos,
                    self.buf.len() - self.pos
                ),
            ));
        }
        let s = &self.buf[self.pos..end];
        self.pos = end;
        Ok(s)
    }

    pub fn i16(&mut self) -> io::Result<i16> {
        let b = self.take(2)?;
        Ok(i16::from_le_bytes([b[0], b[1]]))
    }

    pub fn u16(&mut self) -> io::Result<u16> {
        let b = self.take(2)?;
        Ok(u16::from_le_bytes([b[0], b[1]]))
    }

    pub fn i32(&mut self) -> io::Result<i32> {
        let b = self.take(4)?;
        Ok(i32::from_le_bytes([b[0], b[1], b[2], b[3]]))
    }

    pub fn u32(&mut self) -> io::Result<u32> {
        let b = self.take(4)?;
        Ok(u32::from_le_bytes([b[0], b[1], b[2], b[3]]))
    }

    pub fn f32(&mut self) -> io::Result<f32> {
        Ok(f32::from_bits(self.u32()?))
    }

    /// Advance without decoding.  The format is full of fixed-size fields this
    /// reader does not model (`Colors[3]`, `CliffColors`, `Padding`, the three
    /// dropped floats in a graphic); skipping them keeps the cursor honest
    /// without inventing structs nobody will read.
    pub fn skip(&mut self, n: usize) -> io::Result<()> {
        self.take(n).map(|_| ())
    }

    /// Fixed-width, NUL-padded string: the file version field.
    pub fn fixed_string(&mut self, n: usize) -> io::Result<String> {
        let b = self.take(n)?;
        let end = b.iter().position(|&c| c == 0).unwrap_or(b.len());
        Ok(String::from_utf8_lossy(&b[..end]).into_owned())
    }

    pub fn u8(&mut self) -> io::Result<u8> {
        Ok(self.take(1)?[0])
    }

    /// `serializeDebugString`: u16 marker, u16 length, then `length` bytes.
    ///
    /// Returns `(marker, text, stored_len)`.  The stored length is the WIDTH IN
    /// THE STREAM, which is not `text.len()`: a string may be NUL-padded or may
    /// carry trailing bytes.  The writer needs that width to advance its raw
    /// cursor, and getting it wrong is how this project once produced 991,273
    /// mismatches from a single 3-byte string change.  The Python original
    /// keeps it in `Reader.last_string_len` for the same reason; here it is
    /// returned so a caller cannot forget it exists.
    pub fn debug_string(&mut self) -> io::Result<(u16, String, u16)> {
        let marker = self.u16()?;
        let len = self.u16()?;
        let b = self.take(len as usize)?;
        let end = b.iter().position(|&c| c == 0).unwrap_or(b.len());
        Ok((marker, String::from_utf8_lossy(&b[..end]).into_owned(), len))
    }
}

// ---------------------------------------------------------------------------
// Stage 2: sounds
// ---------------------------------------------------------------------------
#[derive(Debug, Clone)]
pub struct SoundItem {
    pub file: String,
    pub resource_id: i32,
    pub probability: i16,
    pub civilization: i16,
    pub iconset: i16,
}

#[derive(Debug, Clone)]
pub struct Sound {
    pub id: i16,
    pub play_delay: i16,
    pub cache_time: i32,
    pub total_probability: i16,
    pub items: Vec<SoundItem>,
}

fn read_sound_item(r: &mut Reader<'_>) -> io::Result<SoundItem> {
    let (_m, file, _n) = r.debug_string()?;
    Ok(SoundItem {
        file,
        resource_id: r.i32()?,
        probability: r.i16()?,
        civilization: r.i16()?,
        iconset: r.i16()?,
    })
}

pub fn read_sound(r: &mut Reader<'_>) -> io::Result<Sound> {
    let id = r.i16()?;
    let play_delay = r.i16()?;
    // NOTE the order: the item count is read BEFORE cache_time, i.e. it sits
    // 6 bytes earlier in the stream than a "count then payload" reading would
    // put it.  Taken from the Python original line for line.
    let file_count = r.i16()?;
    let cache_time = r.i32()?;
    let total_probability = r.i16()?;
    let mut items = Vec::with_capacity(file_count.max(0) as usize);
    for _ in 0..file_count {
        items.push(read_sound_item(r)?);
    }
    Ok(Sound {
        id,
        play_delay,
        cache_time,
        total_probability,
        items,
    })
}

// ---------------------------------------------------------------------------
// Stage 3: graphics
// ---------------------------------------------------------------------------
/// `(i16, i16, i32, i16, i16, i16, i16)` -- 16 bytes.
pub type GraphicDelta = (i16, i16, i32, i16, i16, i16, i16);
/// Three `(i16, i16, u32)` pairs -- 24 bytes, alongside the deltas.
pub type AngleSound = [(i16, i16, u32); 3];

#[derive(Debug, Clone)]
pub struct Graphic {
    pub name: String,
    pub file: String,
    pub particle_effect: String,
    /// Stored widths of the three strings, as bytes in the stream.
    pub name_len: u16,
    pub file_len: u16,
    pub particle_len: u16,
    pub slp: i32,
    pub is_loaded: u8,
    pub old_color_flag: u8,
    pub layer: u8,
    pub player_color: i16,
    pub transparent_selection: u8,
    pub coordinates: [i16; 4],
    pub sound_id: i16,
    pub wwise_sound_id: u32,
    pub angle_sounds_used: u8,
    pub frame_count: i16,
    pub angle_count: i16,
    pub id: i16,
    pub mirroring_mode: u8,
    pub editor_flag: u8,
    pub deltas: Vec<GraphicDelta>,
    pub angle_sounds: Vec<AngleSound>,
}

fn read_graphic_delta(r: &mut Reader<'_>) -> io::Result<GraphicDelta> {
    Ok((
        r.i16()?, r.i16()?, r.i32()?, r.i16()?, r.i16()?, r.i16()?, r.i16()?,
    ))
}

fn read_graphic_angle_sound(r: &mut Reader<'_>) -> io::Result<AngleSound> {
    Ok([(r.i16()?, r.i16()?, r.u32()?), (r.i16()?, r.i16()?, r.u32()?),
        (r.i16()?, r.i16()?, r.u32()?)])
}

pub fn read_graphic(r: &mut Reader<'_>) -> io::Result<Graphic> {
    let (_m1, name, name_len) = r.debug_string()?;
    let (_m2, file, file_len) = r.debug_string()?;
    let (_m3, particle_effect, particle_len) = r.debug_string()?;

    let slp = r.i32()?;
    let is_loaded = r.u8()?;
    let old_color_flag = r.u8()?;
    let layer = r.u8()?;
    let player_color = r.i16()?;
    let transparent_selection = r.u8()?;
    let mut coordinates = [0i16; 4];
    for slot in coordinates.iter_mut() {
        *slot = r.i16()?;
    }
    let delta_count = r.i16()?;
    let sound_id = r.i16()?;
    let wwise_sound_id = r.u32()?;
    let angle_sounds_used = r.u8()?;
    let frame_count = r.i16()?;
    let angle_count = r.i16()?;
    // SpeedMultiplier, FrameDuration, ReplayDelay: read and dropped, exactly as
    // the Python original does (`r.f32()` with no assignment).
    r.f32()?;
    r.f32()?;
    r.f32()?;
    r.u8()?; // SequenceType
    let id = r.i16()?;
    let mirroring_mode = r.u8()?;
    let editor_flag = r.u8()?;

    let mut deltas = Vec::with_capacity(delta_count.max(0) as usize);
    for _ in 0..delta_count {
        deltas.push(read_graphic_delta(r)?);
    }
    let mut angle_sounds = Vec::new();
    if angle_sounds_used != 0 {
        for _ in 0..angle_count {
            angle_sounds.push(read_graphic_angle_sound(r)?);
        }
    }
    Ok(Graphic {
        name,
        file,
        particle_effect,
        name_len,
        file_len,
        particle_len,
        slp,
        is_loaded,
        old_color_flag,
        layer,
        player_color,
        transparent_selection,
        coordinates,
        sound_id,
        wwise_sound_id,
        angle_sounds_used,
        frame_count,
        angle_count,
        id,
        mirroring_mode,
        editor_flag,
        deltas,
        angle_sounds,
    })
}

// ---------------------------------------------------------------------------
// Stages 2 + 3 together
// ---------------------------------------------------------------------------
pub struct Stages23 {
    pub sounds: Vec<Sound>,
    pub graphic_pointers_nonzero: usize,
    pub graphics: Vec<Graphic>,
}

pub fn read_stages23(r: &mut Reader<'_>) -> io::Result<Stages23> {
    let sound_count = r.i16()?;
    let mut sounds = Vec::with_capacity(sound_count.max(0) as usize);
    for _ in 0..sound_count {
        sounds.push(read_sound(r)?);
    }

    let graphic_count = r.i16()?;
    let mut ptrs = Vec::with_capacity(graphic_count.max(0) as usize);
    for _ in 0..graphic_count {
        ptrs.push(r.i32()?);
    }
    // The pointer array is a presence flag per slot; records exist only where
    // the pointer is non-zero, and they follow in order.  `graphic_count` is
    // the SLOT count, not the record count -- reading it as records is a
    // classic way to over-run here.
    let nonzero = ptrs.iter().filter(|&&p| p != 0).count();
    let mut graphics = Vec::with_capacity(nonzero);
    for &p in ptrs.iter() {
        if p != 0 {
            graphics.push(read_graphic(r)?);
        }
    }
    Ok(Stages23 {
        sounds,
        graphic_pointers_nonzero: nonzero,
        graphics,
    })
}

// ---------------------------------------------------------------------------
// Stages 4-7: terrain, random maps, effects, unit headers
// ---------------------------------------------------------------------------
pub mod stages37;

pub use stages37::{
    read_effect, read_random_maps, read_task, read_terrain, read_terrain_block,
    read_unit_header, read_unit_line, Effect, Task, Terrain, TerrainBlock,
    UnitHeader, UnitLine,
};

pub struct Stages47 {
    pub terrain_block: TerrainBlock,
    pub random_map_count: usize,
    pub effects: Vec<Effect>,
    pub unit_headers: Vec<UnitHeader>,
}

/// Stages 4-7 in one call, with stage 6 deliberately absent.
///
/// DatFile.cpp:214 guards UnitLines with `if (gv >= GV_SWGB)`, and GV_C32 (54)
/// is below GV_SWGB (55), so a VER 8.9 file has NO UnitLines array at this
/// point.  The stage numbering in the docs lists one; the source contradicts
/// that, and reading it here would shift everything after.
pub fn read_stages47(r: &mut Reader<'_>, gv: u32) -> io::Result<Stages47> {
    let terrain_block = read_terrain_block(r)?;
    let random_map_count = read_random_maps(r)?;

    let effect_count = r.i32()?;
    let mut effects = Vec::with_capacity(effect_count.max(0) as usize);
    for _ in 0..effect_count {
        effects.push(read_effect(r)?);
    }

    // stage 6: UnitLines -- not present, see above.

    let unit_header_count = r.i32()?;
    let mut unit_headers = Vec::with_capacity(unit_header_count.max(0) as usize);
    for _ in 0..unit_header_count {
        unit_headers.push(read_unit_header(r, gv)?);
    }

    Ok(Stages47 {
        terrain_block,
        random_map_count,
        effects,
        unit_headers,
    })
}

/// `VER 8.9` -> the ordinal the C++ `GameVersion` enum gives it.
///
/// Mirrors `gv_from_version_string` in the Python original.  Only the versions
/// this project has actually seen are here; an unknown string is an error, not
/// a default, because "assume latest" is what silently mis-parsed a real VER
/// 7.8 mod dat by 1,465,059 bytes.
pub fn gv_from_version(ver: &str) -> io::Result<u32> {
    let t = ver.trim().trim_end_matches('\u{0}');
    let (major, minor) = t
        .strip_prefix("VER ")
        .and_then(|s| s.split_once('.'))
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, format!("bad version {ver:?}")))?;
    let key = format!(
        "{}.{}",
        major.parse::<u32>().map_err(|_| {
            io::Error::new(io::ErrorKind::InvalidData, "bad major in version")
        })?,
        minor.parse::<u32>().map_err(|_| {
            io::Error::new(io::ErrorKind::InvalidData, "bad minor in version")
        })?
    );
    // Ordinals are the enum's own values from `include/genie/Types.h`, taken
    // from the Python original rather than counted by hand: VER 8.9 is GV_C32
    // == 54, VER 7.8 is GV_C21 == 43.  A first version of this function said
    // 32 for VER 8.9, which the comparison probe caught immediately
    // (`game_version py=54 rust=32`).
    let gv = match key.as_str() {
        "7.7" => 42,
        "7.8" => 43,
        "7.9" => 44,
        "8.0" => 45,
        "8.1" => 46,
        "8.2" => 47,
        "8.3" => 48,
        "8.4" => 49,
        "8.5" => 50,
        "8.6" => 51,
        "8.7" => 52,
        "8.8" => 53,
        "8.9" => 54,
        other => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!("unsupported DAT FileVersion {other:?}"),
            ))
        }
    };
    Ok(gv)
}

/// Stage 1: version, terrain block, player colours.
#[derive(Debug, Clone)]
pub struct Stage1 {
    pub file_version: String,
    pub game_version: u32,
    pub terrain_restriction_count: i16,
    pub terrains_used1: i16,
    pub float_ptr_terrain_tables: Vec<i32>,
    pub terrain_pass_graphic_pointers: Vec<i32>,
    /// `(mult[], pass[(i32,i32,i32,f32); terrains_used1])` per restriction.
    pub terrain_restrictions: Vec<TerrainRestriction>,
    pub player_colour_count: i16,
    pub player_colours: Vec<[i32; 9]>,
}

#[derive(Debug, Clone)]
pub struct TerrainRestriction {
    pub mult: Vec<f32>,
    pub pass: Vec<(i32, i32, i32, f32)>,
}

/// Width of the `file_version` field: `"VER 8.9\0"` padded to 8 bytes.
///
/// Not 256, and not "the rest of the header".  Measured the hard way: with 256
/// this reader reported stage 1 ending at byte 306 instead of 145,742 -- every
/// later field shifted by 248 bytes and the parse still "succeeded", which is
/// the failure mode this project keeps paying for.  The Python original has the
/// same number in `FILE_VERSION_SIZE`.
pub const FILE_VERSION_SIZE: usize = 8;

pub fn read_stage1(r: &mut Reader<'_>) -> io::Result<Stage1> {
    let file_version = r.fixed_string(FILE_VERSION_SIZE)?;
    let game_version = gv_from_version(&file_version)?;
    let terrain_restriction_count = r.i16()?;
    let terrains_used1 = r.i16()?;
    let mut float_ptr = Vec::new();
    for _ in 0..terrain_restriction_count {
        float_ptr.push(r.i32()?);
    }
    let mut pass_ptr = Vec::new();
    for _ in 0..terrain_restriction_count {
        pass_ptr.push(r.i32()?);
    }
    let mut restrictions = Vec::new();
    for _ in 0..terrain_restriction_count {
        let n = terrains_used1.max(0) as usize;
        let mut mult = Vec::with_capacity(n);
        for _ in 0..n {
            mult.push(r.f32()?);
        }
        let mut pass = Vec::with_capacity(n);
        for _ in 0..n {
            let a = r.i32()?;
            let b = r.i32()?;
            let c = r.i32()?;
            let f = r.f32()?;
            pass.push((a, b, c, f));
        }
        restrictions.push(TerrainRestriction { mult, pass });
    }
    let player_colour_count = r.i16()?;
    let mut player_colours = Vec::new();
    for _ in 0..player_colour_count {
        let mut c = [0i32; 9];
        for slot in c.iter_mut() {
            *slot = r.i32()?;
        }
        player_colours.push(c);
    }
    Ok(Stage1 {
        file_version,
        game_version,
        terrain_restriction_count,
        terrains_used1,
        float_ptr_terrain_tables: float_ptr,
        terrain_pass_graphic_pointers: pass_ptr,
        terrain_restrictions: restrictions,
        player_colour_count,
        player_colours,
    })
}
