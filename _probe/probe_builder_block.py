# -*- coding: utf-8 -*-
r"""Whose data IS the panel file?  A structural test, not a reference scan.

Two candidate consumers for `resources/_common/dat/futuravailableunits.json`:

  (a) the **build menu** -- the buttons you click to make things,
  (b) the **tech-tree preview screen** -- the diagram of what you can eventually get.

The file is organised as

    <Civ> -> Buildings -> [ {ID: <building>, Units: [...], Techs: [...]}, ... ]

and the observation-planner reported entries hanging under building **118**, whose
tree name is `Builder`.  A villager's build menu IS "building 118 produces these
buildings", which is exactly this shape.  A tech-tree preview is organised by AGE,
not by producer -- so it has no reason to carry a `Builder` block.

That is testable: if the panel's building-118 `Units` array is the villager build
menu, then it should be (i) present for essentially every civ, (ii) composed of
BUILDING ids, and (iii) agree with the civ's tree building rows.
"""
import os
import sys
from collections import Counter

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

ZH = {}
kd = os.path.join(GAME, "resources", "zh", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        with open(os.path.join(kd, fn), "rb") as fh:
            for line in fh.read().decode("utf-8-sig", "replace").splitlines():
                k, _, v = line.strip().partition("\t")
                if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                    ZH.setdefault(int(k.strip()), v[1:-1])


def bname(bid):
    for t in trees.values():
        for r in CT.rows_of(t):
            if r.get("Use Type") == "Building" and r.get("Node ID") == bid:
                sid = r.get("Name String ID")
                if sid and sid in ZH:
                    return ZH[sid]
    u = idx.get("unit", bid)
    return ((u.zh or u.en) if u else None) or ("bldg %s" % bid)


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

print("A  which building ids appear as a BLOCK, and how often?")
blk_count = Counter()
for stem, (disp, obj) in civs.items():
    for blk in BP.buildings(obj, disp):
        blk_count[blk.get("ID")] += 1
print("   distinct building blocks: %d" % len(blk_count))
for bid, n in blk_count.most_common(12):
    print("      building %-6s in %3d civs   %s" % (bid, n, bname(bid)))

print()
print("B  the `Builder` block (118): is it the villager build menu?")
n_have = sum(1 for stem, (disp, obj) in civs.items()
             if any(b.get("ID") == 118 for b in BP.buildings(obj, disp)))
print("   civs with a building-118 block: %d of %d" % (n_have, len(civs)))
sample = "BRITONS"
disp, obj = civs[sample]
blk118 = next((b for b in BP.buildings(obj, disp) if b.get("ID") == 118), None)
us = (blk118 or {}).get(BP.UNITS_KEY) or []
print("   %s, building 118 Units (%d):" % (sample, len(us)))
for e in us:
    print("      %-6s %-22s RequiredAge=%s" % (e.get("ID"), e.get("Name"),
                                               e.get("RequiredAge")))

print()
print("C  are those ids BUILDINGS in the civ's tree?")
tree = trees[sample]
brows = {r.get("Node ID"): r for r in CT.rows_of(tree)
         if r.get("Use Type") == "Building"}
in_tree = [e.get("ID") for e in us if e.get("ID") in brows]
not_in_tree = [e.get("ID") for e in us if e.get("ID") not in brows]
print("   in the tree as Building rows : %d  %s" % (len(in_tree), in_tree))
print("   NOT in the tree as Building  : %d  %s"
      % (len(not_in_tree), [(i, bname(i)) for i in not_in_tree]))
print("   tree Building rows for %s: %d" % (sample, len(brows)))

print()
print("D  agreement across every civ: 118's Units vs the tree's Building rows")
same = diff_missing = diff_extra = 0
details = []
for stem, (disp, obj) in sorted(civs.items()):
    blk = next((b for b in BP.buildings(obj, disp) if b.get("ID") == 118), None)
    if blk is None:
        continue
    p = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
    t = {r.get("Node ID") for r in CT.rows_of(trees[stem])
         if r.get("Use Type") == "Building"}
    miss = t - p
    extra = p - t
    if not miss and not extra:
        same += 1
    else:
        if miss:
            diff_missing += 1
        if extra:
            diff_extra += 1
        details.append((stem, sorted(miss), sorted(extra)))
print("   exact agreement: %d civs" % same)
print("   panel MISSING tree buildings: %d civs" % diff_missing)
print("   panel listing NON-tree buildings: %d civs" % diff_extra)
for stem, miss, extra in details[:12]:
    print("      %-12s missing=%s extra=%s"
          % (stem, [(i, bname(i)) for i in miss][:6],
             [(i, bname(i)) for i in extra][:6]))
