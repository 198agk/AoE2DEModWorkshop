# -*- coding: utf-8 -*-
r"""Extract the answer from the user's test screenshots + print the expected lists.

GAME 2 (Sicilians / siege workshop) already reads, from the tooltips the user
hovered:
    '升级到重型投石车 (价格: 1450 食物, 1000 黄金)'   <- the UPGRADE button
    '建造重型投石车 (价格: 160 木, 135 金)'           <- the UNIT button
The panel file is silent on BOTH (no 588 in `Units`, no 320 in `Techs`) while the
tree grants 588 `ResearchedCompleted` -> the menu does NOT follow the panel alone.

Now read GAME 1 (Poles / dock): is the ELITE CANNON GALLEON upgrade present?
Crop that grid large.
"""
import os

from PIL import Image

A = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_crops")
os.makedirs(OUT, exist_ok=True)

POLES = os.path.join(A, "5a",
    "5a77a828c64b351be52e2dc4d402e8b76798db6bf8f16a41e86ec13ab98ee9e6")
SIC = os.path.join(A, "2b",
    "2be84e564bfc25de5481338f98a153563641d463c1a8241015cfd0701ea86b01")

im = Image.open(POLES).convert("RGB")
print("poles screenshot: %s" % (im.size,))
# whole grid, generously
box = (15, 430, 445, 650)
crop = im.crop(box)
crop.resize((crop.size[0] * 4, crop.size[1] * 4), Image.LANCZOS).save(
    os.path.join(OUT, "poles_grid4x.png"))
print("wrote poles_grid4x.png %s" % ((crop.size[0] * 4, crop.size[1] * 4),))

im2 = Image.open(SIC).convert("RGB")
box2 = (15, 200, 660, 500)
crop2 = im2.crop(box2)
crop2.resize((crop2.size[0] * 3, crop2.size[1] * 3), Image.LANCZOS).save(
    os.path.join(OUT, "sic_grid3x.png"))
print("wrote sic_grid3x.png %s" % ((crop2.size[0] * 3, crop2.size[1] * 3),))

# ---- the data side -----------------------------------------------------------
import sys                                                  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mod.game import buildpanel as BP                    # noqa: E402
from aoe2mod.game import civtechtrees as CT                  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

for stem, disp, bid in (("POLES", "Poles", 45), ("SICILIANS", "Sicilians", 49)):
    t = trees[stem]
    print()
    print("=== %s / building %s ===" % (stem, bid))
    print("  tree unit rows at that building:")
    for r in CT.unit_rows(t):
        if r.get("Building ID") == bid:
            print("     unit %-6s %-24s status=%-18s age=%s trigTech=%r"
                  % (r.get("Node ID"), r.get("Name"), r.get("Node Status"),
                     r.get("Age ID"), r.get("Trigger Tech ID")))
    print("  tree rows naming the KEY unit:")
    for uid in (420, 691, 280, 550, 588):
        r = CT.row_for(t, uid, CT.UNIT_USE_TYPES)
        if r and r.get("Building ID") == bid:
            print("     %-6s status=%r age=%r trig=%r"
                  % (uid, r.get("Node Status"), r.get("Age ID"),
                     r.get("Trigger Tech ID")))
    o = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    for blk in BP.buildings(o, disp):
        if blk.get("ID") == bid:
            print("  panel Units: %s"
                  % [(e.get("ID"), e.get("Name"), e.get("RequiredAge"))
                     for e in (blk.get(BP.UNITS_KEY) or [])])
            print("  panel Techs: %s"
                  % [(e.get("ID"), e.get("Name"))
                     for e in (blk.get(BP.TECHS_KEY) or [])])
