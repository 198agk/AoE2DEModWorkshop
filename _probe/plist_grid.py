# -*- coding: utf-8 -*-
"""Grid sweep to pin the player-list emblem column and row centres exactly."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import numpy as np
from PIL import Image, ImageDraw

SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = _HERE_PATH("_shots", "ui")
F1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
im = Image.open(F1).convert("RGB")

# Grid over the whole score-panel/emblem area
BOX = (2500, 950, 2730, 1480)
Z = 4
c = im.crop(BOX).resize(((BOX[2] - BOX[0]) * Z, (BOX[3] - BOX[1]) * Z), Image.LANCZOS)
d = ImageDraw.Draw(c)
for x in range(BOX[0], BOX[2] + 1, 10):
    X = (x - BOX[0]) * Z
    d.line([X, 0, X, c.height], fill=(255, 0, 255), width=1)
    if x % 50 == 0:
        d.text((X + 2, 2), str(x), fill=(255, 255, 0))
for y in range(BOX[1], BOX[3] + 1, 10):
    Y = (y - BOX[1]) * Z
    d.line([0, Y, c.width, Y], fill=(0, 255, 255), width=1)
    if y % 50 == 0:
        d.text((2, Y + 2), str(y), fill=(255, 255, 0))
c.save(os.path.join(OUT, "plist_grid.png"))
print("wrote plist_grid.png", c.size, "over", BOX)

# column activity profile to find the emblem column numerically
a = np.asarray(im.crop(BOX), dtype=np.float32)
lum = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
sat = a.max(axis=2) - a.min(axis=2)
print()
print("column profile (abs x : lumSD : satMean):")
for i in range(0, a.shape[1], 5):
    print("   %4d : %6.1f : %6.1f" % (BOX[0] + i, lum[:, i].std(), sat[:, i].mean()))
