# -*- coding: utf-8 -*-
"""FINAL DECISION on the two emblem families.

Grid sweep showed the player-list emblem column sits at x approx 2552..2622.
Here: detect the 8 row centres from the column's own saturation profile, crop
each emblem, and score against three candidate sets. Then build the final figure.

Apples-to-apples requires the SAME civ. Player 1 is RemonBo, civ 立陶宛
(Lithuanians) -> use lithuanians.png everywhere.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import numpy as np
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = _HERE_PATH("_shots", "ui")
V1 = os.path.join(GAME, "widgetui", "textures", "ingame", "emblems")
V2 = os.path.join(GAME, "resources", "_common", "wpfg", "resources", "civ_emblems")
MODDIR = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\182654_Age of Anime (Chibi Edition)\widgetui\textures\ingame\emblems"

F1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
im = Image.open(F1).convert("RGB")

X0, X1 = 2550, 2624
Y0, Y1 = 985, 1465
col = im.crop((X0, Y0, X1, Y1))
a = np.asarray(col, dtype=np.float32)
sat = a.max(axis=2) - a.min(axis=2)
prof = sat.mean(axis=1)
k = np.ones(7) / 7.0
prof_s = np.convolve(prof, k, mode="same")
print("row profile peaks in x %d..%d :" % (X0, X1))

# find 8 peaks with min separation
order = np.argsort(prof_s)[::-1]
peaks = []
for i in order:
    if all(abs(i - p) > 30 for p in peaks):
        peaks.append(int(i))
    if len(peaks) == 8:
        break
peaks.sort()
print("   detected row centres (abs y):", [Y0 + p for p in peaks])

H2 = 27  # half height

def lum(x):
    return 0.299 * x[:, :, 0] + 0.587 * x[:, :, 1] + 0.114 * x[:, :, 2]

def rank(crop, folder):
    ow, oh = crop.size
    obs = np.asarray(crop, dtype=np.float32)
    ol = lum(obs)
    out = []
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".png"):
            continue
        try:
            s = np.asarray(Image.open(os.path.join(folder, fn)).convert("RGBA").resize((ow, oh), Image.LANCZOS), dtype=np.float32)
        except Exception:
            continue
        m = s[:, :, 3] > 80
        if m.sum() < 120:
            continue
        A = ol[m] - ol[m].mean()
        B = lum(s)[m] - lum(s)[m].mean()
        den = np.sqrt((A * A).sum() * (B * B).sum())
        if den:
            out.append((float((A * B).sum() / den), fn))
    out.sort(reverse=True)
    return out

NAMES = ["RemonBo (Lithuanians)", "8 mingkang", "7 sunquan", "6 majurian",
         "5 ingvar", "3 eipa", "2 dominik", "4 cabelo"]

print()
print("=== player-list emblems: best per family ===")
crops = []
for lab, p in zip(NAMES, peaks):
    box = (X0, Y0 + p - H2, X1, Y0 + p + H2)
    cr = im.crop(box)
    crops.append((lab, cr))
    rm = rank(cr, MODDIR)[:1]
    r1 = rank(cr, V1)[:1]
    r2 = rank(cr, V2)[:1]
    winner = max([("MOD", rm[0][0]), ("V1", r1[0][0]), ("V2", r2[0][0])], key=lambda z: z[1])[0]
    print("  %-22s MOD %+0.3f %-14s | V1 %+0.3f %-14s | V2 %+0.3f %-14s -> %s"
          % (lab, rm[0][0], rm[0][1], r1[0][0], r1[0][1], r2[0][0], r2[0][1], winner))

# magnified sheet of the observed player-list emblems
Z = 4
ow, oh = crops[0][1].size
sheet = Image.new("RGB", (ow * Z * len(crops), oh * Z + 18), (15, 15, 15))
d = ImageDraw.Draw(sheet)
for i, (lab, cr) in enumerate(crops):
    sheet.paste(cr.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 18))
    d.text((i * ow * Z + 3, 3), lab.split()[0], fill=(255, 255, 0))
sheet.save(os.path.join(OUT, "plist_observed_zoom.png"))
print()
print("wrote plist_observed_zoom.png", sheet.size)

# apples-to-apples for row1: observed vs MOD/V1/V2 lithuanians
obs = crops[0][1]
ow, oh = obs.size
tiles = [("PLIST row1 OBSERVED", obs)]
for folder, tag in ((MODDIR, "MOD"), (V1, "V1"), (V2, "V2")):
    p = os.path.join(folder, "lithuanians.png")
    if os.path.exists(p):
        s = Image.open(p).convert("RGBA")
        bgs = Image.new("RGBA", s.size, (70, 60, 52, 255))
        bgs.alpha_composite(s)
        tiles.append(("%s lithuanians" % tag, bgs.convert("RGB").resize((ow, oh), Image.LANCZOS)))
Z = 5
sh = Image.new("RGB", (ow * Z * len(tiles), oh * Z + 18), (15, 15, 15))
d = ImageDraw.Draw(sh)
for i, (t, mg) in enumerate(tiles):
    sh.paste(mg.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 18))
    d.text((i * ow * Z + 3, 3), t, fill=(255, 255, 0))
sh.save(os.path.join(OUT, "plist_row1_lithuanians.png"))
print("wrote plist_row1_lithuanians.png", sh.size)
