# -*- coding: utf-8 -*-
"""Measure the CAMERA translation between the 5 frames.

The crossframe.py result is useless if the camera panned, because then the
terrain behind the HUD differs for reasons unrelated to HUD alpha.
Here: brute-force integer translation search on a terrain window, so we know
whether "CHANGING" means "transparent" or just "camera moved".
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
frames = {}
for k, (d, n) in F.items():
    frames[k] = np.asarray(Image.open(os.path.join(SHOTS, d, n)).convert("L"), dtype=np.float32)

# a terrain-only search window (avoids HUD): world is roughly y 120..1150, x 0..2700
SX0, SY0, SX1, SY1 = 900, 400, 1500, 600   # 600x200 patch
ref = frames["f1"][SY0:SY1, SX0:SX1]
ref = ref - ref.mean()

R = 80  # search radius
print("reference patch", (SX0, SY0, SX1, SY1), "search radius", R)
print()
print("%-4s %8s %8s %10s   %s" % ("fr", "dx", "dy", "resid", "note"))
for k in frames:
    if k == "f1":
        continue
    cur = frames[k]
    best = None
    for dy in range(-R, R + 1, 1):
        for dx in range(-R, R + 1, 1):
            yy, xx = SY0 + dy, SX0 + dx
            if yy < 0 or xx < 0 or yy + 200 > cur.shape[0] or xx + 600 > cur.shape[1]:
                continue
            w = cur[yy:yy + 200, xx:xx + 600]
            w = w - w.mean()
            # normalized cross correlation
            den = (np.sqrt((w * w).sum()) * np.sqrt((ref * ref).sum()))
            if den <= 0:
                continue
            ncc = float((w * ref).sum() / den)
            if best is None or ncc > best[0]:
                best = (ncc, dx, dy)
    ncc, dx, dy = best
    # residual mean abs diff at best alignment
    w = cur[SY0 + dy:SY0 + dy + 200, SX0 + dx:SX0 + dx + 600]
    resid = float(np.abs(w - frames["f1"][SY0:SY1, SX0:SX1]).mean())
    resid0 = float(np.abs(cur[SY0:SY1, SX0:SX1] - frames["f1"][SY0:SY1, SX0:SX1]).mean())
    note = "camera shifted" if (dx or dy) else "no shift"
    print("%-4s %8d %8d %10.3f   ncc=%.4f  unaligned_resid=%.2f  %s" % (k, dx, dy, resid, ncc, resid0, note))
