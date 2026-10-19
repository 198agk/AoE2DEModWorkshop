# -*- coding: utf-8 -*-
r"""Was v15's British half doomed by the button slot before the tree even mattered?

WHY
---
v15 shipped only two `CivTechTrees` files (plus an unedited `.dat` carrier).
The user's result: the Incas still have the Champi Scout, the Britons still do
not.  I first read that as "the game ignores tree files inside a mod".

That reading skipped something the user himself established on 2026-10-16
(m25679) and which v5 measured in game: a unit whose `train_location.button_id`
points at a slot the civilization has ALREADY filled is masked.  v5 made the
Champi Scout appear for the Britons by moving that byte 1 -> 4 -- one byte in
the `.dat`.  v15 does not touch that byte, so if button 1 is still occupied for
the Britons then the "no button" result was predicted by the slot mechanism and
says NOTHING about whether the tree file was read.

So: count the available units per button slot for these two civs, straight from
the shipped `.dat` train_locations plus the SHIPPED tree (not our edited one).
"""
import contextlib
import io
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.game import locations as G                    # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550
BARRACKS = 12
GRANT = ("ResearchedCompleted", "ResearchRequired")

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)              # forces the lazy parse; _parsed stays None until then
trees = CT.load_trees(GAME)
civs = tk._parsed[1]

print("A  the shipped .dat button slots for unit %d" % UNIT)
for name in ("Britons", "Incas"):
    stem = CT.civ_file_stem(name)
    civ = next(c for c in civs if c["name"] == name)
    tl = civ["units"].get(UNIT)
    print("   %-8s train_location for %d : %s" % (name, UNIT, tl))
    if tl is None:
        print("   %-8s -> ABSENT, cannot be trained at all" % name)
        continue
    slot = tl.get("button_id")
    # who else can this civ build in the same building
    tr = trees.get(stem)
    peers = defaultdict(list)
    for row in CT.unit_rows(tr or {}):
        uid = row.get("Node ID")
        if row.get("Node Status") not in GRANT:
            continue
        pt = civ["units"].get(uid)
        if not pt or pt.get("train_location") != tl.get("location"):
            continue
        peers[pt.get("button_id")].append((uid, row.get("Name")))
    print("   %-8s unit %d sits in slot %s" % (name, UNIT, slot))
    for s in sorted(peers, key=lambda x: (x is None, x)):
        mark = "  <-- 2550 hides here" if s == slot else ""
        print("      slot %-4s : %2d available  %s%s"
              % (s, len(peers[s]),
                 ", ".join("%d %s" % (u, n) for u, n in peers[s][:6]),
                 mark))

print()
print("B  the same two civs, if 2550 were moved to the slot v5 used")
for name in ("Britons", "Incas"):
    stem = CT.civ_file_stem(name)
    civ = next(c for c in civs if c["name"] == name)
    tl = civ["units"].get(UNIT) or {}
    tr = trees.get(stem) or {}
    used = set()
    for row in CT.unit_rows(tr):
        if row.get("Node Status") not in GRANT:
            continue
        pt = civ["units"].get(row.get("Node ID"))
        if pt and pt.get("train_location") == tl.get("location"):
            used.add(pt.get("button_id"))
    free = [s for s in (1, 2, 3, 4, 5) if s not in used]
    print("   %-8s slots occupied in the barracks: %s ; free: %s"
          % (name, sorted(s for s in used if s is not None), free))

print()
print("VERDICT")
b = next(c for c in civs if c["name"] == "Britons")["units"].get(UNIT) or {}
i = next(c for c in civs if c["name"] == "Incas")["units"].get(UNIT) or {}
print("   Britons 2550 button_id = %s" % b.get("button_id"))
print("   Incas   2550 button_id = %s" % i.get("button_id"))
print()
print("   v15 changed NEITHER byte.  If the Britons' slot is already full,")
print("   the missing button was predictable from the slot mechanism alone and")
print("   v15's British half cannot distinguish 'tree ignored' from 'tree read")
print("   but masked'.  The Incas half has the mirror problem: deleting the tree")
print("   row does not remove a train_location from the .dat.")
