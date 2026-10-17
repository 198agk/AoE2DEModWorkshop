# -*- coding: utf-8 -*-
r"""Is the panel's `Units` array "you can build it", or just "the chain lives here"?

`probe_upgrade_gate.py` found an internal inconsistency that could break GAME 1:

    JURCHENS barracks 12
      panel Units : 74, 75, 77, 93, 358, 359, 473, 567, 1901, 1903
      panel Techs : 197, 215, 222, 429, 602, 875, 982

    unit 75 Man-at-Arms      tree RC          panel Units listed   upgTech 222  panel Techs HAS it
    unit 77 Long Swordsman   tree NotAvailable panel Units listed  upgTech 207  panel Techs DOES NOT
    unit 473 Two-Handed      tree NotAvailable panel Units listed  upgTech 217  panel Techs DOES NOT

So the panel names Long Swordsman in `Units` while NOT offering the research that
produces it.  Two readings:

  (a) `Units` means "trainable"  -> the panel is internally inconsistent, and a
      Jurchens Long Swordsman button might be gated by the missing research anyway,
      so GAME 1's outcome would be uninterpretable.
  (b) `Units` means "this building trains this chain, upgrades gate it" -> then
      listing all five militia units is CORRECT and expected, and the kind-P
      "disagreement" is not a disagreement about availability at all.

(b) would mean the two-game protocol is measuring the wrong thing.  Measure which
reading holds, across every civilization and every building.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

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

# For every (unit, building) the .dat trains, ask: if the unit has an upgrade tech
# and is listed in the panel's Units here, is that tech in the panel's Techs here?
from aoe2mod.semantic.index import index as sem_index       # noqa: E402
idx = sem_index()

print("A  the .dat's Trigger Tech per unit (from any civ's tree rows)")
TRIG = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        u, tt = r.get("Node ID"), r.get("Trigger Tech ID")
        if u is not None and tt is not None:
            TRIG.setdefault(u, set()).add(tt)
print("   units with an upgrade tech: %d" % len(TRIG))
for u in (74, 75, 77, 473, 567, 93, 358, 359, 279, 280, 550, 588):
    print("      unit %-6s trigTech=%s" % (u, sorted(TRIG.get(u, ()))))

print()
print("B  panel internal consistency, per (civ, building, unit)")
agree = disagree = notrig = 0
rows = []
for stem, (disp, obj) in sorted(civs.items()):
    for blk in BP.buildings(obj, disp):
        bid = blk.get("ID")
        units = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
        techs = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
        for uid in units:
            tt = TRIG.get(uid)
            if not tt:
                notrig += 1
                continue
            if tt & techs:
                agree += 1
            else:
                disagree += 1
                rows.append((stem, bid, uid, sorted(tt)))
print("   unit listed in Units AND its upgrade tech IS in Techs : %d" % agree)
print("   unit listed in Units but upgrade tech NOT in Techs     : %d" % disagree)
print("   unit listed in Units with no upgrade tech at all       : %d" % notrig)

print()
print("C  the disagreements -- is it systematic?")
byu = Counter(r[2] for r in rows)
print("   distinct units involved: %d" % len(byu))
for uid, n in byu.most_common(20):
    u = idx.get("unit", uid)
    print("      unit %-6s %-24s in %d (civ,bldg) pairs   trigTech=%s"
          % (uid, ((u.zh or u.en) if u else "?"), n, sorted(TRIG.get(uid, ()))))

print()
print("D  the specific GAME 1 question: JURCHENS barracks, is 207 anywhere?")
jt = trees["JURCHENS"]
for tid in (207, 217, 264, 222):
    st = CT.node_status(jt, tid, CT.TECH_USE_TYPES)
    row = CT.row_for(jt, tid, CT.TECH_USE_TYPES)
    print("   tech %-5s in Jurchens' tree: status=%-18s row=%s"
          % (tid, st, "yes" if row else "NO"))
print("   (a missing TREe tech row matters only if the tree drives the menu;")
print("    the panel is a separate file and may say something else)")
