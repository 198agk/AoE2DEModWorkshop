# -*- coding: utf-8 -*-
"""Clean, assumption-light solve for the top bar's alpha.

Earlier attempt used "the band just below the bar" as a terrain proxy and gave
contradictory answers (alpha~2 vs alpha~194) with weak correlations, because
that band samples DIFFERENT world content than the pixels behind the bar.

Correct approach. Define the camera displacement between f1 and fk as (dx,dy),
meaning:  world point seen at screen (x,y) in f1 appears at (x+dx, y+dy) in fk.
Then the world seen under the bar in fk, at screen (x, ybar), is the SAME world
point as f1 screen (x-dx, ybar-dy). If ybar-dy lands BELOW the bar in f1, that
terrain pixel is directly observable -- no proxy, no assumption.

With two frames k1,k2 (k1=f3, k2=f4):
    obs_k1(x,ybar) = a*A(x,ybar) + (1-a)*T_k1(x,ybar)
    obs_k2(x,ybar) = a*A(x,ybar) + (1-a)*T_k2(x,ybar)
    A is identical (same art). Subtract:
    obs_k1 - obs_k2 = (1-a) * [ T_k1 - T_k2 ]
    and T_k1 = f1(x-dx1, ybar-dy1),  T_k2 = f1(x-dx2, ybar-dy2)
Every term on the right is readable from f1. So regress the observable
difference against the known terrain difference -> slope = (1-a).

Step 0: re-estimate the camera shift with a much larger search radius (f3 hit
the old limit at ncc 0.18, which is not a trustworthy match).
"""
import os
import numpy as np
from PIL import Image

SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
F = {
    "f1": ("02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    "f2": ("2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    "f3": ("16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    "f4": ("8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    "f5": ("89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
}
RGB = {}
L = {}
for k, (d, n) in F.items():
    im = Image.open(os.path.join(SHOTS, d, n)).convert("RGB")
    RGB[k] = np.asarray(im, dtype=np.float32)
    L[k] = np.asarray(im.convert("L"), dtype=np.float32)

# ---------- Step 0: camera shift, coarse-to-fine, big radius ----------
SX0, SY0, SW, SH = 1000, 380, 500, 220
ref = L["f1"][SY0:SY0 + SH, SX0:SX0 + SW]
ref = ref - ref.mean()
refn = np.sqrt((ref * ref).sum())


def best_shift(cur, R, step=1):
    best = (-2.0, 0, 0)
    for dy in range(-R, R + 1, step):
        for dx in range(-R, R + 1, step):
            yy, xx = SY0 + dy, SX0 + dx
            if yy < 0 or xx < 0 or yy + SH > cur.shape[0] or xx + SW > cur.shape[1]:
                continue
            w = cur[yy:yy + SH, xx:xx + SW]
            wc = w - w.mean()
            den = np.sqrt((wc * wc).sum()) * refn
            if den <= 0:
                continue
            ncc = float((wc * ref).sum() / den)
            if ncc > best[0]:
                best = (ncc, dx, dy)
    return best


SHIFTS = {}
print("=== camera shift vs f1 (coarse radius 300, then refine) ===")
print("%-4s %8s %8s %8s" % ("fr", "dx", "dy", "ncc"))
SHIFTS["f1"] = (0, 0)
for k in ["f2", "f3", "f4", "f5"]:
    ncc, dx, dy = best_shift(L[k], 300, 4)
    # refine +-4 around the coarse hit
    best = (-2.0, dx, dy)
    for ddy in range(dy - 4, dy + 5):
        for ddx in range(dx - 4, dx + 5):
            yy, xx = SY0 + ddy, SX0 + ddx
            if yy < 0 or xx < 0 or yy + SH > L[k].shape[0] or xx + SW > L[k].shape[1]:
                continue
            w = L[k][yy:yy + SH, xx:xx + SW]
            wc = w - w.mean()
            den = np.sqrt((wc * wc).sum()) * refn
            if den <= 0:
                continue
            v = float((wc * ref).sum() / den)
            if v > best[0]:
                best = (v, ddx, ddy)
    SHIFTS[k] = (best[1], best[2])
    print("%-4s %8d %8d %8.4f" % (k, best[1], best[2], best[0]))

# ---------- Step 1: locate the top bar's vertical extent ----------
# The bar art is a repeated tile; detect where the frame becomes "structured"
# by finding the row band whose pixels are most repeated horizontally.
print()
print("=== horizontal self-similarity by row (f1): high value = tiled bar art ===")
row = L["f1"]
scores = []
for y in range(0, 160):
    r = row[y, 100:2600]
    # compare each 82-px chunk against the next one (tile pitch from the mod art)
    s = []
    for pitch in (246, 164, 82):
        a = r[:-pitch]
        b = r[pitch:]
        if len(a) < 50:
            continue
        s.append(float(np.corrcoef(a, b)[0, 1]))
    scores.append((y, max(s) if s else 0.0))
for y, v in scores:
    if y % 2 == 0:
        bar = "#" * max(0, int((v + 1) * 20))
        print("  y=%3d  selfsim=%6.3f %s" % (y, v, bar))
