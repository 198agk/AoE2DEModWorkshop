# -*- coding: utf-8 -*-
"""DECISIVE + QUANTITATIVE: solve for the top bar's alpha from the camera pan.

Setup: the same panel art (constant) is composited over DIFFERENT terrain in
each frame, because the camera panned. For any two frames i,j:

    observed_i - observed_j = (1 - a) * (terrain_i - terrain_j)

so a linear fit of bar-change against terrain-change gives (1-a), hence alpha.
Terrain change is proxied by the image band just BELOW the bar, which shares
the same camera displacement.
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
G = {}
for k, (d, n) in F.items():
    G[k] = np.asarray(Image.open(os.path.join(SHOTS, d, n)).convert("L"), dtype=np.float32)

# --- where is the top bar, and where is free terrain we can use as reference?
# Scan row-mean brightness down the full width to locate the bar band and check
# that a usable terrain band exists right below it.
full = G["f1"]
print("row profile (f1), y=0..200, mean over x=200..2500")
for y in range(0, 200, 4):
    row = full[y, 200:2500]
    print("  y=%3d  mean=%6.1f  sd=%5.1f" % (y, float(row.mean()), float(row.std())))

BAR = (40, 58)        # the repeated top-bar tile rows (from the mod: 246x52 art)
REF = (150, 168)      # terrain proxy band just below the bar
X0, X1 = 200, 2500

print()
print("=== alpha solve: top bar rows %s vs terrain proxy rows %s ===" % (BAR, REF))
print("%-8s %10s %10s %10s" % ("pair", "barchg", "refchg", "1-a"))
ratios = []
for k in ["f2", "f3", "f4", "f5"]:
    b = np.abs(G[k][BAR[0]:BAR[1], X0:X1] - G["f1"][BAR[0]:BAR[1], X0:X1])
    r = np.abs(G[k][REF[0]:REF[1], X0:X1] - G["f1"][REF[0]:REF[1], X0:X1])
    bch, rch = float(b.mean()), float(r.mean())
    slope = bch / rch if rch > 1e-6 else float("nan")
    ratios.append(slope)
    print("%-8s %10.3f %10.3f %10.4f" % ("f1-%s" % k, bch, rch, slope))
print()
print("mean (1-a) = %.4f  ->  alpha ~= %.1f / 255  (opacity %.0f%%)"
      % (float(np.mean(ratios)), 255 * (1 - float(np.mean(ratios))),
         100 * (1 - float(np.mean(ratios)))))

# --- Second, independent estimate: per-column regression, which is robust to
#     differences in terrain statistics between the two bands.
print()
print("=== per-column regression across the 4 frame pairs (per 200px column) ===")
print("%-12s %10s %10s %10s" % ("x-band", "slope", "r", "alpha"))
allslope = []
for x0 in range(200, 2500, 200):
    x1 = x0 + 200
    B, R = [], []
    for k in ["f2", "f3", "f4", "f5"]:
        b = np.abs(G[k][BAR[0]:BAR[1], x0:x1] - G["f1"][BAR[0]:BAR[1], x0:x1]).ravel()
        r = np.abs(G[k][REF[0]:REF[1], x0:x1] - G["f1"][REF[0]:REF[1], x0:x1]).ravel()
        B.append(b)
        R.append(r)
    B = np.concatenate(B)
    R = np.concatenate(R)
    if R.std() < 1e-6:
        continue
    slope = float(np.cov(B, R)[0, 1] / np.var(R))
    r = float(np.corrcoef(B, R)[0, 1])
    allslope.append(slope)
    print("%-12s %10.4f %10.3f %10.1f" % ("x %d-%d" % (x0, x1), slope, r, 255 * (1 - slope)))
print()
print("median slope = %.4f  ->  alpha ~= %.1f / 255"
      % (float(np.median(allslope)), 255 * (1 - float(np.median(allslope)))))
