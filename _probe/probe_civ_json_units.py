# -*- coding: utf-8 -*-
r"""THE CONTRADICTION, and the hypothesis it forces.

Measured facts after the user's in-game result (villager 1000 = control PASSED,
Champi Scout absent = test FAILED):

    INCAS    tree row for 2550: PRESENT (ResearchedCompleted, Age 1, Bldg 12)
             panel Units: 2550 PRESENT ; panel Techs: 1350 ABSENT
             -> the Incas CAN build it in game, with exactly this data shape

    BRITONS  after the smoke6 write: tree row PRESENT, panel Units PRESENT,
             panel Techs 1350 ABSENT
             -> IDENTICAL in shape to the Incas, yet ABSENT in game

If the menu were fed by the tree OR the panel, the Britons would have it.  So the
menu is fed by **neither** -- or by something else that differs between the two.

The obvious candidate this project has NOT yet examined as a grant mechanism is
`resources/_common/dat/civilizations.json`, which carries per-civ unit fields:

    unique_unit_id, elite_unique_unit_id, unique_unit_line,
    unique_unit_upgrade_id, unique_unit_string_ids, unique_unit_image_paths

A "regional unit" like the Champi Scout is exactly the sort of thing such a line
would name.  Check it, and check the .dat's own per-civ unit-line data, which earlier
rounds noted the parser SKIPS (`DatFile.cpp:214` omits UnitLines for this version).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550

print("A  civilizations.json: which civs name 2550 in any unique-unit field?")
p = os.path.join(GAME, "resources", "_common", "dat", "civilizations.json")
obj = json.loads(open(p, "rb").read().decode("utf-8-sig"))
lst = obj["civilization_list"]
FIELDS = ("unique_unit_id", "elite_unique_unit_id", "unique_unit_line",
          "unique_unit_upgrade_id", "unique_unit_string_ids")
for c in lst:
    vals = {}
    for f in FIELDS:
        v = c.get(f)
        if v is None:
            continue
        vals[f] = v
    hit = False
    for f in FIELDS:
        v = c.get(f)
        if v is None:
            continue
        s = json.dumps(v) if not isinstance(v, (str, int)) else str(v)
        if str(UNIT) in s:
            hit = True
    if hit:
        print("   %-14s %s" % (c.get("internal_name") or c.get("tech_tree_name"),
                               vals))

print()
print("B  the four civs that CAN build 2550, and the target")
TARGETS = ("Incas", "Mapuche", "Muisca", "Tupi", "Britons", "Aztecs", "Mayans")
for c in lst:
    nm = c.get("internal_name") or c.get("tech_tree_name")
    if nm not in TARGETS:
        continue
    print("   %-12s unique_unit_id=%-6s elite=%-6s line=%-28s upgrade=%-6s"
          % (nm, c.get("unique_unit_id"), c.get("elite_unique_unit_id"),
             json.dumps(c.get("unique_unit_line")), c.get("unique_unit_upgrade_id")))

print()
print("C  and the .dat's own UnitLines (the parser skips them on this version)")
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
print("   earlier rounds measured: `UnitLines` is deliberately omitted for GV_C32")
print("   (`DatFile.cpp:214` guards it with `gv >= GV_SWGB`, 55 > 54) -- so this")
print("   file CANNOT be the per-civ regional-unit table.")

print()
print("D  compare the two civilizations' arrays for any OTHER difference in the")
print("   2550 record")
_data, civs, _cs, _gv, _tail, _how = tk._parsed
for want in ("Incas", "British"):
    c = next((x for x in civs if x.get("name") == want), None)
    rec = next((u for u in (c.get("units") or []) if u.get("id") == UNIT), None)
    print("   -- %s --" % want)
    if not rec:
        print("      no record")
        continue
    for k in sorted(rec):
        if k.startswith("_off"):
            continue
        v = rec[k]
        if isinstance(v, list) and len(v) > 3:
            print("      %-20s list[%d] %s" % (k, len(v), v[:3]))
        else:
            print("      %-20s %r" % (k, v))
