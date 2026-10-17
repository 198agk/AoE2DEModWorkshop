# -*- coding: utf-8 -*-
r"""PRE-CHECK for smoke6: can the ENGINE create unit 2550 for the Britons at all?

Granting a tree row is a statement about availability.  It is NOT the same as the
unit being constructible: the engine also needs the unit to exist in that
civilization's `.dat` unit array (its per-civ record).  If 2550 is missing from the
Briton array, then "the Champi Scout did not appear" would be explained by the
`.dat` and would say nothing about the tree -- a fifth gate class, and one that
would waste the user's test.

Check it directly:
  A  is unit 2550 present in EVERY civilization's unit array (including BRITONS)?
  B  what index does it sit at, and does that vary per civilization?
  C  what does its per-civ record look like for BRITONS vs INCAS (the donor civ)?
  D  is its training building (12, Barracks) reachable for BRITONS?
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.dat import locate as L                        # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)                    # force the lazy parse
data, civs, civs_start, gv, tail, how = tk._parsed

print("A  unit %d membership across all %d civilizations" % (UNIT, len(civs)))
present, absent = [], []
idx_by_civ = {}
for c in civs:
    ids = [u.get("id") for u in (c.get("units") or [])]
    if UNIT in ids:
        present.append(c.get("name"))
        idx_by_civ[c.get("name")] = ids.index(UNIT)
    else:
        absent.append(c.get("name"))
print("     present in: %d civs" % len(present))
print("     absent from: %d civs %s" % (len(absent), absent[:12]))
print("     BRITONS present: %s" % ("British" in present))

print()
print("B  the array index of unit %d, per civilization" % UNIT)
from collections import Counter                                 # noqa: E402
cnt = Counter(idx_by_civ.values())
print("     index distribution: %s" % dict(cnt))
print("     British index: %s" % idx_by_civ.get("British"))
print("     Incas index  : %s" % idx_by_civ.get("Incas"))

print()
print("C  the per-civ record, BRITONS vs INCAS")
for want in ("British", "Incas"):
    c = next((x for x in civs if x.get("name") == want), None)
    if not c:
        continue
    rec = next((u for u in (c.get("units") or []) if u.get("id") == UNIT), None)
    if not rec:
        print("     %-9s NO RECORD" % want)
        continue
    keep = {k: rec.get(k) for k in
            ("id", "type", "hit_points", "class", "name",
             "train_locations", "enabled", "disabled", "icon_id")}
    print("     %-9s %s" % (want, keep))

print()
print("D  is the Barracks (12) reachable for BRITONS according to the tree?")
trees = CT.load_trees(GAME)
b = CT.row_for(trees["BRITONS"], 12, CT.UNIT_USE_TYPES)
for r in CT.rows_of(trees["BRITONS"]):
    if r.get("Use Type") == "Building" and r.get("Node ID") == 12:
        b = r
print("     BRITONS building 12 row: %s"
      % ({k: b.get(k) for k in ("Node ID", "Name", "Node Status", "Age ID")}
         if b else None))
print("     the Champi Scout's tree row in INCAS names Building ID: %s"
      % (CT.row_for(trees["INCAS"], UNIT, CT.UNIT_USE_TYPES) or {}).get(
          "Building ID"))

print()
print("E  verdict input")
print("     unit %d in every civ's array: %s" % (UNIT, not absent))
print("     -> the engine has a record to instantiate for the Britons")
