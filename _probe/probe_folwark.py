# -*- coding: utf-8 -*-
r"""A static argument that may settle the question without a game.

`probe_panel_lists_impossible` showed two things:

  * a panel block present with empty Units/Techs means nothing (Huns have an
    empty House block, and Huns cannot build houses) -- so block presence is
    NOT a signal, and the earlier kind-PB count of 67 is mostly noise;
  * building the panel omits while the tree grants it (Poles Folwark 1734,
    Khitans Pasture 1889) is the interesting side.

If the panel has NO trace of the Folwark for the Poles, while the Poles
demonstrably can build Folwarks in the real game (it is their Mill
replacement), then the panel cannot be what fills the build menu -- at least
not for buildings.  That is a paper argument needing no experiment.

Careful checks before believing it:
  * does 1734 appear ANYWHERE in the panel (other civs, other blocks, Units or
    Techs channel)?
  * does the panel do Mill-replacement some other way (e.g. POLES Mill block
    naming a Folwark, or a tech that swaps it)?
  * does the .dat even have 1734 as buildable by Poles?

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_folwark.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.game import buildpanel as BP                 # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def _int(v, default=-1):
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
pol = trees["POLES"]

print("A  what the Poles' tree says about 1734, filtered by Use Type")
for r in CT.rows_of(pol):
    if isinstance(r, dict) and _int(r.get("Node ID")) == 1734:
        print("     use=%-9s %s" % (r.get("Use Type"),
                                    {k: r.get(k) for k in
                                     ("Node ID", "Name", "Node Status", "Age ID",
                                      "Building ID")}))

print()
print("B  does building 1734 appear ANYWHERE in the shipped panel?")
hits = []
name_hits = []
for name, rec in panels.items():
    obj = rec["obj"]
    for blk in BP.buildings(obj, name):
        if _int(blk.get("ID")) == 1734:
            hits.append((name, "BLOCK", blk.get("Name"),
                         len(blk.get("Units") or []), len(blk.get("Techs") or [])))
        for space in ("Units", "Techs"):
            for e in (blk.get(space) or []):
                if _int(e.get("ID")) == 1734:
                    hits.append((name, space, e.get("Name"),
                                 blk.get("ID"), blk.get("Name")))
                nm = (e.get("Name") or "")
                if "folwark" in nm.lower():
                    name_hits.append((name, space, _int(e.get("ID")), nm,
                                      blk.get("ID")))
print("     id hits: %d" % len(hits))
for h in hits[:15]:
    print("       %s" % (h,))
print("     name hits containing 'folwark': %d" % len(name_hits))
for h in name_hits[:15]:
    print("       %s" % (h,))

print()
print("C  how the panel expresses the Poles' Mill replacement")
pk = BP.civ_key_for(panels, "POLES")
obj = panels[pk]["obj"]
for bid in (68, 50, 1734):
    blk = BP.building_block(obj, pk, bid)
    if blk is None:
        print("     %s: ABSENT" % bid)
        continue
    print("     %s %r Units=%s Techs=%s"
          % (bid, blk.get("Name"),
             [(_int(e.get("ID")), e.get("Name")) for e in (blk.get("Units") or [])],
             [(_int(e.get("ID")), e.get("Name")) for e in (blk.get("Techs") or [])]))

print()
print("D  the same question for the Khitans' Pasture (1889)")
kh = trees["KHITANS"]
for r in CT.rows_of(kh):
    if isinstance(r, dict) and _int(r.get("Node ID")) == 1889:
        print("     tree use=%-9s %s" % (r.get("Use Type"),
                                         {k: r.get(k) for k in
                                          ("Node ID", "Name", "Node Status",
                                           "Age ID", "Building ID")}))
khits = [name for name, rec in panels.items()
         if any(_int(b.get("ID")) == 1889 for b in BP.buildings(rec["obj"], name))]
print("     panel civs with a 1889 block: %s" % (khits or "NONE"))

print()
print("E  is any building node granted by the tree missing from the panel as a")
print("   BLOCK, for every civilization? (the general shape of the argument)")
missing_any = {}
for civ in sorted(trees):
    pk2 = BP.civ_key_for(panels, civ)
    if pk2 is None:
        continue
    ids = {_int(b.get("ID")) for b in BP.buildings(panels[pk2]["obj"], pk2)}
    for r in CT.rows_of(trees[civ]):
        if not isinstance(r, dict) or r.get("Use Type") != "Building":
            continue
        if r.get("Node Status") != "ResearchedCompleted":
            continue
        nid = _int(r.get("Node ID"))
        if nid not in ids:
            missing_any.setdefault(nid, set()).add((civ, r.get("Name")))
for nid, civs in sorted(missing_any.items()):
    print("     bldg %-5s missing for %s" % (nid, sorted(civs)[:4]))
sys.exit(0)
