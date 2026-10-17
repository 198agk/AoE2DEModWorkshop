# -*- coding: utf-8 -*-
"""Debug: why did s19_plankfit.py's masked match return None for every candidate?"""
import os
import numpy as np
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOT = r"C:\Users\26913\.dsh\attachments\v1\objects\02\0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"
PANE = os.path.join(GAME, r"widgetui\textures\ingame\panels\ASIA\resource-panel.png")

shot = Image.open(SHOT).convert("RGB")
W, H = shot.size
arr = np.asarray(shot, dtype=np.float64)
pane = Image.open(PANE).convert("RGBA")
PW, PH = pane.size
print("shot", shot.size, "pane", pane.size)
print("arr", arr.shape)

for scale in (0.20, 0.40, 0.598, 0.80, 1.0):
    tw, th = int(round(PW * scale)), int(round(PH * scale))
    for ox, oy in ((-60, -40), (0, 0), (8, 8), (60, 100)):
        cx0, cy0 = max(0, ox), max(0, oy)
        cx1, cy1 = min(W, ox + tw), min(H, oy + th)
        w = cx1 - cx0
        h = cy1 - cy0
        t = pane.resize((tw, th), Image.LANCZOS)
        ta = np.asarray(t, dtype=np.float64)
        sx0, sy0 = cx0 - ox, cy0 - oy
        tas = ta[sy0:sy0 + h, sx0:sx0 + w, :]
        win = arr[cy0:cy1, cx0:cx1, :]
        m = tas[:, :, 3] > 200
        print("scale=%.3f (%d,%d) tw,th=%d,%d clip=%d,%d,%d,%d slice=%s win=%s mask=%d shapes_eq=%s"
              % (scale, ox, oy, tw, th, cx0, cy0, cx1, cy1, tas.shape, win.shape, m.sum(),
                 tas.shape == win.shape))
