# -*- coding: utf-8 -*-
"""Render building frames (ft=0x1f, all five layers) under several
interpretations of the `damage` layer, so the correct one can be chosen
VISUALLY.  Read-only.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import (read_sld, parse_rect_layer, grid_of, decode_bc1_plane,
                    decode_bc4_plane)
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\sld_render"
os.makedirs(OUT, exist_ok=True)

FILES = [
    ("b_afri_archery_range_age2_x1.sld", [0, 1]),
    ("b_afri_stable_age2_x1.sld", [0]),
    ("b_dark_barracks_age1_x1.sld", [0]),
    ("b_west_castle_age3_x1.sld", [0]),
    ("b_west_town_center_age2_back_x1.sld", [0]),
    ("b_afri_gate_stone_e_constr_x1.sld", [2]),
    ("b_afri_mill_age2_x1.sld", [1, 2]),
]


def blocks_of(l, header):
    fmt, n = struct.unpack_from("<2H", l.data, 0) if header == "mask" \
        else (struct.unpack_from("<2H", l.data, 8))
    base = 4 + 2 * n if header == "mask" else 12 + 2 * n
    cmds = [struct.unpack_from("<2B", l.data, base - 2 * n + 2 * i)
            for i in range(n)]
    nb = (l.size - base) // 8
    return fmt, n, cmds, [l.data[base + 8 * i: base + 8 * i + 8]
                          for i in range(nb)]


def render(fn, fi):
    s = read_sld(os.path.join(GP, fn))
    fr = s.frames[fi]
    L = fr.layers
    w, h = fr.canvas_w, fr.canvas_h
    m = L["main"]
    rect, mfmt, mn, mcmds = parse_rect_layer(m)
    x1, y1, rw, rh, bw, bh = grid_of(rect)
    mblocks = [m.data[12 + 2 * mn + 8 * i: 12 + 2 * mn + 8 * i + 8]
               for i in range((m.size - 16 - 2 * mn) // 8)]
    mplane, PW, PH = decode_bc1_plane(mblocks, bw, bh, mcmds)

    panels = []
    # P0: main only
    base = bytearray(w * h * 4)
    for gy in range(PH):
        for gx in range(PW):
            sx, sy = x1 + gx, y1 + gy
            if 0 <= sx < w and 0 <= sy < h:
                o = (sy * w + sx) * 4
                px = mplane[(gy * PW + gx) * 4:(gy * PW + gx) * 4 + 4]
                if px[3]:
                    base[o:o + 4] = bytes(px)
    panels.append(("main only", base))

    if "damage" in L:
        d = L["damage"]
        dfmt, dn, dcmds, dblocks = blocks_of(d, "mask")
        # P1: damage as BC1 colour on main's grid
        try:
            dpl, DW, DH = decode_bc1_plane(dblocks, bw, bh, dcmds)
            p = bytearray(base)
            for gy in range(min(DH, PH)):
                for gx in range(min(DW, PW)):
                    sx, sy = x1 + gx, y1 + gy
                    if not (0 <= sx < w and 0 <= sy < h):
                        continue
                    o = (sy * w + sx) * 4
                    px = dpl[(gy * DW + gx) * 4:(gy * DW + gx) * 4 + 4]
                    if px[3]:
                        p[o:o + 4] = bytes(px)
            panels.append(("dmg as BC1 colour\n(fmt=0x%04x n=%d span=%d)"
                           % (dfmt, dn, sum(c[1] for c in dcmds)), p))
        except Exception as e:
            print("  (%s P1: %s)" % (fn, e))
        # P2: damage as BC4 mask over main -> red where mask
        try:
            dpl, DW, DH = decode_bc4_plane(dblocks, bw, bh, dcmds)
            p = bytearray(base)
            for gy in range(PH):
                for gx in range(PW):
                    sx, sy = x1 + gx, y1 + gy
                    if not (0 <= sx < w and 0 <= sy < h):
                        continue
                    o = (sy * w + sx) * 4
                    if not p[o + 3]:
                        continue
                    k = dpl[gy * DW + gx] if (gy < DH and gx < DW) else 0
                    if k:
                        f = k / 255.0
                        p[o] = int(p[o] * (1 - f) + 255 * f)
                        p[o + 1] = int(p[o + 1] * (1 - f))
                        p[o + 2] = int(p[o + 2] * (1 - f))
            panels.append(("dmg as BC4 mask\n(red = masked)", p))
        except Exception as e:
            print("  (%s P2: %s)" % (fn, e))
        # P3: damage plane alone
        try:
            dpl, DW, DH = decode_bc1_plane(dblocks, bw, bh, dcmds)
            p = bytearray(w * h * 4)
            for gy in range(DH):
                for gx in range(DW):
                    sx, sy = x1 + gx, y1 + gy
                    if 0 <= sx < w and 0 <= sy < h:
                        o = (sy * w + sx) * 4
                        p[o:o + 4] = dpl[(gy * DW + gx) * 4:(gy * DW + gx) * 4 + 4]
            panels.append(("dmg plane alone", p))
        except Exception as e:
            print("  (%s P3: %s)" % (fn, e))

    # crop to main rect
    crops = []
    for label, buf in panels:
        im = Image.frombytes("RGBA", (w, h), bytes(buf))
        im = im.crop((max(0, x1 - 6), max(0, y1 - 6), min(w, x1 + rw + 6),
                      min(h, y1 + rh + 6)))
        sc = max(1, min(3, 420 // max(1, im.height)))
        im = im.resize((im.width * sc, im.height * sc), Image.NEAREST)
        crops.append((label, im))
    return "%s  f%d  ft=0x%02x  canvas=%dx%d  main rect=%s grid=%dx%d" % (
        fn, fi, fr.frame_type, w, h, rect, bw, bh), crops


allrows = []
for fn, idxs in FILES:
    if not os.path.exists(os.path.join(GP, fn)):
        print("(missing)", fn)
        continue
    for fi in idxs:
        try:
            t, c = render(fn, fi)
            allrows.append((t, c))
            print(t, "|", [x[0].split("\n")[0] for x in c])
        except Exception as e:
            print("(%s f%d: %s)" % (fn, fi, e))

if allrows:
    maxp = max(len(c) for _, c in allrows)
    cw = max(im.width for _, c in allrows for _, im in c) + 12
    ch = max(im.height for _, c in allrows for _, im in c) + 34
    sheet = Image.new("RGBA", (cw * maxp, ch * len(allrows)), (18, 18, 22, 255))
    d = ImageDraw.Draw(sheet)
    for r, (title, c) in enumerate(allrows):
        d.text((6, r * ch + 2), title[:150], fill=(235, 235, 235))
        for i, (lab, im) in enumerate(c):
            d.text((i * cw + 6, r * ch + 16), lab.replace("\n", " ")[:44],
                   fill=(160, 200, 255))
            sheet.alpha_composite(im, (i * cw + 6, r * ch + 30))
    p = os.path.join(OUT, "damage_hypotheses.png")
    sheet.save(p)
    print("\n->", p, sheet.size)
