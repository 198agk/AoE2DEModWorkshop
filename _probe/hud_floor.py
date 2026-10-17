# -*- coding: utf-8 -*-
"""Establish the per-frame noise floor for HUD regions.

crossframe.py found every HUD region "CHANGING", but camera_shift.py shows the
camera PANNED between f1/f2 (ncc 0.986) and f3/f4/f5 (ncc 0.18-0.30, at the
80px search limit). So "CHANGING" is confounded. This script separates the two
frames that share an identical camera (f1 vs f2) from the rest, and reports a
few HUD regions that are semantically OPAQUE (empty wood panel, panel border):
if they still change on f1-vs-f2 they cannot be opaque.
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
fr = {}
for k, (d, n) in F.items():
    fr[k] = np.asarray(Image.open(os.path.join(SHOTS, d, n)).convert("RGB"), dtype=np.int16)

REG = {
    # HUD regions that SHOULD be opaque if the panel art is opaque
    "TOPBAR_left_res": (6, 6, 700, 66),
    "TOPBAR_between": (760, 10, 1180, 60),
    "BOTTOM_left_decor": (20, 1180, 180, 1450),
    "BOTTOM_cmd_empty": (620, 1330, 900, 1420),
    "SCOREPANEL_dark": (2620, 800, 2700, 1180),
    # a pure-terrain control region (must change when camera pans)
    "WORLD_ctrl": (900, 400, 1500, 600),
}

print("=== per-frame mean|diff| vs f1, RGB ===")
print("%-18s %9s %9s %9s %9s   %s" % ("region", "f1-f2", "f1-f3", "f1-f4", "f1-f5", "camera"))
for n, (x0, y0, x1, y1) in REG.items():
    b = fr["f1"][y0:y1, x0:x1]
    row = [float(np.abs(fr[k][y0:y1, x0:x1] - b).mean()) for k in ["f2", "f3", "f4", "f5"]]
    cam = "SAME" if abs(row[0]) < 2 else ("PAN" if row[0] > 20 else "?")
    print("%-18s %9.2f %9.2f %9.2f %9.2f   %s" % (n, row[0], row[1], row[2], row[3], cam))

print()
print("=== f1 vs f2 only (identical camera, ncc 0.986): what still moves? ===")
b = fr["f1"]
o = fr["f2"]
D = np.abs(o - b).mean(axis=2)
print("whole frame  mean=%.2f  frac>8=%.3f" % (float(D.mean()), float((D > 8).mean())))
for n, (x0, y0, x1, y1) in REG.items():
    d = D[y0:y1, x0:x1]
    print("  %-18s mean=%6.2f  frac>8=%.3f  max=%5.1f" % (n, float(d.mean()), float((d > 8).mean()), float(d.max())))

# column profile of change across the WHOLE frame, to see which x-bands are static
print()
print("=== whole-frame change vs f2, binned by x (100px bins), y 0..1535 ===")
h, w = D.shape
for x0 in range(0, w, 200):
    x1 = min(x0 + 200, w)
    band = D[:, x0:x1]
    print("  x %4d-%4d  mean=%6.2f  frac>8=%.3f" % (x0, x1, float(band.mean()), float((band > 8).mean())))
