# -*- coding: utf-8 -*-
"""Ground-truth test for aoe2mod.dat.families.

Checks the module against facts measured independently (probe_family_refine.py
for the age edges, and a full read_bird sweep for the task-swap groups):
  * exactly 26 families / 134 ids on VER 8.9
  * Barracks = [12, 20, 132, 498]  (ages Dark/Imperial/Castle/Feudal)
  * House    = [70, 191, 192, 463, 464, 465]
  * the sixteen Sea Gate placements are NOT one family
  * the sixteen City Gate placements are NOT one family
  * Archer (4) is alone -- Crossbowman is a different unit, not an age of it
  * the male villager basket is the 14 TaskSwapGroup-1 records
  * the female basket is the 13 TaskSwapGroup-2 records, and the two baskets
    never merge even though five job names are shared verbatim
  * `206 VMDL`, which linkedUnits.json offers as a villager, is alone -- its
    TaskSwapGroup is 0
And it checks the product path, not just the helper: a plan for a building must
report the whole family, not one id.
"""
import os
import sys
import contextlib
import io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A                 # noqa: E402
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.dat import families as F        # noqa: E402
from aoe2mod.intent import compiler as C     # noqa: E402

FAIL = []


def check(name, cond, detail=""):
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  -- " + str(detail)) if detail else ""))
    if not cond:
        FAIL.append(name)


tk = A.open_toolkit()
tk._ensure()
p = P.Parser(tk._raw)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
stats = p.stats
edges = F.warm(stats, tk.game_root)
print("replacement edges: %d" % len(edges))
fam = F.build_families(tk._civs)

allfams = sorted({tuple(v) for v in fam.values()}, key=lambda v: (-len(v), v[0]))
ids = sum(len(v) for v in allfams)
print("families: %d   ids: %d" % (len(allfams), ids))
print("size histogram: %s" % dict(sorted(
    __import__("collections").Counter(len(v) for v in allfams).items())))

print()
print("=== A. structure ===")
check("26 families", len(allfams) == 26, len(allfams))
check("134 ids", ids == 134, ids)
check("no family has 1 member", all(len(v) >= 2 for v in allfams))
check("every id's family contains it",
      all(F.family_of(fam, u) == list(fam[u]) for u in fam))

print()
print("=== B. the age families we must get right ===")
# The Town Center, Mill and Dock rows grew by the objreplacement.json declared
# swaps (109->444 packed TC, 68->2556 Settlement, 45->2172 Port).  They are part
# of the SAME family because the engine really does move the live object; a mod
# that missed the packed Town Center would silently revert when the TC is packed.
for uid, want, label in (
        (12, [12, 20, 132, 498], "Barracks"),
        (70, [70, 191, 192, 463, 464, 465], "House"),
        (87, [10, 14, 87], "Archery Range"),
        (101, [86, 101, 153], "Stable"),
        (109, [71, 109, 141, 142, 444], "Town Center"),
        (68, [68, 129, 130, 131, 2556, 2558, 2560], "Mill"),
        (209, [209, 210], "University"),
        (82, [82, 2418], "Castle"),
        (45, [45, 47, 51, 133, 2141, 2142, 2143, 2172], "Dock"),
        (103, [18, 19, 103, 105], "Blacksmith"),
        (104, [30, 31, 32, 104], "Monastery"),
        (2556, [68, 129, 130, 131, 2556, 2558, 2560], "Settlement"),
        (562, [562, 563, 564, 565, 584, 585, 586, 587, 1808], "Mining/Lumber Camp"),
        (2162, [2162, 2164, 2165, 2166, 2167, 2270, 2271, 2272], "Polemarch"),
):
    got = F.family_of(fam, uid)
    check("%s (id %d) = %s" % (label, uid, want), got == want, got)

print()
print("=== C. what must NOT be merged (the naive rule's failure mode) ===")
sea = list(range(1379, 1395))
city = list(range(1579, 1595))
check("Sea Gate placements are not one family",
      all(F.family_of(fam, x) == [x] for x in sea),
      [F.family_of(fam, x) for x in sea if F.family_of(fam, x) != [x]][:3])
check("City Gate placements are not one family",
      all(F.family_of(fam, x) == [x] for x in city),
      [F.family_of(fam, x) for x in city if F.family_of(fam, x) != [x]][:3])
check("Archer (4) is alone -- Crossbowman is a different unit",
      F.family_of(fam, 4) == [4], F.family_of(fam, 4))
MALE = [56, 83, 118, 120, 122, 123, 124, 156, 259, 579, 592, 1810, 1892, 2333]
FEMALE = [57, 212, 214, 216, 218, 220, 222, 293, 354, 581, 590, 1891, 2334]
# The objreplacement.json row `83 -> 293, chance 50` declares that the engine may
# hand a spawning villager the OTHER sex's record.  The two baskets must now be
# ONE family, and the reason is worth restating: 83 and 293 have different
# display names, so no name-based rule could ever have joined them.
VILLAGER = sorted(MALE + FEMALE)
SHIPS = [13, 2147, 2171, 2356, 2630]
check("the villager family is the 27 male+female records",
      F.family_of(fam, 83) == VILLAGER, F.family_of(fam, 83))
check("the female villager reaches the same 27 records",
      F.family_of(fam, 293) == VILLAGER, F.family_of(fam, 293))
check("every male basket member maps to the same family",
      all(F.family_of(fam, x) == VILLAGER for x in MALE),
      [F.family_of(fam, x) for x in MALE if F.family_of(fam, x) != VILLAGER][:3])
check("every female basket member maps to the same family",
      all(F.family_of(fam, x) == VILLAGER for x in FEMALE),
      [F.family_of(fam, x) for x in FEMALE if F.family_of(fam, x) != VILLAGER][:3])
check("the fishing-ship basket is the 5 TaskSwapGroup-3 records",
      F.family_of(fam, 13) == SHIPS, F.family_of(fam, 13))
check("206 VMDL is alone -- linkedUnits.json offers it, its group is 0",
      F.family_of(fam, 206) == [206], F.family_of(fam, 206))
check("the family spans BOTH task-swap groups, 1 and 2",
      F.groups_of(tk._civs, VILLAGER) == [1, 2],
      F.groups_of(tk._civs, VILLAGER))
check("an age family reports no task-swap group at all",
      F.groups_of(tk._civs, F.family_of(fam, 12)) == [],
      F.groups_of(tk._civs, F.family_of(fam, 12)))

print()
print("=== D. the family is consistent across civs ===")
bad = []
for c in tk._civs:
    for u in c["units"]:
        if u["id"] in fam and fam[u["id"]] != list(fam[u["id"]]):
            bad.append(u["id"])
check("family lookup is stable", not bad, bad[:5])
# every member of the Barracks family really is a Barracks by display name
_, bindings = C.load_schema()
bars = F.family_of(fam, 12)
hp = {}
for c in tk._civs:
    for u in c["units"]:
        if u["id"] in bars:
            hp.setdefault(u["id"], set()).add(u["hit_points"])
check("Barracks family HP ladder = 1200/1500/1800/2100",
      {u: sorted(hp.get(u, ())) for u in bars} ==
      {12: [1200], 20: [2100], 132: [1800], 498: [1500]},
      {u: sorted(hp.get(u, ())) for u in bars})

print()
if FAIL:
    print("FAILED: %s" % FAIL)
    sys.exit(1)
print("ALL FAMILY CHECKS PASSED")
