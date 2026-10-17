# -*- coding: utf-8 -*-
r"""Can ONE civilization distinguish all four hypotheses at once?

The design audit's finding #4 (task-1): the recommended observation is 2-to-1.
For a kind-P pair (panel lists it, tree says NotAvailable):
    button present <- "the PANEL drives the menu"  OR  "the two layers are unioned"
Two hypotheses, one observation.  Not a test.

A single civilization would be injective if it had BOTH kinds on screen at once:

    A: panel lists it, tree has no usable row   (kind P)
    B: tree grants it, panel is silent          (kind T)

    panel drives  -> A present, B ABSENT
    tree drives   -> A ABSENT,  B present
    union         -> A present, B present
    neither/other -> A ABSENT,  B ABSENT

Four hypotheses, four distinct outcomes.  The earlier search (287 tree-modelled
nodes, filtered by the civ's own buildings) found no such civ -- but it only
looked at units the TREE models.  The audit also measured **1201 of 4323 panel
entries that have NO tree row at all**, which are kind-P by construction and sit
outside that universe.  Widen the net and look again.
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

# One entry per (file, civ display name); `rec["obj"]` is the WHOLE file.
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

print("comparable civilizations: %d" % len(civs))
print()

report = {}
for stem, (disp, obj) in sorted(civs.items()):
    tree = trees[stem]
    # Buildings this civ's tree says it owns (a button needs a building).
    blds = {r.get("Node ID") for r in CT.rows_of(tree)
            if r.get("Use Type") == "Building"}
    # Every unit the panel lists for this civ, by building.
    listed = {}
    for b in sorted(BP.buildings(obj, disp) if False else []) or []:
        pass
    for b_id in range(0, 3000):
        us = BP.entries(obj, disp, b_id, BP.UNITS_KEY)
        if us:
            for e in us:
                listed[e.get("ID")] = (b_id, e.get("RequiredAge"))

    kind_p, kind_t = [], []
    tree_rows = {r.get("Node ID"): r for r in CT.unit_rows(tree)
                 if r.get("Node ID") is not None}
    for uid, (b_id, age) in sorted(listed.items()):
        row = tree_rows.get(uid)
        st = CT.node_status(tree, uid, CT.UNIT_USE_TYPES)
        if row is None and st is None:
            # The tree has NO row for this unit at all -> the tree supplies no
            # button; the panel does.  kind P by construction.
            if b_id in blds:
                kind_p.append(("no-row", uid, b_id, age))
        elif st == "NotAvailable":
            if b_id in blds:
                kind_p.append(("notavail", uid, b_id, age))
    for uid, row in sorted(tree_rows.items()):
        if row.get("Building ID") not in blds:
            continue
        if uid in listed:
            continue
        if CT.node_status(tree, uid, CT.UNIT_USE_TYPES) in (
                "ResearchedCompleted", "ResearchRequired"):
            kind_t.append((uid, row.get("Building ID"), row.get("Age ID"),
                           row.get("Node Status")))

    if kind_p or kind_t:
        report[stem] = (kind_p, kind_t)

print("civilizations with a kind-P set (panel lists, tree cannot supply):")
for stem, (p, t) in sorted(report.items()):
    if p:
        print("   %-13s P=%-3d T=%-3d" % (stem, len(p), len(t)))

print()
print("civilizations with a kind-T set (tree grants, panel silent):")
for stem, (p, t) in sorted(report.items()):
    if t:
        print("   %-13s P=%-3d T=%-3d" % (stem, len(p), len(t)))

print()
both = [(s, p, t) for s, (p, t) in sorted(report.items()) if p and t]
print("*** civilizations that are INJECTIVE in ONE game (both kinds): %d ***"
      % len(both))
for stem, p, t in both:
    print()
    print("  %s  -- tree stem %s" % (stem, stem))
    print("    kind P (panel lists, tree cannot supply) -> present means PANEL "
          "or UNION")
    for why, uid, b, age in p:
        print("       %-9s unit %-6s building %-5s RequiredAge %s"
              % (why, uid, b, age))
    print("    kind T (tree grants, panel silent) -> present means TREE or UNION")
    for uid, b, age, st in t:
        print("       unit %-6s building %-5s Age %s   (%s)" % (uid, b, age, st))
