# -*- coding: utf-8 -*-
r"""GATE CLASS 5: the producing building must itself be buildable by that civ.

The enlarged kind-P table (`probe_missing_row_class.py`) yielded 7 subjects where
the panel lists a unit and the tree carries NO row for it -- including six that sit
on AZTECS/INCAS/MAYANS, base-game civilizations that avoid the DLC-ownership
problem.  They are all unit 1570 (Xolotl Warrior) at **building 101, the Stable**.

They are all USELESS, and the reason is a gate class this project had not
enumerated: **the Aztec/Inca/Mayan tree marks the Stable itself `NotAvailable`**
(those civilizations famously have no Stable).  A unit listed inside a building the
civilization can never construct is unobservable -- the player cannot reach the
menu that would show it.

So the completeness test needs a fifth clause:

    the producing building must be `ResearchedCompleted` or `ResearchRequired`
    in the same layer that is promising the unit

Check every candidate against all five gates and report the survivors.
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


def bname(bid):
    for t in trees.values():
        for r in CT.rows_of(t):
            if r.get("Use Type") == "Building" and r.get("Node ID") == bid:
                return r.get("Name")
    return "bldg %s" % bid


def building_status(tree, bid):
    for r in CT.rows_of(tree):
        if r.get("Use Type") == "Building" and r.get("Node ID") == bid:
            return r.get("Node Status")
    return None            # no row at all


print("A  GATE 5 applied to the 7 no-row candidates")
CASES = [
    ("AZTECS", "Aztecs", 101, 1570), ("INCAS", "Incas", 101, 1570),
    ("MAYANS", "Mayans", 101, 1570), ("MAPUCHE", "Mapuche", 101, 1570),
    ("MUISCA", "Muisca", 101, 1570), ("TUPI", "Tupi", 101, 1570),
    ("SPARTANS", "Spartans", 2172, 2147),
]
usable = []
for stem, disp, bid, uid in CASES:
    t = trees[stem]
    bs = building_status(t, bid)
    can = bs in ("ResearchedCompleted", "ResearchRequired")
    print("   %-11s bldg %-5s (%-14s) building status=%-18s buildable=%s"
          % (stem, bid, bname(bid), bs, can))
    if can:
        usable.append((stem, disp, bid, uid))
print("   -> buildable: %d of %d" % (len(usable), len(CASES)))

print()
print("B  why those six fail: the Aztec-group tree has no Stable")
az = trees["AZTECS"]
for r in CT.rows_of(az):
    if r.get("Use Type") == "Building" and r.get("Node ID") == 101:
        print("      AZTECS building 101 row: %s"
              % {k: r.get(k) for k in ("Node ID", "Name", "Node Status",
                                       "Age ID", "Node Type")})
print("      and the panel still lists a unit under it: %s"
      % [(e.get("ID"), e.get("Name"), e.get("RequiredAge"))
         for blk in BP.buildings(
             panels[BP.panel_path_for(GAME, "Aztecs")[1]]["obj"], "Aztecs")
         if blk.get("ID") == 101 for e in (blk.get(BP.UNITS_KEY) or [])])
print("      => a unit in a building the civ cannot build is unobservable")

print()
print("C  the survivor (if any), in full")
for stem, disp, bid, uid in usable:
    t = trees[stem]
    r = CT.row_for(t, uid, CT.UNIT_USE_TYPES)
    u = idx.get("unit", uid)
    print("      civ %s (%s)" % (disp, stem))
    print("         building %s = %r status=%r"
          % (bid, bname(bid), building_status(t, bid)))
    print("         unit %s = %r  tree row: %s"
          % (uid, ((u.zh or u.en) if u else None),
             "NONE" if r is None else {k: r.get(k) for k in
                                       ("Name", "Node Status", "Age ID")}))
    o = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    for blk in BP.buildings(o, disp):
        if blk.get("ID") == bid:
            print("         panel: %s"
                  % [(e.get("ID"), e.get("Name"), e.get("RequiredAge"))
                     for e in (blk.get(BP.UNITS_KEY) or [])])

print()
print("D  NOW recheck the four NotAvailable-class subjects against gate 5")
CASES2 = [("MAPUCHE", "Mapuche", 45, 528), ("MUISCA", "Muisca", 12, 359),
          ("POLES", "Poles", 45, 691), ("WU", "Wu", 87, 474)]
for stem, disp, bid, uid in CASES2:
    t = trees[stem]
    bs = building_status(t, bid)
    ok = bs in ("ResearchedCompleted", "ResearchRequired")
    print("   %-11s bldg %-5s (%-16s) status=%-18s buildable=%s"
          % (stem, bid, bname(bid), bs, ok))
    if not ok:
        print("      !! the producing building is not buildable -> subject unusable")

print()
print("E  and recheck the two kind-T subjects against gate 5")
for stem, disp, bid, uid in (("SICILIANS", "Sicilians", 49, 588),
                             ("SPARTANS", "Spartans", 2172, 13)):
    t = trees[stem]
    bs = building_status(t, bid)
    ok = bs in ("ResearchedCompleted", "ResearchRequired")
    print("   %-11s bldg %-5s (%-16s) status=%-18s buildable=%s"
          % (stem, bid, bname(bid), bs, ok))
