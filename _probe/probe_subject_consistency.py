# -*- coding: utf-8 -*-
r"""Pick the GAME 1 subject properly: internal consistency of the panel's TWO channels.

Round 43 filtered the 11 kind-P subjects by "is the unit's upgrade tech in the
panel's `Techs` array?" and called the ones WITHOUT it "clean".  `probe_upgrade_gate`
shows that logic was BACKWARDS:

    JURCHENS barracks 12
      panel Units : 74, 75, 77, 93, 358, 359, 473, 567, 1901, 1903
      panel Techs : 197 Pikeman, 215 Squires, 222 Man-at-Arms, 429 Halberdier, ...

    unit 77 Long Swordsman  trigger tech 207  -> 207 is NOT in panel Techs

So for Jurchens the panel says "you can train Long Swordsman" while NOT offering the
research that produces it.  Under an engine that needs the research, BOTH hypotheses
predict "no Long Swordsman" and GAME 1 would prove nothing.

The subject that discriminates cleanly is one where the panel is INTERNALLY
CONSISTENT: the unit is in `Units` AND its upgrade tech IS in `Techs`.  Then the
panel asserts a complete path, the tree asserts `NotAvailable`, and the two readings
predict different outcomes.

Score every kind-P subject on that criterion, and report the whole upgrade chain.
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


# button_id chains, from the .dat
import aoe2mod.api as A                                    # noqa: E402
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
CHAIN = {}
for civ in (tk._parsed[1] or [])[1:3]:
    for u in civ.get("units") or []:
        uid = u.get("id")
        for t in (u.get("train_locations") or []):
            bid, bt = t.get("unit_id"), t.get("button_id")
            if bid is None or bid < 0 or bt is None:
                continue
            CHAIN.setdefault((bid, bt), set()).add(uid)

# find the kind-P pairs again
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

CASES = []
for stem, (disp, obj) in sorted(civs.items()):
    tree = trees[stem]
    own = {r.get("Node ID") for r in CT.rows_of(tree)
           if r.get("Use Type") == "Building"}
    for blk in BP.buildings(obj, disp):
        bid = blk.get("ID")
        if bid not in own:
            continue
        techs = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
        for e in (blk.get(BP.UNITS_KEY) or []):
            uid = e.get("ID")
            st = CT.node_status(tree, uid, CT.UNIT_USE_TYPES)
            if st != "NotAvailable":
                continue
            row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
            tt = (row or {}).get("Trigger Tech ID") if row else None
            u = idx.get("unit", uid)
            if u is None or not (u.zh or u.en):
                continue
            CASES.append((stem, disp, bid, uid, tt, tt in techs if tt else None,
                          e.get("RequiredAge"), e.get("Name")))

print("A  every kind-P subject, scored for internal consistency")
print("   %-11s %-6s %-20s %-6s %-9s %-8s %s"
      % ("civ", "unit", "name", "age", "upgTech", "in Techs", "building"))
consistent = []
for stem, disp, bid, uid, tt, ok, age, nm in CASES:
    flag = "YES" if ok else ("no tech" if tt is None else "NO")
    print("   %-11s %-6s %-20s %-6s %-9s %-8s %s"
          % (stem, uid, nm, age, tt, flag, bname(bid)))
    if ok:
        consistent.append((stem, disp, bid, uid, tt, age, nm))

print()
print("B  internally consistent kind-P subjects (the panel asserts a COMPLETE path)")
for stem, disp, bid, uid, tt, age, nm in consistent:
    print("   %-11s unit %-6s %-20s age %-4s upgTech %s (%s)  building %s"
          % (stem, uid, nm, age, tt, tname(tt), bname(bid)))

print()
print("C  for each consistent subject, the WHOLE chain at that building")
for stem, disp, bid, uid, tt, age, nm in consistent:
    tree = trees[stem]
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    units_at = set()
    techs_at = set()
    for blk in BP.buildings(obj, disp):
        if blk.get("ID") == bid:
            units_at = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
            techs_at = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
    print("   --- %s / %s / unit %s (%s) ---" % (stem, bname(bid), uid, nm))
    for (cb, cbt), members in sorted(CHAIN.items()):
        if cb != bid or uid not in members:
            continue
        for m in sorted(members):
            st = CT.node_status(tree, m, CT.UNIT_USE_TYPES)
            row = CT.row_for(tree, m, CT.UNIT_USE_TYPES)
            mtt = (row or {}).get("Trigger Tech ID")
            mu = idx.get("unit", m)
            print("        %-5s %-20s tree=%-18s panelUnits=%-7s trigTech=%-5s "
                  "panelTechs=%s"
                  % (m, ((mu.zh or mu.en) if mu else "?"),
                     st if st else "(none)", m in units_at, mtt,
                     (mtt in techs_at) if mtt else "n/a"))
    print("        panel Techs at building: %s"
          % [(t, tname(t)) for t in sorted(techs_at)])
