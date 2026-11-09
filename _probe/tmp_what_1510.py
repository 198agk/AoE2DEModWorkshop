# -*- coding: utf-8 -*-
"""What is at 1510, in each of the three spaces the warning mixes up?"""
import io
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))
from aoe2mod import api as A
from aoe2mod.game import civtechtrees as CT
import os

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(GAME)
tk._ensure()

# 1. the .dat unit record at index 1510, in civ 1's unit list
units = tk._civs[1]["units"]
print("civ1 unit count: %d" % len(units))
for i, u in enumerate(units):
    if u.get("id") == 1510:
        print("dat unit 1510: name=%r hp=%r type=%r civ=%r"
              % (u.get("name"), u.get("hit_points"), u.get("type"), u.get("civ")))
        break
else:
    print("dat unit 1510: NO RECORD")

# 2. every tree row whose Node ID is 1510, any civ, any use type
trees = CT.load_trees(GAME)
hits = []
for civ, tree in trees.items():
    for row in CT.rows_of(tree):
        if isinstance(row, dict) and row.get("Node ID") == 1510:
            hits.append((civ, row.get("Use Type"), row.get("Name")))
print("tree rows at node 1510: %d" % len(hits))
for h in hits[:5]:
    print("   %r" % (h,))

# 3. the tech array
print("tech records: %d" % len(tk._tech_records()))

# 4. which names are actually above 1509 in the tree tech space
over = set()
for tree in trees.values():
    for row in CT.tech_rows(tree):
        nid = row.get("Node ID")
        if isinstance(nid, int) and nid > 1509:
            over.add((nid, row.get("Name")))
print("tech node ids above 1509 that SHIP: %d" % len(over))
for o in sorted(over)[:8]:
    print("   %r" % (o,))
