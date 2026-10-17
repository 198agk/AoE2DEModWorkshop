# -*- coding: utf-8 -*-
"""Audit probe 12 -- definitive, with the key-space bridge that p9 and p11 both
got wrong (trees are stems 'BRITONS', panels are display names 'Britons').
p11's 11b-11d printed 0 because panels.get('BRITONS') was None for all 62 civs."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, sys, collections
sys.path.insert(0, _HERE_PATH("..", "..", ".."))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UE = CT.UNIT_USE_TYPES

def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)

trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

head("12a: key spaces")
print("   tree keys sample :", sorted(trees)[:8])
print("   panel keys sample:", sorted(panels)[:8])
print("   overlap (exact)  :", len(set(trees) & set(panels)), sorted(set(trees) & set(panels))[:10])
print("   tree-only        :", len(set(trees) - set(panels)), sorted(set(trees) - set(panels))[:10])
print("   panel-only       :", len(set(panels) - set(trees)), sorted(set(panels) - set(trees))[:12])

head("12b: bridge every panel civ to a tree via CT.civ_file_stem")
pairs = []
unmatched = []
for pk in panels:
    stem = CT.civ_file_stem(pk)
    if stem in trees:
        pairs.append((pk, stem))
    else:
        unmatched.append((pk, stem))
print("   matched pairs: %d ; unmatched panel civs: %d %s" % (len(pairs), len(unmatched), unmatched))
print("   trees with no panel:", [s for s in trees if s not in {st for _, st in pairs}])

head("12c: A-direction (tree bldg-12 row, panel does not place it at bldg 12)")
miss = []
for pk, stem in pairs:
    p = panels[pk]
    for row in CT.rows_of(trees[stem]):
        if not isinstance(row, dict) or row.get("Use Type") not in UE:
            continue
        if row.get("Building ID") != 12:
            continue
        nid = row.get("Node ID")
        bid_, _ = BP.find_entry(p["obj"], p["key"], nid, BP.UNITS_KEY)
        if bid_ != 12:
            miss.append((stem, nid, row.get("Name"), row.get("Age ID"), row.get("Node Status"),
                         row.get("Node Type"), bid_))
print("   count = %d" % len(miss))
print("   %-12s %-7s %-26s %-4s %-20s %-14s %s" % ("civ", "id", "name", "age", "status", "nodeType", "panelBldg"))
for m in miss[:60]:
    print("   %-12s %-7s %-26s %-4s %-20s %-14s %s" % m)
if miss:
    print("   by status:", dict(collections.Counter(m[4] for m in miss)))

head("12d: A-direction restricted to GRANTING statuses (would a tree-only edit be visible?)")
g = [m for m in miss if m[4] in ("ResearchedCompleted", "ResearchRequired")]
print("   %d of %d" % (len(g), len(miss)))
for m in g[:40]:
    print("   %-12s %-7s %-26s %-4s %-20s %-14s %s" % m)

head("12e: B-direction (panel places it at bldg 12, tree row missing / NotAvailable)")
bad = []
for pk, stem in pairs:
    p = panels[pk]
    for b in BP.buildings(p["obj"], p["key"]):
        if b.get("ID") != 12:
            continue
        for e in BP.entries(p["obj"], p["key"], 12, BP.UNITS_KEY):
            nid = e.get("ID")
            row = CT.row_for(trees[stem], nid, UE)
            st = None if row is None else row.get("Node Status")
            if st not in ("ResearchedCompleted", "ResearchRequired"):
                bad.append((stem, nid, e.get("Name"), e.get("RequiredAge"), st,
                            None if row is None else row.get("Age ID"),
                            None if row is None else row.get("Building ID"),
                            None if row is None else row.get("Node Type")))
print("   count = %d" % len(bad))
print("   %-12s %-7s %-26s %-6s %-12s %-5s %-6s %s" % ("civ", "id", "panelName", "ReqAge", "treeStatus", "AgeT", "BldgT", "NodeType"))
for m in bad[:60]:
    print("   %-12s %-7s %-26s %-6s %-12s %-5s %-6s %s" % m)

head("12f: global tallies over ALL panel unit entries (properly bridged)")
tot = norow = notgrant = 0
for pk, stem in pairs:
    p = panels[pk]
    for b in BP.buildings(p["obj"], p["key"]):
        bid = b.get("ID")
        for e in BP.entries(p["obj"], p["key"], bid, BP.UNITS_KEY):
            tot += 1
            row = CT.row_for(trees[stem], e.get("ID"), UE)
            if row is None:
                norow += 1
            elif row.get("Node Status") not in ("ResearchedCompleted", "ResearchRequired"):
                notgrant += 1
print("   panel unit entries=%d ; no tree row=%d ; tree row not granting=%d" % (tot, norow, notgrant))

head("12g: do panel entries for a unit carry RequiredAge that tracks the tree Age ID?")
mism = []
for pk, stem in pairs:
    p = panels[pk]
    for b in BP.buildings(p["obj"], p["key"]):
        for e in BP.entries(p["obj"], p["key"], b.get("ID"), BP.UNITS_KEY):
            row = CT.row_for(trees[stem], e.get("ID"), UE)
            if row is None:
                continue
            if row.get("Building ID") != b.get("ID"):
                mism.append(("BLDG", stem, e.get("ID"), e.get("Name"), b.get("ID"), row.get("Building ID")))
            if row.get("Age ID") != e.get("RequiredAge"):
                mism.append(("AGE", stem, e.get("ID"), e.get("Name"), e.get("RequiredAge"), row.get("Age ID")))
print("   mismatches: %d" % len(mism))
print("   by kind:", dict(collections.Counter(m[0] for m in mism)))
for m in mism[:40]:
    print("   %s" % (m,))
