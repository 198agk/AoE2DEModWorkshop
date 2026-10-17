# -*- coding: utf-8 -*-
r"""Symmetry check: does the kind-P subject (Jurchens 77) carry a hidden channel too?

The two-channel rule removed GEORGIANS from kind-T.  The same rule must be applied
to the kind-P subject, or the protocol has been checked on one side only.

For JURCHENS unit 77: the panel lists it in `Units` at building 12, and the tree
row carries `Trigger Tech ID = 207`.  If the panel ALSO lists 207 in that
building's `Techs`, then the panel is saying "research 207, then build 77" -- the
button may legitimately be gated, and "absent" would again be evidence about a
gate rather than about which file drives the menu.

The important difference, and the reason kind-P survives: `Trigger Tech ID` is a
COMMON row field but not a universal one -- measured 1,894 of 3,686 shipped unit
rows carry one (51.4%).  The first draft of this docstring asserted "2,667 of
2,673 rows carry one", a number copied from the panel-entry agreement figure
rather than measured here; the measurement above is the real one.  **A number in
a comment is a claim and has to come from a measurement in the same file.**
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


def tname(tid):
    u = idx.get("tech", tid)
    return ((u.zh or u.en) if u else None) or ("tech %s" % tid)


print("A  is Trigger Tech ID universal?  (if yes it cannot be a gate)")
tot = with_tt = 0
for t in trees.values():
    for r in CT.unit_rows(t):
        tot += 1
        if r.get("Trigger Tech ID") is not None:
            with_tt += 1
print("   unit rows: %d   with Trigger Tech ID: %d  (%.1f%%)"
      % (tot, with_tt, 100.0 * with_tt / max(tot, 1)))

print()
print("B  JURCHENS building 12, BOTH channels as the panel has them")
obj = panels[BP.panel_path_for(GAME, "Jurchens")[1]]["obj"]
for blk in BP.buildings(obj, "Jurchens"):
    if blk.get("ID") != 12:
        continue
    us = blk.get(BP.UNITS_KEY) or []
    ts = blk.get(BP.TECHS_KEY) or []
    print("   Units (%d): %s" % (len(us), [(e.get("ID"), e.get("Name")) for e in us]))
    print("   Techs (%d): %s" % (len(ts), [(e.get("ID"), e.get("Name")) for e in ts]))
    tech_ids = {e.get("ID") for e in ts}
    for uid in (77, 473, 567):
        row = CT.row_for(trees["JURCHENS"], uid, CT.UNIT_USE_TYPES)
        ttl = row.get("Trigger Tech ID")
        print("   unit %-5s Trigger Tech ID=%-6s in panel Techs? %s  (%s)"
              % (uid, ttl, (ttl in tech_ids) if ttl else False,
                 tname(ttl) if ttl else "-"))

print()
print("C  the same check for every kind-P subject")
CASES = [("JURCHENS", "Jurchens", 77), ("JURCHENS", "Jurchens", 473),
         ("JURCHENS", "Jurchens", 567), ("MUISCA", "Muisca", 359),
         ("HUNS", "Huns", 532), ("WU", "Wu", 474),
         ("BULGARIANS", "Bulgarians", 569), ("ARMENIANS", "Armenians", 569),
         ("POLES", "Poles", 691), ("MAPUCHE", "Mapuche", 528),
         ("SHU", "Shu", 532)]
flagged = []
for stem, disp, uid in CASES:
    tree = trees[stem]
    o = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
    ttl = row.get("Trigger Tech ID") if row else None
    u_b, u_e = BP.find_entry(o, disp, uid, BP.UNITS_KEY)
    tech_ids = set()
    for blk in BP.buildings(o, disp):
        for e in (blk.get(BP.TECHS_KEY) or []):
            tech_ids.add(e.get("ID"))
    in_techs = bool(ttl and ttl in tech_ids)
    if in_techs:
        flagged.append((stem, uid, ttl))
    print("   %-12s unit %-5s panel-Unit bldg=%-5s triggerTech=%-6s in panel "
          "Techs=%s" % (stem, uid, u_b, ttl, in_techs))

print()
print("D  verdict for the kind-P side")
if flagged:
    print("   ⚠ these kind-P subjects ALSO have their upgrade tech in the panel's"
          " Techs channel:")
    for stem, uid, ttl in flagged:
        print("      %-12s unit %-6s tech %s (%s)" % (stem, uid, ttl, tname(ttl)))
    print("   -> the button may legitimately require that research first; the")
    print("      observation must be taken AFTER researching it, or the subject")
    print("      replaced.")
else:
    print("   no kind-P subject has its trigger tech in the panel's Techs channel,")
    print("   so for them the panel asserts the unit is buildable outright.")
