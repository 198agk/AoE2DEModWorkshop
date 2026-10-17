# -*- coding: utf-8 -*-
"""Is the vanilla top bar OPAQUE? 550412 halves its alpha (64/255).
The top bar spans the full width over terrain that varies (desert tan vs dark trees).
 - vanilla (top-bar_tile.png is RGB, no alpha)  -> uniform dark wood across x
 - mod (alpha 64)                               -> colour follows the terrain behind it
So column-colour variance across the bar tells us whether the override applied.
"""
import os
from PIL import Image

OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\ui"
os.makedirs(OUT, exist_ok=True)
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
f1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
im = Image.open(f1).convert("RGB")
W, H = im.size
print("shot:", im.size)

# --- row profile: find the top bar band (rows that are dark & low-variance) ---
px = im.load()
print()
print("row  meanR meanG meanB   minB maxB")
for y in range(0, 120, 4):
    vals = [px[x, y] for x in range(0, W, 8)]
    mr = sum(v[0] for v in vals) / len(vals)
    mg = sum(v[1] for v in vals) / len(vals)
    mb = sum(v[2] for v in vals) / len(vals)
    bs = sorted(v[2] for v in vals)
    print("%4d %6.1f %5.1f %5.1f  %4d %4d" % (y, mr, mg, mb, bs[0], bs[-1]))

# --- pick a band inside the top bar and measure column variance ---
for y0, y1, tag in ((14, 26, "topbar_upper"), (28, 44, "topbar_mid"), (46, 60, "topbar_lower"),
                    (86, 110, "terrain_below_bar"), (1180, 1210, "mid_game_terrain")):
    cols = []
    for x in range(0, W, 6):
        vals = [px[x, y] for y in range(y0, y1)]
        cols.append(tuple(sum(v[i] for v in vals) / len(vals) for i in range(3)))
    mr = sum(c[0] for c in cols) / len(cols)
    mg = sum(c[1] for c in cols) / len(cols)
    mb = sum(c[2] for c in cols) / len(cols)
    var = sum((c[0] - mr) ** 2 + (c[1] - mg) ** 2 + (c[2] - mb) ** 2 for c in cols) / len(cols)
    # luminance std as well
    lum = [0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in cols]
    ml = sum(lum) / len(lum)
    sd = (sum((v - ml) ** 2 for v in lum) / len(lum)) ** 0.5
    print()
    print("band %-18s y%d-%d  mean=(%.1f,%.1f,%.1f)  lumMean=%.1f  lumSD=%.1f  rgbVar=%.1f"
          % (tag, y0, y1, mr, mg, mb, ml, sd, var))

# --- save enlarged crops of the top bar for visual check ---
crop = im.crop((0, 0, W, 78))
crop = crop.resize((crop.width, crop.height * 6), Image.NEAREST)
crop.save(os.path.join(OUT, "topbar_x6.png"))
print()
print("wrote topbar_x6.png", crop.size)
