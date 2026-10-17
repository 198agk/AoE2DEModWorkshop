# -*- coding: utf-8 -*-
"""Why did my own probe report 0 pairs where the shipped probe reports 18?

Same failure class this project keeps paying for: a check that silently finds
nothing.  Find the bug before trusting either number.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

print("panels keys (%d): %s" % (len(panels), sorted(panels)[:8]))
rec = panels.get("Jurchens")
print("panels['Jurchens'] type: %s" % type(rec).__name__)
if rec is None:
    print("  -> 'Jurchens' is NOT a key of load_all()!")
    print("  keys sample:", sorted(panels)[:20])
# the shape of one record
k0 = sorted(panels)[0]
print("record keys for %r: %s" % (k0, sorted(panels[k0])))
obj0 = panels[k0]["obj"]
print("obj top-level keys (%d) sample: %s"
      % (len(obj0), sorted(x for x in obj0 if isinstance(x, str))[:8]))

# the exact lookups the shipped probe does
print()
for disp in ("Jurchens", "Britons"):
    pk = BP.panel_path_for(GAME, disp)
    print("%-10s panel_path_for -> %s" % (disp, pk))
    stem = CT.civ_file_stem(disp)
    print("%-10s civ_file_stem  -> %r   in trees: %s"
          % ("", stem, stem in trees))
    rec = panels.get(pk[1])
    print("%-10s load_all key   -> %s" % ("", pk[1] in panels))
    if rec:
        bb, ee = BP.find_entry(rec["obj"], pk[1], 77, BP.UNITS_KEY)
        print("%-10s find_entry(77) -> bldg=%r entry=%r" % ("", bb, ee))
        st = CT.node_status(trees[stem], 77, CT.UNIT_USE_TYPES)
        print("%-10s tree status 77  -> %r" % ("", st))
