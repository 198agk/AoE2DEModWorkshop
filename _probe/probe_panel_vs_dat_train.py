# -*- coding: utf-8 -*-
r"""Is the panel a FILTER over the .dat's train locations, or ADDITIVE?

Round 45 established the panel is not the complete build menu: it omits Barracks,
House, Mill and Lumber Camp for every civilization, all of which the game certainly
lets you build.  That leaves two shapes for the panel:

  FILTER   -- the .dat already says every civ can train X at building B; the panel
              lists the subset the civilization actually gets, so the panel can only
              REMOVE or narrow.  A write to the panel cannot grant anything new.
  ADDITIVE -- the panel can name something the .dat does not already permit, so a
              write to it can grant.

The `.dat` side is the unit record's `train_locations` (list of
`{train_time, unit_id, button_id}` where `unit_id` is the training BUILDING), which
earlier work found to be identical across civilizations.

This decides a product question: whether "let the Britons build X" is even
expressible through the panel, or must go through the tree / .dat.
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
idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

# `Toolkit._parsed` is None until `_ensure()` runs, and `_ensure()` is called
# lazily from the public verbs.  Touching `_parsed` first raised
# `TypeError: 'NoneType' object is not subscriptable` -- the parse is not done
# merely because the toolkit exists.
tk.describe(4)
assert tk._parsed is not None, "the toolkit is still unparsed"

# --- the .dat side: which buildings train each unit? -------------------------
# `train_locations` came from `locate.walk_unit`; read it for the first civ only,
# since earlier work showed the array is identical across civilizations.
_civs = tk._parsed[1]
TRAIN = {}
for u in _civs[0]["units"]:
    uid = u.get("id")
    if uid is None:
        continue
    tl = u.get("train_locations") or []
    TRAIN.setdefault(uid, set())
    for t in tl:
        b = t.get("unit_id")
        if b is not None and b >= 0:
            TRAIN[uid].add(b)

print("A  shape of the .dat side (first civ = %r)" % _civs[0].get("name"))
print("   units with a non-empty train_locations set: %d of %d"
      % (sum(1 for v in TRAIN.values() if v), len(TRAIN)))
print("   sample: unit 77 -> %s" % sorted(TRAIN.get(77, ())))
print("           unit 5  -> %s" % sorted(TRAIN.get(5, ())))
print("           unit 74 -> %s" % sorted(TRAIN.get(74, ())))
print("           unit 588-> %s" % sorted(TRAIN.get(588, ())))
print("           unit 2550-> %s" % sorted(TRAIN.get(2550, ())))

# --- the panel side ----------------------------------------------------------
civs = {}
seen = set()
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            continue
        seen.add((rec["path"], disp))
        stem = CT.civ_file_stem(disp)
        if stem in trees:
            civs[stem] = (disp, rec["obj"])

print()
print("B  for every panel entry: does the .dat permit that training building?")
agree = disagree = no_train_data = 0
examples_disagree = []
for stem, (disp, obj) in sorted(civs.items()):
    for blk in BP.buildings(obj, disp):
        b = blk.get("ID")
        for e in (blk.get(BP.UNITS_KEY) or []):
            uid = e.get("ID")
            allowed = TRAIN.get(uid)
            if not allowed:
                no_train_data += 1
                continue
            if b in allowed:
                agree += 1
            else:
                disagree += 1
                if len(examples_disagree) < 20:
                    examples_disagree.append((stem, uid, e.get("Name"), b,
                                              sorted(allowed)[:4]))
print("   panel entries whose building IS in the .dat's train_locations : %d"
      % agree)
print("   panel entries whose building is NOT                            : %d"
      % disagree)
print("   panel entries with no .dat train data at all                   : %d"
      % no_train_data)
print()
print("   the disagreements (panel lists a building the .dat does not train at):")
for row in examples_disagree:
    print("      %-12s unit %-6s %-24s panel bldg %-5s dat trains at %s"
          % row)

print()
print("C  the product question: is the panel ADDITIVE or a FILTER?")
if disagree == 0:
    print("   ADDITIVE would require at least one panel entry the .dat forbids;")
    print("   there are none -> the panel never names a training building the")
    print("   .dat does not already permit.")
else:
    print("   %d panel entries name a building the .dat does not train at, so"
          % disagree)
    print("   the panel is at least partly ADDITIVE.")

print()
print("D  the kind-P subjects specifically (Jurchens 77 etc.)")
CASES = [("JURCHENS", "Jurchens", 77, 12), ("JURCHENS", "Jurchens", 473, 12),
         ("JURCHENS", "Jurchens", 567, 12), ("MUISCA", "Muisca", 359, 12),
         ("HUNS", "Huns", 532, 45), ("POLES", "Poles", 691, 45),
         ("SICILIANS", "Sicilians", 588, 49), ("SPARTANS", "Spartans", 13, 2172),
         ("BRITONS", "Britons", 5, 87)]
for stem, disp, uid, bld in CASES:
    tree = trees[stem]
    st = CT.node_status(tree, uid, CT.UNIT_USE_TYPES)
    row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
    o = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    _b, e = BP.find_entry(o, disp, uid, BP.UNITS_KEY)
    allowed = sorted(TRAIN.get(uid, ()))
    print("   %-11s unit %-6s tree=%-18s panel=%-6s dat-train=%s"
          % (stem, uid, st, "listed" if e else "silent", allowed))
