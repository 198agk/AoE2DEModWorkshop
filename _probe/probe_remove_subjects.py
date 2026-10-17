# -*- coding: utf-8 -*-
"""Pick two Dark-Age Barracks units Britons HAS, one for each half.

Better experiment than granting two foreign units: REMOVE one unit from each
half independently and see which removal the game notices.

  * remove Spearman from the TREE only   -> if Spearmen vanish, the game read the tree
  * remove Militia  from the PANEL only  -> if Militia  vanish, the game read the panel

Both sit in the SAME menu (the Barracks), both are Dark Age, so the user opens
one screen and compares two rows.  A `unit.stat` sentence (villager HP) rides
along as a positive control, so "nothing changed" cannot mean "the mod did not
load".
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

tk = A.open_toolkit()
trees = CT.load_trees(tk.game_root)
panels = BP.load_all(tk.game_root)
brit = trees["BRITONS"]
brit_key = BP.panel_path_for(tk.game_root, "Britons")[1]
obj = panels[brit_key]["obj"]

print("Britons tree rows (Dark Age, at the Barracks 12):")
print("%-8s %-10s %-22s %-8s" % ("Node ID", "Use Type", "panel lists it?",
                                 "Name ID"))
rows = []
for r in CT.unit_rows(brit):
    if r.get("Age ID") != 1:
        continue
    nid = r.get("Node ID")
    b, e = BP.find_entry(obj, brit_key, nid, BP.UNITS_KEY)
    rows.append((nid, r.get("Node Type"), b, e, r.get("Building ID")))
for nid, nt, b, e, tb in sorted(rows):
    print("%-8s %-10s bldg %-4s treebldg %-4s panel %s"
          % (nid, nt, b, tb, ("yes %r" % (e,)) if e else "--"))
print()

# Every Dark-Age Britons unit that the panel also lists -> removable either way
both = [(nid, nt, b, e, tb) for nid, nt, b, e, tb in rows if e is not None]
print("in BOTH halves (Age 1): %s" % [(n, e.get("Name")) for n, _, _, e, _ in both])
print()

print("full Britons tree rows by age / building:")
for r in sorted(CT.unit_rows(brit), key=lambda r: (r.get("Age ID") or 0,
                                                   r.get("Building ID") or 0)):
    nid = r.get("Node ID")
    b, e = BP.find_entry(obj, brit_key, nid, BP.UNITS_KEY)
    print("  age %-3s bldg %-5s unit %-6s panel=%-5s %s"
          % (r.get("Age ID"), r.get("Building ID"), nid,
             "yes" if e else "no", (e or {}).get("Name", "")))
