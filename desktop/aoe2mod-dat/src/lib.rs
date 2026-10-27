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
        Ok(f32::from_bits(self.u32()? as u32))
    }

    /// Fixed-width, NUL-padded string: the file version field.
    pub fn fixed_string(&mut self, n: usize) -> io::Result<String> {
        let b = self.take(n)?;
        let end = b.iter().position(|&c| c == 0).unwrap_or(b.len());
        Ok(String::from_utf8_lossy(&b[..end]).into_owned())
    }
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
