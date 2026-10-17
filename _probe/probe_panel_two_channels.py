# -*- coding: utf-8 -*-
r"""The panel has TWO availability channels -- my kind-T class missed one.

`futuravailableunits.json` lists, per building, a `Units` array AND a `Techs`
array.  A unit that requires an upgrade research appears in the *Techs* array
(you research it, the unit then becomes trainable) rather than in `Units`.

Measured just now: unit 588 (Siege Onager) has `Trigger Tech ID = 320`, and

    GEORGIANS  panel Techs at building 49 CONTAINS 320
    SICILIANS  panel Techs at building 49 does NOT

so for GEORGIANS the panel is **not** silent about Siege Onager -- it says so in
the Techs channel.  Calling that a kind-T disagreement was wrong, and if the user
had played the Georgians game, "no Siege Onager button" would have been evidence
about a gate I had failed to see.

Refine the definition: a subject is kind-T only if the panel lists NEITHER the
unit in `Units` NOR its `Trigger Tech ID` in that building's `Techs`.
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
    return ((u.zh or u.en) if u else None) or None


def tname(tid):
    u = idx.get("tech", tid)
    return ((u.zh or u.en) if u else None) or ("tech %s" % tid)


civs = {}
seen = set()
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            continue
        seen.add((rec["path"], disp))
        stem = CT.civ_file_stem(disp)
        if stem in trees:
            civs[stem] = (disp, rec["obj"])

print("A  how many civs get unit 588 (Siege Onager) in each channel?")
n_tree = n_panel_tech = n_panel_unit = 0
for stem, (disp, obj) in sorted(civs.items()):
    tree = trees[stem]
    st = CT.node_status(tree, 588, CT.UNIT_USE_TYPES)
    units_at = set()
    techs_at = set()
    for blk in BP.buildings(obj, disp):
        if blk.get("ID") != 49:
            continue
        for e in (blk.get(BP.UNITS_KEY) or []):
            units_at.add(e.get("ID"))
        for e in (blk.get(BP.TECHS_KEY) or []):
            techs_at.add(e.get("ID"))
    if st == "ResearchedCompleted":
        n_tree += 1
    if 588 in units_at:
        n_panel_unit += 1
    if 320 in techs_at:
        n_panel_tech += 1
print("   tree says ResearchedCompleted : %d civs" % n_tree)
print("   panel Units lists 588         : %d civs" % n_panel_unit)
print("   panel Techs lists 320         : %d civs" % n_panel_tech)
print()

print("B  the refinement: kind-T must be silent in BOTH channels")
kindT_old, kindT_new = [], []
for stem, (disp, obj) in sorted(civs.items()):
    tree = trees[stem]
    owned = {r.get("Node ID") for r in CT.rows_of(tree)
             if r.get("Use Type") == "Building"}
    units_all, techs_all = set(), set()
    for blk in BP.buildings(obj, disp):
        for e in (blk.get(BP.UNITS_KEY) or []):
            units_all.add(e.get("ID"))
        for e in (blk.get(BP.TECHS_KEY) or []):
            techs_all.add(e.get("ID"))
    for r in CT.unit_rows(tree):
        uid = r.get("Node ID")
        if uid is None or not uname(uid):
            continue
        if (r.get("Node Status") != "ResearchedCompleted"
                or r.get("Building ID") not in owned or uid in units_all):
            continue
        ttl = r.get("Trigger Tech ID")
        # OLD rule: Units channel only
        kindT_old.append((stem, uid, uname(uid), r.get("Age ID"),
                          r.get("Building ID"), ttl))
        # NEW rule: silent in BOTH channels
        if ttl and ttl in techs_all:
            continue
        kindT_new.append((stem, uid, uname(uid), r.get("Age ID"),
                          r.get("Building ID"), ttl))

print("   OLD (Units channel only): %d" % len(kindT_old))
for row in sorted(kindT_old, key=lambda r: (r[3] or 9, r[0])):
    print("      %s" % (row,))
print()
print("   NEW (silent in Units AND Techs): %d" % len(kindT_new))
for row in sorted(kindT_new, key=lambda r: (r[3] or 9, r[0])):
    print("      %s" % (row,))

print()
print("C  which of the OLD ones were false positives?")
old_set = {(r[0], r[1]) for r in kindT_old}
new_set = {(r[0], r[1]) for r in kindT_new}
for k in sorted(old_set - new_set):
    stem, uid = k
    print("   %-12s unit %-6s %s  -> the panel DOES list its tech, so the panel"
          % (stem, uid, uname(uid)))
    row = next(r for r in kindT_old if (r[0], r[1]) == k)
    if row[5]:
        print("        is not silent: Trigger Tech ID %s (%s) is in its Techs"
              % (row[5], tname(row[5])))
