# -*- coding: utf-8 -*-
r"""PIN: the panel is not a pure projection of the .dat's train locations.

`unit.availability` writes two layers.  To know what a panel WRITE can mean, the
panel must be compared against the `.dat`'s own statement about where a unit is
trained -- the unit record's `train_locations` (each entry's `unit_id` is the
training BUILDING).

Measured over every panel entry in all 62 civs:

    4,239  entries whose building IS in the .dat's train_locations
       20  entries whose building is NOT
       64  entries with no .dat train data at all

The 20 reduce to **8 distinct (unit, building) pairs**, and every one of them
involves a building introduced by a late DLC:

    unit 199 Fish Trap       -> building 2171  (Oyster Boat / 牡蛎船)   6 civs
    unit  13 Fishing Ship    -> building 2172  (Port / 港口)            5 civs
    unit 2552 Settlement     -> building 118   (Builder / 建筑者)        4 civs
    unit   7 Skirmisher      -> building 2556  (Settlement / 聚落)       1 civ
    unit   6 Elite Skirmisher-> building 2556                          1 civ
    unit  93 Spearman        -> building 2556                          1 civ
    unit 358 Pikeman         -> building 2556                          1 civ
    unit 359 Halberdier      -> building 2556                          1 civ

So the panel can name a training building the `.dat` does not list for that unit.
That does not prove the engine honours it, but it does prove the two layers are not
redundant and a panel write carries information the `.dat`'s train list does not.

Also pinned: the `.dat`'s train map is nearly civ-invariant -- **4 distinct maps
across 63 civs (group sizes 56 / 3 / 3 / 1)** -- and the disagreement set is
IDENTICAL whether the reference civ is Gaia or British (symmetric difference 0), so
earlier comparisons that used civ[0] = Gaia were not misled by it.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)                     # `_parsed` is None until a verb runs
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


maps = [train_map(c) for c in civs_dat]
print("A  the .dat side is nearly civ-invariant")
fps = {}
for m in maps:
    fps.setdefault(tuple(sorted(m.items())), 0)
    fps[tuple(sorted(m.items()))] += 1
print("     distinct train maps across %d civs: %d   groups: %s"
      % (len(maps), len(fps), sorted(fps.values(), reverse=True)[:6]))
check("the train map has few distinct values (so one reference civ is enough)",
      len(fps) <= 6, "distinct maps = %d" % len(fps))

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


def disagreements(ref):
    agree = dis = nodata = 0
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
                    dis += 1
                    rows.append((stem, uid, b))
    return agree, dis, nodata, rows


print()
print("B  the comparison, against two different reference civilizations")
a_g, d_g, n_g, rows_g = disagreements(maps[0])
a_b, d_b, n_b, rows_b = disagreements(maps[1])
print("     reference Gaia    : agree=%-5d disagree=%-4d no-data=%d"
      % (a_g, d_g, n_g))
print("     reference British : agree=%-5d disagree=%-4d no-data=%d"
      % (a_b, d_b, n_b))
check("the two references give the SAME disagreement set",
      {(s, u, b) for s, u, b in rows_g} == {(s, u, b) for s, u, b in rows_b},
      "gaia %d vs british %d" % (d_g, d_b))
check("most panel entries agree with the .dat's own train locations",
      a_b > 4000 and a_b > 100 * d_b,
      "agree=%d disagree=%d" % (a_b, d_b))
check("the panel nonetheless names buildings the .dat does not train at",
      d_b > 0, "disagree=%d" % d_b)

print()
print("C  the 8 distinct (unit, building) pairs behind those entries")
pairs = {}
for _s, u, b in rows_b:
    pairs.setdefault((u, b), 0)
    pairs[(u, b)] += 1
for (u, b), n in sorted(pairs.items()):
    print("     unit %-6s -> building %-6s in %d civs" % (u, b, n))
check("they reduce to exactly 8 distinct (unit, building) pairs",
      len(pairs) == 8, "got %d: %s" % (len(pairs), sorted(pairs)))

print()
print("PANEL-VS-DAT: the panel names training buildings the .dat does not,")
print("  so the two layers are not redundant and a panel write is not a no-op")
print("  in principle.  NOT PROVEN: that the engine honours such an entry.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
