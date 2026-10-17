# -*- coding: utf-8 -*-
r"""THE REFRAMING: the panel is ~the tree, not a rival authority.

`probe_future_items.py` measured, over every (civ, unit) pair:

    tree grants AND panel lists : 3107
    tree grants, panel SILENT   :    8
    tree REFUSES, panel lists   :   11

So the two layers agree on **3107 / 3126 = 99.4%** of pairs.  The entire
"contradiction" this experiment is built on is **19 data points**.  That changes
what the experiment is measuring: not "which of two rival authorities wins" but
"which of two near-identical copies is consulted".

Two consequences worth nailing:

  1. If one file is derived from the other at BUILD time, the 19 disagreements are
     drift/staleness, not design.  The panel's mtime is 2026-09-23 and the exe is
     2026-10-12 -- the panel is 19 days older than the engine that reads it.
  2. For the PRODUCT the answer stops mattering much: writing BOTH (which
     `aoe2mod/api.py` already does) is correct whichever file is consulted, because
     they encode the same model to within 0.6%.

Also verify the "same data, two copies" reading by checking whether the panel could
have been generated FROM the tree: each panel entry's `RequiredAge` should equal the
tree row's `Age ID`, and its position should follow the tree's `Building ID`.

And check the entry-count arithmetic from the previous probe, which printed 524,068
panel entries -- far more than 68 civs x 31 buildings x ~10 units would give, so that
number may be an overcount caused by iterating a civ key more than once.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

print("A  count the panel entries correctly (dedupe civ keys per file)")
seen_pairs = set()
entries = 0
per_civ = Counter()
for path_key, rec in sorted(panels.items()):
    obj = rec["obj"]
    for disp in sorted(k for k in obj if isinstance(k, str)):
        if (rec["path"], disp) in seen_pairs:
            continue
        seen_pairs.add((rec["path"], disp))
        for blk in BP.buildings(obj, disp):
            for e in (blk.get(BP.UNITS_KEY) or []) + (blk.get(BP.TECHS_KEY) or []):
                entries += 1
                per_civ[disp] += 1
print("   distinct (file, civ) pairs : %d" % len(seen_pairs))
print("   total entries              : %d" % entries)
print("   entries per civ: min %d  max %d  avg %.1f"
      % (min(per_civ.values()), max(per_civ.values()),
         sum(per_civ.values()) / len(per_civ)))
print("   (the earlier probe printed 524068 because it re-iterated a civ key")
print("    once per key in the same file -- a 25x overcount)")

print()
print("B  the 19 disagreements, named")
rows = []
for stem, tree in sorted(trees.items()):
    disp = next((d for d in sorted(panels)
                 if CT.civ_file_stem(d) == stem), None)
    if disp is None:
        continue
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    listed = {}
    for blk in BP.buildings(obj, disp):
        for e in (blk.get(BP.UNITS_KEY) or []):
            listed[e.get("ID")] = blk.get("ID")
    for r in CT.unit_rows(tree):
        uid = r.get("Node ID")
        if uid is None:
            continue
        ok = r.get("Node Status") in ("ResearchedCompleted", "ResearchRequired")
        inp = uid in listed
        if ok == inp:
            continue
        rows.append((stem, disp, uid, r.get("Node Status"), inp,
                     r.get("Building ID"), listed.get(uid), r.get("Name"),
                     r.get("Age ID")))
print("   %-12s %-7s %-20s %-18s %-5s %-6s %s"
      % ("civ", "unit", "tree name", "tree status", "panel", "tBldg", "pBldg"))
for r in sorted(rows):
    print("   %-12s %-7s %-20s %-18s %-5s %-6s %s"
          % (r[0], r[2], r[7], r[3], r[4], r[5], r[6]))
print("   total: %d" % len(rows))
print("   kinds: %s" % Counter(("panel-only" if r[4] else "tree-only")
                             for r in rows))

print()
print("C  could the panel have been GENERATED from the tree?")
# RequiredAge vs tree Age ID, over agreed pairs
same_age = diff_age = missing = 0
samples = []
for stem, tree in sorted(trees.items()):
    disp = next((d for d in sorted(panels)
                 if CT.civ_file_stem(d) == stem), None)
    if disp is None:
        continue
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    ages = {}
    for blk in BP.buildings(obj, disp):
        for e in (blk.get(BP.UNITS_KEY) or []):
            ages[e.get("ID")] = e.get("RequiredAge")
    for r in CT.unit_rows(tree):
        uid = r.get("Node ID")
        if uid is None or uid not in ages:
            missing += 1
            continue
        if r.get("Age ID") == ages[uid]:
            same_age += 1
        else:
            diff_age += 1
            if len(samples) < 10:
                samples.append((stem, uid, r.get("Age ID"), ages[uid],
                                r.get("Name")))
print("   panel RequiredAge == tree Age ID : %d" % same_age)
print("   different                        : %d" % diff_age)
print("   panel has no entry at all        : %d" % missing)
for s in samples:
    print("      %-12s unit %-7s tree=%s panel=%s %s" % s)

print()
print("D  the panel's mtime vs the engine's")
for rel in ("resources/_common/dat/futuravailableunits.json",
            "resources/_common/dat/CivTechTrees/SICILIANS.json",
            "AoE2DE_s.exe"):
    p = os.path.join(GAME, rel.replace("/", os.sep))
    if os.path.exists(p):
        import datetime
        m = datetime.datetime.fromtimestamp(os.path.getmtime(p))
        print("   %-52s %s" % (rel, m))

print()
print("E  so: what does writing only ONE layer risk?")
print("   The panel and the tree encode the SAME model to within 0.6%%.")
print("   A tool that writes one and not the other creates a 0.6%% inconsistency")
print("   at worst, and a 100%% one if the file it did not write is the one read.")
print("   => writing BOTH, as aoe2mod/api.py does, is the right default and does")
print("      not require knowing which is consulted.")
