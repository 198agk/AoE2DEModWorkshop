# -*- coding: utf-8 -*-
r"""The .dat already carries BUTTON SLOTS.  Does the panel participate at all?

A command-panel button grid needs, per button: which slot, what icon, what tooltip.
The `.dat`'s unit records carry `train_locations`, and each entry is
`{train_time, unit_id, button_id}` -- where `unit_id` is the training BUILDING and
`button_id` is the SLOT in that building's grid.

If the `.dat` supplies the slots, then the grid can be filled from the `.dat` alone,
and the panel file (`futuravailableunits.json`) would be doing something else.

Test: for a civilization, take the units its TREE permits at a building, sort them
by the `.dat`'s own `button_id`, and see whether that ordering is a sane grid.  Then
do the same for the units the TREE forbids but the PANEL lists (the kind-P
subjects) -- if those also carry button slots in the `.dat`, the `.dat` alone would
draw them, and the tree/panel would be narrowing, not supplying.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
civs_dat = tk._parsed[1]

# button_id per (unit, training building), from a playable civ
SLOTS = {}
for civ in civs_dat[1:3]:
    for u in civ.get("units") or []:
        uid = u.get("id")
        if uid is None:
            continue
        for t in (u.get("train_locations") or []):
            b = t.get("unit_id")
            if b is None or b < 0:
                continue
            SLOTS.setdefault((uid, b), set()).add(t.get("button_id"))

print("A  does the .dat carry a button slot for our subjects?")
CASES = [("JURCHENS", "Jurchens", 77, 12), ("JURCHENS", "Jurchens", 473, 12),
         ("JURCHENS", "Jurchens", 567, 12), ("MUISCA", "Muisca", 359, 12),
         ("HUNS", "Huns", 532, 45), ("SICILIANS", "Sicilians", 588, 49),
         ("SPARTANS", "Spartans", 13, 45), ("BRITONS", "Britons", 5, 87),
         ("BRITONS", "Britons", 77, 12)]
for stem, disp, uid, bld in CASES:
    s = SLOTS.get((uid, bld))
    print("   %-11s unit %-6s at building %-5s button_id=%s"
          % (stem, uid, bld, sorted(s) if s else "NO SLOT RECORDED"))

print()
print("B  the full grid the .dat would draw for one building (BRITONS barracks 12)")
tree = trees["BRITONS"]
trows = {r.get("Node ID"): r for r in CT.unit_rows(tree)
         if r.get("Node ID") is not None}
obj = panels[BP.panel_path_for(GAME, "Britons")[1]]["obj"]
panel_ids = {}
for blk in BP.buildings(obj, "Britons"):
    for e in (blk.get(BP.UNITS_KEY) or []):
        panel_ids[e.get("ID")] = blk.get("ID")

rows = []
for u in civs_dat[1].get("units") or []:
    uid = u.get("id")
    for t in (u.get("train_locations") or []):
        if t.get("unit_id") != 12:
            continue
        st = CT.node_status(tree, uid, CT.UNIT_USE_TYPES)
        en = (idx.get("unit", uid) or None)
        rows.append((t.get("button_id"), uid, en.zh if en else None,
                     st, panel_ids.get(uid)))
rows.sort(key=lambda r: (r[0] is None, r[0]))
print("   %-9s %-6s %-22s %-18s %s"
      % ("button", "unit", "name", "tree status", "panel lists at"))
for b, uid, nm, st, pb in rows:
    print("   %-9s %-6s %-22s %-18s %s" % (b, uid, nm, st, pb))

print()
print("C  does the .dat's train_locations entry order match the button grid order?")
print("   (the grid is drawn in button_id order; if the .dat orders it, the panel")
print("    is not needed to order it)")

print()
print("D  do the kind-P subjects sit in the .dat with a slot at the TREE's building?")
for stem, disp, uid, bld in CASES:
    s = SLOTS.get((uid, bld))
    if not s:
        continue
    print("   %-11s unit %-6s building %-5s -> the .dat WOULD draw a button here"
          % (stem, uid, bld))
