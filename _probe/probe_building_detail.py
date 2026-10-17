# -*- coding: utf-8 -*-
"""Two questions raised by probe_building_intents.py.

Q1  describe() printed `type -1` for a building's empty cost slots.  The tech
    path already filters those; the unit path does not.  Confirm and classify.

Q2  Every building name is ambiguous: House -> 70/191/192/463/464/465.  If the
    tool cannot tell the player's real House from a variant, "make houses
    tougher" is unusable.  Look for a discriminator the .dat itself carries.
"""
import os
import sys
import contextlib
import io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A          # noqa: E402
from aoe2mod.dat import locate as L   # noqa: E402

tk = A.open_toolkit()
tk._ensure()          # the probe reads tk._civs directly, so trigger the parse

print("=== Q1: what do the cost slots of these units actually hold? ===")
for name, uid in (("House", 70), ("Barracks", 12), ("Castle", 82),
                  ("Town Center", 71), ("Archer", 4), ("Villager", 83)):
    hits = L.find_units(tk._civs, uid)
    _, _, u = hits[0]
    print("  %-12s id %-4s slots=%s" % (name, uid, [
        (c["type"], c["amount"], c.get("flag")) for c in (u.get("costs") or [])]))

print()
print("=== Q2: the ambiguous candidates, by type/class ===")
for query in ("House", "Barracks", "Castle", "Town Center"):
    print("  -- %s" % query)
    for h in tk.search(query, kind="unit", limit=25):
        uid = h["id"]
        hits = L.find_units(tk._civs, uid)
        _, _, u = hits[0]
        print("     id %-6s civs %-4s type %-4s class %-5s hp %-6s cost %s"
              % (uid, len(hits), u.get("type"), u.get("class"),
                 u.get("hit_points"),
                 [(c["type"], c["amount"]) for c in (u.get("costs") or [])
                  if c["amount"]]))
