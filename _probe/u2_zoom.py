# -*- coding: utf-8 -*-
"""Zoom in on the edited region so the BC1 endpoint edit is visually obvious."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import (read_sld, parse_rect_layer, grid_of, rect_blocks,
                    decode_bc1_plane)
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\sld_render"
WORK = r"D:\Software\DeepSeek Harness\工作区2\_probe\sld_out"
name = "u_arc_archer_idlea_x1.sld"


def frame_image(path, idx, scale=1):
    s = read_sld(path)
    fr = s.frames[idx]
    w, h = fr.canvas_w, fr.canvas_h
    m = fr.layers["main"]
    rect, f, n, c = parse_rect_layer(m)
    x1, y1, rw, rh, bw, bh = grid_of(rect)
    plane, PW, PH = decode_bc1_plane(rect_blocks(m, n), bw, bh, c)
    cv = bytearray(w * h * 4)
    for gy in range(PH):
        for gx in range(PW):
            sx, sy = x1 + gx, y1 + gy
            if 0 <= sx < w and 0 <= sy < h:
                o = (sy * w + sx) * 4
                px = plane[(gy * PW + gx) * 4:(gy * PW + gx) * 4 + 4]
                if px[3]:
                    cv[o:o + 4] = bytes(px)
    im = Image.frombytes("RGBA", (w, h), bytes(cv))
    if scale > 1:
        im = im.resize((w * scale, h * scale), Image.NEAREST)
    return im


a = frame_image(os.path.join(GP, name), 0, scale=14)
b = frame_image(os.path.join(WORK, "edit_" + name), 0, scale=14)
# crop to the tunic area (ref 88..132 x, 64..108 y) scaled
box = (88 * 14, 64 * 14, 132 * 14, 108 * 14)
a = a.crop(box)
b = b.crop(box)
sheet = Image.new("RGBA", (a.width + b.width + 40, a.height + 60),
                  (18, 18, 22, 255))
d = ImageDraw.Draw(sheet)
d.text((10, 8), "ORIGINAL  archer tunic", fill=(235, 235, 235))
d.text((a.width + 30, 8), "AFTER BC1 endpoint edit", fill=(140, 235, 140))
sheet.alpha_composite(a, (10, 40))
sheet.alpha_composite(b, (a.width + 30, 40))
p = os.path.join(OUT, "sld_edit_ZOOM.png")
sheet.convert("RGB").save(p)
print("wrote", p, sheet.size)
