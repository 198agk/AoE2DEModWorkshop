# -*- coding: utf-8 -*-
"""Candidates for a DISCRIMINATING experiment.

Design: put TWO units on the SAME Dark-Age screen (Britons' Barracks, id 12)
and move the two halves in OPPOSITE directions:

  * A = panel entry ADDED, tree row NOT added   (panel-only)
  * B = tree row ADDED,   panel entry NOT added (tree-only)

Then one game session tells the whole story:
  both A and B appear -> both layers are read
  only A              -> the menu comes from the panel file
  only B              -> the menu comes from the tree file
  neither             -> neither layer is read that way

Both need building 12 and Age ID / RequiredAge 1 so the Dark Age shows them.
"""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

BLD = 12          # Barracks
tk = A.open_toolkit()
trees = CT.load_trees(tk.game_root)
panels = BP.load_all(tk.game_root)

# --- every panel entry under building 12 with RequiredAge 1 ------------------
found = defaultdict(list)
for path, rec in panels.items():
    obj = rec["obj"]
    for civ_key, blk in obj.items():
        if not isinstance(blk, dict):
            continue
        units = BP.entries(obj, civ_key, BLD, BP.UNITS_KEY) or []
        for e in units:
            if e.get("RequiredAge") == 1:
                found[e.get("ID")].append((civ_key, e.get("Name")))

print("panel entries, building %d, RequiredAge 1 -- candidates:" % BLD)
for nid, civs in sorted(found.items(), key=lambda kv: -len(kv[1])):
    names = Counter(n for _, n in civs)
    print("   unit %-6s %-22s %d civs  e.g. %s"
          % (nid, names.most_common(1)[0][0], len(civs),
             sorted(c[0] for c in civs)[:4]))

# --- every tree row under building 12 with Age ID 1 -------------------------
print()
print("tree rows, building %d, Age ID 1 -- candidates:" % BLD)
tfound = defaultdict(list)
for stem, tree in trees.items():
    for r in CT.unit_rows(tree):
        if r.get("Building ID") == BLD and r.get("Age ID") == 1:
            tfound[r.get("Node ID")].append(stem)
for nid, stems in sorted(tfound.items(), key=lambda kv: -len(kv[1])):
    print("   unit %-6s %d civs  e.g. %s" % (nid, len(stems), sorted(stems)[:4]))

# --- which of those does Britons lack in EACH half? ------------------------
brit = trees["BRITONS"]
kb = BP.civ_key_for(panels, "Britons")
pkey = BP.panel_path_for(tk.game_root, "Britons")[1]
pobj = panels[pkey]["obj"]
btree_ids = {r.get("Node ID") for r in CT.unit_rows(brit)}
bpanel_ids = set()
for e in (BP.entries(pobj, kb, BLD, BP.UNITS_KEY) or []):
    bpanel_ids.add(e.get("ID"))

print()
print("Britons half-membership for the candidate ids (building %d):" % BLD)
allids = sorted(set(found) | set(tfound))
print("   %-7s %-22s %-10s %s" % ("unit", "name", "in tree", "in panel"))
for nid in allids:
    nm = ""
    if found.get(nid):
        nm = Counter(n for _, n in found[nid]).most_common(1)[0][0]
    print("   %-7s %-22s %-10s %s"
          % (nid, nm, nid in btree_ids, nid in bpanel_ids))
