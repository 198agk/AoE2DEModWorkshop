# -*- coding: utf-8 -*-
r"""HOLE CHECK: kind-T silence must be checked across EVERY building, not one.

`test_protocol_subjects.py` judged "the panel is silent" by looking only at the
building the tree row names.  But the panel lists units per building, and the same
unit can be listed under a DIFFERENT building of the same civilization (a monk might
be absent from building 1806 while being listed under building 104).  If so, the
panel is NOT silent, the layers do not disagree, and the subject is useless.

It also surfaced two new Age-3 kind-T survivors (ARMENIANS/GEORGIANS unit 125 Monk
at building 1806) which would be much cheaper than an Imperial-Age test, so they are
worth verifying properly.

Check silence globally: for each kind-T candidate, search the civ's WHOLE panel for
the unit id and for its upgrade tech.
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
os.makedirs(os.path.join(HERE, "out_hole"), exist_ok=True)


def uname(uid):
    u = idx.get("unit", uid)
    return (u.zh or u.en) if u else None


print("A  every panel entry mentioning the kind-T candidates, WHOLE civ")
CANDS = [("ARMENIANS", "Armenians", 1806, 125),
         ("ARMENIANS", "Armenians", 1806, 1811),
         ("GEORGIANS", "Georgians", 1806, 125),
         ("SICILIANS", "Sicilians", 49, 588),
         ("SPARTANS", "Spartans", 2172, 13)]
for stem, disp, bid, uid in CANDS:
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    where_u, where_t = [], []
    for blk in BP.buildings(obj, disp):
        b = blk.get("ID")
        for e in (blk.get(BP.UNITS_KEY) or []):
            if e.get("ID") == uid:
                where_u.append((b, e.get("Name"), e.get("RequiredAge")))
        for e in (blk.get(BP.TECHS_KEY) or []):
            if e.get("ID") == uid:
                where_t.append((b, e.get("Name")))
    print("   %-11s unit %-6s %-14s tree names bldg %-5s | panel Units: %s | "
          "panel Techs: %s"
          % (stem, uid, uname(uid), bid, where_u or "NOWHERE",
             where_t or "NOWHERE"))

print()
print("B  what building 1806 is, and who has it")
for x in (1806, 104, 45, 49):
    nm, owners = None, []
    for s, t in trees.items():
        for r in CT.rows_of(t):
            if r.get("Use Type") == "Building" and r.get("Node ID") == x:
                owners.append(s)
                nm = nm or r.get("Name")
    print("   building %-5s name=%-16r in %d civs: %s"
          % (x, nm, len(owners), sorted(owners)[:10]))

print()
print("C  ARMENIANS / GEORGIANS: the tree rows at 1806 and the panel for the same "
      "civilization")
for stem, disp in (("ARMENIANS", "Armenians"), ("GEORGIANS", "Georgians")):
    t = trees[stem]
    print("   --- %s ---" % stem)
    for r in CT.unit_rows(t):
        if r.get("Building ID") == 1806:
            print("      tree: unit %-6s %-18s status=%-18s age=%s"
                  % (r.get("Node ID"), r.get("Name"), r.get("Node Status"),
                     r.get("Age ID")))
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    pbs = [blk.get("ID") for blk in BP.buildings(obj, disp)]
    print("      panel buildings: %s" % sorted(pbs))
    if 1806 in pbs:
        for blk in BP.buildings(obj, disp):
            if blk.get("ID") == 1806:
                print("      panel 1806 Units: %s"
                      % [(e.get("ID"), e.get("Name"), e.get("RequiredAge"))
                         for e in (blk.get(BP.UNITS_KEY) or [])])
    else:
        print("      panel has NO building 1806 block at all")

print()
print("D  the Monk question: is unit 125 listed under the Monastery (104)?")
for stem, disp in (("ARMENIANS", "Armenians"), ("GEORGIANS", "Georgians"),
                   ("BRITONS", "Britons")):
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    hits = []
    for blk in BP.buildings(obj, disp):
        for e in (blk.get(BP.UNITS_KEY) or []):
            if e.get("ID") == 125:
                hits.append((blk.get("ID"), e.get("Name"), e.get("RequiredAge")))
    print("   %-11s unit 125 in panel at: %s" % (stem, hits or "NOWHERE"))

print()
print("E  verdict: which kind-T candidates survive GLOBAL silence?")
survivors = []
for stem, disp, bid, uid in CANDS:
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    any_u = any(e.get("ID") == uid for blk in BP.buildings(obj, disp)
                for e in (blk.get(BP.UNITS_KEY) or []))
    tts = set()
    t = trees[stem]
    for r in CT.unit_rows(t):
        if r.get("Node ID") == uid and r.get("Trigger Tech ID") is not None:
            tts.add(r.get("Trigger Tech ID"))
    any_t = any(e.get("ID") in tts for blk in BP.buildings(obj, disp)
                for e in (blk.get(BP.TECHS_KEY) or [])) if tts else False
    ok = not any_u and not any_t
    print("   %-11s unit %-6s panel-lists-unit=%-5s panel-lists-tech=%-5s -> %s"
          % (stem, uid, any_u, any_t, "SURVIVES" if ok else "DISQUALIFIED"))
    if ok:
        survivors.append((stem, disp, bid, uid))
print("   survivors: %s" % survivors)
