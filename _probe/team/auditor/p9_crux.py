# -*- coding: utf-8 -*-
"""Audit probe 9 -- THE CRUX.

Do the shipped files already contain instances of the two manipulations?

  A-direction ("tree has it, panel does not")  : shipped instance => tree-only would already be observable
  B-direction ("panel lists it, tree says NotAvailable / row missing") : shipped instance => panel can
                                                override a disabled tree row => panel drives at least the display

Also: is `panel` a subset of `tree` everywhere (that would prove the panel cannot be the sole source)?
Also: what gates does the granted 2550 row carry, and is it unique in Britons' tree?
"""
import json, os, sys, collections
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
D = os.path.join(GAME, "resources", "_common", "dat")


def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)


trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
print("trees=%d panels=%d" % (len(trees), len(panels)))

head("9a: panel entry key shapes, all civs / all buildings")
shapes = collections.Counter()
for ck, p in panels.items():
    for b in BP.buildings(p["obj"], p["key"]):
        for space in (BP.UNITS_KEY, BP.TECHS_KEY):
            for e in BP.entries(p["obj"], p["key"], b.get("ID"), space):
                if isinstance(e, dict):
                    shapes[(space, tuple(sorted(e)))] += 1
for k, v in sorted(shapes.items(), key=lambda x: -x[1]):
    print("   %-8s %-42s %d" % (k[0], k[1], v))

head("9b: panel UNITS entries whose tree row is missing or not ResearchedCompleted")
rows = []
for ck, p in panels.items():
    tree = trees.get(ck)
    if tree is None:
        continue
    for b in BP.buildings(p["obj"], p["key"]):
        bid = b.get("ID")
        for e in BP.entries(p["obj"], p["key"], bid, BP.UNITS_KEY):
            nid = e.get("ID")
            row = CT.row_for(tree, nid, CT.UNIT_USE_TYPES) if tree else None
            st = None if row is None else row.get("Node Status")
            if st != "ResearchedCompleted":
                rows.append((ck, bid, nid, e.get("Name"), e.get("RequiredAge"),
                             None if row is None else row.get("Node Status"),
                             None if row is None else row.get("Age ID"),
                             None if row is None else row.get("Building ID"),
                             None if row is None else row.get("Node Type")))
print("   total disagreements: %d" % len(rows))
print("   %-12s %-5s %-6s %-26s %-5s %-20s %-5s %-5s %s" % ("civ", "bldg", "id", "panel Name", "ReqA", "tree Status", "AgeT", "BldT", "NodeType"))
for r in rows:
    print("   %-12s %-5s %-6s %-26s %-5s %-20s %-5s %-5s %s" % r)

head("9c: same, restricted to the Dark-Age Barracks (bldg 12, RequiredAge 1)")
for r in rows:
    if r[1] == 12 and r[4] == 1:
        print("   %-12s %-5s %-6s %-26s ReqA=%s treeStatus=%r treeAge=%r treeBldg=%r nodeType=%r" % r)

head("9d: tree rows at bldg 12 that the civ's panel does NOT list (the A direction)")
miss = []
for ck, tree in trees.items():
    p = panels.get(ck)
    if p is None:
        continue
    for row in (tree.get("Units") or []):
        if not isinstance(row, dict):
            continue
        if row.get("Building ID") != 12:
            continue
        nid = row.get("Node ID")
        bid_, _ = BP.find_entry(p["obj"], p["key"], nid, BP.UNITS_KEY)
        if bid_ != 12:
            miss.append((ck, nid, row.get("Name"), row.get("Age ID"), row.get("Node Status"),
                         row.get("Node Type"), bid_))
print("   shipped (civ, unit) with tree bldg-12 row but panel has it elsewhere/not at all: %d" % len(miss))
print("   %-12s %-6s %-24s %-5s %-20s %-14s %s" % ("civ", "id", "name", "age", "status", "nodeType", "panelBldg"))
for m in miss[:60]:
    print("   %-12s %-6s %-24s %-5s %-20s %-14s %s" % m)
print("   ... by age:", dict(collections.Counter(m[3] for m in miss)))
print("   ... by status:", dict(collections.Counter(m[4] for m in miss)))

head("9e: the granted 2550 row's gate fields, vs every other Britons bldg-12 tree row")
brit = trees["BRITONS"]
print("   Britons bldg-12 tree rows:")
for row in (brit.get("Units") or []):
    if isinstance(row, dict) and row.get("Building ID") == 12:
        print("     id=%-6s age=%-2s status=%-20s type=%-14s trig=%-6s link=%-12s draw=%s" % (
            row.get("Node ID"), row.get("Age ID"), row.get("Node Status"), row.get("Node Type"),
            row.get("Trigger Tech ID"), row.get("Link Node Type"), row.get("Draw Node Type")))
print("   Britons tree Node Type histogram:", dict(collections.Counter(
    r.get("Node Type") for r in (brit.get("Units") or []) if isinstance(r, dict))))
dro = CT.donor_row(trees, 2550, CT.UNIT_USE_TYPES)[1]
print("   donor row to be copied:", json.dumps(dro, ensure_ascii=False))
edited = json.loads(json.dumps(brit, ensure_ascii=False)); edited.pop("path", None)
CT.grant(edited, 2550, dro)
print("   after grant, Node Type histogram:", dict(collections.Counter(
    r.get("Node Type") for r in (edited.get("Units") or []) if isinstance(r, dict))))
print("   after grant, bldg-12 Age-1 rows:",
      [(r.get("Node ID"), r.get("Node Type")) for r in edited["Units"]
       if isinstance(r, dict) and r.get("Building ID") == 12 and r.get("Age ID") == 1])

head("9f: is the panel a SUBSET of the tree? (would prove panel cannot be sole source)")
tot = bad = 0
for ck, p in panels.items():
    tree = trees.get(ck)
    for b in BP.buildings(p["obj"], p["key"]):
        bid = b.get("ID")
        for e in BP.entries(p["obj"], p["key"], bid, BP.UNITS_KEY):
            tot += 1
            row = CT.row_for(tree, e.get("ID"), CT.UNIT_USE_TYPES) if tree else None
            if row is None:
                bad += 1
print("   panel unit entries=%d ; with NO tree row at all=%d" % (tot, bad))

head("9g: Distinct unit ids the panel lists anywhere but NO civ's tree has as a UNIT row")
alltree_ids = set()
for ck, tree in trees.items():
    for row in (tree.get("Units") or []):
        if isinstance(row, dict):
            alltree_ids.add(row.get("Node ID"))
panel_ids = set()
for ck, p in panels.items():
    for b in BP.buildings(p["obj"], p["key"]):
        for e in BP.entries(p["obj"], p["key"], b.get("ID"), BP.UNITS_KEY):
            panel_ids.add(e.get("ID"))
print("   distinct panel unit ids=%d  distinct tree unit ids=%d" % (len(panel_ids), len(alltree_ids)))
print("   panel-only ids (in no tree at all):", sorted(panel_ids - alltree_ids)[:40])
