# -*- coding: utf-8 -*-
"""Per-sub-block spans for one unit record, so the Rust side can be diffed block by block."""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.parser as P          # noqa: E402

DAT = os.path.join(r"d:\games\steam\steamapps\common\AoE2DE",
                   "resources", "_common", "dat", "empires2_x2_p1.dat")
raw, _ = P.load_dat(DAT)
q = P.Parser(raw)
try:
    q.parse(stop_after=8)
except SystemExit:
    pass
offs = {n: (a, b) for n, a, b in q.stage_offsets}

r = P.Reader(raw)
r.pos = offs["8 Civs"][0]
r.i16(); r.u8(); r.debug_string(); n = r.i16(); r.i16(); r.i16()
r.f32_array(n); r.u8(); m = r.i16(); ptrs = r.i32_array(m)

print("unit0 start", r.pos)
u0 = r.pos
t = r.u8()
print("type", t)

# replay the common block with named spans
def block(name, fn):
    a = r.pos
    fn()
    print("  %-22s +%-4d  -> %d" % (name, r.pos - a, r.pos))

block("common(rest)", lambda: (
    r.i16(), r.i32(), r.i32(), r.i16(), r.i16_array(2), r.i16(), r.i16(),
    r.u8(), r.i16(), r.f32(), r.u8(), r.f32_array(3), r.i16(), r.i16(),
    r.i16(), r.i16(), r.u8(), r.u8(), r.i16(), r.u8(), r.i16(), r.u8(),
    r.u8(), r.i16_array(2), r.i16_array(2), r.f32_array(2), r.u8(), r.u8(),
    r.i16(), r.u8(), r.i16(), r.f32(),
    [r.u8() for _ in range(5)], r.f32(), r.u8(), r.i32(), r.i32(),
    [r.u8() for _ in range(4)], [r.u8() for _ in range(3)],
    r.u8(), r.u8(), r.i16(), r.u8(), r.u8(), r.f32_array(3), r.i32_array(2),
    [(r.i16(), r.f32(), r.u8()) for _ in range(3)],
))
dgc = r.u8()
print("  dgc", dgc)
block("damage_graphics", lambda: [P.read_damage_graphic(r) for _ in range(dgc)])
block("sounds", lambda: (r.i16(), r.i16(), r.i32_array(4), r.u8(), r.u8()))
block("name+ids", lambda: (r.debug_string(), r.i16(), r.i16()))

print("after common:", r.pos)
block("speed", lambda: r.f32()) if t >= 20 else None
if t >= 30:
    block("dead_fish", lambda: P.read_dead_fish(r))
if t >= 40:
    a = r.pos
    tsg = P.read_bird(r)
    print("  %-22s +%-4d  -> %d   tsg=%d" % ("bird", r.pos - a, r.pos, tsg))
if t >= 50:
    block("type50", lambda: P.read_type50(r))
if t == 60:
    block("projectile", lambda: P.read_projectile(r))
if t >= 70:
    block("creatable", lambda: P.read_creatable(r))
if t == 80:
    block("building", lambda: P.read_building(r))

print("unit0 end", r.pos, "SPAN", r.pos - u0)
