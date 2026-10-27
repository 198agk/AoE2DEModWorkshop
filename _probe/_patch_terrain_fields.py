# -*- coding: utf-8 -*-
"""Give Terrain the string markers and stored widths its writer needs.

Same reason as graphics: `debug_string` is `u16 marker + u16 len + bytes`, the
marker is not constant, and re-emitting needs the width the INPUT used, not the
width of the decoded text (trailing bytes and padding are dropped by the
reader).  Without these the writer has to guess and the round trip stops being
byte-identical.
"""
import io
import os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                 "desktop", "aoe2mod-dat", "src", "stages37.rs")
P = os.path.normpath(P)
src = io.open(P, encoding="utf-8").read()

src = src.replace(
    """    pub name: String,
    pub name2: String,
    pub slp: i32,""",
    """    pub name: String,
    pub name2: String,
    /// Markers + stored widths for the three strings.  See `Graphic`: the
    /// marker is not constant, and a re-emit needs the INPUT width.
    pub name_marker: u16,
    pub name_len: u16,
    pub name2_marker: u16,
    pub name2_len: u16,
    pub slp: i32,""", 1)

src = src.replace(
    """    pub blend_type: i32,
    pub overlay_mask_name: String,""",
    """    pub blend_type: i32,
    pub overlay_mask_name: String,
    pub overlay_marker: u16,
    pub overlay_len: u16,""", 1)

src = src.replace(
    """    t.name = r.debug_string()?.1;
    t.name2 = r.debug_string()?.1;
    t.slp = r.i32()?;""",
    """    let (name_marker, name, name_len) = r.debug_string()?;
    t.name = name;
    t.name_marker = name_marker;
    t.name_len = name_len;
    let (name2_marker, name2, name2_len) = r.debug_string()?;
    t.name2 = name2;
    t.name2_marker = name2_marker;
    t.name2_len = name2_len;
    t.slp = r.i32()?;""", 1)

src = src.replace(
    """    t.overlay_mask_name = r.debug_string()?.1;""",
    """    let (overlay_marker, overlay, overlay_len) = r.debug_string()?;
    t.overlay_mask_name = overlay;
    t.overlay_marker = overlay_marker;
    t.overlay_len = overlay_len;""", 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(src)
print("patched", P)
for probe in ("pub name_marker: u16", "pub overlay_marker: u16",
              "t.name_len = name_len"):
    print("  ", probe, "->", probe in src)
