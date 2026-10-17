# -*- coding: utf-8 -*-
"""Before changing reskin.plan, measure what family expansion would do.

The in-game result (2026-10-17) showed a villager that is a sheep while idle and
while attacking, but a human while building/chopping/mining -- because the engine
re-points a villager to a task-specific RECORD, and each record carries its own
art stem.  Replacing only unit 83's stem covers 1 of 18 villager pictures.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import aoe2mod.api as A
from aoe2mod.dat import families as F
from aoe2mod.game import sprites as S
from aoe2mod.intent import reskin as RK

tk = A.open_toolkit()
tk._ensure()
ix = tk._reskin_art()
civs = tk._parsed[1]
F.warm(tk._stats, game_root=tk.game_root)
fams = F.build_families(civs)

recs = {}
for civ in civs:
    for u in civ["units"]:
        recs.setdefault(u["id"], u)


def art_of(uid):
    u = recs.get(uid)
    return ix.art(u) if u else None


def family_art(uid):
    """(distinct stems, ids with art) over the whole family of ``uid``."""
    ids = fams.get(uid) or [uid]
    stems = {}
    for i in ids:
        a = art_of(i)
        if a and a.get("kind") == "loose":
            stems.setdefault(a["stem"], []).append(i)
    return ids, stems


print("=== what a family expansion would add, per candidate pair ===")
pairs = [(4, 8), (83, 594), (74, 4), (12, 498), (93, 74), (2550, 4), (594, 4),
         (13, 21), (70, 84), (101, 12)]
for t, d in pairs:
    tids, tstems = family_art(t)
    dids, dstems = family_art(d)
    base = RK.plan(tk.game_root, tk._stats["graphics"], civs, t, d, scope="all")
    print("  unit %-5d <- %-5d  target family %2d ids / %2d stems | donor family %2d / %2d"
          % (t, d, len(tids), len(tstems), len(dids), len(dstems)))
    print("        single-record plan : ok=%-5r files=%d"
          % (base.get("ok"), len(base.get("files") or {})))
    if len(tstems) > 1:
        print("        would ALSO need   : %s"
              % ", ".join(sorted(tstems)[:8]))
    print()

print("=== villager family in full ===")
tids, tstems = family_art(83)
print("  ids  : %r" % (sorted(tids),))
for s in sorted(tstems):
    print("  stem %-24s ids=%r" % (s, tstems[s]))

print()
print("=== how many families would grow a reskin's file count ===")
grown = 0
total = 0
for uid in sorted(fams):
    ids, stems = family_art(uid)
    if not stems:
        continue
    total += 1
    if len(stems) > 1:
        grown += 1
print("  unit ids with loose art: %d ; of those, family spans >1 stem: %d"
      % (total, grown))
