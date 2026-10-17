# -*- coding: utf-8 -*-
r"""The AZTECS Xolotl Warrior case -- a BASE-GAME civilization candidate.

`probe_missing_row_class.py` found 7 more subjects where the panel lists a unit and
the tree has NO ROW for it.  Six of them are unit 1570 ('索洛托勇士' / Xolotl
Warrior) at building 101 (Stable), for AZTECS, INCAS, MAYANS, MAPUCHE, MUISCA and
TUPI -- and the first three are base-game / The Conquerors civilizations that almost
any player owns.  That matters because all four Imperial-Age complete-path subjects
sits on DLC civilizations.

Check the case in full, including whether the AoE2DE Stable is really in the Aztec
tree and what the panel says, so the recommendation can avoid the DLC question.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)


def uname(uid):
    u = idx.get("unit", uid)
    return ((u.zh or u.en) if u else None)


print("A  the six civilizations that carry unit 1570 in the panel, tree row?")
for stem in ("AZTECS", "INCAS", "MAYANS", "MAPUCHE", "MUISCA", "TUPI"):
    t = trees[stem]
    r = CT.row_for(t, 1570, CT.UNIT_USE_TYPES)
    b101 = CT.row_for(t, 101, CT.BUILDING_USE_TYPES) if hasattr(
        CT, "BUILDING_USE_TYPES") else None
    # find the building row by hand
    b = None
    for x in CT.rows_of(t):
        if x.get("Use Type") == "Building" and x.get("Node ID") == 101:
            b = x
    print("   %-11s unit1570 tree row=%-5s | building 101 row: %s"
          % (stem, "YES" if r else "none",
             {k: b.get(k) for k in ("Node Status", "Name", "Age ID")} if b else None))

print()
print("B  AZTECS, in full, at building 101")
az = trees["AZTECS"]
b = None
for x in CT.rows_of(az):
    if x.get("Use Type") == "Building" and x.get("Node ID") == 101:
        b = x
print("   tree building 101 row: %s" % ({k: b.get(k) for k in
                                        ("Name", "Node Status", "Age ID",
                                         "Node ID")} if b else None))
print("   tree unit rows at building 101:")
for r in CT.unit_rows(az):
    if r.get("Building ID") == 101:
        print("      unit %-6s %-22s status=%-18s age=%s"
              % (r.get("Node ID"), r.get("Name"), r.get("Node Status"),
                 r.get("Age ID")))
o = panels[BP.panel_path_for(GAME, "Aztecs")[1]]["obj"]
for blk in BP.buildings(o, "Aztecs"):
    if blk.get("ID") == 101:
        print("   panel building 101 Units: %s"
              % [(e.get("ID"), e.get("Name"), e.get("RequiredAge"))
                 for e in (blk.get(BP.UNITS_KEY) or [])])
        print("   panel building 101 Techs: %s"
              % [(e.get("ID"), e.get("Name"))
                 for e in (blk.get(BP.TECHS_KEY) or [])])

print()
print("C  is 1570 present in ANY tree anywhere?")
stems = [s for s, t in trees.items()
         if CT.row_for(t, 1570, CT.UNIT_USE_TYPES) is not None]
print("   civs whose tree has a row for 1570: %d %s" % (len(stems), stems))

print()
print("D  what is unit 1570 (the .dat record), and how is it obtained in AoE2?")
import aoe2mod.api as A                                    # noqa: E402
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
recs = tk._unit_records() if hasattr(tk, "_unit_records") else None
if recs:
    r = recs[1570] if 1570 < len(recs) else None
    if r:
        print("   type=%s class=%s hp=%s train_locations=%s"
              % (r.get("type"), r.get("class"), r.get("hit_points"),
                 r.get("train_locations")))
print("   semantic: en=%r zh=%r" % (
    (idx.get("unit", 1570).en if idx.get("unit", 1570) else None),
    (idx.get("unit", 1570).zh if idx.get("unit", 1570) else None)))

print()
print("E  which building is 2172 (SPARTANS Port) vs 101 (Stable)?")
for x in (101, 2172):
    nm = None
    for t in trees.values():
        for r in CT.rows_of(t):
            if r.get("Use Type") == "Building" and r.get("Node ID") == x:
                nm = r.get("Name")
                break
        if nm:
            break
    own = [s for s, t in trees.items()
           if any(r.get("Use Type") == "Building" and r.get("Node ID") == x
                  for r in CT.rows_of(t))]
    print("   building %-5s name=%-16r in %d civs" % (x, nm, len(own)))
    if x == 101:
        print("      stable owners: %s" % sorted(own))
