# -*- coding: utf-8 -*-
"""Trace ONE unit record field by field on both sides.

The whole-civ diff said "Gaia is 2 MB too long"; bisecting said "unit 0 is 484
bytes in Python and 630 in Rust".  Neither names a field.  This does: it replays
`read_unit` with the cursor printed after every step, so the first line where
the two implementations disagree IS the bug.

Writes `_golden/unit0_trace.txt` so the Rust side can be diffed against it
without either side guessing.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.parser as P          # noqa: E402

DAT = os.path.join(r"d:\games\steam\steamapps\common\AoE2DE",
                   "resources", "_common", "dat", "empires2_x2_p1.dat")
OUT = os.path.join(ROOT, "_golden", "unit0_trace.txt")

raw, _ = P.load_dat(DAT)
q = P.Parser(raw)
try:
    q.parse(stop_after=8)
except SystemExit:
    pass
offs = {n: (a, b) for n, a, b in q.stage_offsets}

r = P.Reader(raw)
r.pos = offs["8 Civs"][0]
civ_count = r.i16()
r.u8()
cname = r.debug_string()[1]
n = r.i16()
r.i16(); r.i16()
r.f32_array(n)
r.u8()
m = r.i16()
ptrs = r.i32_array(m)

lines = []


def step(label, fn):
    before = r.pos
    val = fn()
    lines.append("%-34s %7d -> %-7d (+%d)  %r"
                 % (label, before, r.pos, r.pos - before, val))
    return val


lines.append("civ %r units=%d start=%d" % (cname, m, r.pos))
u0 = r.pos
lines.append("=== unit record at %d ===" % u0)

step("type u8", r.u8) if False else None
lines.append("%-34s %7d -> %-7d (+%d)  %r" % ("type u8", r.pos, r.pos + 1, 1, None))
t = r.u8()
lines[-1] = "%-34s %7d -> %-7d (+%d)  %r" % ("type u8", u0, r.pos, 1, t)
step("id i16", r.i16)
step("LanguageDLLName i32", r.i32)
step("LanguageDLLCreation i32", r.i32)
step("class i16", r.i16)
step("StandingGraphic i16[2]", lambda: r.i16_array(2))
step("DyingGraphic i16", r.i16)
step("UndeadGraphic i16", r.i16)
step("UndeadMode u8", r.u8)
step("hit_points i16", r.i16)
step("LineOfSight f32", r.f32)
step("GarrisonCapacity u8", r.u8)
step("CollisionSize f32[3]", lambda: r.f32_array(3))
step("TrainSound i16", r.i16)
step("DamageSound i16", r.i16)
step("DeadUnitID i16", r.i16)
step("BloodUnitID i16", r.i16)
step("SortNumber u8", r.u8)
step("CanBeBuiltOn u8", r.u8)
step("IconID i16", r.i16)
step("HideInEditor u8", r.u8)
step("OldPortraitPict i16", r.i16)
step("Enabled u8", r.u8)
step("Disabled u8", r.u8)
step("PlacementSideTerrain i16[2]", lambda: r.i16_array(2))
step("PlacementTerrain i16[2]", lambda: r.i16_array(2))
step("ClearanceSize f32[2]", lambda: r.f32_array(2))
step("HillMode u8", r.u8)
step("FogVisibility u8", r.u8)
step("TerrainRestriction i16", r.i16)
step("FlyMode u8", r.u8)
step("ResourceCapacity i16", r.i16)
step("ResourceDecay f32", r.f32)
step("BlastDefenseLevel.. u8[5]", lambda: [r.u8() for _ in range(5)])
step("MultipleAttributeMode f32", r.f32)
step("MinimapColor u8", r.u8)
step("LanguageDLLHelp i32", r.i32)
step("LanguageDLLHotKeyText i32", r.i32)
# gv=54, so NO extra hotkey int32
step("Recyclable..GatherGroup u8[4]", lambda: [r.u8() for _ in range(4)])
step("OcclusionMode..Class u8[3]", lambda: [r.u8() for _ in range(3)])
step("Trait u8", r.u8)
step("Civilization u8", r.u8)
step("Nothing i16", r.i16)
step("SelectionEffect u8", r.u8)
step("EditorSelectionColour u8", r.u8)
step("OutlineSize f32[3]", lambda: r.f32_array(3))
step("trigger i32[2]", lambda: r.i32_array(2))
for k in range(3):
    step("ResourceStorage[%d] i16+f32+u8" % k, lambda: (r.i16(), r.f32(), r.u8()))
dgc = r.u8()
lines.append("%-34s damage_graphic_count=%r" % ("dgc u8", dgc))
for k in range(dgc):
    step("DamageGraphic[%d]" % k, lambda: (r.i16(), r.i16(), r.u8()))
step("SelectionSound i16", r.i16)
step("DyingSound i16", r.i16)
step("Wwise u32[4]", lambda: r.i32_array(4))
step("OldAttackReaction u8", r.u8)
step("ConvertTerrain u8", r.u8)
step("name debug_string", r.debug_string)
step("CopyID i16", r.i16)
step("BaseID i16", r.i16)
lines.append("--- after common block: type=%d pos=%d ---" % (t, r.pos))
if t >= 20:
    step("Speed f32", r.f32)
if t >= 30:
    lines.append("(dead fish block)")
if t >= 40:
    lines.append("%-34s pos=%d  (bird block follows)" % ("task_swap_group u8", r.pos))

lines.append("=== unit0 ends at %s (span %d) ===" % (None, -1))
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")
print("\n".join(lines[-24:]))
print()
print("wrote", OUT)
