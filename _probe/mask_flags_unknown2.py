# -*- coding: utf-8 -*-
"""Three questions:
  Q1  what does the 0x0080 bit in a mask layer's fmt mean?
  Q2  what are the 24 playercolor layers whose sum(skip+draw) != main grid?
  Q3  can `unknown2` be decoded as a mask/colour layer on main's grid?
"""
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
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\sld_render"
os.makedirs(OUT, exist_ok=True)


def mask(l):
    fmt, n = struct.unpack_from("<2H", l.data, 0)
    cmds = [struct.unpack_from("<2B", l.data, 4 + 2 * i) for i in range(n)]
    return fmt, n, cmds, sum(c[0] + c[1] for c in cmds)


# ---------------- Q1 + Q2 ----------------
c = Counter()
outl = []
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
            fmt, n, cmds, cells = mask(L[nm])
            flag = "80" if fmt & 0x80 else "00"
            same = (cmds == mcmds)
            c["%s fmt=0x%04x cmds==main" % (nm, fmt)] += 1 if same else 0
            c["%s fmt=0x%04x cmds!=main" % (nm, fmt)] += 0 if same else 1
            c["%s flag=%s ncmd=%d" % (nm, flag, n)] += 0
            if cells != g:
                outl.append((f, fr.index, nm, fmt, n, cells, g, len(mcmds)))

print("=== Q1: fmt bit 0x80 vs command-array identity ===")
for k in sorted(c):
    if "cmds" in k:
        print("  %-34s %7d" % (k, c[k]))

print("\n=== Q2: mask layers whose cell count != main grid: %d ===" % len(outl))
for o in outl[:30]:
    print("   ", o)

