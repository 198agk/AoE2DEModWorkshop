import _gamepaths as GP
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure exact sub-section boundaries the parent asked about (Graphics
pointer array vs. bodies) plus the key top-level offsets, from the live parse."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

data, how = P.load_dat(GP.DAT)
r = P.Reader(data)

# --- header + terrain restriction block --------------------------------
print("FileVersion             0x%08X  = %r" % (r.pos, r.fixed_string(P.FILE_VERSION_SIZE)))
n = r.i16(); tu = r.i16()
print("terrain_restriction_count = %d, TerrainsUsed1 = %d (offset after = 0x%08X)" % (n, tu, r.pos))
r.i32_array(n); r.i32_array(n)
tr_start = r.pos
print("TerrainRestrictions     0x%08X" % tr_start)
for _ in range(n):
    P.read_terrain_restriction(r, tu)

pc_count_off = r.pos
pcn = r.i16()
print("PlayerColours count     0x%08X (count=%d)" % (pc_count_off, pcn))
pc_start = r.pos
for _ in range(pcn):
    P.read_player_colour(r)
print("PlayerColours bodies    0x%08X -> 0x%08X" % (pc_start, r.pos))

snd_count_off = r.pos
sn = r.i16()
print("Sounds count            0x%08X (count=%d)" % (snd_count_off, sn))
for _ in range(sn):
    P.read_sound(r)
print("Sounds end              0x%08X" % r.pos)

# --- graphics: the disputed boundary -----------------------------------
gcount_off = r.pos
gn = r.i16()
ptr_start = r.pos
print("\nGraphics count          0x%08X (count=%d)" % (gcount_off, gn))
ptrs = r.i32_array(gn)
body_start = r.pos
print("Graphics pointer array  0x%08X -> 0x%08X  (%d bytes = %d x int32)" % (ptr_start, body_start, body_start - ptr_start, gn))
nz = sum(1 for p in ptrs if p != 0)
print("  nonzero pointers      = %d   (zero/null slots = %d)" % (nz, gn - nz))
print("Graphics bodies start   0x%08X" % body_start)
for p in ptrs:
    if p != 0:
        P.read_graphic(r)
print("Graphics bodies end     0x%08X  (%d bytes)" % (r.pos, r.pos - body_start))
print("  => Graphics whole stage 0x%08X -> 0x%08X" % (gcount_off, r.pos))

tb_off = r.pos
P.read_terrain_block(r)
print("\nTerrainBlock            0x%08X -> 0x%08X (%d bytes)" % (tb_off, r.pos, r.pos - tb_off))
rm_off = r.pos
P.read_random_maps(r)
print("RandomMaps              0x%08X -> 0x%08X (%d bytes)" % (rm_off, r.pos, r.pos - rm_off))

eff_off = r.pos
en = r.i32()
print("\nEffects count (int32)   0x%08X = %d" % (eff_off, en))
for _ in range(en):
    P.read_effect(r)
print("Effects end             0x%08X" % r.pos)

# UnitLines absent
uh_off = r.pos
uhn = r.i32()
print("\nUnitHeaders count (int32) 0x%08X = %d" % (uh_off, uhn))
for _ in range(uhn):
    P.read_unit_header(r)
print("UnitHeaders end         0x%08X" % r.pos)

civ_off = r.pos
cn = r.i16()
print("\nCivs count (int16)      0x%08X = %d" % (civ_off, cn))
for _ in range(cn):
    P.read_civ(r)
print("Civs end                0x%08X" % r.pos)

t_off = r.pos
tn = r.i16()
print("\nTechs count (int16)     0x%08X = %d" % (t_off, tn))
for _ in range(tn):
    P.read_tech(r)
print("Techs end               0x%08X" % r.pos)

tail_off = r.pos
for _ in range(7):
    r.i32()
print("\nTail 7 x int32          0x%08X -> 0x%08X" % (tail_off, r.pos))
tt_off = r.pos
P.read_tech_tree(r)
print("TechTree                0x%08X -> 0x%08X (%d bytes)" % (tt_off, r.pos, r.pos - tt_off))

print("\nFINAL offset %d ; file size %d ; exact=%s" % (r.pos, len(data), r.pos == len(data)))
