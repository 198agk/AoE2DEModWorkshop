# -*- coding: utf-8 -*-
"""Add the marker/width fields the writers need, and a graphic_count field.

Every `debug_string` in the stream is `u16 marker + u16 len + bytes`, and the
marker is not constant.  A writer that invents a marker (say 0x0A60) writes
bytes the input did not have, so the round trip stops being byte-identical while
still producing a file the game would read.  That is the worst possible outcome
to debug, so the reader keeps the marker instead.
"""
import io
import os
import re

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                 "desktop", "aoe2mod-dat", "src", "lib.rs")
P = os.path.normpath(P)
src = io.open(P, encoding="utf-8").read()

# 1. SoundItem gains marker + file_len
src = src.replace(
    """pub struct SoundItem {
    pub file: String,
    pub resource_id: i32,
    pub probability: i16,
    pub civilization: i16,
    pub iconset: i16,
}""",
    """pub struct SoundItem {
    pub file: String,
    pub resource_id: i32,
    pub probability: i16,
    pub civilization: i16,
    pub iconset: i16,
    /// The u16 marker and the width the INPUT used for the text.  Both are
    /// needed to re-emit the string without shifting the cursor, and the marker
    /// is NOT constant -- inventing one writes bytes the input never had.
    pub marker: u16,
    pub file_len: u16,
}""", 1)

src = src.replace(
    """    let (_m, file, _n) = r.debug_string()?;
    Ok(SoundItem {
        file,
        resource_id: r.i32()?,
        probability: r.i16()?,
        civilization: r.i16()?,
        iconset: r.i16()?,
    })""",
    """    let (marker, file, file_len) = r.debug_string()?;
    Ok(SoundItem {
        file,
        resource_id: r.i32()?,
        probability: r.i16()?,
        civilization: r.i16()?,
        iconset: r.i16()?,
        marker,
        file_len,
    })""", 1)

# 2. Graphic gains the three markers
src = src.replace(
    """    pub name: String,
    pub file: String,
    pub particle_effect: String,
    /// Stored widths of the three strings, as bytes in the stream.
    pub name_len: u16,
    pub file_len: u16,
    pub particle_len: u16,""",
    """    pub name: String,
    pub file: String,
    pub particle_effect: String,
    /// Stored widths of the three strings, as bytes in the stream.
    pub name_len: u16,
    pub file_len: u16,
    pub particle_len: u16,
    /// The markers in front of each string.  Not constant, and not decoration:
    /// re-emitting a different one changes bytes the game will read.
    pub name_marker: u16,
    pub file_marker: u16,
    pub particle_marker: u16,""", 1)

src = src.replace(
    """    let (_m1, name, name_len) = r.debug_string()?;
    let (_m2, file, file_len) = r.debug_string()?;
    let (_m3, particle_effect, particle_len) = r.debug_string()?;""",
    """    let (name_marker, name, name_len) = r.debug_string()?;
    let (file_marker, file, file_len) = r.debug_string()?;
    let (particle_marker, particle_effect, particle_len) = r.debug_string()?;""", 1)

src = src.replace(
    """        name_len,
        file_len,
        particle_len,""",
    """        name_len,
        file_len,
        particle_len,
        name_marker,
        file_marker,
        particle_marker,""", 1)

# 3. Stages23 gains the slot count (graphic_count), which is NOT graphics.len()
src = src.replace(
    """pub struct Stages23 {
    pub sounds: Vec<Sound>,
    pub graphic_pointers_nonzero: usize,
    pub graphics: Vec<Graphic>,
}""",
    """pub struct Stages23 {
    pub sounds: Vec<Sound>,
    /// `graphic_count` from the stream: the number of POINTER SLOTS, which is
    /// the record count only when every slot is occupied.  A writer needs both.
    pub graphic_count: i16,
    pub graphic_pointers_nonzero: usize,
    pub graphics: Vec<Graphic>,
}""", 1)

src = src.replace(
    """    Ok(Stages23 {
        sounds,
        graphic_pointers_nonzero: nonzero,
        graphics,
    })""",
    """    Ok(Stages23 {
        sounds,
        graphic_count,
        graphic_pointers_nonzero: nonzero,
        graphics,
    })""", 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(src)
print("patched", P)
for probe in ("pub marker: u16", "pub name_marker: u16", "pub graphic_count: i16"):
    print("  ", probe, "->", probe in src)
