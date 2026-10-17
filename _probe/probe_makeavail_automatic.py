# -*- coding: utf-8 -*-
r"""The 'make avail' techs: are they in the tree, or do they apply automatically?

The user's latest result is a CLEAN test for the first time:

    「不列颠黑暗时代兵营，没有蔷琵侦察兵，村民血量是1000」

Control passed (villager 1000 = the `.dat` loaded and rendered) and the test failed
(no Champi Scout).  So the dat-adjacent JSON availability write does NOT reach the
build menu -- while the `.dat` demonstrably does.

That makes the `.dat`-only route (`_probe/test_dat_grant_route.py`) the live one: the
shipped data grants regional units with **effect command type 2, b=1, on a tech whose
`civ` names the civilization**:

    tech 1363  civ 57 (Muisca)   'Guecha Warrior (make avail)'  type 2 a=2562 b=1
    tech 1471  civ 61 (Varangians) 'Jarl (make avail)'          type 2 a=2708 b=1

BEFORE imitating it, one thing decides whether it is usable at all:

    **does such a tech need to be present in the civilization's CivTechTrees file
    (i.e. researched), or does `tech.civ` alone make it apply?**

If it needs a tree row, the route is circular -- it would be gated by exactly the
layer that does not work.  If it applies automatically, a `.dat`-only grant is real.

Answer it from the shipped data.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
civs = tk._parsed[1]
names = [c["name"] for c in civs]
techs = tk._tech_records()
effs = tk._effect_records()
trees = CT.load_trees(GAME)


def stem_of(idx):
    return CT.civ_file_stem(names[idx])


print("A  the shipped 'make avail' techs, in full")
CAND = []
for rec in effs:
    ti = rec.get("index")
    if ti is None or ti >= len(techs):
        continue
    t = techs[ti]
    if not isinstance(t, dict):
        continue
    for c in rec.get("commands") or []:
        if c.get("type") == 2 and c.get("b") == 1 and (c.get("a") or -1) > 0:
            CAND.append((ti, t, c.get("a")))
            break
for ti, t, u in CAND:
    civ = t.get("civ")
    owner = names[civ] if isinstance(civ, int) and 0 <= civ < len(names) else civ
    rl = t.get("research_locations")
    print("     tech %-5s civ=%-11s type=%-3s res_locs=%-24s unit a=%-6s name=%r"
          % (ti, owner, t.get("type"), str(rl)[:24], u, str(t.get("name"))[:30]))

print()
print("B  THE DECISIVE QUESTION: is that tech in the owning civ's TREE?")
for ti, t, u in CAND:
    civ = t.get("civ")
    if not isinstance(civ, int) or civ < 0:
        continue
    stem = stem_of(civ)
    tr = trees.get(stem)
    if tr is None:
        print("     tech %-5s civ=%-11s NO TREE FILE" % (ti, names[civ]))
        continue
    row = None
    for r in CT.rows_of(tr):
        if r.get("Node ID") == ti and r.get("Use Type") == "Tech":
            row = r
            break
    st = row.get("Node Status") if row else None
    print("     tech %-5s civ=%-11s tree row: %s"
          % (ti, names[civ], ("status=%r" % st) if row else "ABSENT"))

print()
print("C  and does ANY civ's tree carry these techs?")
for ti, t, u in CAND[:12]:
    holders = []
    for s, tr in trees.items():
        for r in CT.rows_of(tr):
            if r.get("Node ID") == ti and r.get("Use Type") == "Tech":
                holders.append((s, r.get("Node Status")))
    print("     tech %-5s in %d tree(s): %s" % (ti, len(holders), holders[:4]))

print()
print("D  a second, cleaner sample: techs whose effects touch a unit, by cmd type")
# If a civ-owned tech with type 2 is consistently ABSENT from the tree, that is the
# evidence that `tech.civ` alone applies it -- like a civilization bonus.
civ_owned_type2 = []
for rec in effs:
    ti = rec.get("index")
    if ti is None or ti >= len(techs):
        continue
    t = techs[ti]
    if not isinstance(t, dict):
        continue
    civ = t.get("civ")
    if not isinstance(civ, int) or civ < 0:
        continue
    if any(c.get("type") == 2 for c in (rec.get("commands") or [])):
        civ_owned_type2.append((ti, civ, t))
absent = present = 0
for ti, civ, t in civ_owned_type2:
    stem = stem_of(civ)
    tr = trees.get(stem)
    has = False
    if tr:
        has = any(r.get("Node ID") == ti and r.get("Use Type") == "Tech"
                  for r in CT.rows_of(tr))
    absent += (not has)
    present += has
print("     civ-owned techs containing a type-2 command: %d" % len(civ_owned_type2))
print("     ...present in the owning civ's tree : %d" % present)
print("     ...ABSENT from the owning civ's tree: %d" % absent)
print()
if absent > present:
    print("     => the majority apply WITHOUT a tree row.  A `.dat`-only grant is")
    print("        therefore NOT circular: `tech.civ` + type 2 is enough by itself.")
else:
    print("     => they usually DO have a tree row, so the route may be circular.")
    print("        Compare with the tree status to see whether it must be researched.")
