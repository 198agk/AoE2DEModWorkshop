# -*- coding: utf-8 -*-
"""Diagnose glyph alpha extraction + YO/baseline semantics; dump sample glyph crops."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, struct, json
from PIL import Image, ImageChops

FONTDIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\fonts"
OUT = _HERE_PATH("_probe", "hud_render")
name = "combined"
data = open(os.path.join(FONTDIR, name + ".box"), "rb").read()
ver, cnt, pages, srcpx = struct.unpack_from("<IIIf", data, 0)
recs = []
off = 16
for _ in range(cnt):
    recs.append(struct.unpack_from("<6fI3f", data, off)); off += 40
cmap = {}
for _ in range(cnt):
    cp, gi = struct.unpack_from("<HH", data, off); off += 4
    cmap[cp] = gi

rep = []
rep.append("header ver=%s cnt=%s pages=%s srcpx=%s" % (ver, cnt, pages, srcpx))

def page(i):
    return Image.open(os.path.join(FONTDIR, "%s_%04d.png" % (name, i))).convert("RGB")

# baseline hypothesis: bottom of a capital == baseline
for ch in "A0a.,":
    gi = cmap[ord(ch)]
    W, H, u0, u1, v0, v1, pg, XO, YO, adv = recs[gi]
    rep.append("%r gi=%d W=%.1f H=%.1f uv=(%.6f,%.6f)-(%.6f,%.6f) pg=%d XO=%.3f YO=%.3f adv=%.3f  YO+H=%.3f"
               % (ch, gi, W, H, u0, u1, v0, v1, pg, XO, YO, adv, YO + H))

# dump crops of '0' and 'A' to inspect the alpha
tiles = []
for ch in "0123456789A":
    gi = cmap[ord(ch)]
    W, H, u0, u1, v0, v1, pg, XO, YO, adv = recs[gi]
    im = page(pg)
    x0, y0 = int(round(u0 * im.width)), int(round(v0 * im.height))
    x1, y1 = int(round(u1 * im.width)), int(round(v1 * im.height))
    c = im.crop((x0, y0, x1, y1))
    r, g, b = c.split()
    a = ImageChops.lighter(ImageChops.lighter(r, g), b)
    hist = a.histogram()
    lo = sum(hist[:32]); mid = sum(hist[32:224]); hi = sum(hist[224:])
    rep.append("%r crop uv=%d,%d,%d,%d size=%s  alpha lo=%d mid=%d hi=%d  rgbmean=%s"
               % (ch, x0, y0, x1, y1, c.size, lo, mid, hi,
                  tuple(round(v, 1) for v in [sum(r.histogram()[i] * i for i in range(256)) / (r.width * r.height),
                                              sum(g.histogram()[i] * i for i in range(256)) / (g.width * g.height),
                                              sum(b.histogram()[i] * i for i in range(256)) / (b.width * b.height)])))
    big = c.resize((c.width * 4, c.height * 4), Image.NEAREST)
    tiles.append(big)

sheet = Image.new("RGB", (sum(t.width for t in tiles) + 10 * len(tiles), max(t.height for t in tiles)), (40, 40, 40))
x = 0
for t in tiles:
    sheet.paste(t, (x, 0)); x += t.width + 10
sheet.save(os.path.join(OUT, "glyph_diag.png"))
rep.append("sheet -> glyph_diag.png %s" % (sheet.size,))

# Where does the '0' glyph actually sit on the page? Dump a bigger neighbourhood.
gi = cmap[ord("0")]
W, H, u0, u1, v0, v1, pg, XO, YO, adv = recs[gi]
im = page(pg)
pad = 20
x0, y0 = int(round(u0 * im.width)) - pad, int(round(v0 * im.height)) - pad
c = im.crop((max(0, x0), max(0, y0), x1 + pad if False else int(round(u1 * im.width)) + pad, int(round(v1 * im.height)) + pad))
c = c.resize((c.width * 3, c.height * 3), Image.NEAREST)
c.save(os.path.join(OUT, "glyph_diag_0_ctx.png"))

txt = "\n".join(rep)
open(os.path.join(OUT, "glyph_diag.txt"), "w", encoding="utf-8").write(txt)
print(txt)
