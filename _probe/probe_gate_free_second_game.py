# -*- coding: utf-8 -*-
r"""Does the 'tree grants it' half survive a RESEARCH GATE?

GAME 2 is SICILIANS / unit 588 (Siege Onager): the tree says
`ResearchedCompleted`, the panel is silent, so a missing button is supposed to
mean "the panel drives the menu".  But 354 panel entries *do* carry a research
gate (`PrereqTech`), and a tree row can be gated by a prerequisite tech even when
its own status reads `ResearchedCompleted` -- `ResearchedCompleted` means "the
tree offers it", not "it is available at minute one".

Check, for every kind-T subject, whether a prerequisite chain could hide the
button for a reason unrelated to which file the menu reads.  If it can, find a
kind-T subject with no gate at all.
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
    if u is None:
        return "tech %s" % tid
    return (u.zh or u.en) or ("tech %s" % tid)


def uname(uid):
    u = idx.get("unit", uid)
    return (u.zh or u.en) if u else ("unit %s" % uid)


# --- what is Trigger Tech ID, and does it gate? ------------------------------
print("A  Trigger Tech ID on the kind-T subjects -- does its tech exist?")
for stem, disp, uid in (("SICILIANS", "Sicilians", 588),
                        ("GEORGIANS", "Georgians", 588),
                        ("SPARTANS", "Spartans", 13)):
    tree = trees[stem]
    row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
    ttl = row.get("Trigger Tech ID")
    print("  %-11s unit %-5s Trigger Tech ID=%r  -> that tech's civ status=%r"
          % (stem, uid, ttl,
             CT.node_status(tree, ttl, CT.TECH_USE_TYPES) if ttl else None))

print()
print("B  for each kind-T subject: how many TECHS does the civ hold under that "
      "building, and is the unit's own cost/tech chain empty?")
# A tree row's "Node Status: ResearchedCompleted" means the civ's tree OFFERS it.
# The real question for a menu button is whether the civ must research something
# first.  The panel file is the only place that can say "gated behind research"
# (via PrereqTech) -- and for a kind-T subject the panel is silent, so the panel
# asserts nothing.  The TREE cannot express "needs research" per-unit at all
# (that is precisely why CivTechTrees exists as a per-civ file).
for stem, disp, uid, bld in (("SICILIANS", "Sicilians", 588, 49),
                             ("GEORGIANS", "Georgians", 588, 49),
                             ("SPARTANS", "Spartans", 13, 2172)):
    tree = trees[stem]
    row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
    print("  %-11s unit %-5s (%s)  age=%s  Link ID=%r"
          % (stem, uid, uname(uid), row.get("Age ID"), row.get("Link ID")))
    # Techs the panel lists for the same building (these are the research steps)
    pk = BP.panel_path_for(GAME, disp)[1]
    obj = panels[pk]["obj"]
    techs = BP.entries(obj, disp, bld, BP.TECHS_KEY) or []
    print("      panel's Techs at building %s: %s"
          % (bld, [(t.get("ID"), t.get("Name"), t.get("RequiredAge"))
                   for t in techs]))

print()
print("C  search the WHOLE corpus for kind-T subjects that are gate-free")
print("   (tree ResearchedCompleted, panel silent everywhere, and neither the")
print("    panel entry nor a prereq chain exists to explain a missing button)")

kindT = []
seen = set()
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            continue
        seen.add((rec["path"], disp))
        stem = CT.civ_file_stem(disp)
        tree = trees.get(stem)
        if tree is None:
            continue
        owned = {r.get("Node ID") for r in CT.rows_of(tree)
                 if r.get("Use Type") == "Building"}
        listed = set()
        for blk in BP.buildings(rec["obj"], disp):
            for e in (blk.get(BP.UNITS_KEY) or []):
                listed.add(e.get("ID"))
        rows = {r.get("Node ID"): r for r in CT.unit_rows(tree)
                if r.get("Node ID") is not None}
        for uid, r in rows.items():
            if (r.get("Node Status") != "ResearchedCompleted"
                    or r.get("Building ID") not in owned or uid in listed):
                continue
            u = idx.get("unit", uid)
            if not (u and (u.zh or u.en)):
                continue          # invisible internals are not subjects
            ttl = r.get("Trigger Tech ID")
            tstat = (CT.node_status(tree, ttl, CT.TECH_USE_TYPES)
                     if ttl else None)
            kindT.append((stem, uid, uname(uid), r.get("Age ID"),
                          r.get("Building ID"), ttl, tstat))

print("   %-12s %-6s %-24s %-5s %-6s %-8s %s"
      % ("civ", "unit", "name", "age", "bldg", "trigTech", "civ tech status"))
for row in sorted(kindT, key=lambda r: (r[3] or 9, r[0])):
    print("   %-12s %-6s %-24s %-5s %-6s %-8s %s" % row)
print("   total: %d" % len(kindT))
