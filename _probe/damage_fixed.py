# -*- coding: utf-8 -*-
"""Final SLD mask-layer verification + correct damage rendering.

Invariant under test: for BOTH mask layers (playercolor, damage),
sum(skip+draw) == main's bw*bh, i.e. both index main's cell grid exactly.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import (read_sld, parse_rect_layer, grid_of, placed_blocks,
                    decode_bc1_plane, decode_bc4_plane)
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = _HERE_PATH("_shots", "sld_render")
os.makedirs(OUT, exist_ok=True)

def mask(l):
    fmt, n = struct.unpack_from("<2H", l.data, 0)
    cmds = [struct.unpack_from("<2B", l.data, 4 + 2 * i) for i in range(n)]
    return fmt, cmds, sum(c[0] + c[1] for c in cmds)

print("=== grid invariant: sum(skip+draw) == main bw*bh ===")
c = Counter()
for f in sorted(os.listdir(GP)):
    if not f.endswith(".sld"):
        continue
    p = os.path.join(GP, f)
    if os.path.getsize(p) == 0:
        continue
    try:
        s = read_sld(p)
    except Exception:
        continue
    for fr in s.frames:
        L = fr.layers
        if not isinstance(L, dict) or "main" not in L:
            continue
        r, mfmt, mn, mcmds = parse_rect_layer(L["main"])
        x1, y1, w, h, bw, bh = grid_of(r)
        g = bw * bh
        for nm in ("playercolor", "damage"):
            if nm not in L:
                continue
            c[nm + "_layers"] += 1
            fmt, cmds, cells = mask(L[nm])
            if cells == g:
                c[nm + "_cells==grid"] += 1
            else:
                c[nm + "_cells!=grid"] += 1
            if "fmt_0x%04x" % fmt:
                c[nm + "_fmt_0x%04x" % fmt] += 1
for k, v in sorted(c.items()):
    print("  %-30s %7d" % (k, v))

# ---------------------------------------------------------------- rendering
def blocks(l, header):
    if header == "mask":
        fmt, n = struct.unpack_from("<2H", l.data, 0)
        base = 4 + 2 * n
    else:
        fmt, n = struct.unpack_from("<2H", l.data, 8)
        base = 12 + 2 * n
    return [l.data[base + 8 * i: base + 8 * i + 8]
            for i in range(max(0, (l.size - base) // 8))]

def render(fn, fi):
    s = read_sld(os.path.join(GP, fn))
    fr = s.frames[fi]
    L = fr.layers
    w, h = fr.canvas_w, fr.canvas_h
    m = L["main"]
    rect, mfmt, mn, mcmds = parse_rect_layer(m)
    x1, y1, rw, rh, bw, bh = grid_of(rect)
    mplane, PW, PH = decode_bc1_plane(blocks(m, "rect"), bw, bh, mcmds)

    base = bytearray(w * h * 4)
    for gy in range(PH):
        for gx in range(PW):
            sx, sy = x1 + gx, y1 + gy
            if 0 <= sx < w and 0 <= sy < h:
                o = (sy * w + sx) * 4
                px = mplane[(gy * PW + gx) * 4:(gy * PW + gx) * 4 + 4]
                if px[3]:
                    base[o:o + 4] = bytes(px)

    panels = [("main only", base)]

    if "playercolor" in L:
        pf, pc, _ = mask(L["playercolor"])
        ppl, _, _ = decode_bc4_plane(blocks(L["playercolor"], "mask"), bw, bh, pc)
        p = bytearray(base)
        for gy in range(PH):
            for gx in range(PW):
                sx, sy = x1 + gx, y1 + gy
                if not (0 <= sx < w and 0 <= sy < h):
                    continue
                o = (sy * w + sx) * 4
                if not p[o + 3]:
                    continue
                k = ppl[gy * bw + gx]
                if k:
                    fq = k / 255.0
                    p[o] = int(p[o] * (1 - fq) + 220 * fq)
                    p[o + 1] = int(p[o + 1] * (1 - fq) + 60 * fq)
                    p[o + 2] = int(p[o + 2] * (1 - fq) + 60 * fq)
        panels.append(("+playercolor\n(red tint)", p))

    if "damage" in L:
        df, dc, _ = mask(L["damage"])
        dpl, _, _ = decode_bc4_plane(blocks(L["damage"], "mask"), bw, bh, dc)
        p = bytearray(base)
        for gy in range(PH):
            for gx in range(PW):
                sx, sy = x1 + gx, y1 + gy
                if not (0 <= sx < w and 0 <= sy < h):
                    continue
                o = (sy * w + sx) * 4
                if not p[o + 3]:
                    continue
                k = dpl[gy * bw + gx]
                if k:
                    fq = k / 255.0
                    p[o] = int(p[o] * (1 - fq) + 40 * fq)
                    p[o + 1] = int(p[o + 1] * (1 - fq) + 40 * fq)
                    p[o + 2] = int(p[o + 2] * (1 - fq) + 40 * fq)
        panels.append(("+damage\n(dark tint, fmt=0x%04x)" % df, p))
        # damage plane alone, on main's grid
        q = bytearray(w * h * 4)
        for gy in range(PH):
            for gx in range(PW):
                sx, sy = x1 + gx, y1 + gy
                if 0 <= sx < w and 0 <= sy < h:
                    o = (sy * w + sx) * 4
                    v = dpl[gy * bw + gx]
                    q[o:o + 4] = bytes((v, v, v, 255))
        panels.append(("damage mask\n(alone)", q))

    crops = []
    for label, buf in panels:
        im = Image.frombytes("RGBA", (w, h), bytes(buf))
        im = im.crop((max(0, x1 - 6), max(0, y1 - 6),
                      min(w, x1 + rw + 6), min(h, y1 + rh + 6)))
        sc = max(1, min(3, 380 // max(1, im.height)))
        im = im.resize((im.width * sc, im.height * sc), Image.NEAREST)
        crops.append((label, im))
    return ("%s f%d ft=0x%02x %dx%d main=%s grid=%dx%d"
            % (fn, fi, fr.frame_type, w, h, rect, bw, bh), crops)

JOBS = [("b_afri_archery_range_age2_x1.sld", 0),
        ("b_afri_gate_stone_e_constr_x1.sld", 2),
        ("b_afri_gate_stone_n_constr_x1.sld", 2),
        ("b_afri_mill_age2_x1.sld", 1),
        ("b_west_castle_age3_x1.sld", 0),
        ("b_dark_barracks_age1_x1.sld", 0)]
rows = []
for fn, fi in JOBS:
    if not os.path.exists(os.path.join(GP, fn)):
        print("(missing)", fn)
        continue
    t, cs = render(fn, fi)
    rows.append((t, cs))
    print(t, "->", [x[0].split("\n")[0] for x in cs])

if rows:
    maxp = max(len(cs) for _, cs in rows)
    cw = max(im.width for _, cs in rows for _, im in cs) + 12
    ch = max(im.height for _, cs in rows for _, im in cs) + 32
    sheet = Image.new("RGBA", (cw * maxp, ch * len(rows)), (18, 18, 22, 255))
    d = ImageDraw.Draw(sheet)
    for r, (t, cs) in enumerate(rows):
        d.text((6, r * ch + 2), t[:150], fill=(235, 235, 235))
        for i, (lab, im) in enumerate(cs):
            d.text((i * cw + 6, r * ch + 15), lab.replace("\n", " ")[:46],
                   fill=(160, 200, 255))
            sheet.alpha_composite(im, (i * cw + 6, r * ch + 29))
    p = os.path.join(OUT, "damage_fixed.png")
    sheet.save(p)
    print("\n->", p, sheet.size)
