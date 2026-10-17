# -*- coding: utf-8 -*-
r"""PIN: a subject is decisive only if the "yes" layer supplies a COMPLETE path.

Round 43 scored the kind-P subjects by "is the unit's upgrade tech in the panel's
`Techs` array?" and marked the ones WITHOUT it as "clean".  That was **backwards**,
and it produced the recommended GAME 1 subject (JURCHENS 77 Long Swordsman):

    JURCHENS barracks 12
      panel Units : 74, 75, 77, 93, 358, 359, 473, 567, 1901, 1903
      panel Techs : 197 Pikeman, 215 Squires, 222 Man-at-Arms, 429 Halberdier, ...

    77 Long Swordsman's upgrade tech is 207 and 207 is NOT in panel Techs.

So the panel names Long Swordsman while not offering the research that produces it.
If the engine requires the research, **Long Swordsman is unreachable whichever file
the menu reads**, and "no Long Swordsman" would be indistinguishable from "the menu
reads the tree".  GAME 1 as recommended could not have worked.

The decisive kind-P subject is one where the panel supplies BOTH the unit and its
upgrade tech (and, for a chain, its predecessors).  Only 4 qualify:

    MAPUCHE  528 Heavy Demolition Ship  (panel Units 528 + panel Techs 244)
    MUISCA   359 Halberdier             (panel Units 359 + panel Techs 429)
    POLES    691 Elite Cannon Galleon   (panel Units 691 + panel Techs 376)
    WU       474 Heavy Cavalry Archer   (panel Units 474 + panel Techs 218)

And the kind-T side needs the mirror check: the TREE must grant the unit AND supply
its upgrade, so that "absent" means "the panel is driving":

    SICILIANS  588 Siege Onager   <- recommended GAME 2

This pins the corrected criterion, so the mistake cannot come back.

Run:  $env:PYTHONPATH='D:\\Software\\DeepSeek Harness\\工作区2'; python _probe\test_decisive_subjects.py
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
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)


def named(uid):
    u = idx.get("unit", uid)
    return bool(u and (u.zh or u.en))


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

TRIG = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        u, tt = r.get("Node ID"), r.get("Trigger Tech ID")
        if u is not None and tt is not None:
            TRIG.setdefault(u, set()).add(tt)

complete, incomplete = [], []
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
            if not named(uid):
                continue
            row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
            tt = (row or {}).get("Trigger Tech ID")
            (complete if (tt is None or tt in techs) else incomplete).append(
                (stem, bid, uid, tt))

print("A  the correction: 'upgrade tech absent' means UNUSABLE, not clean")
print("     complete-path kind-P subjects : %d" % len(complete))
print("     incomplete-path (unusable)    : %d" % len(incomplete))
for stem, bid, uid, tt in sorted(incomplete):
    print("        %-11s unit %-6s building %-5s upgrade tech %s absent"
          % (stem, uid, bid, tt))
check("the previously-recommended JURCHENS 77 is INCOMPLETE (present but unusable)",
      any(s == "JURCHENS" and u == 77 for s, _b, u, _t in incomplete),
      "incomplete = %s" % sorted(incomplete))
check("the complete-path set is exactly the 4 measured subjects",
      sorted((s, u) for s, _b, u, _t in complete)
      == [("MAPUCHE", 528), ("MUISCA", 359), ("POLES", 691), ("WU", 474)],
      "complete = %s" % sorted((s, u) for s, _b, u, _t in complete))

print()
print("B  the kind-T mirror check: the TREE must supply the upgrade too")
t_ok = []
for stem, (disp, obj) in sorted(civs.items()):
    tree = trees[stem]
    own = {r.get("Node ID") for r in CT.rows_of(tree)
           if r.get("Use Type") == "Building"}
    units_all, techs_all = set(), set()
    for blk in BP.buildings(obj, disp):
        for e in (blk.get(BP.UNITS_KEY) or []):
            units_all.add(e.get("ID"))
        for e in (blk.get(BP.TECHS_KEY) or []):
            techs_all.add(e.get("ID"))
    for r in CT.unit_rows(tree):
        uid = r.get("Node ID")
        if (uid is None or r.get("Building ID") not in own
                or r.get("Node Status") != "ResearchedCompleted"
                or uid in units_all or not named(uid)):
            continue
        tt = r.get("Trigger Tech ID")
        if tt is not None and tt in techs_all:
            continue        # the panel actually names it -> not silent
        t_ok.append((stem, uid, r.get("Building ID"), tt))
print("     decisive kind-T subjects: %s" % sorted((s, u) for s, u, _b, _t in t_ok))
check("SICILIANS 588 is a decisive kind-T subject",
      any(s == "SICILIANS" and u == 588 for s, u, _b, _t in t_ok),
      "kind-T = %s" % sorted((s, u) for s, u, _b, _t in t_ok))
check("SPARTANS 13 remains but its name collides with the kind-P 2147, so it is "
      "not usable as a distinct subject",
      any(s == "SPARTANS" and u == 13 for s, u, _b, _t in t_ok))

print()
print("C  the corrected two-game protocol")
check("GAME 1 subject is MUISCA 359 (panel complete path, tree NotAvailable)",
      any(s == "MUISCA" and u == 359 for s, _b, u, _t in complete))
check("GAME 2 subject is SICILIANS 588 (tree ResearchedCompleted, panel silent "
      "in both channels)", any(s == "SICILIANS" and u == 588
                               for s, u, _b, _t in t_ok))
for stem, bid, uid, tt in complete:
    if stem == "MUISCA" and uid == 359:
        print("        Muisca  building %s  unit 359 Halberdier  upgrade %s"
              % (bid, tt))
print()
print("DECISIVE SUBJECTS: only a subject whose 'yes' layer supplies a COMPLETE")
print("  path can distinguish the hypotheses.  The earlier recommendation was")
print("  scored the wrong way round.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
