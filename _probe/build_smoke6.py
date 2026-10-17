# -*- coding: utf-8 -*-
r"""smoke6: the first test that can actually answer "does an availability write work?"

## Why every earlier in-game test was inconclusive

    m21855  a mod with NO `.dat`  -> the game would not start at all
    m21927  a mod WITH `.dat`     -> started, villager HP 1000 (the .dat worked),
                                     but the availability subject was
                                     Hand Cannoneer, which is Age 4 (Imperial)
                                     and the game was in the Dark Age

So the availability WRITE has never been tested with a subject that could have been
visible.  The `.dat` carrier is fixed now (`aoe2mod/mod/emitter.py`), which removes
the first failure; this artifact removes the second.

## The design -- one observation settles it

    CONTROL  Villager hit_points = 1000   (PROVEN to appear in game already)
    TEST     BRITONS get the Champi Scout (unit 2550) at the Barracks (12)

The subject was chosen from the six-gate filter (`_probe/test_protocol_subjects.py`)
and then relaxed to the strongest available case:

  * **Age 1** (`RequiredAge: 1`) -- visible in the DARK AGE, so no age gate can
    explain its absence;
  * **Barracks (12)**, which every civilization builds;
  * **no tree row at all** for BRITONS, so the write genuinely adds something;
  * the donor entry exists in four civilizations (Incas/Mapuche/Muisca/Tupi), so
    nothing has to be invented;
  * a distinctive name (蔷琵侦察兵) that cannot be confused with a native unit.

Reading the result:

    villager 1000  AND  Champi Scout present  -> the availability write WORKS
    villager 1000  AND  Champi Scout absent   -> the write does NOT reach the menu
    villager 25    (no Champi Scout)          -> the mod did not load; nothing follows

The third row is why the control is bundled: without it, "absent" would be
ambiguous between "the write failed" and "the mod never ran".
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

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_smoke6")
TITLE = "aoe2mod Smoke6 Champi Scout"
UNIT_ID = 2550
CIV = "Britons"
BUILDING_ID = 12
INTENTS = [
    {"intent": "unit.stat", "unit": "Villager", "stat": "hit_points",
     "value": 1000},
    {"intent": "unit.availability", "unit": UNIT_ID, "civ": CIV,
     "action": "grant"},
]

print("A  the subject is observable from the Dark Age (no age gate)")
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
_inca = CT.row_for(trees["INCAS"], UNIT_ID, CT.UNIT_USE_TYPES)
print("     INCAS row: %s" % {k: _inca.get(k) for k in
                              ("Node ID", "Name", "Node Status", "Age ID",
                               "Building ID")})
assert _inca is not None, "the donor row must exist"
assert _inca.get("Age ID") == 1, "the subject must be Dark-Age visible"
assert CT.row_for(trees["BRITONS"], UNIT_ID, CT.UNIT_USE_TYPES) is None, \
    "BRITONS must not already have a row"
_o = panels[BP.panel_path_for(GAME, CIV)[1]]["obj"]
assert BP.find_entry(_o, BP.civ_key_for(panels, CIV), UNIT_ID,
                     BP.UNITS_KEY)[1] is None, "BRITONS must not already list it"
print("     BRITONS: no tree row, no panel entry -> the write adds something")

print()
print("B  plan")
p = tk_plan = A.open_toolkit(game_root=GAME).plan_bundle(INTENTS)
for d in p["descriptions"]:
    print("     %s" % d)
print("     edit_count=%s  mod_contains_dat=%s  dat_is_carrier=%s  changes_dat=%s"
      % (p["edit_count"], p["mod_contains_dat"], p["dat_is_carrier"],
         p["changes_dat"]))

print()
print("C  build")
tk = A.open_toolkit(game_root=GAME)
man = tk.build_bundle(INTENTS, OUT, title=TITLE, author="aoe2mod",
                      description="villager hp 1000 + Britons get the Champi "
                                  "Scout (Dark-Age observable)",
                      overwrite=True)
print("     files:")
for root, _d, fs in os.walk(OUT):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("        %10d  %s" % (os.path.getsize(fp),
                                    os.path.relpath(fp, OUT)))
print("     mod_contains_dat=%s  dat_is_carrier=%s  changes_dat=%s"
      % (man.get("mod_contains_dat"), man.get("dat_is_carrier"),
         man.get("changes_dat")))

print()
print("D  read the artifact back off DISK, the way the game would")
_new = CT.load_trees(OUT)
_r = CT.row_for(_new["BRITONS"], UNIT_ID, CT.UNIT_USE_TYPES)
print("     BRITONS tree row for %s: %s"
      % (UNIT_ID, "PRESENT" if _r else "MISSING"))
if _r:
    print("        %s" % {k: _r.get(k) for k in
                          ("Node ID", "Name", "Node Status", "Age ID",
                           "Building ID")})
_p2 = BP.load_all(OUT)
_key = BP.civ_key_for(_p2, CIV)
_b, _e = BP.find_entry(_p2[BP.panel_path_for(OUT, CIV)[1]]["obj"], _key,
                       UNIT_ID, BP.UNITS_KEY)
print("     BRITONS panel entry: %s (building %s)" % (_e, _b))
assert _r is not None and _e is not None, "the artifact must contain both halves"

_dat = os.path.join(OUT, "resources", "_common", "dat", "empires2_x2_p1.dat")
assert os.path.exists(_dat), "the carrier .dat must be present"
print("     carrier .dat present: %d B" % os.path.getsize(_dat))

print()
print("SMOKE6 READY: %s" % OUT)
print("  CONTROL  villager hit points = 1000  (if this does not appear, the mod")
print("           did not load and the test below means nothing)")
print("  TEST     Britons Barracks, DARK AGE -> is there a 蔷琵侦察兵")
print("           that can be TRAINED?  (the row exists at Age 1)")
