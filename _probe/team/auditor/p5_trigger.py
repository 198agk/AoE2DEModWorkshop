# -*- coding: utf-8 -*-
"""Audit probe 5: is `Trigger Tech ID` a menu gate, and is subject A controlled?

If Trigger Tech ID is a gate that the civ must satisfy, then granting row 2550
into BRITONS (whose Trigger Tech 1350 no civ carries) plants an UNCONTROLLED
variable inside the "tree drives the menu" arm of the experiment.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import collections, json, os, sys
sys.path.insert(0, _HERE_PATH("..", "..", ".."))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import aoe2mod.api as A
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)

trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

head("5a: for every unit row carrying a Trigger Tech ID, does its own civ hold that tech?")
tot = 0
held = 0
by_type = collections.Counter()
missing_by_type = collections.Counter()
examples = []
for c in sorted(trees):
    for r in CT.unit_rows(trees[c]):
        tt = r.get("Trigger Tech ID")
        if tt is None:
            continue
        tot += 1
        nt = r.get("Node Type")
        by_type[nt] += 1
        st = CT.node_status(trees[c], tt, CT.TECH_USE_TYPES)
        if st is not None and st != "NotAvailable":
            held += 1
        else:
            missing_by_type[nt] += 1
            if len(examples) < 12:
                examples.append((c, r.get("Node ID"), nt, tt, st))
print("   unit rows with a Trigger Tech ID : %d" % tot)
print("   ... whose civ HOLDS that tech    : %d  (%.1f%%)"
      % (held, 100.0 * held / tot if tot else 0))
print("   by Node Type      : %s" % dict(by_type))
print("   MISSING by Node Type: %s" % dict(missing_by_type))
for e in examples:
    print("      %-10s unit %-5s %-13s TriggerTech=%-5s tree-status=%r" % e)

head("5b: tech 1350 -- where does it live at all?")
print("   as a TECH row in any CivTechTrees/*.json : %d of 62"
      % sum(1 for c in trees if CT.row_for(trees[c], 1350, CT.TECH_USE_TYPES)))
print("   as a UNIT row in any CivTechTrees/*.json : %d of 62"
      % sum(1 for c in trees if CT.row_for(trees[c], 1350, CT.UNIT_USE_TYPES)))
tk = A.open_toolkit(); tk._ensure()
data, civs, civs_start, gv, tail, how = tk._parsed
# look in the .dat for tech 1350 via the toolkit's tech accessor if any
print("   toolkit attrs: %s" % [a for a in dir(tk) if not a.startswith('__')])

head("5c: subject A's donor row vs. a row whose civ DOES hold its Trigger Tech")
brit = trees["BRITONS"]
print("   BRITONS Longbowman 8 :", json.dumps(
    CT.row_for(brit, 8, CT.UNIT_USE_TYPES), sort_keys=True))
print()
print("   donor 2550           :", json.dumps(
    CT.donor_row(trees, 2550, CT.UNIT_USE_TYPES)[1], sort_keys=True))

head("5d: does the PANEL carry a matching gate for 2550? (PrereqTech / extra keys)")
p, kb = BP.panel_path_for(GAME, "Britons")
obj = panels[kb]["obj"]
for c in ("Incas", "Britons"):
    ck = BP.civ_key_for(panels, c)
    bid, e = BP.find_entry(obj, ck, 2550, BP.UNITS_KEY)
    print("   %-8s find_entry -> bldg=%r entry=%r" % (c, bid, e))
# any entry anywhere with 2550 and extra keys?
allkeys = collections.Counter()
for ck in obj:
    for b in BP.buildings(obj, ck):
        for space in (BP.UNITS_KEY, BP.TECHS_KEY):
            for e2 in (b.get(space) or []):
                if e2.get("ID") == 2550:
                    allkeys[tuple(sorted(e2))] += 1
print("   key-shapes used by the 2550 panel entries: %s" % dict(allkeys))

head("5e: the 4 native civs -- tree row vs panel entry, full detail")
for c in ("INCAS", "MAPUCHE", "MUISCA", "TUPI"):
    r = CT.row_for(trees[c], 2550, CT.UNIT_USE_TYPES)
    ck = BP.civ_key_for(panels, c)
    bid, e = BP.find_entry(obj, ck, 2550, BP.UNITS_KEY)
    print("   %-8s tree TriggerTech=%-5s tree-status=%-20s panel bldg=%r entry=%r"
          % (c, r.get("Trigger Tech ID"), r.get("Node Status"), bid, e))
    print("            tree's OTHER age-1 bldg-12 units: %s"
          % [x.get("Node ID") for x in CT.unit_rows(trees[c])
             if x.get("Age ID") == 1 and x.get("Building ID") == 12])
