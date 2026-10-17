# -*- coding: utf-8 -*-
"""Legible render check: a handful of frames, big, labelled, side by side.
Read-only w.r.t. game tree.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, render_frame
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = _HERE_PATH("_shots", "sld_render")
os.makedirs(OUT, exist_ok=True)

def frame_img(fn, idx, scale=3, team=(220, 60, 60), with_pc=True):
    s = read_sld(os.path.join(GP, fn))
    fr = s.frames[idx]
    canvas, w, h, info = render_frame(fr, team=team, with_pc=with_pc)
    im = Image.frombytes("RGBA", (w, h), bytes(canvas))
    rect = info.get("main_rect")
    if rect:
        x1, y1, x2, y2 = rect
        im = im.crop((max(0, x1 - 6), max(0, y1 - 6), x2 + 6, y2 + 6))
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    return im, info, s

JOBS = [
    ("u_arc_archer_idlea_x1.sld", [0, 10, 20, 30], "Archer idle"),
    ("u_inf_militia_idlea_x1.sld", [0, 8, 16, 24], "Militia idle"),
    ("u_cav_knight_idlea_x1.sld", [0, 8, 16, 24], "Knight idle"),
    ("u_monk_west_idlea_x1.sld", [0, 8, 16, 24], "Monk idle"),
]
for fn, idxs, label in JOBS:
    tiles, metas = [], []
    for i in idxs:
        im, info, s = frame_img(fn, i, scale=4)
        tiles.append(im)
        metas.append(info)
        print("%-34s f%-4d rect=%-22s grid=%s" % (label, i, info.get("main_rect"), info.get("grid")))
    Hh = max(t.height for t in tiles) + 30
    Ww = sum(t.width + 10 for t in tiles) + 10
    sheet = Image.new("RGBA", (Ww, Hh), (20, 20, 24, 255))
    d = ImageDraw.Draw(sheet)
    d.text((6, 6), "%s  (%s)  4x" % (label, fn), fill=(240, 240, 240))
    x = 5
    for t, m in zip(tiles, metas):
        sheet.alpha_composite(t, (x, 28))
        x += t.width + 10
    p = os.path.join(OUT, "big_%s.png" % label.replace(" ", "_"))
    sheet.save(p)
    print("   ->", p, sheet.size)

# team colour proof, knight frame 0, three tints incl. mask-only
s = read_sld(os.path.join(GP, "u_cav_knight_idlea_x1.sld"))
fr = s.frames[0]
c_none, w, h, info = render_frame(fr, with_pc=False)
rect = info["main_rect"]
x1, y1, x2, y2 = rect
box = (max(0, x1 - 6), max(0, y1 - 6), x2 + 6, y2 + 6)
tiles = []
for label, kw in [("no player colour", dict(with_pc=False)),
                  ("team 1 blue", dict(team=(40, 80, 230))),
                  ("team 2 red", dict(team=(220, 60, 50))),
                  ("team 3 green", dict(team=(40, 200, 60)))]:
    c, _, _, _ = render_frame(fr, **kw)
    im = Image.frombytes("RGBA", (w, h), bytes(c)).crop(box)
    im = im.resize((im.width * 4, im.height * 4), Image.NEAREST)
    tiles.append((label, im))
Hh = max(t.height for _, t in tiles) + 30
Ww = sum(t.width + 10 for _, t in tiles) + 10
sheet = Image.new("RGBA", (Ww, Hh), (20, 20, 24, 255))
d = ImageDraw.Draw(sheet)
d.text((6, 6), "u_cav_knight_idlea_x1.sld frame 0 -- player colour from BC4 mask", fill=(240, 240, 240))
x = 5
for label, t in tiles:
    sheet.alpha_composite(t, (x, 28))
    d.text((x + 2, Hh - 12), label, fill=(200, 200, 200))
    x += t.width + 10
p = os.path.join(OUT, "big_teamcolor.png")
sheet.save(p)
print("->", p, sheet.size)
