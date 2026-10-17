# -*- coding: utf-8 -*-
r"""FIND THE SUBJECTS THAT ARE ACTUALLY DECISIVE, both directions, full-path.

Round 43 scored kind-P subjects by "is the unit's upgrade tech in the panel's Techs?"
and marked the ones WITHOUT it as "clean".  `probe_upgrade_gate.py` and
`probe_subject_consistency.py` show that logic was **backwards**:

  JURCHENS 77 Long Swordsman  panel Units LISTS it, panel Techs LACKS 207 (its upgrade)
  MUISCA   359 Halberdier     panel Units LISTS it, panel Techs HAS  429 (its upgrade)

For the *inconsistent* one, if the engine requires the upgrade research to produce the
unit, then LONG SWORDSMAN IS UNREACHABLE whichever file the menu reads -> "absent"
proves nothing.  Only the *consistent* subject yields a decisive observation in both
outcomes.

The same standard must be applied to the kind-T side, whose "yes" layer is the TREE:
the tree must supply the unit AND its upgrade tech for "absent" to mean "the panel is
driving".

Score BOTH directions on full-path consistency and report the usable subjects.
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
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)

ZH = {}
kd = os.path.join(GAME, "resources", "zh", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        with open(os.path.join(kd, fn), "rb") as fh:
            for line in fh.read().decode("utf-8-sig", "replace").splitlines():
                k, _, v = line.strip().partition("\t")
                if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                    ZH.setdefault(int(k.strip()), v[1:-1])


def uname(uid):
    u = idx.get("unit", uid)
    return ((u.zh or u.en) if u else None) or ("unit %s" % uid)


def tname(tid):
    u = idx.get("tech", tid)
    return ((u.zh or u.en) if u else None) or ("tech %s" % tid)


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

# unit -> its upgrade tech (from any tree row that has one)
TRIG = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        u, tt = r.get("Node ID"), r.get("Trigger Tech ID")
        if u is not None and tt is not None:
            TRIG.setdefault(u, set()).add(tt)

P_OK, T_OK = [], []
for stem, (disp, obj) in sorted(civs.items()):
    tree = trees[stem]
    own = {r.get("Node ID") for r in CT.rows_of(tree)
           if r.get("Use Type") == "Building"}
    for blk in BP.buildings(obj, disp):
        bid = blk.get("ID")
        if bid not in own:
            continue
        units = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
        techs = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
        for uid in units:
            if CT.node_status(tree, uid, CT.UNIT_USE_TYPES) != "NotAvailable":
                continue
            if uname(uid) is None:
                continue
            row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
            tt = (row or {}).get("Trigger Tech ID")
            # kind-P is decisive only if the panel supplies a COMPLETE path
            complete = (tt is None) or (tt in techs)
            if not complete:
                continue
            ue = None
            for e in (blk.get(BP.UNITS_KEY) or []):
                if e.get("ID") == uid:
                    ue = e
            P_OK.append((stem, disp, bid, uid, tt, (ue or {}).get("RequiredAge"),
                         (ue or {}).get("Name")))

        # kind-T: tree ResearchedCompleted, panel silent in BOTH channels
        for r in CT.unit_rows(tree):
            uid = r.get("Node ID")
            if uid is None or r.get("Building ID") != bid:
                continue
            if r.get("Node Status") != "ResearchedCompleted":
                continue
            if uid in units or uname(uid) is None:
                continue
            tt = r.get("Trigger Tech ID")
            # decisive only if the TREE supplies a complete path (the tree is the
            # "yes" layer here), i.e. the upgrade tech exists in the tree too
            if tt is not None and CT.node_status(tree, tt,
                                                 CT.TECH_USE_TYPES) is None:
                continue
            T_OK.append((stem, disp, bid, uid, r.get("Age ID"),
                         r.get("Name"), tt))

print("=" * 78)
print("KIND-P, decisive (panel Units lists it AND its upgrade tech is in panel Techs)")
print("=" * 78)
print("   %-11s %-6s %-22s %-5s %-8s %s"
      % ("civ", "unit", "name", "age", "upgTech", "building"))
for stem, disp, bid, uid, tt, age, nm in P_OK:
    print("   %-11s %-6s %-22s %-5s %-8s %s"
          % (stem, uid, nm, age, tt, bname(bid)))
print("   count: %d" % len(P_OK))

print()
print("=" * 78)
print("KIND-T, decisive (tree grants it, panel silent in BOTH, tree has its upgrade)")
print("=" * 78)
print("   %-11s %-6s %-22s %-5s %-8s %s"
      % ("civ", "unit", "name", "age", "upgTech", "building"))
for stem, disp, bid, uid, age, nm, tt in T_OK:
    print("   %-11s %-6s %-22s %-5s %-8s %s"
          % (stem, uid, nm, age, tt, bname(bid)))
print("   count: %d" % len(T_OK))

print()
print("=" * 78)
print("BEST PAIR for the two-game protocol")
print("=" * 78)
# prefer the lowest age and a subject whose name is distinctive
P_OK.sort(key=lambda r: (r[5] or 9, r[0]))
T_OK.sort(key=lambda r: (r[4] or 9, r[0]))
if P_OK:
    stem, disp, bid, uid, tt, age, nm = P_OK[0]
    print("  GAME 1 (panel asserts a COMPLETE path, tree says NotAvailable)")
    print("     civ %s (%s)  building %s  unit %s %s  age %s"
          % (disp, stem, bname(bid), uid, nm, age))
    print("     panel: Units lists %s AND Techs lists %s (%s)"
          % (uid, tt, tname(tt) if tt else "-"))
    print("     present -> the menu read the PANEL ; absent -> it did not")
if T_OK:
    stem, disp, bid, uid, age, nm, tt = T_OK[0]
    print("  GAME 2 (tree grants AND supplies the upgrade, panel silent both ways)")
    print("     civ %s (%s)  building %s  unit %s %s  age %s"
          % (disp, stem, bname(bid), uid, nm, age))
    print("     present -> the menu read the TREE ; absent -> it read the PANEL")
print()
print("  both present -> union ; both absent -> neither")
