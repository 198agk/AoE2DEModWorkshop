# -*- coding: utf-8 -*-
"""Determine the real HUD's on-screen scale from the layout's KNOWN box positions.

Why the two earlier attempts failed (kept as a warning):
  v1 sliding_window_view template match -> broadcasting error: window axes are
     APPENDED, so an RGB image yields (H,W,h,w,3); the last axis is colour.
  v2 luminance dark-run detection -> locked onto TEXT edges, producing nonsense
     pitches like [211,119,317,22,14].
  v3 brute-force scale search of the whole plank as one template -> hit the
     search boundary at scale 0.60 with MAD 60-80, i.e. no real match. The plank
     cannot be the template because the screenshot may only show part of it.

This version exploits a much stronger constraint: the layout JSON pins each
resource box's position exactly, so for a candidate scale s there is exactly ONE
place to look -- no search over offsets needed.

From resourcepanel.json:
  Background Base  VP(0,0 1750x276 TopLeft)          -> ref top-left (0,0)
  Wood   Base      VP(57,57  84x84 CentreCentre)     -> left = 57-42 = 15
  Food   Base      VP(257,57 84x84 CentreCentre)     -> left = 257-42 = 215
  Gold   Base      VP(457,57 84x84 CentreCentre)     -> left = 457-42 = 415
  Stone  Base      VP(657,57 84x84 CentreCentre)     -> left = 657-42 = 615
So box i has ref rect (15 + 200*i, 15, 84, 84).

Score = mean |pixel - icon| over pixels where the icon's own alpha > 200.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import numpy as np
from PIL import Image

O = _HERE_PATH("_probe", "hud_render")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
ICONS = os.path.join(GAME, r"widgetui\textures\ingame\icons")
ATT = r"C:\Users\26913\.dsh\attachments\v1\objects"
SHOTS = [
    ("shot0", os.path.join(ATT, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")),
    ("shot1", os.path.join(ATT, "2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974")),
    ("shot2", os.path.join(ATT, "16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be")),
    ("shot3", os.path.join(ATT, "8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850")),
    ("shot4", os.path.join(ATT, "89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9")),
]
NAMES = ["wood", "food", "gold", "stone"]
SRC = [Image.open(os.path.join(ICONS, "resource_%s.png" % n)).convert("RGBA") for n in NAMES]

rep = []
rep.append("icons: %s" % ", ".join("resource_%s.png %s" % (n, SRC[i].size) for i, n in enumerate(NAMES)))
rep.append("predicted ref rect for box i: (%d + 200*i, 15, 84, 84)" % 15)
rep.append("")

SCALES = np.arange(0.25, 0.95, 0.002)
best_by_shot = {}
for tag, path in SHOTS:
    im = Image.open(path).convert("RGB")
    W, H = im.size
    arr = np.asarray(im, dtype=np.float64)
    curve = []
    for s in SCALES:
        bs = int(round(84 * s))
        if bs < 12 or bs > 200:
            curve.append((s, None, None))
            continue
        tot, cnt = 0.0, 0
        per = []
        for i in range(4):
            lx = int(round((15 + 200 * i) * s))
            ly = int(round(15 * s))
            if lx < 0 or ly < 0 or lx + bs > W or ly + bs > H:
                per = None
                break
            win = arr[ly:ly + bs, lx:lx + bs, :]
            ic = np.asarray(SRC[i].resize((bs, bs), Image.LANCZOS), dtype=np.float64)
            m = ic[:, :, 3] > 200
            if m.sum() < 20:
                per = None
                break
            per.append(float(np.abs(win[m] - ic[:, :, :3][m]).mean()))
        if per is None:
            curve.append((s, None, None))
        else:
            curve.append((s, float(np.mean(per)), per))
    valid = [(s, v) for s, v, _ in curve if v is not None]
    if not valid:
        rep.append("%s no valid scale" % tag)
        continue
    bs_sc, bs_v = min(valid, key=lambda t: t[1])
    best_by_shot[tag] = (bs_sc, bs_v, W, H)
    rep.append("%s %dx%d  W/3840=%.6f  H/2160=%.6f" % (tag, W, H, W / 3840.0, H / 2160.0))
    rep.append("   BEST scale=%.4f  mean|diff| over icon pixels=%.2f" % (bs_sc, bs_v))
    # local neighbourhood of the optimum, to show the curve is a real minimum
    nb = [(round(s, 3), round(v, 1)) for s, v in valid if abs(s - bs_sc) <= 0.06]
    rep.append("   curve near optimum (scale,score) every ~0.01: %s" % nb[::5])
    # per-box scores at the optimum
    for s, v, per in curve:
        if s == bs_sc and per:
            rep.append("   per-box at optimum: %s   (wood,food,gold,stone)" % [round(x, 1) for x in per])
    rep.append("   implied plank rect: (%d,%d,%d,%d)" % (0, 0, int(round(1750 * bs_sc)), int(round(276 * bs_sc))))
    rep.append("   implied box size 84*s = %.1f px ; pitch 200*s = %.1f px" % (84 * bs_sc, 200 * bs_sc))
    rep.append("")

if best_by_shot:
    ss = [v[0] for v in best_by_shot.values()]
    rep.append("MEAN scale over shots = %.4f   spread=%.4f" % (float(np.mean(ss)), float(np.max(ss) - np.min(ss))))
    rep.append("Compare with W/3840 = 0.7109 and H/2160 = 0.7106")
    rep.append("Ratio (mean scale)/(W/3840) = %.4f" % (float(np.mean(ss)) / (best_by_shot[list(best_by_shot)[0]][2] / 3840.0)))

txt = "\n".join(rep)
open(os.path.join(O, "align_measure.txt"), "w", encoding="utf-8").write(txt)
print(txt)
