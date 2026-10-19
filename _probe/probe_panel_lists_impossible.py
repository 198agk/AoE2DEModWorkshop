# -*- coding: utf-8 -*-
r"""Does the panel list buildings a civilization demonstrably cannot build?

`probe_building_subjects` found 67 kind-PB rows (the tree says NotAvailable, the
panel still lists the building).  Some of them are facts every player knows:

    Huns    House(70)      -- Huns famously cannot build houses
    Aztecs  Stable(101)    -- no American civilization has a stable

If the panel really lists those buildings, then "listed in the panel" cannot
mean "buildable", i.e. the panel is not the authority for the build menu.  That
is a free result: it needs no game, only the shipped files plus what players
already know.  But it is only free if the panel's block actually carries
content, so print the blocks.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_panel_lists_impossible.py
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

CASES = [("HUNS", 70, "House, which Huns cannot build"),
         ("AZTECS", 101, "Stable, which Aztecs cannot build"),
         ("MAYANS", 101, "Stable, which Mayans cannot build"),
         ("INCAS", 101, "Stable, which Incas cannot build"),
         ("CUMANS", 117, "Stone Wall, which Cumans cannot build"),
         ("GOTHS", 117, "Stone Wall, which Goths cannot build"),
         ("HUNS", 155, "Fortified Wall, which Huns cannot build"),
         ("CUMANS", 234, "Guard Tower, which Cumans cannot build"),
         ("POLES", 1734, "Folwark, which the tree grants but the panel omits"),
         ("KHITANS", 1889, "Pasture, which the tree grants but the panel omits")]


def _int(v, default=-1):
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

for civ, bid, why in CASES:
    pk = BP.civ_key_for(panels, civ)
    obj = panels[pk]["obj"]
    blk = BP.building_block(obj, pk, bid)
    row = CT.row_for(trees[civ], bid, ("Building", "Tech"))
    print("%-9s bldg %-5s %s" % (civ, bid, why))
    tree_desc = ("absent" if row is None
                 else "%s / %s / age %s" % (row.get("Name"),
                                            row.get("Node Status"),
                                            row.get("Age ID")))
    print("     tree: %s" % tree_desc)
    if blk is None:
        print("     panel: block ABSENT")
    else:
        print("     panel: block present, Name=%r" % blk.get("Name"))
        print("            Units=%s" % [(_int(e.get("ID")), e.get("Name"))
                                       for e in (blk.get("Units") or [])])
        print("            Techs=%s" % [(_int(e.get("ID")), e.get("Name"))
                                       for e in (blk.get("Techs") or [])])
    # who builds what: does the panel put the impossible building anywhere at all?
    print()

print("=" * 70)
print("Is a building the panel omits, but the tree grants, buildable in practice?")
print("(this is the kind-TB side, and it cannot separate the tree from the .dat,")
print(" because the .dat is a superset that already allows it)")
sys.exit(0)
