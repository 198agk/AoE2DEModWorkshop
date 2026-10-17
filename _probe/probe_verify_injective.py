# -*- coding: utf-8 -*-
r"""Verify the injective candidates, case by case, against the shipped files.

Four civilizations appear to have BOTH kinds of contradiction on one screen:
GEORGIANS, HUNS, SPARTANS, TUPI.  Each was found by widening the net to panel
entries with NO tree row (the audit measured 1201 of 4323 such entries), so each
needs checking before it is trusted: a "no tree row" unit might be a genuine
kind-P, or an artifact of the tree recording it somewhere I am not looking.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
ZH = {}
kd = os.path.join(GAME, "resources", "zh", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        with open(os.path.join(kd, fn), "rb") as fh:
            for line in fh.read().decode("utf-8-sig", "replace").splitlines():
                k, _, v = line.strip().partition("\t")
                if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                    ZH.setdefault(int(k.strip()), v[1:-1])

idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)


def uname(uid):
    u = idx.get("unit", uid)
    return (u and (u.zh or u.en)) or ("unit %s" % uid)


def bname(bid):
    for t in trees.values():
        for r in CT.rows_of(t):
            if r.get("Use Type") == "Building" and r.get("Node ID") == bid:
                sid = r.get("Name String ID")
                if sid and sid in ZH:
                    return ZH[sid]
    return "building %s" % bid


CASES = [
    ("GEORGIANS", "Georgians", 49, 320, 588),
    ("HUNS", "Huns", 45, 532, None),
    ("SPARTANS", "Spartans", 2172, 2147, 13),
    ("TUPI", "Tupi", 101, 1570, 532),
]

for stem, disp, bld, p_uid, t_uid in CASES:
    tree = trees[stem]
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    print("=" * 76)
    print("%s   building %s = %s" % (stem, bld, bname(bld)))
    print("=" * 76)
    # Is this building one the civ's tree says it owns?
    owned = {r.get("Node ID") for r in CT.rows_of(tree)
             if r.get("Use Type") == "Building"}
    print("  the civ's tree lists building %s as its own: %s"
          % (bld, bld in owned))
    # The panel's full list for this building.
    print("  PANEL, building %s:" % bld)
    for e in (BP.entries(obj, disp, bld, BP.UNITS_KEY) or []):
        uid = e.get("ID")
        st = CT.node_status(tree, uid, CT.UNIT_USE_TYPES)
        row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
        print("     %-6s %-24s RequiredAge=%-3s  tree=%-18s tree row=%s"
              % (uid, e.get("Name"), e.get("RequiredAge"),
                 st if st else "(none)",
                 "yes" if row else "NO"))
    # The tree's full list for this building.
    print("  TREE, building %s:" % bld)
    for r in sorted(CT.unit_rows(tree), key=lambda r: r.get("Node ID") or 0):
        if r.get("Building ID") != bld:
            continue
        uid = r.get("Node ID")
        _b, e = BP.find_entry(obj, disp, uid, BP.UNITS_KEY)
        print("     %-6s %-24s NodeStatus=%-18s Age=%-3s panel=%s"
              % (uid, r.get("Name"), r.get("Node Status"), r.get("Age ID"),
                 "listed" if e else "SILENT"))
    # is the kind-P unit really absent from the tree ANYWHERE (any use type)?
    print("  kind-P unit %s (%s):" % (p_uid, uname(p_uid)))
    print("     node_status unit-space : %r" % CT.node_status(
        tree, p_uid, CT.UNIT_USE_TYPES))
    print("     node_status tech-space : %r" % CT.node_status(
        tree, p_uid, CT.TECH_USE_TYPES))
    print("     row_for any use type   : %r" % (CT.row_for(
        tree, p_uid, CT.UNIT_USE_TYPES),))
    print()
