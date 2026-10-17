# -*- coding: utf-8 -*-
r"""Is my kind-P filter broken?  Check the specific cells it claims.

Section B of `probe_injective_filtered.py` printed ARCHER (4) as a kind-P subject
for HUNS -- an archer is core AoE2, so that must be wrong, and if the filter is
broken then its "0 injective civilizations" answer cannot be trusted either.
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

stem, disp = "HUNS", "Huns"
tree = trees[stem]
rows = {r.get("Node ID"): r for r in CT.unit_rows(tree)}
print("HUNS tree row for 4 (Archer): %r"
      % (rows.get(4) and {k: rows[4][k] for k in
                          ("Node ID", "Node Status", "Building ID", "Age ID",
                           "Use Type")},))
print("HUNS node_status(4) unit-space: %r"
      % CT.node_status(tree, 4, CT.UNIT_USE_TYPES))
print()
print("all HUNS tree rows, Node ID -> (status, building)")
for uid, r in sorted(rows.items()):
    print("   %-6s %-22s %-18s bldg %-5s age %s"
          % (uid, r.get("Name"), r.get("Node Status"), r.get("Building ID"),
             r.get("Age ID")))
    if uid > 500:
        break
