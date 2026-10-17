# -*- coding: utf-8 -*-
"""Compare alpha-extraction heuristics for the combined atlas pages.

Hypothesis: the latin glyphs used by the HUD are stored NEUTRAL (R~=G~=B) on a
black background, while neighbouring coloured copies of other scripts are
saturated (one channel dominant). max(R,G,B) therefore floods the crop with the
neighbour's colour; min(R,G,B) isolates the neutral glyph.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, struct
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
_pg = {}

def page(i):
    if i not in _pg:
        _pg[i] = Image.open(os.path.join(FONTDIR, "%s_%04d.png" % (name, i))).convert("RGB")
    return _pg[i]

def crop(gi):
    W, H, u0, u1, v0, v1, pg = recs[gi][:7]
    im = page(pg)
    return im.crop((int(round(u0 * im.width)), int(round(v0 * im.height)),
                    int(round(u1 * im.width)), int(round(v1 * im.height))))

rep = []
rows = []
for ch in "0123456789/":
    gi = cmap.get(ord(ch))
    if gi is None:
        rep.append("%r NOT IN CMAP" % ch); continue
    c = crop(gi)
    r, g, b = c.split()
    mx = ImageChops.lighter(ImageChops.lighter(r, g), b)
    mn = ImageChops.darker(ImageChops.darker(r, g), b)
    n = c.width * c.height
    for lbl, m in (("max", mx), ("min", mn)):
        h = m.histogram()
        hi = sum(h[224:]); lo = sum(h[:32])
        rep.append("%r gi=%-5d %s-crop  size=%s  %s: lo=%.1f%% hi=%.1f%% mean=%.1f"
                   % (ch, gi, "uv", c.size, lbl, 100.0 * lo / n, 100.0 * hi / n,
                      sum(i * h[i] for i in range(256)) / n))
    rows.append((ch, c, mn))

# render both variants of the digit string
for lbl in ("max", "min"):
    tiles = []
    for ch in "0123456789/":
        gi = cmap[ord(ch)]
        c = crop(gi)
        r, g, b = c.split()
        m = ImageChops.lighter(ImageChops.lighter(r, g), b) if lbl == "max" else ImageChops.darker(ImageChops.darker(r, g), b)
        t = Image.new("RGB", c.size, (30, 30, 30))
        t.paste(Image.new("RGB", c.size, (255, 255, 255)), (0, 0), m)
        tiles.append(t.resize((c.width * 3, c.height * 3), Image.NEAREST))
    sh = Image.new("RGB", (sum(t.width + 8 for t in tiles), max(t.height for t in tiles)), (30, 30, 30))
    x = 0
    for t in tiles:
        sh.paste(t, (x, 0)); x += t.width + 8
    sh.save(os.path.join(OUT, "glyph_alpha_%s.png" % lbl))
    rep.append("wrote glyph_alpha_%s.png %s" % (lbl, sh.size))

# Full-line check: render "10000" with each heuristic at the real PointSize 34.
for lbl in ("max", "min"):
    line = Image.new("RGB", (300, 60), (30, 30, 30))
    pen = 0
    for ch in "10000":
        gi = cmap[ord(ch)]
        c = crop(gi)
        r, g, b = c.split()
        m = ImageChops.lighter(ImageChops.lighter(r, g), b) if lbl == "max" else ImageChops.darker(ImageChops.darker(r, g), b)
        sc = 34.0 / 64.0
        gw, gh = max(1, int(round(c.width * sc))), max(1, int(round(c.height * sc)))
        m = m.resize((gw, gh), Image.LANCZOS)
        line.paste(Image.new("RGB", (gw, gh), (255, 255, 255)), (int(pen), 5), m)
        pen += recs[gi][9] * sc
    line.resize((line.width * 3, line.height * 3), Image.NEAREST).save(os.path.join(OUT, "glyph_line_%s.png" % lbl))
    rep.append("wrote glyph_line_%s.png" % lbl)

txt = "\n".join(rep)
open(os.path.join(OUT, "glyph_alpha_compare.txt"), "w", encoding="utf-8").write(txt)
print(txt)
