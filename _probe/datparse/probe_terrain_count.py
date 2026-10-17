#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe: find the correct Terrain count for TerrainBlock by trying candidates
and checking whether the bytes that follow look like a plausible RandomMaps
header (uint32 count, int32 ptr) and then a plausible Effects int32 count."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import parse_dat as P

data, how = P.load_dat(sys.argv[1] if len(sys.argv) > 1 else
                       r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat")
print("size %d  (%s)" % (len(data), how))

r = P.Reader(data)
# stage 1
r.fixed_string(8)
n_terr = r.i16()
r.i16()
r.i32_array(n_terr)
r.i32_array(n_terr)
for _ in range(n_terr):
    P.read_terrain_restriction(r, 134)
r.i16()
for _ in range(r.pos):  # noop
    break
# player colours: we already consumed count; re-do properly
r2 = P.Reader(data)
r2.fixed_string(8)
c = r2.i16()
r2.i16()
r2.i32_array(c)
r2.i32_array(c)
for _ in range(c):
    P.read_terrain_restriction(r2, 134)
pc = r2.i16()
for _ in range(pc):
    P.read_player_colour(r2)
sc = r2.i16()
for _ in range(sc):
    P.read_sound(r2)
gc = r2.i16()
ptrs = r2.i32_array(gc)
for p in ptrs:
    if p:
        P.read_graphic(r2)

stage4_start = r2.pos
print("stage4 start 0x%X" % stage4_start)

results = []
for tc in range(20, 300):
    rr = P.Reader(data)
    rr.pos = stage4_start
    try:
        P.read_terrain_block.__wrapped__ if False else None
        # inline terrain block read with variable terrain count
        rr.u32(); rr.u32(); rr.i32(); rr.i32(); rr.i32(); rr.i32()
        for _ in range(P.TILE_TYPE_COUNT):
            rr.i16_array(3)
        rr.i16()
        for _ in range(tc):
            P.read_terrain(rr)
        rr.f32(); rr.f32(); rr.f32(); rr.f32(); rr.f32(); rr.f32()
        rr.i16()
        rr.i16()
        rr.i16()
        for _ in range(12):
            rr.i16()
        rr.u32(); rr.u32(); rr.u8()
        rr.u8(); rr.u8()
        end_tb = rr.pos
        if end_tb + 8 > len(data):
            continue
        rm_count = rr.u32()
        rm_ptr = rr.i32()
        eff_count = None
        ok = 0 <= rm_count <= 500 and -1000000 <= rm_ptr <= 1000000
        results.append((tc, end_tb, rm_count, rm_ptr, ok))
    except Exception as e:
        continue

print("candidates with plausible RandomMaps header:")
for tc, end_tb, rm_count, rm_ptr, ok in results:
    if ok:
        print("  tc=%-4d tb_end=0x%08X  rm_count=%-6d rm_ptr=%-10d" % (tc, end_tb, rm_count, rm_ptr))
print("")
print("all results (tc, end, rmc, rmptr):")
for row in results:
    print("  %-4d 0x%08X  %-8d %-10d" % row[:4])
