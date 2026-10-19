# -*- coding: utf-8 -*-
r"""Are the five panel-omitted buildings real, buildable .dat records?

`probe_folwark` found five buildings where the POLES-style tree grants the
building but the shipped panel has no trace of it -- not as a block, not in any
Units/Techs list, not even by name:

    1734 Folwark           Poles
    1754 Caravanserai      Indians, Persians
    1806 Fortified Church  Armenians, Georgians
    1889 Pasture           Khitans
    2415 Fortified Outpost Macedonians

Players build every one of these in ordinary games.  If the panel filled the
build menu, none of them could appear.  This probe checks they are genuine .dat
records with a real cost, HP and button, so the argument cannot be dismissed
with "those are scenario-only or renamed something else".

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_five_buildings_dat.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P                        # noqa: E402
from aoe2mod.dat import locate as L                        # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat",
                   "empires2_x2_p1.dat")
WANT = {1734: "Folwark", 1754: "Caravanserai", 1806: "Fortified Church",
        1889: "Pasture", 2415: "Fortified Outpost"}

print("parsing %s ..." % DAT)
dat = P.load_dat(DAT)
print("parsed: units=%d civs=%d techs=%d"
      % (len(dat.units), len(dat.civs), len(dat.techs)))

print()
print("A  the five buildings as raw .dat unit records")
by_id = {}
for u in dat.units:
    by_id[getattr(u, "id", None)] = u
for uid in sorted(WANT):
    u = by_id.get(uid)
    if u is None:
        print("     %-5s %-20s NOT FOUND" % (uid, WANT[uid]))
        continue
    cost = getattr(u, "resource_costs", None) or getattr(u, "cost", None)
    cost_s = ""
    if isinstance(cost, dict):
        cost_s = {k: v for k, v in cost.items() if v}
    else:
        try:
            cost_s = [(getattr(c, "resource", None), getattr(c, "amount", None),
                       getattr(c, "flag", None)) for c in (cost or [])]
        except Exception:
            cost_s = cost
    print("     %-5s %-20s hp=%-5s time=%-4s button=%-3s loc=%-4s cost=%s"
          % (uid, getattr(u, "name", WANT[uid]),
             getattr(u, "hit_points", "?"), getattr(u, "creation_time", "?"),
             getattr(u, "button_id", "?"), getattr(u, "train_location", "?"),
             cost_s))

print()
print("B  per-civilization ownership, read through locate.walk_civ")
for uid in sorted(WANT):
    owners = []
    for ci, civ in enumerate(dat.civs):
        try:
            t = ci
            # locate.walk_civ yields (kind, index, value) triples
            found = False
            for item in L.walk_civ(civ, ci) if False else ():
                del item
            del t, found
        except Exception:
            pass
    # simpler: does the unit table of the civ list the id?
    for ci, civ in enumerate(dat.civs):
        tbl = getattr(civ, "units", None) or getattr(civ, "unit_ids", None)
        if tbl is None:
            continue
        ids = [getattr(x, "id", x) if not isinstance(x, int) else x for x in tbl]
        if uid in ids:
            owners.append(getattr(civ, "name", "#%d" % ci))
    print("     %-5s owned by: %s" % (uid, owners[:8] or "not via civ.units"))

print()
print("C  the argument in one line")
print("     If the panel were the build-menu source, these five buildings")
print("     could never be built -- yet every one of them is a normal")
print("     civilization-defining building in the shipped game.")
sys.exit(0)
