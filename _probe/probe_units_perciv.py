# -*- coding: utf-8 -*-
r"""DECISIVE: is the panel's `Units` array per-civ, or "the chain lives here"?

If `Units` were a per-civ availability statement ("this civ can build this"), then a
unit's presence would track the civ's TREE status.  If instead `Units` merely lists
the building's unit CHAIN and per-civ gating happens in `Techs` (for upgrades) or the
tree (for base units), then presence would be near-constant across civilizations.

My whole kind-P class rests on reading `Units` as an availability statement.  The
upgrade-gate probe just showed JURCHENS lists 77 (Long Swordsman) in `Units` while
NOT offering its upgrade tech 207 in `Techs` -- internally inconsistent under that
reading.  So measure it: for each (building, unit) pair the panel names, how many of
the civs that HAVE that building list it, and how does that compare to the tree?
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

# Per (building, unit): which civs list it in Units, which civs' trees say buildable
LIST = defaultdict(set)
HAVE_BLD = defaultdict(set)
for stem, (disp, obj) in sorted(civs.items()):
    for blk in BP.buildings(obj, disp):
        bid = blk.get("ID")
        HAVE_BLD[bid].add(stem)
        for e in (blk.get(BP.UNITS_KEY) or []):
            LIST[(bid, e.get("ID"))].add(stem)

TREE_OK = defaultdict(set)
for stem, tree in sorted(trees.items()):
    for r in CT.unit_rows(tree):
        uid = r.get("Node ID")
        if uid is not None and r.get("Node Status") != "NotAvailable":
            TREE_OK[uid].add(stem)

TRIG = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        u, tt = r.get("Node ID"), r.get("Trigger Tech ID")
        if u is not None and tt is not None:
            TRIG.setdefault(u, set()).add(tt)

print("A  for the GAME 1 and GAME 2 subjects: how many civs list them where?")


def report(bid, uid, label):
    lc = LIST.get((bid, uid), set())
    tb = TREE_OK.get(uid, set())
    have = HAVE_BLD.get(bid, set())
    print("   %-28s unit %-6s" % (label, uid))
    print("      civs that HAVE building %s      : %d" % (bid, len(have)))
    print("      of those, panel Units lists it  : %d" % len(lc & have))
    print("      tree says NOT NotAvailable      : %d" % len(tb & have))
    print("      panel-listed but tree refuses   : %d" % len((lc & have) - tb))
    print("      tree allows but panel silent    : %d" % len((tb & have) - lc))
    print("      upgrade tech                   : %s"
          % sorted(TRIG.get(uid, ())))


report(12, 77, "Long Swordsman (GAME 1)")
report(12, 74, "Militia (base, no upgrade)")
report(49, 588, "Siege Onager (GAME 2)")
report(49, 550, "Onager (base for 588)")
report(45, 532, "Fast Fire Ship")
report(87, 474, "Heavy Cavalry Archer")

print()
print("B  across EVERY (building, unit) the panel names: is presence per-civ or near-constant?")
frac = []
for (bid, uid), civs_listing in sorted(LIST.items()):
    have = HAVE_BLD.get(bid, set())
    if len(have) < 10:
        continue
    frac.append((len(civs_listing & have) / float(len(have)), bid, uid,
                 len(civs_listing & have), len(have)))
buckets = Counter()
for f, _b, _u, _n, _h in frac:
    if f >= 0.99:
        buckets["all civs (100%)"] += 1
    elif f >= 0.9:
        buckets["90-99%"] += 1
    elif f >= 0.5:
        buckets["50-90%"] += 1
    else:
        buckets["<50%"] += 1
print("   pairs examined: %d" % len(frac))
for k in ("all civs (100%)", "90-99%", "50-90%", "<50%"):
    print("      %-18s %d" % (k, buckets[k]))

print()
print("C  the pairs that are NOT universal (the only ones that could be per-civ claims)")
odd = [x for x in frac if x[0] < 0.9]
print("   count: %d" % len(odd))
for f, bid, uid, n, h in sorted(odd)[:25]:
    tb = TREE_OK.get(uid, set())
    print("      bldg %-5s unit %-6s listed in %3d/%-3d civs (%.0f%%)  tree-ok in %d"
          % (bid, uid, n, h, f * 100, len(tb & HAVE_BLD.get(bid, set()))))
