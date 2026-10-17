# -*- coding: utf-8 -*-
"""Britons' Dark-Age (Age 1) menu, in both halves, with ids.

The decisive experiment needs the two halves to DISAGREE, otherwise a positive
result cannot say which file the game read:

  * one unit revoked from the TREE only  (panel still lists it)
  * one unit revoked from the PANEL only (tree row still there)

Both must be visible in the same screen in the Dark Age.  This lists what
actually is.
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
pkey = BP.panel_path_for(tk.game_root, "Britons")[1]
obj = panels[pkey]["obj"]
kb = BP.civ_key_for(panels, "Britons")
print("tree stem BRITONS / panel file key %r / civ cache key %r" % (pkey, kb))

print()
print("%-8s %-9s %-6s %-6s %-14s %s"
      % ("unit", "NodeType", "Age", "bldg", "panel?", "Name"))
rows = []
for r in sorted(CT.unit_rows(brit),
                key=lambda r: (r.get("Building ID") or 0, r.get("Age ID") or 0,
                               r.get("Node ID") or 0)):
    nid = r.get("Node ID")
    b, e = BP.find_entry(obj, kb, nid, BP.UNITS_KEY)
    rows.append((nid, r, b, e))
    if r.get("Age ID") == 1:
        print("%-8s %-9s %-6s %-6s %-14s %s"
              % (nid, r.get("Node Type"), r.get("Age ID"),
                 r.get("Building ID"), "yes" if e else "NO",
                 (e or {}).get("Name", "")))

print()
print("Age-1 units present in BOTH halves (usable for either-direction revoke):")
for nid, r, b, e in rows:
    if r.get("Age ID") == 1 and e is not None:
        print("   unit %-6d %-22s tree bldg %-4s panel bldg %-4s"
              % (nid, e.get("Name"), r.get("Building ID"), b))

print()
print("Age-1 units in the TREE but NOT the panel (panel-only-revoke subjects):")
for nid, r, b, e in rows:
    if r.get("Age ID") == 1 and e is None:
        print("   unit %-6d tree bldg %-4s (no panel entry)" % (nid, r.get("Building ID")))

print()
print("Age-1 panel entries whose id Britons' tree does NOT model:")
have = {r.get("Node ID") for r in CT.unit_rows(brit)}
for nid, entry_rows in sorted(BP.entry_pool(obj, BP.UNITS_KEY).items()):
    if nid in have:
        continue
    for ck, b, e in entry_rows:
        if e.get("RequiredAge") == 1:
            print("   unit %-6d %-22s panel bldg %-4s donor %s"
                  % (nid, e.get("Name"), b, ck))
