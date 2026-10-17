# -*- coding: utf-8 -*-
"""Audit probe 20: the MASKING confound.
Subject B removes panel entry 74 from Britons. But the design itself REQUIRES
(build_smoke5.py:91) that Britons' TREE row for 74 reads ResearchedCompleted.
If the engine reads the tree at all, the tree independently grants 74 and the
remove-from-panel edit cannot make the button disappear. Measure how general
that is.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, sys, json
sys.path.insert(0, _HERE_PATH("..", "..", ".."))
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BLD = 12

def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)

trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

head("20a: Britons panel Units at bldg 12 -- does the TREE also grant each one?")
brit = trees["BRITONS"]
_t, po = BP.load_panel(os.path.join(GAME, BP.PANEL_REL))
kb = BP.civ_key_for(po, "Britons")
masked = 0
unmasked = 0
for b in BP.buildings(po, kb):
    if b.get("ID") != BLD:
        continue
    for e in (b.get("Units") or []):
        nid = e.get("ID")
        r = CT.row_for(brit, nid, CT.UNIT_USE_TYPES)
        st = r.get("Node Status") if r else None
        grants = CT.can_build(brit, nid)
        tag = "MASKED(tree grants too)" if grants else "clean(panel-only)"
        print("   %-5s %-24s tree=%-18s -> %s" % (nid, e.get("Name"), st, tag))
        if grants:
            masked += 1
        else:
            unmasked += 1
print("   => MASKED=%d  clean=%d" % (masked, unmasked))

head("20b: across all civs -- panel bldg-12 unit entries the tree ALSO grants")
tot_m = tot_c = 0
for pk, pv in panels.items():
    stem = CT.civ_file_stem(pk)
    t = trees.get(stem)
    if t is None:
        continue
    for b in BP.buildings(pv["obj"], pv["key"]):
        if b.get("ID") != BLD:
            continue
        for e in (b.get("Units") or []):
            nid = e.get("ID")
            if CT.row_for(t, nid, CT.UNIT_USE_TYPES) is None:
                tot_c += 1
                continue
            if CT.can_build(t, nid):
                tot_m += 1
            else:
                tot_c += 1
print("   MASKED (tree grants too, so a panel removal would NOT remove the button): %d" % tot_m)
print("   CLEAN  (tree absent or NotAvailable, so a panel removal is a real test):     %d" % tot_c)
if tot_m + tot_c:
    print("   => %.1f%% of panel bldg-12 unit entries are MASKED by their own tree row"
          % (100.0 * tot_m / (tot_m + tot_c)))

head("20c: is there ANY node the design could have used for a clean subject B?")
cands = []
for pk in ("Britons",):
    pv = panels[pk]
    stem = CT.civ_file_stem(pk)
    t = trees[stem]
    for b in BP.buildings(pv["obj"], pv["key"]):
        if b.get("ID") != BLD:
            continue
        for e in (b.get("Units") or []):
            nid = e.get("ID")
            r = CT.row_for(t, nid, CT.UNIT_USE_TYPES)
            if r is None or not CT.can_build(t, nid):
                cands.append((nid, e.get("Name"), e.get("RequiredAge"),
                              r.get("Node Status") if r else None))
print("   Britons bldg-12 panel units with a NON-granting/missing tree row: %d" % len(cands))
for c in cands:
    print("      %s" % (c,))

head("20d: the shipped NotAvailable-vs-panel contradictions, re-verified")
for stat in ("JURCHENS", "MUISCA"):
    t = trees.get(stat)
    for pk, pv in panels.items():
        if CT.civ_file_stem(pk) != stat:
            continue
        for b in BP.buildings(pv["obj"], pv["key"]):
            if b.get("ID") != BLD:
                continue
            for e in (b.get("Units") or []):
                r = CT.row_for(t, e.get("ID"), CT.UNIT_USE_TYPES)
                if r and not CT.can_build(t, e.get("ID")):
                    print("   %-9s panel lists %-5s %-24s bldg12 but TREE row = %s" % (
                        stat, e.get("ID"), e.get("Name"), r.get("Node Status")))
