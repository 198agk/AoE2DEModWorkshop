# -*- coding: utf-8 -*-
r"""Widen the kind-P class: does the panel list units the tree has NO ROW for?

The zero-mod experiment has been restricted to the 11 shipped pairs where the tree
says `NotAvailable` AND the panel lists the unit.  But the tree can also say "no"
by carrying **no row at all**:

    no tree row   == the civ's tech tree does not contain it
    panel lists it == the menu (if panel-driven) would offer it

That is the same logical disagreement, and it should be a much LARGER class --
including civilizations that shipped with the base game, which matters because all
four complete-path subjects found so far sit on DLC civilizations a player may not
own.

For each candidate, apply the corrected completeness test:
  * the unit must be listed in the panel's `Units` for a building the civ owns;
  * if the unit has a `Trigger Tech ID` anywhere in the corpus, the panel must also
    list that research in the same building's `Techs` (otherwise the panel promises
    a unit whose research it does not offer -> unreachable either way -> useless);
  * the unit must have a display name;
  * the subject must be restricted to an age the user can reach.
"""
import os
import sys
from collections import Counter, defaultdict

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


def named(uid):
    u = idx.get("unit", uid)
    return (u.zh or u.en) if u else None


# unit -> its upgrade tech, from ANY tree row in the corpus
TRIG = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        u, tt = r.get("Node ID"), r.get("Trigger Tech ID")
        if u is not None and tt is not None:
            TRIG.setdefault(u, set()).add(tt)

print("A  unit -> Trigger Tech ID map: %d units" % len(TRIG))

rows = []
for stem, tree in sorted(trees.items()):
    disp = None
    for d in sorted(panels):
        if CT.civ_file_stem(d) == stem:
            disp = d
            break
    if disp is None:
        continue
    path_key = BP.panel_path_for(GAME, disp)
    obj = panels[path_key[1]]["obj"]
    own = {r.get("Node ID") for r in CT.rows_of(tree)
           if r.get("Use Type") == "Building"}
    listed = defaultdict(set)      # building -> unit ids
    techs = defaultdict(set)       # building -> tech ids
    ages = {}
    for blk in BP.buildings(obj, disp):
        bid = blk.get("ID")
        if bid not in own:
            continue
        for e in (blk.get(BP.UNITS_KEY) or []):
            listed[bid].add(e.get("ID"))
            ages[(bid, e.get("ID"))] = e.get("RequiredAge")
        for e in (blk.get(BP.TECHS_KEY) or []):
            techs[bid].add(e.get("ID"))
    for bid, uids in listed.items():
        for uid in uids:
            if CT.row_for(tree, uid, CT.UNIT_USE_TYPES) is not None:
                continue                       # tree HAS a row -> not this class
            nm = named(uid)
            if not nm:
                continue
            tts = TRIG.get(uid) or set()
            # completeness: if the unit is produced by a research anywhere, the
            # panel must offer that research at this building too
            complete = (not tts) or bool(tts & techs[bid])
            rows.append({
                "stem": stem, "disp": disp, "bid": bid, "uid": uid, "name": nm,
                "age": ages.get((bid, uid)), "trig": sorted(tts),
                "complete": complete,
            })

print("B  panel-lists / tree-has-NO-row disagreements: %d" % len(rows))
print("   age distribution : %s" % Counter(r["age"] for r in rows))
print("   complete paths   : %d" % sum(1 for r in rows if r["complete"]))

print()
print("C  complete-path subjects at Age 1 or 2 (reachable early, no Imperial)")
early = [r for r in rows if r["complete"] and (r["age"] or 9) <= 2]
early.sort(key=lambda r: (r["age"] or 9, r["stem"], r["uid"]))
print("   count: %d" % len(early))
for r in early[:40]:
    print("      %-13s bldg %-5s unit %-6s age %-4s %-26s trig=%s"
          % (r["stem"], r["bid"], r["uid"], r["age"], r["name"], r["trig"]))

print()
print("D  which civilizations contribute complete-path subjects at all?")
byciv = Counter(r["stem"] for r in rows if r["complete"])
print("   %d civilizations" % len(byciv))
for stem, n in byciv.most_common(30):
    print("      %-13s %d" % (stem, n))

print()
print("E  the two candidate replacement subjects, checked in full")
for want in ("MUISCA", "POLES", "WU", "MAPUCHE"):
    for r in rows:
        if r["stem"] == want and r["complete"]:
            print("      %-13s bldg %-5s unit %-6s age %-4s %s"
                  % (r["stem"], r["bid"], r["uid"], r["age"], r["name"]))
            break
