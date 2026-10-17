# -*- coding: utf-8 -*-
"""Player-list emblem family: FINAL, on the CORRECT band.

plist_pin.png showed the emblem column is at abs x ~ 2658..2690 (the earlier
2550..2624 band was the score text). Detect the 8 rows from that band's own
saturation profile, using autocorrelation for the pitch, then score.

Row1 owner is RemonBo, civ 立陶宛 (Lithuanians) -> lithuanians.png is the
apples-to-apples reference for every family.
"""
import os
import numpy as np
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\ui"
V1 = os.path.join(GAME, "widgetui", "textures", "ingame", "emblems")
V2 = os.path.join(GAME, "resources", "_common", "wpfg", "resources", "civ_emblems")
MOD = (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
       r"\subscribed\182654_Age of Anime (Chibi Edition)"
       r"\widgetui\textures\ingame\emblems")
F1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
im = Image.open(F1).convert("RGB")
A = np.asarray(im, dtype=np.float32)
sat = A.max(axis=2) - A.min(axis=2)

X0, X1 = 2656, 2694
prof = sat[960:1340, X0:X1].mean(axis=1)
prof = prof - prof.mean()

# autocorrelation -> dominant pitch
ac = np.correlate(prof, prof, mode="full")[len(prof) - 1:]
ac[:6] = 0
pitch = int(np.argmax(ac[14:60]) + 14)
print("column x %d..%d  detected row pitch = %d px" % (X0, X1, pitch))

# phase: best offset of a comb with that pitch
best = None
for off in range(pitch):
    idx = np.arange(off, len(prof), pitch)
    v = prof[idx].sum()
    if best is None or v > best[1]:
        best = (off, v)
rows = [960 + int(i) for i in np.arange(best[0], len(prof), pitch)]
print("row centres (abs y):", rows, " count =", len(rows))

H2 = max(10, pitch // 2 - 3)


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
            s = np.asarray(Image.open(os.path.join(folder, fn)).convert("RGBA")
                           .resize((ow, oh), Image.LANCZOS), dtype=np.float32)
        except Exception:
            continue
        m = s[:, :, 3] > 80
        if m.sum() < 100:
            continue
        A_ = ol[m] - ol[m].mean()
        B_ = lum(s)[m] - lum(s)[m].mean()
        den = np.sqrt((A_ * A_).sum() * (B_ * B_).sum())
        if den:
            out.append((float((A_ * B_).sum() / den), fn))
    out.sort(reverse=True)
    return out


print()
print("=== per-row best match (crop x %d..%d, h=%d) ===" % (X0, X1, 2 * H2))
crops = []
for i, r in enumerate(rows):
    box = (X0, r - H2, X1, r + H2)
    cr = im.crop(box)
    crops.append(("row%d y=%d" % (i + 1, r), cr))
    rm = rank(cr, MOD)[:1]
    r1 = rank(cr, V1)[:1]
    r2 = rank(cr, V2)[:1]
    tri = [("MOD", rm[0][0]), ("V1", r1[0][0]), ("V2", r2[0][0])]
    w = max(tri, key=lambda z: z[1])
    print("  %-11s MOD %+0.3f %-16s V1 %+0.3f %-16s V2 %+0.3f %-16s -> %s"
          % (crops[-1][0], rm[0][0], rm[0][1], r1[0][0], r1[0][1],
             r2[0][0], r2[0][1], w[0]))

# ---- final figure: observed row1 vs the three lithuanians.png ----
obs = crops[0][1]
ow, oh = obs.size
tiles = [("PLIST row1 OBSERVED", obs)]
for folder, tag in ((MOD, "MOD"), (V1, "V1"), (V2, "V2")):
    p = os.path.join(folder, "lithuanians.png")
    if os.path.exists(p):
        s = Image.open(p).convert("RGBA")
        bg = Image.new("RGBA", s.size, (68, 58, 50, 255))
        bg.alpha_composite(s)
        tiles.append(("%s lithuanians.png" % tag,
                      bg.convert("RGB").resize((ow, oh), Image.LANCZOS)))
Z = 6
sh = Image.new("RGB", (ow * Z * len(tiles), oh * Z + 20), (12, 12, 12))
d = ImageDraw.Draw(sh)
for i, (t, mg) in enumerate(tiles):
    sh.paste(mg.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 20))
    d.text((i * ow * Z + 4, 4), t, fill=(255, 255, 0))
sh.save(os.path.join(OUT, "plist_row1_FINAL.png"))
print()
print("wrote plist_row1_FINAL.png", sh.size)

Z = 4
sh2 = Image.new("RGB", (ow * Z * len(crops), oh * Z + 20), (12, 12, 12))
d = ImageDraw.Draw(sh2)
for i, (lab, cr) in enumerate(crops):
    sh2.paste(cr.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 20))
    d.text((i * ow * Z + 4, 4), lab, fill=(255, 255, 0))
sh2.save(os.path.join(OUT, "plist_observed_FINAL.png"))
print("wrote plist_observed_FINAL.png", sh2.size)
