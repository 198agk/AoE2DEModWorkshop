# -*- coding: utf-8 -*-
r"""Diagnose the three failures from `test_panel_shape.py`.

  C  "the Builder block's Units list is a strict subset of the tree's building rows"
     failed for at least one civilization though BRITONS/FRANKS/CELTS all pass.

  E  the panel has 134 (civ, block) pairs whose block ID is not a tree Building row
     for that civ.  The distinct ids are [13, 68, 104, 118, 2171, 2414] -- and 118 is
     the Builder pseudo-building, which is a menu CATEGORY rather than a place.
     Some of the others are real buildings (68 Mill, 104 Monastery), so there is
     more than one reason a block may have no tree row.
"""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

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

def tbuild(stem):
    return {r.get("Node ID") for r in CT.rows_of(trees[stem])
            if r.get("Use Type") == "Building"}

print("A  which civs have a Builder Units entry that is NOT a tree building?")
bad = []
for stem, (disp, obj) in sorted(civs.items()):
    blk = next((b for b in BP.buildings(obj, disp) if b.get("ID") == 118), None)
    us = {e.get("ID") for e in ((blk or {}).get(BP.UNITS_KEY) or [])}
    extra = sorted(us - tbuild(stem))
    if extra:
        bad.append((stem, extra))
print("   civs failing: %d" % len(bad))
for stem, extra in bad:
    # what are those extras in the tree at all (any Use Type)?
    rows = [r for r in CT.rows_of(trees[stem])
            if r.get("Node ID") in extra]
    print("   %-13s extras=%s" % (stem, extra))
    for r in rows:
        print("        tree row: Node %s UseType=%r Name=%r Status=%r"
              % (r.get("Node ID"), r.get("Use Type"), r.get("Name"),
                 r.get("Node Status")))

print()
print("B  the panel-only block ids: what are they?")
only = defaultdict(set)
for stem, (disp, obj) in sorted(civs.items()):
    tb = tbuild(stem)
    for b in BP.buildings(obj, disp):
        bid = b.get("ID")
        if bid not in tb:
            only[bid].add(stem)
for bid in sorted(only, key=lambda x: -len(only[x])):
    stems = sorted(only[bid])
    nm = None
    for t in trees.values():
        for r in CT.rows_of(t):
            if r.get("Use Type") == "Building" and r.get("Node ID") == bid:
                nm = r.get("Name")
                break
        if nm:
            break
    print("   block %-6s in %2d civs  tree building name=%-18r civs=%s"
          % (bid, len(stems), nm, stems[:8]))

print()
print("C  is 118 a pseudo-block (a menu category)?")
o = panels[BP.panel_path_for(GAME, "Britons")[1]]["obj"]
b = next(x for x in BP.buildings(o, "Britons") if x.get("ID") == 118)
print("   118 keys: %s" % sorted(b))
print("   118 Name=%r" % b.get("Name"))
print("   118 Units=%s" % [e.get("ID") for e in (b.get(BP.UNITS_KEY) or [])])
print("   118 Techs=%s" % [e.get("ID") for e in (b.get(BP.TECHS_KEY) or [])])
print("   -> it lists buildings the villager can PLACE, so its 'Units' are")
print("      buildings-as-buildable-items, not units produced by a building")

print()
print("D  and the ones that are real buildings but absent from that civ's tree")
for bid in (68, 104, 13, 2171, 2414):
    stems = sorted(only.get(bid, ()))
    print("   %-6s absent from the tree of: %s" % (bid, stems))
    for s in stems[:3]:
        # does the civ have ANY row for it, under another Use Type?
        rows = [r for r in CT.rows_of(trees[s]) if r.get("Node ID") == bid]
        print("        %-13s rows=%s" % (s, [(r.get("Use Type"),
                                              r.get("Node Status"))
                                             for r in rows]))
