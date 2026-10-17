# -*- coding: utf-8 -*-
"""Which requirement kills the candidate pool?  Count them one at a time."""
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
have = {r.get("Node ID") for r in CT.unit_rows(brit)}
bldgs = {r.get("Building ID") for r in CT.unit_rows(brit) if r.get("Building ID")}
print("Britons unit rows: %d   owns buildings: %s" % (len(have), sorted(bldgs)))

# --- the tree side, counted cumulatively --------------------------------
n_all = n_notbrit = n_age1 = n_owned = 0
age_hist = {}
for ck, tree in sorted(trees.items()):
    for r in CT.unit_rows(tree):
        nid = r.get("Node ID")
        n_all += 1
        if nid in have:
            continue
        n_notbrit += 1
        a = r.get("Age ID")
        age_hist[a] = age_hist.get(a, 0) + 1
        if a != 1:
            continue
        n_age1 += 1
        if r.get("Building ID") not in bldgs:
            continue
        n_owned += 1
print()
print("tree rows total                    : %d" % n_all)
print("  ...whose id Britons lacks        : %d" % n_notbrit)
print("  ...and Age ID == 1               : %d" % n_age1)
print("  ...and at a building Britons owns: %d" % n_owned)
print("Age ID histogram (Britons-lacking rows): %s"
      % dict(sorted(age_hist.items(), key=lambda kv: (kv[0] is None, kv[0]))))

# distinct ids at the last stage
ids = set()
for ck, tree in sorted(trees.items()):
    for r in CT.unit_rows(tree):
        nid = r.get("Node ID")
        if nid in have or r.get("Age ID") != 1:
            continue
        if r.get("Building ID") in bldgs:
            ids.add(nid)
print("distinct ids at the last stage     : %d  %s"
      % (len(ids), sorted(ids)[:30]))

# --- the panel side ------------------------------------------------------
obj = panels[brit_key]["obj"]
pools = BP.entry_pool(obj, BP.UNITS_KEY)
print()
print("panel entry pool: %d node ids" % len(pools))
stage = {}
for nid, rows in pools.items():
    if nid in have:
        continue
    for ck, b, e in rows:
        stage.setdefault(nid, []).append((b, e.get("RequiredAge"), ck))
ages = {}
for nid, rows in stage.items():
    for b, a, ck in rows:
        ages[a] = ages.get(a, 0) + 1
print("panel rows for ids Britons lacks   : %d ids, RequiredAge hist %s"
      % (len(stage), dict(sorted(ages.items(), key=lambda kv: (kv[0] is None, kv[0])))))
owned = {n: r for n, r in stage.items()
         if any(b in bldgs for b, a, ck in r)}
print("  ...at a building Britons owns    : %d ids %s"
      % (len(owned), sorted(owned)[:30]))
dark = {n: r for n, r in owned.items()
        if any(a == 1 for b, a, ck in r if b in bldgs)}
print("  ...and RequiredAge == 1          : %d ids %s"
      % (len(dark), sorted(dark)[:30]))
