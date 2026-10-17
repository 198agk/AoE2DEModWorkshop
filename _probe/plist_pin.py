# -*- coding: utf-8 -*-
"""Pin the exact x-band of the player-list emblem column.

Discriminators:
  * era-plaque column  = nearly IDENTICAL art in every row -> low inter-row variance
  * emblem column      = DIFFERENT art per row            -> high inter-row variance
  * text columns       = different per row, but luminance-heavy / low saturation
So: high inter-row variance + high saturation + dark surround == emblem column.
"""
import os
import numpy as np
from PIL import Image, ImageDraw

SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\ui"
F1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
im = Image.open(F1).convert("RGB")
A = np.asarray(im, dtype=np.float32)
sat = A.max(axis=2) - A.min(axis=2)

# --- locate the 8 roster rows using the era-plaque side (rightmost band) ---
band = sat[1000:1470, 2680:2726]
rp = band.mean(axis=1)
k = np.ones(9) / 9.0
rps = np.convolve(rp, k, mode="same")
order = np.argsort(rps)[::-1]
rows = []
for i in order:
    if all(abs(i - p) > 30 for p in rows):
        rows.append(int(i))
    if len(rows) == 8:
        break
rows.sort()
rows = [1000 + r for r in rows]
print("era-plaque row centres (abs y):", rows)

# --- per-column inter-row variance, restricted to the emblem vertical span ---
H2 = 24
print()
print("  x   interRowSD  meanSat   (y-span = rows +-%d)" % H2)
best = []
for x in range(2560, 2696, 2):
    patches = [sat[r - H2:r + H2, x] for r in rows]
    P = np.stack(patches, axis=0)
    sd = P.std(axis=0).mean()
    ms = sat[rows[0] - H2:rows[-1] + H2, x].mean()
    best.append((sd, x, ms))
best.sort(reverse=True)
for sd, x, ms in best[:14]:
    print("  %4d  %8.2f  %7.2f" % (x, sd, ms))

xs = sorted(b[1] for b in best[:12])
print()
print("top-12 x cluster:", xs)

# --- wide strip around the winner with a fine grid, for visual pinning ---
x0, x1 = 2570, 2700
y0, y1 = rows[0] - 60, rows[-1] + 60
Z = 5
crop = im.crop((x0, y0, x1, y1))
big = crop.resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
d = ImageDraw.Draw(big)
for ax in range(x0, x1 + 1, 10):
    gx = (ax - x0) * Z
    col = (255, 0, 255) if ax % 50 == 0 else (255, 160, 255)
    d.line([(gx, 0), (gx, big.size[1])], fill=col, width=1)
    if ax % 50 == 0:
        d.text((gx + 2, 2), str(ax), fill=(255, 255, 0))
for r in rows:
    gy = (r - y0) * Z
    d.line([(0, gy), (big.size[0], gy)], fill=(0, 255, 255), width=1)
big.save(os.path.join(OUT, "plist_pin.png"))
print("wrote plist_pin.png", big.size, "span x", x0, x1, "y", y0, y1)
print("rows:", rows)
