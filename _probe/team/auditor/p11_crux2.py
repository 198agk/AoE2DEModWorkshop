# -*- coding: utf-8 -*-
"""Audit probe 11 -- REDO of p9's tree-side scans using the REAL accessor
(rows_of/_rows), because p9 used tree["Units"] which does not exist and made
its 9d/9e results vacuous zeros."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, sys, collections, inspect
sys.path.insert(0, _HERE_PATH("..", "..", ".."))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UE = CT.UNIT_USE_TYPES

def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)

print("### rows_of / _rows source")
print("\n".join(inspect.getsource(CT.rows_of).splitlines()[:30]))
print()
print("### _rows source")
print("\n".join(inspect.getsource(CT._rows).splitlines()[:25]))

trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

head("11a: sanity -- how many unit rows does the real accessor see per civ")
print("   BRITONS rows_of -> %d ; INCAS -> %d" % (len(CT.rows_of(trees["BRITONS"])),
                                                 len(CT.rows_of(trees["INCAS"]))))

head("11b: A-direction: tree rows at bldg 12 the civ's panel does NOT list")
miss = []
for ck, tree in trees.items():
    p = panels.get(ck)
    if p is None:
        continue
    for row in CT.rows_of(tree):
        if not isinstance(row, dict) or row.get("Use Type") not in UE:
            continue
        if row.get("Building ID") != 12:
            continue
        nid = row.get("Node ID")
        bid_, _ = BP.find_entry(p["obj"], p["key"], nid, BP.UNITS_KEY)
        if bid_ != 12:
            miss.append((ck, nid, row.get("Name"), row.get("Age ID"), row.get("Node Status"),
                         row.get("Node Type"), bid_))
print("   shipped (civ,unit) with a bldg-12 tree row that the panel does NOT place at bldg 12: %d" % len(miss))
print("   %-12s %-7s %-26s %-4s %-20s %-14s %s" % ("civ", "id", "name", "age", "status", "nodeType", "panelBldg"))
for m in miss[:80]:
    print("   %-12s %-7s %-26s %-4s %-20s %-14s %s" % m)
print("   ... by age   :", dict(sorted(collections.Counter(m[3] for m in miss).items(), key=str)))
print("   ... by status:", dict(collections.Counter(m[4] for m in miss)))
print("   ... by type  :", dict(collections.Counter(m[5] for m in miss)))
print("   ... by panelBldg:", dict(collections.Counter(m[6] for m in miss)))

head("11c: same but restricted to status that GRANTS access (ResearchedCompleted/ResearchRequired)")
g = [m for m in miss if m[4] in ("ResearchedCompleted", "ResearchRequired")]
print("   %d of %d" % (len(g), len(miss)))
for m in g[:60]:
    print("   %-12s %-7s %-26s %-4s %-20s %-14s %s" % m)

head("11d: tree rows at bldg 12 that panel lacks ENTIRELY (panelBldg is None)")
n = [m for m in miss if m[6] is None]
print("   %d" % len(n))
for m in n[:60]:
    print("   %-12s %-7s %-26s %-4s %-20s %-14s %s" % m)

head("11e: Britons Age-1 bldg-12 rows, real accessor")
for row in CT.rows_of(trees["BRITONS"]):
    if isinstance(row, dict) and row.get("Building ID") == 12 and row.get("Age ID") == 1:
        print("   %s" % json.dumps(row, ensure_ascii=False))

head("11f: the granted row vs Britons' existing rows -- gates that differ")
brit = trees["BRITONS"]
dro = CT.donor_row(trees, 2550, UE)[1]
print("   donor:", json.dumps(dro, ensure_ascii=False))
rows12 = [r for r in CT.rows_of(brit) if isinstance(r, dict) and r.get("Building ID") == 12]
allf = collections.Counter()
for r in rows12:
    allf.update(r.keys())
print("   bldg-12 row count=%d ; field presence: %s" % (len(rows12), dict(allf)))
print("   rows carrying Trigger Tech ID at bldg 12:", [r.get("Node ID") for r in rows12 if r.get("Trigger Tech ID")])
print("   rows carrying Link Node Type:", collections.Counter(r.get("Link Node Type") for r in rows12))

head("11g: what does a RegionalUnit row imply that a Unit row does not? (Draw/Link fields)")
for nt in ("Unit", "RegionalUnit", "UniqueUnit"):
    ex = [r for r in CT.rows_of(brit) if isinstance(r, dict) and r.get("Node Type") == nt][:2]
    for e in ex:
        print("   %-13s %s" % (nt, json.dumps(e, ensure_ascii=False)[:230]))
