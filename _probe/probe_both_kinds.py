# -*- coding: utf-8 -*-
"""Find a civilization where BOTH directions of the disagreement already exist.

The mod-based test is fragile (two mods ship the same three paths; the control
cannot attribute; subject B was masked).  The shipped files already disagree in
both directions -- if one civilization has BOTH kinds at once, a single game
answers the question with NO MOD AT ALL.

  kind P: panel lists it, tree says NotAvailable -> a visible button proves the
          PANEL is consulted (the tree cannot supply it)
  kind T: tree grants it, panel does not list it -> a MISSING button proves the
          PANEL drives (the tree WOULD supply it), and a visible one proves the
          TREE drives
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

NODES = sorted({r.get("Node ID") for t in trees.values()
                for r in CT.unit_rows(t) if r.get("Node ID") is not None})
INFO = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        nid = r.get("Node ID")
        if nid is not None:
            INFO.setdefault(nid, (r.get("Building ID"), r.get("Age ID"),
                                  r.get("Name")))

P = defaultdict(list)      # civ -> [(unit, age, bldg)]
T = defaultdict(list)
seen = set()
for pkey, rec in sorted(panels.items()):
    obj = rec["obj"]
    for disp in sorted(k for k in obj if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            continue
        seen.add((rec["path"], disp))
        stem = CT.civ_file_stem(disp)
        tree = trees.get(stem)
        if tree is None:
            continue
        blds = {r.get("Node ID") for r in CT.rows_of(tree)
                if r.get("Use Type") == "Building"}
        for nid in NODES:
            st = CT.node_status(tree, nid, CT.UNIT_USE_TYPES)
            bb, ee = BP.find_entry(obj, disp, nid, BP.UNITS_KEY)
            bl, age, nm = INFO.get(nid, (None, None, None))
            if st == "NotAvailable" and ee is not None:
                P[stem].append((nid, nm, ee.get("RequiredAge"), bb))
            elif st == "ResearchedCompleted" and ee is None and bb is None:
                if bl in blds:
                    T[stem].append((nid, nm, age, bl))

print("civs with BOTH kinds of shipped disagreement (the ideal no-mod test):")
both = sorted(set(P) & set(T))
for c in both:
    print("  %s" % c)
    for nid, nm, age, bb in P[c]:
        print("     P panel-only : %-6s %-22s Age %-3s bldg %s"
              % (nid, nm, age, bb))
    for nid, nm, age, bl in T[c]:
        print("     T tree-only  : %-6s %-22s Age %-3s bldg %s"
              % (nid, nm, age, bl))
print("  -> %d civs: %s" % (len(both), both))

print()
print("civs with a DARK-AGE (Age 1) disagreement of either kind:")
for c in sorted(set(P) | set(T)):
    rows = [("P",) + r for r in P[c] if r[2] == 1] + \
           [("T",) + r for r in T[c] if r[2] == 1]
    if rows:
        print("  %-12s %s" % (c, rows))

print()
print("all civs with a kind-P pair (panel lists, tree says NotAvailable):")
for c in sorted(P):
    print("   %-12s %s" % (c, [(n, nm, a, b) for n, nm, a, b in P[c]]))
print()
print("all civs with a kind-T pair (tree grants, panel silent):")
for c in sorted(T):
    print("   %-12s %s" % (c, [(n, nm, a, b) for n, nm, a, b in T[c]]))
