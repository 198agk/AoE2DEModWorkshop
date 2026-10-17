# -*- coding: utf-8 -*-
r"""Resolve the `Builder` block: 18 panel entries vs 29 tree Building rows.

If the panel's building-118 block were "what a villager can build", it should
contain the basics -- Barracks (12), Mill (68), House (70), Palisade (72).  It does
not.  So either

  (a) the missing ones are listed SOMEWHERE ELSE in the panel, or
  (b) the block means something narrower than "the build menu".

Both are answerable by looking, and the answer decides what an `unit.availability`
write to this file actually controls -- which is the product question.
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

ZH = {}
kd = os.path.join(GAME, "resources", "zh", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        with open(os.path.join(kd, fn), "rb") as fh:
            for line in fh.read().decode("utf-8-sig", "replace").splitlines():
                k, _, v = line.strip().partition("\t")
                if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                    ZH.setdefault(int(k.strip()), v[1:-1])

NAME = {}
for t in trees.values():
    for r in CT.rows_of(t):
        if r.get("Use Type") == "Building" and r.get("Node ID") is not None:
            sid = r.get("Name String ID")
            if sid and sid in ZH:
                NAME.setdefault(r.get("Node ID"), ZH[sid])


def nm(bid):
    if bid in NAME:
        return NAME[bid]
    u = idx.get("unit", bid)
    return ((u.zh or u.en) if u else None) or ("bldg %s" % bid)


stem, disp = "BRITONS", "Britons"
tree = trees[stem]
obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]

trows = {r.get("Node ID"): r for r in CT.rows_of(tree)
         if r.get("Use Type") == "Building"}
p118 = {e.get("ID"): e for e in (
    next(b for b in BP.buildings(obj, disp) if b.get("ID") == 118)
    .get(BP.UNITS_KEY) or [])}

print("A  every tree Building row for %s, and whether it is in the 118 block"
      % stem)
print("   %-7s %-22s %-22s %-8s %s"
      % ("id", "name", "Node Type", "in 118?", "in ANY panel block?"))
all_panel_ids = {}
for blk in BP.buildings(obj, disp):
    for e in (blk.get(BP.UNITS_KEY) or []):
        all_panel_ids.setdefault(e.get("ID"), []).append(blk.get("ID"))
for bid, r in sorted(trows.items()):
    print("   %-7s %-22s %-22s %-8s %s"
          % (bid, nm(bid), r.get("Node Type"), bid in p118,
             all_panel_ids.get(bid, "NO")))

print()
print("B  the panel's 118 block: 18 ids, their Node Type in the tree")
for e in (next(b for b in BP.buildings(obj, disp) if b.get("ID") == 118)
          .get(BP.UNITS_KEY) or []):
    r = trows.get(e.get("ID"))
    print("   %-7s %-22s tree Node Type=%-20s RequiredAge=%s"
          % (e.get("ID"), e.get("Name"),
             (r or {}).get("Node Type"), e.get("RequiredAge")))

print()
print("C  the ids in the tree but NOT in the 118 block -- where do they live?")
missing = [b for b in trows if b not in p118]
for bid in sorted(missing):
    print("   %-7s %-22s Node Type=%-20s in other panel blocks: %s"
          % (bid, nm(bid), trows[bid].get("Node Type"),
             all_panel_ids.get(bid, "NOWHERE IN PANEL")))

print()
print("D  what Node Type do the 118-block ids share?")
from collections import Counter                                # noqa: E402
print("   118 block   :", Counter((trows.get(i) or {}).get("Node Type")
                                  for i in p118))
print("   tree-only   :", Counter((trows.get(i) or {}).get("Node Type")
                                  for i in missing))
