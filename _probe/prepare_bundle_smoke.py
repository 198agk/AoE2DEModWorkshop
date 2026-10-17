# -*- coding: utf-8 -*-
"""Bundle smoke test: a .dat edit AND an availability edit in ONE mod.

WHY THIS REPLACES THE LAST TEST
-------------------------------
The previous mod carried only dat-layer JSON (the tree file and/or the panel
file) and the game refused to start: "无法打开文件: .gpv".  The user's diagnosis
-- a mod that overrides the DAT storage point must also ship
`empires2_x2_p1.dat` -- fits every observation in hand, including the ones not
made by this tool:

  * `aoe2mod Smoke HP+Units`  : .dat + CivTechTrees/BRITONS.json   -> started
  * `297820` (third-party)    : .dat + civilizations.json          -> works
  * `aoe2mod Smoke2 BuildPanel`: futuravailableunits.json only     -> no start
  * `aoe2mod Panel Smoke`     : futuravailableunits.json + tree    -> no start

Note the third-party row: a JSON override at the dat ROOT is fine as long as a
.dat travels with it.  So the variable is the MISSING .dat, not the JSON.

This mod therefore ships all three, as a two-intent bundle:
  1. unit.stat          villager 83 hit_points -> 1000   (the known-good .dat edit)
  2. unit.availability  unit 5 Hand Cannoneer  -> British, grant

Three questions one game answers:
  Q1 does the game start at all?
  Q2 is the villager 1000 hp (so the .dat half is live)?
  Q3 does the Britons Archery Range offer the Hand Cannoneer (so availability is)?
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import sys

sys.path.insert(0, _HERE_PATH(".."))
import aoe2mod.api as A                                     # noqa: E402
from aoe2mod.game import locations as L                     # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_bundle_smoke")
NAME = "aoe2mod Bundle VillagerHP plus Britons HandCannon"
TITLE = "aoe2mod Bundle - Villager HP + Britons Hand Cannoneer"

INTENTS = [
    {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "value": 1000},
    {"intent": "unit.availability", "unit": 5, "civ": "British", "action": "grant"},
]

tk = A.open_toolkit()
print("game   : %s" % tk.game_root)
print("profile: %s" % L.find_profile_root())
print()

plans = tk.plan_bundle(INTENTS)
print("=== plan_bundle (type %s) ===" % type(plans).__name__)
_p = plans if isinstance(plans, dict) else {"plans": plans}
for i, p in enumerate(_p.get("plans") or [], 1):
    if isinstance(p, dict):
        print("  %d. %-42s editable=%s  writes=%s"
              % (i, (p.get("description") or "?")[:42],
                 p.get("editable"), p.get("writes")))
    else:
        print("  %d. %s" % (i, p))
print("  edit_count      : %s" % _p.get("edit_count"))
print("  overlap_count   : %s" % _p.get("overlap_count"))
print("  availability    : %s" % (_p.get("availability") or []))
print()

rep = tk.build_bundle(INTENTS, OUT, title=TITLE, author="aoe2mod",
                      description="villager hp + Britons hand cannoneer",
                      overwrite=True)

print("=== emitted mod: %s ===" % OUT)
total = 0
for root, _dirs, files in os.walk(OUT):
    for fn in sorted(files):
        p = os.path.join(root, fn)
        sz = os.path.getsize(p)
        total += sz
        print("   %-58s %10d B" % (os.path.relpath(p, OUT), sz))
print("   total %.1f MB" % (total / 1048576.0))
print()

print("verification ok : %s" % rep["verification"]["ok"])
print("mod_contains_dat: %s" % rep.get("mod_contains_dat"))
print("dat_file_bytes  : %s" % rep.get("dat_file_bytes"))
print("reparse_ok      : %s" % rep.get("reparse_ok"))
for c in (rep.get("availability") or {}).get("civs", []):
    print("availability    : %s %s %s -> panel %s"
          % (c["civ"], c["action"], c["node_name"],
             (c.get("panel") or {}).get("mode")))
print()

for old in tk.mods():
    if old["name"].startswith("aoe2mod"):
        try:
            tk.uninstall(old["name"], kind=old.get("kind") or "local")
            print("removed old mod: %s" % old["name"])
        except Exception as exc:                            # noqa: BLE001
            print("could not remove %s: %s" % (old["name"], exc))

tk.install(OUT, name=NAME, title=TITLE, kind="local", enabled=True,
           position=0, overwrite=True)

print()
print("=== mod-status, read back from DISK ===")
for i, m in enumerate(tk.mods(), 1):
    mark = "ON " if m["enabled"] else "off"
    print("  %2d %s p%-2s %-52s exists=%s"
          % (i, mark, m["priority"], m["name"][:52], m["exists"]))
