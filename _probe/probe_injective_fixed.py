# -*- coding: utf-8 -*-
r"""Injective search, with the building-iteration bug fixed.

TWO bugs were found in the previous attempts, both of which silently produced an
empty result that read as a finding:

  1. `buildpanel.buildings(obj, key)` returns a list of building BLOCKS (dicts
     with an `ID` key), not a list of ids.  Iterating it and passing each element
     as `building_id` makes `building_block()` compare `blk["ID"] == <dict>`,
     which never matches -> `entries()` returns `[]` -> the panel looks empty for
     every civilization.
  2. The widened net ("panel lists it, tree has no row") admitted unit 320 for
     GEORGIANS, which is `ARROW8`, an engine-internal projectile with no display
     name.  A player can never see it, so it is not an observation subject.

This version iterates the blocks properly and requires every subject to be
VISIBLE (has a display name) and to have a DISTINCT name from its counterpart.
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


def name_of(uid):
    u = idx.get("unit", uid)
    return ((u.zh or u.en) if u else None) or None


def visible(uid):
    return name_of(uid) is not None


def bname(bid):
    for t in trees.values():
        for r in CT.rows_of(t):
            if r.get("Use Type") == "Building" and r.get("Node ID") == bid:
                sid = r.get("Name String ID")
                if sid and sid in ZH:
                    return ZH[sid]
    return "bldg %s" % bid


# --- panel listings, per civ, iterating BLOCKS (the fix) ---------------------
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

panel_by_civ = {}
for stem, (disp, obj) in civs.items():
    rows = {}
    for blk in BP.buildings(obj, disp):
        bid = blk.get("ID")
        for e in (blk.get(BP.UNITS_KEY) or []):
            rows.setdefault(e.get("ID"), []).append((bid, e.get("RequiredAge"),
                                                     e.get("Name")))
    panel_by_civ[stem] = rows

print("A  the fix changes the picture: panel units seen per civ")
for s in ("HUNS", "GEORGIANS", "SPARTANS", "SICILIANS", "JURCHENS", "BRITONS"):
    print("   %-11s %d units listed" % (s, len(panel_by_civ.get(s, {}))))
print()

kindP, kindT = {}, {}
for stem in sorted(civs):
    disp, obj = civs[stem]
    tree = trees[stem]
    owned = {r.get("Node ID") for r in CT.rows_of(tree)
             if r.get("Use Type") == "Building"}
    trows = {r.get("Node ID"): r for r in CT.unit_rows(tree)
             if r.get("Node ID") is not None}
    panel = panel_by_civ[stem]
    panel_ids = set(panel)
    P = []
    for uid, places in panel.items():
        if not visible(uid):
            continue
        for bid, age, nm in places:
            if bid not in owned:
                continue
            st = trows[uid].get("Node Status") if uid in trows else None
            if uid not in trows or st == "NotAvailable":
                P.append((uid, bid, age, nm, st or "(no tree row)"))
    T = []
    for uid, r in trows.items():
        if r.get("Node Status") != "ResearchedCompleted":
            continue
        if r.get("Building ID") not in owned:
            continue
        if uid in panel_ids:
            continue
        if not visible(uid):
            continue
        T.append((uid, r.get("Building ID"), r.get("Age ID"), r.get("Name")))
    if P:
        kindP[stem] = P
    if T:
        kindT[stem] = T

print("B  kind-P (panel lists a VISIBLE unit the tree cannot supply): %d civs"
      % len(kindP))
for s in sorted(kindP):
    print("   %-12s %s" % (s, [(u, n, a, bname(b)) for u, b, a, n, _ in kindP[s]]))

print()
print("C  kind-T (tree grants a VISIBLE unit, panel silent): %d civs" % len(kindT))
for s in sorted(kindT):
    print("   %-12s %s" % (s, [(u, n, a, bname(b)) for u, b, a, n in kindT[s]]))

print()
print("D  INJECTIVE in one game (both kinds present), names considered:")
n_any, n_clean = 0, 0
for s in sorted(set(kindP) & set(kindT)):
    pnames = {(n or "").lower() for _u, _b, _a, n, _st in kindP[s]}
    tnames = {(n or "").lower() for _u, _b, _a, n in kindT[s]}
    disjoint = pnames and tnames and not (pnames & tnames)
    n_any += 1
    if disjoint:
        n_clean += 1
    print("   %-12s  P=%s  T=%s   names disjoint: %s"
          % (s, sorted(pnames), sorted(tnames), disjoint))
print("   -> %d civs have both kinds; %d of them have DISJOINT subject names"
      % (n_any, n_clean))

print()
print("E  the two-game protocol (needs no single civ to be injective)")
print("   GAME 1  Jurchens   Castle Age  Barracks(12)  -> look for 长剑士(77)")
print("   GAME 2  Sicilians  Imperial Age SiegeWorkshop(49) -> look for 重型投石车(588)")
print("   1有 2无 -> PANEL   1无 2有 -> TREE   都有 -> UNION   都无 -> neither")
