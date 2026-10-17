# -*- coding: utf-8 -*-
"""Is the floating chibi figure in the HUD a *crop from the chibi mod's emblem PNGs*?
If yes, the loose-PNG route DOES work and only the score panel differs.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, glob
import numpy as np
from PIL import Image

G = r"D:\Games\Steam\steamapps\common\AoE2DE"
CHIBI = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\182654_Age of Anime (Chibi Edition)\widgetui\textures\ingame\emblems"
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = _HERE_PATH("_shots", "ui")
os.makedirs(OUT, exist_ok=True)

f1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
im = Image.open(f1).convert("RGB")
print("shot:", im.size)

# --- 1. high-res crop of the HUD chibi figure (upper-left-ish of bottom band) ---
for box, tag, sc in (((560, 960, 800, 1260), "hudchibi", 4),
                     ((2280, 1010, 2700, 1500), "scoreemb", 3),
                     ((0, 1080, 560, 1535), "bottomleft", 3)):
    c = im.crop(box)
    c = c.resize((c.width * sc, c.height * sc), Image.LANCZOS)
    c.save(os.path.join(OUT, tag + ".png"))
    print("   wrote %s.png %s from %s" % (tag, c.size, box))

# --- 2. template search: chibi crop vs all emblem PNGs (multi-scale, NCC) ---
def to_arr(img, size=None):
    if size:
        img = img.resize(size, Image.LANCZOS)
    return np.asarray(img.convert("RGBA"), dtype=np.float32)

# use the whole bottom band of the shot as the search image
band = im.crop((0, 1000, 2730, 1400)).convert("RGB")
band_small = band.resize((band.width // 2, band.height // 2), Image.LANCZOS)
B = np.asarray(band_small, dtype=np.float32)
Bh, Bw, _ = B.shape

files = sorted(glob.glob(os.path.join(CHIBI, "*.png")))
print()
print("chibi emblem PNGs:", len(files))

results = []
for fp in files:
    try:
        src = Image.open(fp).convert("RGBA")
    except Exception:
        continue
    # try a few scales of the whole sheet placed anywhere in the band
    for scale in (0.18, 0.25, 0.33, 0.45, 0.6):
        tw = max(16, int(src.width * scale))
        th = max(16, int(src.height * scale))
        if tw >= Bw or th >= Bh:
            continue
        T = to_arr(src, (tw, th))
        tm = T[:, :, :3].mean(axis=2)
        ta = T[:, :, 3]
        # only match where template has alpha
        msk = ta > 40
        if msk.sum() < 50:
            continue
        tm_mean = tm[msk].mean()
        tm_c = (tm - tm_mean) * msk
        tden = np.sqrt((tm_c ** 2).sum())
        if tden < 1e-6:
            continue
        best = -2.0
        bestpos = None
        step = 4
        for y in range(0, Bh - th, step):
            for x in range(0, Bw - tw, step):
                win = B[y:y + th, x:x + tw].mean(axis=2)
                wm = win[msk]
                wc = (wm - wm.mean())
                den = np.sqrt((wc ** 2).sum()) * tden
                if den < 1e-6:
                    continue
                r = float((wc * tm_c[msk]).sum() / den)
                if r > best:
                    best = r
                    bestpos = (x * 2, y * 2 + 1000, int(tw * 2), int(th * 2))
        if bestpos:
            results.append((best, os.path.basename(fp), scale, bestpos))

results.sort(reverse=True)
print()
print("=== top 12 matches (NCC on luminance, band x0-2730 y1000-1400) ===")
for r in results[:12]:
    print("   r=%+.4f  %-26s scale=%.2f  at=%s" % (r[0], r[1], r[2], r[3]))

# --- 3. also compare against the vanilla emblems for control ---
V1 = os.path.join(G, "widgetui", "textures", "ingame", "emblems")
ctrl = []
for fp in sorted(glob.glob(os.path.join(V1, "*.png")))[:62]:
    src = Image.open(fp).convert("RGBA")
    for scale in (0.18, 0.25, 0.33, 0.45):
        tw = max(16, int(src.width * scale)); th = max(16, int(src.height * scale))
        if tw >= Bw or th >= Bh:
            continue
        T = to_arr(src, (tw, th))
        tm = T[:, :, :3].mean(axis=2); ta = T[:, :, 3]
        msk = ta > 40
        if msk.sum() < 50:
            continue
        tm_c = (tm - tm[msk].mean()) * msk
        tden = np.sqrt((tm_c ** 2).sum())
        if tden < 1e-6: continue
        best = -2
        for y in range(0, Bh - th, 4):
            for x in range(0, Bw - tw, 4):
                win = B[y:y + th, x:x + tw].mean(axis=2)
                wc = win[msk] - win[msk].mean()
                den = np.sqrt((wc ** 2).sum()) * tden
                if den < 1e-6: continue
                r = float((wc * tm_c[msk]).sum() / den)
                if r > best: best = r
        ctrl.append((best, os.path.basename(fp), scale))
ctrl.sort(reverse=True)
print()
print("=== control: top 6 vanilla V1 emblem matches ===")
for r in ctrl[:6]:
    print("   r=%+.4f  %-26s scale=%.2f" % r)
