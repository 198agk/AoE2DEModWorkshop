# -*- coding: utf-8 -*-
"""Find which asset directory holds the FULL-COLOUR heraldic shields used in the
player list (x 2656..2694, rows y 1088..1291).

Observed: saturated multi-hue shields (red castle, gold coin, black/red crest,
gold eagle, blue/yellow pinwheel, silver helm, red cross shield, green/red
triangles). V1/V2 are monochrome-ish tan engravings. So the real source is a
third place. Scan every image-bearing directory for highly saturated,
multi-hue shield-like PNGs/DDS and rank.
"""
import os
import numpy as np
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SKIP = ("\\drs\\graphics", "\\atlas\\", "\\wwise\\", "\\sound\\")

hits = []
for root, dirs, files in os.walk(GAME):
    low = root.lower()
    if any(s in low for s in SKIP):
        dirs[:] = []
        continue
    exts = {}
    for f in files:
        e = os.path.splitext(f)[1].lower()
        exts[e] = exts.get(e, 0) + 1
    img = exts.get(".png", 0) + exts.get(".dds", 0) + exts.get(".jpg", 0)
    if img == 0:
        continue
    # sample a few images
    samples = [f for f in files if os.path.splitext(f)[1].lower() in (".png", ".dds", ".jpg")][:6]
    stats = []
    for s in samples:
        try:
            im = Image.open(os.path.join(root, s)).convert("RGBA")
        except Exception:
            continue
        if im.width < 32 or im.height < 32:
            continue
        a = np.asarray(im, dtype=np.float32)
        m = a[:, :, 3] > 60
        if m.sum() < 200:
            continue
        rgb = a[:, :, :3][m]
        sat = rgb.max(axis=1) - rgb.min(axis=1)
        # hue spread: how many distinct strong hues
        stats.append((float(sat.mean()), float((sat > 40).mean()), im.size, s))
    if not stats:
        continue
    msat = np.mean([s[0] for s in stats])
    frac = np.mean([s[1] for s in stats])
    if msat > 30 and frac > 0.10:
        rel = root.replace(GAME, "")
        hits.append((msat, frac, img, rel, stats[0][2], stats[0][3]))

hits.sort(reverse=True)
print("candidate directories with saturated colour art (top 40):")
print("%7s %7s %6s  %-64s %s" % ("meanSat", "frac>40", "imgs", "dir", "sample"))
for msat, frac, img, rel, size, s in hits[:40]:
    print("%7.1f %7.3f %6d  %-64s %s %s" % (msat, frac, img, rel[:64], size, s))
