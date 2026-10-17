# -*- coding: utf-8 -*-
"""Audit probe 2: the gates on subject A, the alternatives for the menu source."""
import collections, json, os, sys
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import aoe2mod.api as A
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
STEM, CIV = "BRITONS", "Britons"


def p(*a):
    print(*a)


def head(t):
    p(); p("=" * 78); p(t); p("=" * 78)


tk = A.open_toolkit()
trees = CT.load_trees(GAME)
brit = trees[STEM]
panels = BP.load_all(GAME)
pkey = BP.panel_path_for(GAME, CIV)[1]
pobj = panels[pkey]["obj"]
kb = BP.civ_key_for(panels, CIV)

head("A-gate: `Trigger Tech ID` on the donor row for 2550, and is it in BRITONS?")
donor, dro = CT.donor_row(trees, 2550, CT.UNIT_USE_TYPES)
tt = dro.get("Trigger Tech ID")
p("  donor civ            : %s" % donor)
p("  donor Trigger Tech ID: %r" % tt)
p("  donor Node Type      : %r" % dro.get("Node Type"))
p("  donor keys           : %s" % sorted(dro))
if tt is not None:
    p("  BRITONS tree has tech %d as a TECH row? %r"
      % (tt, CT.row_for(brit, tt, CT.TECH_USE_TYPES) is not None))
    p("  BRITONS can_build tech %d (TECH space): %r"
      % (tt, CT.can_build(brit, tt, CT.TECH_USE_TYPES)))
    p("  BRITONS node_status tech %d           : %r"
      % (tt, CT.node_status(brit, tt, CT.TECH_USE_TYPES)))
    p("  INCAS   node_status tech %d           : %r"
      % (tt, CT.node_status(trees["INCAS"], tt, CT.TECH_USE_TYPES)))
    # how many civs even carry this tech row
    carriers = [c for c in sorted(trees)
                if CT.row_for(trees[c], tt, CT.TECH_USE_TYPES) is not None]
    p("  civs carrying tech %d in their tree   : %d  %s"
      % (tt, len(carriers), carriers))
    ready = [c for c in carriers
             if CT.node_status(trees[c], tt, CT.TECH_USE_TYPES) == "ResearchedCompleted"]
    p("  of those, ResearchedCompleted         : %d  %s" % (len(ready), ready))
    # and the same tech id as a unit row (namespace)
    p("  same id %d as a UNIT row for BRITONS  : %r"
      % (tt, CT.row_for(brit, tt, CT.UNIT_USE_TYPES)))

head("A-gate 2: every (civ) that has a RegionalUnit 2550 row -- do they all have the tech?")
for c in sorted(trees):
    r = CT.row_for(trees[c], 2550)
    if r is None:
        continue
    p("  %-10s TriggerTech=%r  tech row present=%r  status=%r"
      % (c, r.get("Trigger Tech ID"),
         CT.row_for(trees[c], r.get("Trigger Tech ID"), CT.TECH_USE_TYPES) is not None,
         CT.node_status(trees[c], r.get("Trigger Tech ID"), CT.TECH_USE_TYPES)))

head("A-gate 3: other RegionalUnit rows -- are they panel-listed for their own civ?")
tbl = collections.Counter()
for c in sorted(trees):
    for r in CT.unit_rows(trees[c]):
        if r.get("Node Type") != "RegionalUnit":
            continue
        nid = r.get("Node ID")
        ck = BP.civ_key_for(panels, c)
        listed = None
        if ck:
            listed = BP.find_entry(pobj if ck in pobj else {}, ck, nid, BP.UNITS_KEY)[1] is not None
        key = (r.get("Building ID") == 12, listed, r.get("Trigger Tech ID") is not None)
        tbl[key] += 1
p("  (barracks?, panel-listed-for-own-civ?, has TriggerTech?) -> count")
for k, v in sorted(tbl.items(), key=lambda kv: -kv[1]):
    p("      %-40s %d" % (k, v))

head("A-gate 4: the .dat unit 2550 -- is it a trainable unit at all?")
tk._ensure()
data, civs, civs_start, gv, tail, how = tk._parsed
import aoe2mod.parser as P
units = data.get("units") if isinstance(data, dict) else None
p("  data keys: %s" % (sorted(data)[:20] if isinstance(data, dict) else type(data)))
if units:
    for uid in (2550, 74, 83):
        u = next((x for x in units if x.get("id") == uid), None)
        if u is None:
            p("  unit %d NOT FOUND in .dat (n=%d units)" % (uid, len(units)))
            continue
        keys = sorted(u)
        p("  unit %-5d name=%-18r type=%-4s hp=%-6s"
          % (uid, u.get("name"), u.get("type"), u.get("hit_points")))
        p("        keys: %s" % keys)
        if "train_locations" in u:
            p("        train_locations: %r" % (u.get("train_locations"),))
        for f in ("enabled", "disabled", "creatable", "garrison", "language_dll_name"):
            if f in u:
                p("        %s=%r" % (f, u[f]))
    vills = [x for x in units if x.get("id") in (83, 293, 65)]
    for v in vills:
        p("  villager-ish unit %-5d name=%r hp=%r"
          % (v.get("id"), v.get("name"), v.get("hit_points")))
