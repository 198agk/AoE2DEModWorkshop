# -*- coding: utf-8 -*-
r"""Redo the injective search with UNNAMED units filtered out.

The widened net ("panel lists it and the tree has no row") picked up unit 320 for
GEORGIANS -- which turns out to be `ARROW8`, an engine-internal projectile with no
display name at all (zh=None, en=None).  A player can never see it, so it cannot
be an observation subject, and its presence made GEORGIANS look injective when it
is not.

This is the same lesson as the `None`-that-flows-into-the-verdict: an internal
object passed silently into a candidate list and would have been reported as a
subject to look for.

Filter: the unit must have a display name (`Entity.is_visible`).
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
idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

ZH = {}
kd = os.path.join(GAME, "resources", "zh", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        with open(os.path.join(kd, fn), "rb") as fh:
            for line in fh.read().decode("utf-8-sig", "replace").splitlines():
                k, _, v = line.strip().partition("\t")
                if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                    ZH.setdefault(int(k.strip()), v[1:-1])


def visible(uid):
    """Does a player ever see this unit by name?  Internal objects do not count."""
    u = idx.get("unit", uid)
    if u is None:
        return False
    return bool(u.zh or u.en)


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
    return "bldg %s" % bid


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

print("A  the false positives the visibility filter removes")
for stem, disp in (("GEORGIANS", "Georgians"), ("SPARTANS", "Spartans")):
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    for b_id in BP.buildings(obj, disp) or []:
        for e in (BP.entries(obj, disp, b_id, BP.UNITS_KEY) or []):
            uid = e.get("ID")
            if not visible(uid):
                print("   %-11s unit %-6s name=%-18s building %-5s  NOT VISIBLE"
                      % (stem, uid, e.get("Name"), b_id))
print()

kindP, kindT = {}, {}
for stem, (disp, obj) in sorted(civs.items()):
    tree = trees[stem]
    owned = {r.get("Node ID") for r in CT.rows_of(tree)
             if r.get("Use Type") == "Building"}
    rows = {r.get("Node ID"): r for r in CT.unit_rows(tree)
            if r.get("Node ID") is not None}
    panel_rows, panel_ids = {}, set()
    for b_id in BP.buildings(obj, disp) or []:
        for e in (BP.entries(obj, disp, b_id, BP.UNITS_KEY) or []):
            panel_ids.add(e.get("ID"))
            panel_rows[e.get("ID")] = (b_id, e.get("RequiredAge"), e.get("Name"))
    P = [(uid, b, age, nm) for uid, (b, age, nm) in panel_rows.items()
         if visible(uid) and b in owned
         and (uid not in rows or rows[uid].get("Node Status") == "NotAvailable")]
    T = [(uid, r.get("Building ID"), r.get("Age ID"), r.get("Name"))
         for uid, r in rows.items()
         if r.get("Node Status") == "ResearchedCompleted"
         and r.get("Building ID") in owned and uid not in panel_ids
         and visible(uid)]
    if P:
        kindP[stem] = P
    if T:
        kindT[stem] = T

print("B  kind-P (panel lists a VISIBLE unit the tree cannot supply):")
for s, v in sorted(kindP.items()):
    print("   %-12s %s" % (s, [(u, n, a, bname(b)) for u, b, a, n in v]))

print()
print("C  kind-T (tree grants a VISIBLE unit, panel silent):")
for s, v in sorted(kindT.items()):
    print("   %-12s %s" % (s, [(u, n, a, bname(b)) for u, b, a, n in v]))

print()
print("D  injective in ONE game (both kinds, VISIBLE subjects):")
both = sorted(set(kindP) & set(kindT))
for s in both:
    print("   %-12s  P=%s   T=%s" % (s, kindP[s], kindT[s]))
print("   -> %d" % len(both))

print()
print("E  the two-game protocol (each half individually clean)")
print("   GAME 1  Jurchens   Castle Age  Barracks(12)   look for 长剑士(77)")
print("      tree=NotAvailable, panel lists RequiredAge 3")
print("   GAME 2  Sicilians  Imperial Age SiegeWorkshop(49) look for 重型投石车(588)")
print("      tree=ResearchedCompleted, panel SILENT")
print()
print("   1有 2无 -> PANEL   1无 2有 -> TREE   都有 -> UNION   都无 -> neither")
