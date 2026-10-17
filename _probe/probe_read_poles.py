# -*- coding: utf-8 -*-
r"""Read the Poles dock grid in full, and print what each hypothesis predicts.

GAME 2 is already decided by the user's shots 3 and 4:
    '升级到重型投石车（价格：1450食物，1000黄金）'   <- tech 320, hotkey S
    '建造重型投石车（价格：160木，135金）（热键：W）' <- unit 588, hotkey W
both in a Sicilians siege workshop, while `futuravailableunits.json` lists NEITHER.
That alone refutes "the menu is fed by the panel".

GAME 1 decides between "tree only" and "union": Poles' tree says 691
`NotAvailable` while the panel lists it.  Count the dock's buttons and see whether
the cannon line carries an upgrade.

Print, for the Poles dock, what each hypothesis predicts as the button count, so the
screenshot can be read against a number rather than by eye.
"""
import os
import sys

from PIL import Image

A = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_crops")
os.makedirs(OUT, exist_ok=True)
POLES = os.path.join(A, "5a",
    "5a77a828c64b351be52e2dc4d402e8b76798db6bf8f16a41e86ec13ab98ee9e6")

im = Image.open(POLES).convert("RGB")
w, h = im.size
print("poles screenshot %sx%s" % (w, h))
# the whole bottom UI, then the grid at 3x
c = im.crop((0, int(0.44 * h), w, h))
c.resize((c.size[0] * 2, c.size[1] * 2), Image.LANCZOS).save(
    os.path.join(OUT, "poles_ui2x.png"))
print("wrote poles_ui2x.png %s" % ((c.size[0] * 2, c.size[1] * 2),))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mod.game import buildpanel as BP                    # noqa: E402
from aoe2mod.game import civtechtrees as CT                  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
o = panels[BP.panel_path_for(GAME, "Poles")[1]]["obj"]
pu = {}
for blk in BP.buildings(o, "Poles"):
    if blk.get("ID") == 45:
        for e in (blk.get(BP.UNITS_KEY) or []):
            pu[e.get("ID")] = e
print()
print("Poles dock: panel lists %d unit entries" % len(pu))
for uid, e in pu.items():
    r = CT.row_for(trees["POLES"], uid, CT.UNIT_USE_TYPES)
    print("   %-6s %-24s panel age=%s | tree status=%-18s trig=%r"
          % (uid, e.get("Name"), e.get("RequiredAge"),
             (r or {}).get("Node Status"), (r or {}).get("Trigger Tech ID")))

# chains, as the game groups them
print()
print("chains (a button = a chain):")
CHAINS = [[539, 21, 442], [1103, 529, 532], [1104, 527, 528],
          [2626, 2627, 2628], [420, 691], [13], [545], [17]]
for ch in CHAINS:
    stat = []
    for u in ch:
        r = CT.row_for(trees["POLES"], u, CT.UNIT_USE_TYPES)
        stat.append("%s:%s" % (u, ((r or {}).get("Node Status") or "-")))
    print("   %-28s %s" % (ch, " ".join(stat)))

print()
print("what each hypothesis predicts for THIS dock")
panel_ok = sum(1 for u in pu if CT.node_status(trees["POLES"], u,
                                               CT.UNIT_USE_TYPES) != "NotAvailable")
panel_all = len(pu)
tree_only = sum(1 for r in CT.unit_rows(trees["POLES"])
                if r.get("Building ID") == 45
                and r.get("Node Status") in ("ResearchedCompleted",
                                             "ResearchRequired"))
print("   panel entries (all)                    : %d" % panel_all)
print("   of those the tree also allows          : %d" % panel_ok)
print("   tree rows the tree allows at this bldg : %d" % tree_only)
print()
print("   panel-only entry = 691 Elite Cannon Galleon")
print("   -> if the dock SHOWS an Elite Cannon Galleon upgrade, the menu unions")
print("      the layers; if it does not, the tree is authoritative alone.")
