# -*- coding: utf-8 -*-
r"""Is the two-game protocol blocked by a THIRD gate -- the upgrade technology?

Round 48 found `button_id` names a CHAIN: one grid button cycles an upgrade line
(`74 Militia -> 75 Man-at-Arms -> 77 Long Swordsman -> 473 -> 567`).  Each step has
a `Trigger Tech ID` (77 -> 207, 473 -> 217, 567 -> 264).

That raises a confound the protocol has not excluded.  For GAME 1 the claim is
"the tree says Long Swordsman is NotAvailable while the panel lists it, so a
reachable Long Swordsman means the panel was read".  But if the game's *upgrade*
needs technology 207 and NEITHER layer offers 207 to Jurchens, then Long Swordsman
is unreachable WHATEVER file the menu reads -> the observation proves nothing.

Same question for GAME 2: Sicilians' Siege Onager (588) has Trigger Tech ID 320.

This checks, for every subject in both games, whether the layer that is supposed
to supply it also supplies its upgrade path.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

ZH = {}
kd = os.path.join(GAME, "resources", "zh", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        with open(os.path.join(kd, fn), "rb") as fh:
            for line in fh.read().decode("utf-8-sig", "replace").splitlines():
                k, _, v = line.strip().partition("\t")
                if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                    ZH.setdefault(int(k.strip()), v[1:-1])


def uname(uid):
    u = idx.get("unit", uid)
    return ((u.zh or u.en) if u else None) or ("unit %s" % uid)


def tname(tid):
    u = idx.get("tech", tid)
    return ((u.zh or u.en) if u else None) or ("tech %s" % tid)


CASES = [
    ("JURCHENS", "Jurchens", 12, [74, 75, 77, 473, 567], "GAME 1"),
    ("SICILIANS", "Sicilians", 49, [279, 280, 550, 588], "GAME 2"),
    ("GEORGIANS", "Georgians", 49, [279, 280, 550, 588], "GAME 2 alt"),
]

for stem, disp, bld, ids, label in CASES:
    tree = trees[stem]
    pk = BP.panel_path_for(GAME, disp)
    obj = panels[pk[1]]["obj"]
    units_at, techs_at = set(), set()
    for blk in BP.buildings(obj, disp):
        if blk.get("ID") == bld:
            units_at = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
            techs_at = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
    print("=" * 78)
    print("%s  %s  building %s" % (label, stem, bld))
    print("=" * 78)
    print("  panel Units at this building: %s" % sorted(units_at))
    print("  panel Techs at this building: %s"
          % [(t, tname(t)) for t in sorted(techs_at)])
    print()
    print("  %-6s %-22s %-12s %-14s %-10s %s"
          % ("unit", "name", "tree", "panel Units", "trigTech", "tech reachable?"))
    for uid in ids:
        row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
        st = CT.node_status(tree, uid, CT.UNIT_USE_TYPES)
        ttl = (row or {}).get("Trigger Tech ID")
        in_units = uid in units_at
        if ttl is None:
            reach = "n/a (no upgrade tech)"
        else:
            t_stat = CT.node_status(tree, ttl, CT.TECH_USE_TYPES)
            in_ptechs = ttl in techs_at
            reach = "tree=%r panelTechs=%s" % (t_stat, in_ptechs)
        print("  %-6s %-22s %-12s %-14s %-10s %s"
              % (uid, uname(uid), st if st else "(none)",
                 "listed" if in_units else "silent", ttl, reach))
    print()
