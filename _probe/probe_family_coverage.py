# -*- coding: utf-8 -*-
"""How much of a task-swapping family can ONE donor actually dress?

The user's report was specific: the villager was a sheep when idle and when
attacking, but a human while chopping, mining and building.  Those moments are
served by different sibling records with their own art, and the family needs ten
distinct animations between them.  So the useful question is not "is there a
donor" but "which donor covers the moments the player will actually see".
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

# Every animation key the villager family can put on screen, with how many
# members use it -- this is how often the player would see a leftover.
need = {}
members_for = {}
for mid in fam[83]:
    rec = tables[0].get(mid)
    if rec is None:
        continue
    a = idx.art(rec)
    if a.get("kind") != "loose":
        continue
    for k in a["tokens"]:
        need[k] = need.get(k, 0) + 1
        members_for.setdefault(k, []).append(mid)

print("the villager family needs %d animation keys" % len(need))
for k in sorted(need, key=lambda x: (-need[x], x)):
    print("   %-8s used by %2d member(s)" % (k, need[k]))

# THE MOMENTS A PLAYER NOTICES.  carry/work/task are what a villager does for
# most of a real game, so a donor missing them is not a cosmetic gap.
WORKING = ["idle", "walk", "attack", "death", "carry", "work"]

print()
print("=== donors, ranked by how many of the family's needs they cover ===")
cands = {}
for mid in sorted(tables[0]):
    a = idx.art(tables[0][mid])
    if a.get("kind") != "loose":
        continue
    cands[mid] = set(a["tokens"])

want = set(need)
rows = []
for mid, keys in cands.items():
    if mid in fam[83]:
        continue                      # a family member cannot dress the family
    cov = want & keys
    rows.append((len(cov), mid, keys))
rows.sort(key=lambda r: (-r[0], r[1]))
print("  best coverage: %d of %d" % (rows[0][0], len(want)))
for n, mid, keys in rows[:12]:
    a = idx.art(tables[0][mid])
    miss = sorted(want - keys)
    print("   %2d/%d  unit %-5d %-30s missing %s"
          % (n, len(want), mid, a["stem"], ",".join(miss)))

print()
print("=== who covers the WORKING set (%s)? ===" % ", ".join(WORKING))
ww = set(WORKING)
ok = [mid for mid, keys in cands.items() if ww <= keys and mid not in fam[83]]
print("count: %d" % len(ok))
for mid in sorted(ok)[:25]:
    a = idx.art(tables[0][mid])
    print("   unit %-5d %s" % (mid, a["stem"]))
print()
print("=== family members themselves that cover the WORKING set ===")
inside = [mid for mid in fam[83] if ww <= (cands.get(mid) or set())]
for mid in sorted(inside):
    a = idx.art(tables[0][mid])
    print("   unit %-5d %s" % (mid, a["stem"]))
