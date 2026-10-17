# -*- coding: utf-8 -*-
r"""Verify the zero-mod experiment's linchpin: JURCHENS at the Barracks.

The shipped files disagree with no mod installed:

  panel lists Long Swordsman (77) / Two-Handed (473) / Champion (567) for
  Jurchens at building 12, while the tree says `NotAvailable`.

If the user opens a Jurchens game and those buttons ARE there, the PANEL is
consulted -- the tree cannot supply them.  If they are NOT there, the tree (or
something else) is what the menu follows.

Before asking anyone to spend a game on it, confirm the disagreement is real and
not an artifact of reading the wrong row / the wrong use-type space.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

for civ in ("JURCHENS", "BRITONS"):
    tree = trees[civ]
    print("=" * 74)
    print("%s  -- every barracks (12) row in the tree" % civ)
    print("=" * 74)
    for r in sorted(CT.unit_rows(tree), key=lambda r: (r.get("Node ID") or 0)):
        if r.get("Building ID") != 12:
            continue
        print("  node %-6s %-22s Node Status=%-18s Age=%s"
              % (r.get("Node ID"), r.get("Name"), r.get("Node Status"),
                 r.get("Age ID")))
    print()
    print("  -- the panel's barracks (12) entries")
    pk = BP.panel_path_for(GAME, civ.title() if civ != "JURCHENS" else "Jurchens")
    obj = panels[pk[1]]["obj"]
    for e in (BP.entries(obj, pk[1], 12, BP.UNITS_KEY) or []):
        print("     %r" % (e,))
    print()
    print("  -- node_status for the three Contested ids, in BOTH use-type spaces")
    for nid in (77, 473, 567, 74, 93):
        u = CT.node_status(tree, nid, CT.UNIT_USE_TYPES)
        t = CT.node_status(tree, nid, CT.TECH_USE_TYPES)
        row = CT.row_for(tree, nid, CT.UNIT_USE_TYPES)
        print("     %-5s unit-space=%-18s tech-space=%-18s Use Type=%r Node Type=%r"
              % (nid, u, t, (row or {}).get("Use Type"),
                 (row or {}).get("Node Type")))
    print()

# cross-check: is Jurchens' NotAvailable for 77 unique, or do many civs share it?
print("=" * 74)
print("who else calls node 77 NotAvailable?")
na = []
for stem, tree in sorted(trees.items()):
    if CT.node_status(tree, 77, CT.UNIT_USE_TYPES) == "NotAvailable":
        na.append(stem)
print("  %d civs: %s" % (len(na), na))
print()
print("and do those civs' PANELS list it?")
for stem in na:
    disp = None
    for cand in sorted(panels):
        if CT.civ_file_stem(cand) == stem:
            disp = cand
            break
    if disp is None:
        continue
    obj = panels[disp]["obj"]
    bb, ee = BP.find_entry(obj, disp, 77, BP.UNITS_KEY)
    print("  %-14s panel entry: %r" % (stem, ee))
