# -*- coding: utf-8 -*-
"""Prepare the clean single-variable test of the availability path.

AFTER ROUND 40 the product writes BOTH layers for one intent:
  * resources/_common/dat/CivTechTrees/BRITONS.json   (the model)
  * resources/_common/dat/futuravailableunits.json    (the baked panel the menu reads)

The 2026-10-14 test shipped only the first, so if the menu reads the panel that
test could not have moved the menu.  This mod ships both, which is the only way
to learn which one the game consults -- and if only one half works, that half is
the answer.

Single variable: Britons gain the Hand Cannoneer (unit 5).  Measured facts:
  * 24 civs can build it, 38 are told NotAvailable -- the game enforces it;
  * the .dat provably cannot carry that distinction (six-layered refutation);
  * the shipped panel file does NOT list it under Britons' Archery Range (87);
  * the shipped tree row for Britons says NotAvailable.
So "does it appear" has exactly one cause per layer, and both are observable in
the Archery Range build menu.
"""
import os
import sys

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
import aoe2mod.api as A                                     # noqa: E402
from aoe2mod.game import locations as L                     # noqa: E402
from aoe2mod.game import civtechtrees as CT                 # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_panel_smoke")
NAME = "aoe2mod Panel Smoke Britons HandCannon"
TITLE = "aoe2mod Panel Smoke - Britons Hand Cannoneer"

tk = A.open_toolkit()
game = tk.game_root
prof = L.find_profile_root()
acct = L.pick_account(prof)
status = L.status_path(acct)

print("game   : %s" % game)
print("profile: %s" % prof)
print("account: %s" % acct)
print("status : %s" % status)
print()

# --- what the two shipped layers say today -------------------------------
trees = tk._trees()
tree_status = CT.node_status(trees[CT.civ_file_stem("British")], 5, CT.UNIT_USE_TYPES)
print("shipped tree  : Britons unit 5 -> %r" % (tree_status,))

from aoe2mod.game import buildpanel as BP                   # noqa: E402
panels = BP.load_all(game)
key = BP.civ_key_for(panels, "British")
rec = panels[key]
before = BP.has_entry(rec["obj"], key, 87, 5, BP.UNITS_KEY)
print("shipped panel : Britons (key %r) Archery Range 87 lists unit 5 -> %s"
      % (key, before))
print("panel file    : %s" % os.path.basename(rec["path"]))
print()

# --- build ---------------------------------------------------------------
intent = {
    "intent": "unit.availability",
    "unit": 5,
    "civ": "British",
    "action": "grant",
}
plan = tk.plan(intent)
print("plan editable : %s" % plan["editable"])
print("plan writes   : %s" % plan["writes"])
print()

rep = tk.build(intent, OUT, title=TITLE, author="aoe2mod",
               description="smoke test: does the build menu follow the panel file?",
               overwrite=True)
print("built         : %s" % OUT)
for root, _dirs, files in os.walk(OUT):
    for fn in sorted(files):
        p = os.path.join(root, fn)
        print("   %-58s %9d B" % (os.path.relpath(p, OUT), os.path.getsize(p)))
print()

pa = rep["panel"]
print("panel mode    : %s" % pa.get("mode"))
print("panel reason  : %s" % pa.get("reason"))
print("panel rel     : %s" % pa.get("rel_path"))
print("panel donor   : %s" % pa.get("donor"))
print("panel entry   : %s" % pa.get("entry"))
print()
print("verification ok: %s" % rep["verification"]["ok"])
for line in rep["verification"]["proven"]:
    print("   proven    : %s" % line)
for line in rep["verification"]["not_proven"]:
    print("   NOT proven: %s" % line)
print()

# --- install, enabled, top priority --------------------------------------
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
print("=== mod-status, read back from DISK (the game rewrites this file) ===")
for i, m in enumerate(tk.mods(), 1):
    mark = "ON " if m["enabled"] else "off"
    print("  %2d %s p%-2s %-52s exists=%s"
          % (i, mark, m["priority"], m["name"][:52], m["exists"]))
