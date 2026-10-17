# -*- coding: utf-8 -*-
"""Locate the player-list emblem column precisely, then settle its family.

The earlier scoreemb.png (crop 2280,1010,2700,1500 at 3x) showed the emblem column
around 44-57% of that crop's width -> original x approx 2467..2520. My previous
boxes at x2555..2645 missed. Find the column by looking for columns with high
vertical structure and warm/desaturated parchment tone, then crop each row.
"""
import os
import numpy as np
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\ui"
V1 = os.path.join(GAME, "widgetui", "textures", "ingame", "emblems")
V2 = os.path.join(GAME, "resources", "_common", "wpfg", "resources", "civ_emblems")
MODDIR = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\182654_Age of Anime (Chibi Edition)\widgetui\textures\ingame\emblems"

F1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
im = Image.open(F1).convert("RGB")

BAND = (2380, 1000, 2730, 1500)
c = im.crop(BAND)
c.resize((c.width * 3, c.height * 3), Image.LANCZOS).save(os.path.join(OUT, "plist_band.png"))
print("wrote plist_band.png", (c.width * 3, c.height * 3), "from", BAND)

a = np.asarray(c, dtype=np.float32)
lum = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
# column "busyness": std along y, smoothed across x
colstd = lum.std(axis=0)
k = np.ones(9) / 9.0
colsm = np.convolve(colstd, k, mode="same")
mx = int(np.argmax(colsm))
print("busiest column at x=%d (abs %d), std=%.1f" % (mx, BAND[0] + mx, colsm[mx]))
print("top 6 columns:", [(int(i + BAND[0]), round(float(colsm[i]), 1))
                         for i in np.argsort(colsm)[-6:][::-1]])

# pick the emblem column as the strongest local peak, then define row boxes
CX = int(np.argsort(colsm)[-3])          # third busiest, robust against the bar edge
print("using centre column x=%d (abs %d)" % (CX, BAND[0] + CX))

# panel rows: from the fourway sheet the 8 rows sat at ~46 px pitch starting y~1020
ROWS = [("1 RemonBo (Lithuanians)", 1018), ("8 mingkang", 1071), ("7 sunquan", 1124),
        ("6 majurian", 1177), ("5 ingvar", 1230), ("3 eipa", 1283),
        ("2 dominik", 1336), ("4 cabelo", 1389)]
W, H = 74, 62
boxes = [(lab, (BAND[0] + CX - W // 2, y, BAND[0] + CX + W // 2, y + H)) for lab, y in ROWS]


def lumof(x):
    return 0.299 * x[:, :, 0] + 0.587 * x[:, :, 1] + 0.114 * x[:, :, 2]


def rank(crop, folder):
    ow, oh = crop.size
    obs = np.asarray(crop, dtype=np.float32)
    ol = lumof(obs)
    out = []
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".png"):
            continue
        try:
            s = np.asarray(Image.open(os.path.join(folder, fn)).convert("RGBA").resize((ow, oh), Image.LANCZOS), dtype=np.float32)
        except Exception:
            continue
        m = s[:, :, 3] > 60
        if m.sum() < 80:
            continue
        A = ol[m] - ol[m].mean()
        B = lumof(s)[m] - lumof(s)[m].mean()
        den = np.sqrt((A * A).sum() * (B * B).sum())
        if den:
            out.append((float((A * B).sum() / den), fn))
    out.sort(reverse=True)
    return out


print()
print("=== per-row best match per family ===")
tiles = []
for lab, box in boxes:
    cr = im.crop(box)
    rm = rank(cr, MODDIR)[:2]
    r1 = rank(cr, V1)[:2]
    r2 = rank(cr, V2)[:2]
    winner = max([("MOD", rm[0][0]), ("V1", r1[0][0]), ("V2", r2[0][0])], key=lambda z: z[1])
    print("  %-24s MOD %+0.3f %-16s | V1 %+0.3f %-16s | V2 %+0.3f %-16s  -> %s"
          % (lab, rm[0][0], rm[0][1], r1[0][0], r1[0][1], r2[0][0], r2[0][1], winner[0]))
    tiles.append((lab, cr))

# side-by-side for row 1 (Lithuanians) with all three families
Z = 3
obs = tiles[0][1]
ow, oh = obs.size
sht = [("PLIST row1 observed", obs)]
for folder, tag in ((MODDIR, "MOD"), (V1, "V1"), (V2, "V2")):
    p = os.path.join(folder, "lithuanians.png")
    if os.path.exists(p):
        s = Image.open(p).convert("RGBA")
        bgs = Image.new("RGBA", s.size, (72, 64, 56, 255))
        bgs.alpha_composite(s)
        sht.append(("%s lithuanians" % tag, bgs.convert("RGB").resize((ow, oh), Image.LANCZOS)))
sh = Image.new("RGB", (ow * Z * len(sht), oh * Z + 18), (15, 15, 15))
d = ImageDraw.Draw(sh)
for i, (t, mg) in enumerate(sht):
    sh.paste(mg.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 18))
    d.text((i * ow * Z + 3, 3), t, fill=(255, 255, 0))
sh.save(os.path.join(OUT, "plist_row1_vs_families.png"))
print("wrote plist_row1_vs_families.png", sh.size)

# full player-list column strip vs the two vanilla families, for the record
strip = Image.new("RGB", (ow * Z * len(tiles), oh * Z), (15, 15, 15))
for i, (lab, cr) in enumerate(tiles):
    strip.paste(cr.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 0))
strip.save(os.path.join(OUT, "plist_rows_all.png"))
print("wrote plist_rows_all.png", strip.size)