# ---------------- Q3: unknown2 ----------------
print("\n=== Q3: unknown2 shape ===")
c2 = Counter()
samples = []
for f in sorted(os.listdir(GP))[:6000]:
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
        if not isinstance(L, dict) or "main" not in L or "unknown2" not in L:
            continue
        u = L["unknown2"]
        r, mfmt, mn, mcmds = parse_rect_layer(L["main"])
        x1, y1, w, h, bw, bh = grid_of(r)
        g = bw * bh
        # try mask layout
        fmt, n = struct.unpack_from("<2H", u.data, 0)
        ok_mask = (u.size == 8 + 2 * n + 8 * ((u.size - 8 - 2 * n) // 8))
        cmds = [struct.unpack_from("<2B", u.data, 4 + 2 * i) for i in range(n)] \
            if 4 + 2 * n <= len(u.data) else []
        cells = sum(a + b for a, b in cmds)
        c2["layers"] += 1
        c2["u16_0=%d" % fmt] += 1
        if cmds:
            c2["cells==main grid"] += 1 if cells == g else 0
            c2["cells!=main grid"] += 0 if cells == g else 1
        if len(samples) < 6:
            samples.append((f, fr.index, u.size, fmt, n, cells, g,
                            u.data[:40].hex(" ")))
for k, v in sorted(c2.items()):
    print("  %-24s %7d" % (k, v))
for s in samples:
    print("   sample:", s)

# ---------------- render unknown2 attempts ----------------
def render_unknown2(fn, fi):
    s = read_sld(os.path.join(GP, fn))
    fr = s.frames[fi]
    L = fr.layers
    w, h = fr.canvas_w, fr.canvas_h
    m = L["main"]
    rect, mfmt, mn, mcmds = parse_rect_layer(m)
    x1, y1, rw, rh, bw, bh = grid_of(rect)
    mbase = 12 + 2 * mn
    mblocks = [m.data[mbase + 8 * i: mbase + 8 * i + 8]
               for i in range((m.size - mbase) // 8)]
    mplane, PW, PH = decode_bc1_plane(mblocks, bw, bh, mcmds)
    base = bytearray(w * h * 4)
    for gy in range(PH):
        for gx in range(PW):
            sx, sy = x1 + gx, y1 + gy
            if 0 <= sx < w and 0 <= sy < h:
                o = (sy * w + sx) * 4
                px = mplane[(gy * PW + gx) * 4:(gy * PW + gx) * 4 + 4]
                if px[3]:
                    base[o:o + 4] = bytes(px)
    panels = [("main", base)]
    u = L["unknown2"]
    txt = u.data
    # attempt A: mask layout, whole payload as BC4 on main grid
    for label, header, dec in (("A mask-layout BC4", 4, "bc4"),
                               ("B mask-layout BC1", 4, "bc1"),
                               ("C rect-layout BC1", 12, "bc1")):
        try:
            fmt, n = struct.unpack_from("<2H", txt, 0) if header == 4 else \
                struct.unpack_from("<2H", txt, 8)
            cmds = [struct.unpack_from("<2B", txt, header + 2 * i)
                    for i in range(n)]
            b0 = header + 2 * n
            nb = (u.size - b0) // 8
            blocks = [txt[b0 + 8 * i: b0 + 8 * i + 8] for i in range(nb)]
            if dec == "bc4":
                pl, _, _ = decode_bc4_plane(blocks, bw, bh, cmds)
                q = bytearray(w * h * 4)
                for gy in range(PH):
                    for gx in range(PW):
                        sx, sy = x1 + gx, y1 + gy
                        if 0 <= sx < w and 0 <= sy < h:
                            o = (sy * w + sx) * 4
                            v = pl[gy * bw + gx]
                            q[o:o + 4] = bytes((v, v, v, 255))
                panels.append(("%s n=%d cells=%d)" % (label, n,
                              sum(a + b for a, b in cmds)), q))
            else:
                pl, PW2, PH2 = decode_bc1_plane(blocks, bw, bh, cmds)
                q = bytearray(w * h * 4)
                for gy in range(PH):
                    for gx in range(PW):
                        sx, sy = x1 + gx, y1 + gy
                        if 0 <= sx < w and 0 <= sy < h:
                            o = (sy * w + sx) * 4
                            q[o:o + 4] = pl[(gy * PW2 + gx) * 4:(gy * PW2 + gx) * 4 + 4]
                panels.append(("%s n=%d" % (label, n), q))
        except Exception as e:
            print("   (%s %s: %s)" % (fn, label, e))
    crops = []
    for label, buf in panels:
        im = Image.frombytes("RGBA", (w, h), bytes(buf))
        im = im.crop((max(0, x1 - 6), max(0, y1 - 6),
                      min(w, x1 + rw + 6), min(h, y1 + rh + 6)))
        sc = max(1, min(3, 300 // max(1, im.height)))
        im = im.resize((im.width * sc, im.height * sc), Image.NEAREST)
        crops.append((label, im))
    return ("%s f%d unknown2 size=%d %dx%d" % (fn, fi, u.size, w, h), crops)


SRC = r"D:\Games\Steam\steamapps\common\AoE2DE\_probe_src"
JOBS = []
for cand in ("u_arc_archer_idlea_x1.sld", "u_inf_militia_idlea_x1.sld",
             "u_cav_knight_idlea_x1.sld", "b_afri_stable_age2_x1.sld"):
    if os.path.exists(os.path.join(GP, cand)):
        JOBS.append((cand, 0))
rows = []
for fn, fi in JOBS:
    try:
        t, cs = render_unknown2(fn, fi)
        rows.append((t, cs))
        print(t, "->", [x[0].split(")")[0] for x in cs])
    except Exception as e:
        print("(%s: %s)" % (fn, e))
if rows:
    maxp = max(len(cs) for _, cs in rows)
    cw = max(im.width for _, cs in rows for _, im in cs) + 12
    ch = max(im.height for _, cs in rows for _, im in cs) + 32
    sheet = Image.new("RGBA", (cw * maxp, ch * len(rows)), (18, 18, 22, 255))
    d = ImageDraw.Draw(sheet)
    for r, (t, cs) in enumerate(rows):
        d.text((6, r * ch + 2), t[:150], fill=(235, 235, 235))
        for i, (lab, im) in enumerate(cs):
            d.text((i * cw + 6, r * ch + 15), lab[:52], fill=(160, 200, 255))
            sheet.alpha_composite(im, (i * cw + 6, r * ch + 29))
    p = os.path.join(OUT, "unknown2_hypotheses.png")
    sheet.save(p)
    print("\n->", p, sheet.size)
