# -*- coding: utf-8 -*-
r"""Who are buildings 2171 / 2172 / 2556, and does the reference civ matter?

Section B of `probe_panel_vs_dat_train.py` found 20 panel entries naming a building
the `.dat` does not train at.  Before calling the panel "additive", two things must
be checked:

  1. **the reference civ.**  That comparison used civ[0] = Gaia, and Gaia's map
     differs from every other civ's (it carries 529 extra eyecandy units).  Re-run
     against a playable civ and see whether the same 20 appear.
  2. **the building ids.**  2171, 2172 and 2556 do not look like the standard
     buildings; a panel pointing at a building the tree does not model would be a
     different kind of oddity from a panel granting a unit the .dat forbids.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
civs_dat = tk._parsed[1]


def train_map(civ):
    out = {}
    for u in civ.get("units") or []:
        uid = u.get("id")
        if uid is None:
            continue
        out[uid] = tuple(sorted(t.get("unit_id")
                                for t in (u.get("train_locations") or [])
                                if t.get("unit_id") is not None
                                and t.get("unit_id") >= 0))
    return out


GAIA = train_map(civs_dat[0])
BRIT = train_map(civs_dat[1])

panels_civs = {}
seen = set()
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            continue
        seen.add((rec["path"], disp))
        stem = CT.civ_file_stem(disp)
        if stem in trees:
            panels_civs[stem] = (disp, rec["obj"])


def compare(ref, label):
    agree = disagree = nodata = 0
    rows = []
    for stem, (disp, obj) in sorted(panels_civs.items()):
        for blk in BP.buildings(obj, disp):
            b = blk.get("ID")
            for e in (blk.get(BP.UNITS_KEY) or []):
                uid = e.get("ID")
                allowed = ref.get(uid)
                if not allowed:
                    nodata += 1
                    continue
                if b in allowed:
                    agree += 1
                else:
                    disagree += 1
                    rows.append((stem, uid, e.get("Name"), b, sorted(allowed)))
    print("   reference %-8s agree=%-5d disagree=%-4d no-dat-data=%d"
          % (label, agree, disagree, nodata))
    return rows


print("A  does the reference civilization change the answer?")
r_gaia = compare(GAIA, "Gaia")
r_brit = compare(BRIT, "British")
set_g = {(s, u, b) for s, u, _n, b, _a in r_gaia}
set_b = {(s, u, b) for s, u, _n, b, _a in r_brit}
print("   same disagreement set: %s   (gaia %d / british %d, symmetric diff %d)"
      % (set_g == set_b, len(set_g), len(set_b), len(set_g ^ set_b)))

print()
print("B  who are the buildings the panel points at?")
for bid in (2171, 2172, 2556, 118, 12, 45, 87, 49, 13):
    u = idx.get("unit", bid)
    nm = ((u.zh or u.en) if u else None)
    # is it a Building row in any tree?
    bname = None
    for t in trees.values():
        for r in CT.rows_of(t):
            if r.get("Use Type") == "Building" and r.get("Node ID") == bid:
                bname = r.get("Name")
                break
        if bname:
            break
    print("   %-6s semantic=%-24s tree Building row=%s"
          % (bid, nm, bname or "NONE"))

print()
print("C  the disagreement rows (British reference)")
for stem, uid, nm, b, allowed in r_brit:
    print("   %-12s unit %-6s %-20s panel bldg %-6s dat trains at %s"
          % (stem, uid, nm, b, allowed))

print()
print("D  how many DISTINCT (unit, panel-building) pairs is that?")
pairs = Counter((u, b) for _s, u, _n, b, _a in r_brit)
print("   distinct pairs: %d" % len(pairs))
for (u, b), n in pairs.most_common():
    print("      unit %-6s at building %-6s in %d civs" % (u, b, n))
