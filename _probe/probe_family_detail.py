# -*- coding: utf-8 -*-
"""Why did the villager turn back into a human when chopping?

The in-game report was: a freshly trained male villager is a sheep, but every
work task (chop, mine, build) and attacking turns it back into a human.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import aoe2mod.api as A
import aoe2mod.game.sprites as SP

tk = A.open_toolkit()
tk._ensure()
civs = tk._parsed[1]
idx = SP.art_index(tk.game_root, tk._stats["graphics"])
fam = tk._families()

tables = {}
for ci, c in enumerate(civs):
    tables[ci] = {u.get("id"): u for u in c.get("units") or ()}

print("=== the villager family, member by member ===")
print("%-6s %-22s %-28s %s" % ("unit", "stem", "animations", "display name"))
ids = sorted(fam.get(83) or [])
for mid in ids:
    rec = tables[0].get(mid) or tables[1].get(mid)
    if rec is None:
        print("%-6d %-22s %-28s %s" % (mid, "?", "?", "NO RECORD"))
        continue
    a = idx.art(rec)
    name = rec.get("_dll_name")
    disp = tk.describe(mid).get("display") if mid < 2700 else "?"
    if a.get("kind") != "loose":
        print("%-6d %-22s %-28s %s" % (mid, "-", a.get("kind"), disp))
        continue
    print("%-6d %-22s %-28s %s"
          % (mid, a["stem"], ",".join(sorted(a["tokens"])), disp))

print()
print("=== what a unit's name field says for the two records the user saw ===")
for mid in (83, 118, 120, 122, 123, 124):
    rec = tables[0].get(mid)
    if not rec:
        continue
    a = idx.art(rec)
    print("  unit %-4d stem=%-22s name=%r file=%r"
          % (mid, a.get("stem"), a.get("name"), a.get("file")))
