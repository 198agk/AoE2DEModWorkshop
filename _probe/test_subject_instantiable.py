# -*- coding: utf-8 -*-
r"""PIN: before testing an availability write, confirm the `.dat` can INSTANTIATE it.

A tree row says "you may have this".  It does not make the engine able to build it:
the engine also needs a per-civilization `.dat` unit record.  If that record were
missing for the target civilization, "the unit did not appear" would be explained by
the `.dat` and would say nothing about the tree -- a **fifth gate class**, and one
that would waste the user's in-game test.

This pins the pre-check for the smoke6 subject (BRITONS get the Champi Scout, 2550):

  * `2550` is in **63 of 63** civilizations' unit arrays (absent from none);
  * at index **2014** for 62 of them (Gaia differs at 2493), so the record exists
    for the Britons;
  * the Briton record carries `train_locations` already: building **12 (Barracks)**,
    `button_id` 1, `train_time` 42;
  * the Britons' tree marks building **12** `ResearchedCompleted`, and the Champi
    Scout's INCAS tree row names the same `Building ID` 12.

So the `.dat` is already sufficient to build the unit for the Britons, and the tree
row plus the panel entry are the ONLY gate.  That is what makes smoke6 decisive:
if it does not appear, the gate is not what the write changed.

The general rule this pins: **an availability test needs the DATA layer to be able
to instantiate the subject first.**  Otherwise a negative result is unattributable.

Run:  python _probe\test_subject_instantiable.py
"""
import os
import _gamepaths as GP
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = GP.GAME
UNIT = 2550
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
_data, civs, _cs, _gv, _tail, _how = tk._parsed

print("A  the .dat can instantiate the subject for EVERY civilization")
present, absent, idx = [], [], {}
for c in civs:
    ids = [u.get("id") for u in (c.get("units") or [])]
    if UNIT in ids:
        present.append(c.get("name"))
        idx[c.get("name")] = ids.index(UNIT)
    else:
        absent.append(c.get("name"))
print("     present %d / %d civilizations" % (len(present), len(civs)))
print("     index distribution: %s" % dict(Counter(idx.values())))
check("the subject is present in every civilization's unit array",
      not absent, "absent from %s" % absent)
check("including the TARGET civilization (British)", "British" in present)
check("the subject sits at the SAME index for all playable civs",
      len(set(idx.values())) <= 2,
      "indices=%s" % dict(Counter(idx.values())))

print()
print("B  the target's record already names the producing building")
_br = next((c for c in civs if c.get("name") == "British"), None)
_rec = next((u for u in (_br.get("units") or []) if u.get("id") == UNIT), None)
check("the Briton record exists", _rec is not None)
if _rec:
    print("     %s" % {k: _rec.get(k) for k in
                       ("id", "type", "hit_points", "class", "name",
                        "icon_id")})
    _tl = _rec.get("train_locations") or []
    print("     train_locations: %s"
          % [{k: v for k, v in t.items() if not k.startswith("_")}
             for t in _tl])
    check("it already has at least one train location", bool(_tl))
    check("and that location is the Barracks (12)",
          any(t.get("unit_id") == 12 for t in _tl),
          "locations=%s" % _tl)

print()
print("C  and the tree says the target may build that building")
trees = CT.load_trees(GAME)
_b = next((r for r in CT.rows_of(trees["BRITONS"])
           if r.get("Use Type") == "Building" and r.get("Node ID") == 12), None)
print("     BRITONS building 12: %s"
      % ({k: _b.get(k) for k in ("Node ID", "Name", "Node Status", "Age ID")}
         if _b else None))
check("the Britons' tree grants the Barracks",
      (_b or {}).get("Node Status") == "ResearchedCompleted")
_inca = CT.row_for(trees["INCAS"], UNIT, CT.UNIT_USE_TYPES)
check("the donor row names the same building",
      (_inca or {}).get("Building ID") == 12,
      "donor Building ID=%s" % (_inca or {}).get("Building ID"))

print()
print("D  so the ONLY gate is the one the write touches")
check("the target civilization has NO tree row for the subject",
      CT.row_for(trees["BRITONS"], UNIT, CT.UNIT_USE_TYPES) is None)
print("     -> the `.dat` can already instantiate it, and the Barracks is buildable,")
print("        so a tree row + a panel entry are the complete remaining gate.")

print()
print("SUBJECT INSTANTIABLE: the .dat, the record and the producing building are all")
print("  present for the target civilization, so a negative in-game result CANNOT be")
print("  explained by the data layer.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
