# -*- coding: utf-8 -*-
r"""The SHIPPED disagreement: pairs where the two halves already contradict.

These need NO mod at all -- the user just opens the right civilization and looks.
That is cheaper and has fewer confounds than any mod-based test.

The join is the trap (paid for twice already):
  * the tree keys a civ by FILE STEM (`BRITONS`)
  * the panel keys it by DISPLAY NAME (`Britons`)
  * `civtechtrees.civ_file_stem()` is the bridge; using the stem as a panel key
    silently looks up a civilization that does not exist and returns None for
    every unit, which reads as "no disagreement anywhere".
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

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(game_root=GAME)
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

# Every unit id any civ's tree models -- the comparable universe.
NODES = sorted({r.get("Node ID") for t in trees.values()
                for r in CT.unit_rows(t) if r.get("Node ID") is not None})
# Which building does a unit live in, and at what age (from the tree rows).
INFO = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        nid = r.get("Node ID")
        if nid is None:
            continue
        INFO.setdefault(nid, (r.get("Building ID"), r.get("Age ID"),
                              r.get("Name")))

panel_only, tree_only = [], []
_counters = {"civs_seen": 0, "no_tree": 0, "nodes": len(NODES),
             "na_with_entry": 0, "rc_without_entry": 0}
# `load_all()` is keyed by CIV, and EACH value's `obj` is the WHOLE multi-civ
# file.  Iterating `panels.items()` and then every key inside each `obj` visits
# the same civilization once per civ record in that file -- 3,208 lookups for 56
# real civilizations, and every pair counted ~57 times.  Dedupe on
# (file, civ display name) so each civilization is examined exactly once.
seen = set()
for pkey, rec in sorted(panels.items()):
    obj = rec["obj"]
    for disp in sorted(k for k in obj if isinstance(k, str)):
        tag = (rec["path"], disp)
        if tag in seen:
            continue
        seen.add(tag)
        stem = CT.civ_file_stem(disp)
        tree = trees.get(stem)
        if tree is None:
            _counters["no_tree"] += 1
            continue
        _counters["civs_seen"] += 1
        # buildings this civ's tree says it has
        blds = {r.get("Node ID") for r in CT.rows_of(tree)
                if r.get("Use Type") == "Building"}
        for nid in NODES:
            st = CT.node_status(tree, nid, CT.UNIT_USE_TYPES)
            bb, ee = BP.find_entry(obj, disp, nid, BP.UNITS_KEY)
            if st == "NotAvailable" and ee is not None:
                _counters["na_with_entry"] += 1
                panel_only.append((stem, disp, nid, ee.get("Name"),
                                   ee.get("RequiredAge"), bb))
            elif (st == "ResearchedCompleted" and ee is None
                  and bb is None):
                _counters["rc_without_entry"] += 1
                bl, age, nm = INFO.get(nid, (None, None, None))
                if bl in blds:
                    tree_only.append((stem, disp, nid, nm, age, bl))

print("PANEL lists it, TREE says NotAvailable  (%d pairs)" % len(panel_only))
print("  a button here proves the PANEL is consulted -- the tree cannot supply it")
print("  %-14s %-6s %-22s %-5s %s" % ("civ", "unit", "name", "Age", "bldg"))
for s, d, n, nm, age, bb in panel_only:
    if age == 1:
        print("  %-14s %-6s %-22s %-5s %s   <- Dark Age, observable at once"
              % (s, n, nm, age, bb))
for s, d, n, nm, age, bb in panel_only:
    if age != 1:
        print("  %-14s %-6s %-22s %-5s %s" % (s, n, nm, age, bb))

print()
print("TREE grants it, PANEL does not list it  (%d pairs)" % len(tree_only))
print("  a MISSING button here would prove the PANEL drives the menu")
print("  %-14s %-6s %-22s %-5s %s" % ("civ", "unit", "name", "Age", "bldg"))
for s, d, n, nm, age, bb in tree_only[:30]:
    print("  %-14s %-6s %-22s %-5s %s" % (s, n, nm, age, bb))
print()
print("counts: panel-only %d / tree-only %d" % (len(panel_only), len(tree_only)))
print("counters: %s" % _counters)
