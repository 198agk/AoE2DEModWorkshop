# -*- coding: utf-8 -*-
"""Verify the auditor's fatal findings myself, then pick a better experiment.

Three claims to check:
  1. the Bundle mod's .dat is byte-identical to smoke5's .dat, so the positive
     control cannot attribute which mod loaded;
  2. both mods ship the same three engine paths with DIFFERENT content, so with
     both enabled no outcome can be attributed;
  3. subject B (Militia, 74) is masked: the TREE already grants it, so removing
     the panel entry cannot be observed.

Then: find the units where the two halves DISAGREE in the shipped data.  Those
need no mod at all and are a strictly cheaper experiment.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
LOCAL = os.path.join(ACC, "mods", "local")

PATHS = {
    "dat": "resources/_common/dat/empires2_x2_p1.dat",
    "panel": "resources/_common/dat/futuravailableunits.json",
    "tree": "resources/_common/dat/CivTechTrees/BRITONS.json",
}


def sha(p):
    if not os.path.isfile(p):
        return "(absent)"
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


print("1  the three engine paths, across the installed mods")
for tag, base in (("GAME", GAME),) + tuple(
        (d, os.path.join(LOCAL, d)) for d in sorted(os.listdir(LOCAL))
        if os.path.isdir(os.path.join(LOCAL, d))):
    row = []
    for k, rel in PATHS.items():
        p = os.path.join(base, *rel.split("/"))
        row.append("%s=%s" % (k, sha(p)))
    print("   %-52s %s" % (tag[:52], "  ".join(row)))

print()
print("2  is smoke5 registered in mod-status.json?")
st = json.loads(open(os.path.join(ACC, "mods", "mod-status.json"), "rb")
                .read().decode("utf-8-sig"), strict=False)
for m in st.get("Mods", []):
    print("   prio %-3s %-6s %s" % (m.get("Priority"), m.get("Enabled"),
                                    m.get("Path")))
print("   -> 'Smoke5' present in the list: %s"
      % any("Smoke5" in (m.get("Path") or "") for m in st.get("Mods", [])))

print()
print("3  is subject B (Militia 74) masked by the tree?  And who is NOT")
tk = A.open_toolkit()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
brit = trees["BRITONS"]
kb = BP.panel_path_for(GAME, "Britons")[1]
pobj = panels[kb]["obj"]
b, e = BP.find_entry(pobj, kb, 74, BP.UNITS_KEY)
st74 = CT.node_status(brit, 74, CT.UNIT_USE_TYPES)
print("   Britons: panel lists 74 at %r (%r);  tree status %r"
      % (b, e, st74))
print("   -> is the panel edit observable?  %s"
      % ("NO -- the tree grants it independently" if CT.can_build(brit, 74)
         else "yes"))

print()
print("4  units where the two halves DISAGREE, shipped, no mod needed")
unit_ids = sorted({r.get("Node ID") for t in trees.values()
                   for r in CT.unit_rows(t)})
bldg_of = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        if r.get("Building ID") is not None:
            bldg_of.setdefault(r.get("Node ID"), r.get("Building ID"))

clean_panel_only, clean_tree_only = [], []
for civ_key, tree in sorted(trees.items()):
    try:
        pk = BP.panel_path_for(GAME, civ_key)[1]
    except Exception:
        continue
    obj = panels[pk]["obj"]
    if civ_key not in obj:
        continue
    for nid in unit_ids:
        st = CT.node_status(tree, nid, CT.UNIT_USE_TYPES)
        _bb, ee = BP.find_entry(obj, civ_key, nid, BP.UNITS_KEY)
        if st is not None and st != "NotAvailable" and ee is None:
            clean_tree_only.append((civ_key, nid, st, bldg_of.get(nid)))
        if st == "NotAvailable" and ee is not None:
            clean_panel_only.append((civ_key, nid, ee.get("RequiredAge"),
                                     ee.get("Name"), bldg_of.get(nid)))

print("   TREE grants, PANEL does not list  (a visible button => TREE drives):")
for c, n, s, bl in clean_tree_only:
    print("     %-12s unit %-5s %-18s tree=%s bldg=%s"
          % (c, n, "", s, bl))
print("   PANEL lists, TREE says NotAvailable  (a visible button => PANEL drives):")
for c, n, age, nm, bl in clean_panel_only:
    print("     %-12s unit %-5s %-20s panel Age=%s bldg=%s"
          % (c, n, nm, age, bl))
print()
print("   counts: tree-only %d / panel-only %d"
      % (len(clean_tree_only), len(clean_panel_only)))
