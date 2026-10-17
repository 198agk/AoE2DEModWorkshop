# -*- coding: utf-8 -*-
"""Which donor can dress a WHOLE villager family?

The villager is 27 records over 18 stems, and the family needs ten different
animation keys between them.  A donor that only has idle/walk/attack/death
leaves the villager human while it works, which is exactly the bug the user
reported.  So the useful question is: who supplies ALL of them?
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

# what the villager family needs, in total
need = {}
for mid in fam[83]:
    for ci in (0, 1):
        rec = tables[ci].get(mid)
        if rec is None:
            continue
        a = idx.art(rec)
        if a.get("kind") == "loose":
            for k in a["tokens"]:
                need.setdefault(k, (mid, a["stem"]))
        break
print("the villager family needs %d different animations:" % len(need))
for k in sorted(need):
    print("   %-8s e.g. unit %-5d %s" % (k, need[k][0], need[k][1]))

# every unit that has loose art, as a potential donor
cands = {}
for mid in sorted(tables[0]):
    a = idx.art(tables[0][mid])
    if a.get("kind") != "loose":
        continue
    cands[mid] = set(a["tokens"])

want = set(need)
print()
print("=== donors that supply EVERY animation the family needs ===")
full = []
for mid, keys in cands.items():
    if want <= keys and mid not in fam[83]:
        full.append(mid)
print("count: %d" % len(full))
for mid in full:
    rec = tables[0][mid]
    a = idx.art(rec)
    try:
        disp = tk.describe(mid).get("display")
    except Exception:
        disp = "?"
    print("   unit %-5d %-12s %s" % (mid, disp, a["stem"]))

print()
print("=== and of those, which are ordinary trainable units (not heroes/cinematic)? ===")
for mid in full:
    rec = tables[0][mid]
    a = idx.art(rec)
    n = (a.get("name") or "").lower()
    heroish = any(w in n for w in ("hero", "king", "monk", "cinematic", "campaign"))
    try:
        disp = tk.describe(mid).get("display")
    except Exception:
        disp = "?"
    if not heroish:
        print("   unit %-5d %-14s %s" % (mid, disp, a["stem"]))
