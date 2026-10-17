# -*- coding: utf-8 -*-
"""Render real .sld frames with sldlib.py and dump PNG contact sheets.
Read-only w.r.t. the game tree; writes only under _shots\sld_render\.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, parse_mask_layer, grid_of, \
    decode_bc1_plane, decode_bc4_plane, render_frame
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = _HERE_PATH("_shots", "sld_render")
os.makedirs(OUT, exist_ok=True)

def rgba_to_img(buf, w, h):
    return Image.frombytes("RGBA", (w, h), bytes(buf))

SAMPLES = [
    ("u_arc_archer_idlea_x1.sld", [0, 20, 40]),
    ("u_inf_militia_idlea_x1.sld", [0, 10, 20]),
    ("u_cav_knight_idlea_x1.sld", [0, 10, 20]),
    ("a_herd_sheep_idleA_x1.sld", [0, 1, 2]),
    ("b_afri_stable_age2_x1.sld", [0, 1, 2]),
]

TILES = []
for fn, idxs in SAMPLES:
    p = os.path.join(GP, fn)
    if not os.path.exists(p):
        print("(missing)", fn)
        continue
    s = read_sld(p)
    print("%-38s fo=%d n=%d walked=%d  ok=%s"
          % (fn, s.frame_offset, s.num_frames, len(s.frames),
             s.num_frames == len(s.frames)))
    for i in idxs:
        if i >= len(s.frames):
            continue
        fr = s.frames[i]
        canvas, w, h, info = render_frame(fr)
        img = rgba_to_img(canvas, w, h)
        name = "%s_f%03d.png" % (fn[:-4], i)
        img.save(os.path.join(OUT, name))
        # also a bbox crop so small sprites are legible
        rect = info.get("main_rect")
        print("   f%-4d ft=0x%02x canvas=%dx%d rect=%s grid=%s layers=%s"
              % (fr.index, fr.frame_type, w, h, rect,
                 info.get("grid"), "+".join(sorted(fr.layers))))
        TILES.append((fn, i, img, rect))

# contact sheet: each sprite cropped to its rect, scaled 3x, side by side
CROPS = []
for fn, i, img, rect in TILES:
    if rect:
        x1, y1, x2, y2 = rect
        c = img.crop((max(0, x1 - 4), max(0, y1 - 4), x2 + 4, y2 + 4))
    else:
        c = img.crop(img.getbbox() or (0, 0, img.width, img.height))
    c = c.resize((c.width * 3, c.height * 3), Image.NEAREST)
    CROPS.append(c)

if CROPS:
    Hh = max(c.height for c in CROPS)
    Ww = sum(c.width + 8 for c in CROPS)
    sheet = Image.new("RGBA", (Ww, Hh + 20), (24, 24, 28, 255))
    x = 0
    for c in CROPS:
        sheet.alpha_composite(c, (x, 20))
        x += c.width + 8
    sheet.save(os.path.join(OUT, "sld_frames_CONTACT.png"))
    print("\nwrote", os.path.join(OUT, "sld_frames_CONTACT.png"), sheet.size)

# player-colour proof on the knight
import struct
p = os.path.join(GP, "u_cav_knight_idlea_x1.sld")
s = read_sld(p)
fr = s.frames[0]
canvas, w, h, info = render_frame(fr, team=(220, 60, 60))
rect = info["main_rect"]
x1, y1, x2, y2 = rect
parts = []
for label, tint in [("team red", (220, 60, 60)), ("team blue", (40, 80, 230)),
                    ("team none", None)]:
    if tint is None:
        c2, _, _, _ = render_frame(fr, with_pc=False)
    else:
        c2, _, _, _ = render_frame(fr, team=tint)
    im = rgba_to_img(c2, w, h).crop((x1 - 4, y1 - 4, x2 + 4, y2 + 4))
    im = im.resize((im.width * 4, im.height * 4), Image.NEAREST)
    parts.append((label, im))
Hh = max(im.height for _, im in parts)
Ww = sum(im.width + 8 for _, im in parts)
sheet = Image.new("RGBA", (Ww, Hh), (24, 24, 28, 255))
x = 0
for label, im in parts:
    sheet.alpha_composite(im, (x, 0))
    x += im.width + 8
sheet.save(os.path.join(OUT, "knight_teamcolor.png"))
print("wrote", os.path.join(OUT, "knight_teamcolor.png"), sheet.size)
