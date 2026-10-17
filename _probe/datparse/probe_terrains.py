#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostic: read TerrainBlock Terrains one at a time and report each
terrain's byte length + its name strings, to find where it goes wrong."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

data, how = P.load_dat(r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat")
print("size %d  (%s)" % (len(data), how))

r = P.Reader(data)
r.fixed_string(8)
c = r.i16(); r.i16()
r.i32_array(c); r.i32_array(c)
for _ in range(c): P.read_terrain_restriction(r, 134)
pc = r.i16()
for _ in range(pc): P.read_player_colour(r)
sc = r.i16()
for _ in range(sc): P.read_sound(r)
gc = r.i16()
ptrs = r.i32_array(gc)
for p in ptrs:
    if p: P.read_graphic(r)

print("stage4 start 0x%X (%d)" % (r.pos, r.pos))

r.u32(); r.u32(); r.i32(); r.i32(); r.i32(); r.i32()
print("map dims: %d x %d  world %d x %d" % (0,0,0,0))
for _ in range(P.TILE_TYPE_COUNT):
    r.i16_array(3)
r.i16()

for i in range(12):
    start = r.pos
    try:
        t = P.read_terrain(r)
    except Exception as e:
        print("terrain %d FAILED at 0x%X: %s" % (i, r.pos, e))
        break
    print("terrain %2d  0x%08X -> 0x%08X  len=%-6d name=%r name2=%r slp=%d"
          % (i, start, r.pos, r.pos - start, t["name"], t["name2"], t["slp"]))
