# -*- coding: utf-8 -*-
"""Is the floating chibi girl screen-anchored (UI widget) or world-anchored (sprite)?

Decisive test: f1 vs f2 have a STATIC camera (measured dx=dy=0, ncc 0.9869).
  * If the chibi is a UI widget, its screen position must be identical in f1 and f2
    (unless the widget itself is animated).
  * If it is a world object, its screen position must track the camera shift
    (f1->f3 (67,-144), f1->f4 (224,99), f1->f5 (127,115)).

Signature mask for the character: strong red dress (r-g>=50 and r-b>=60),
bright desaturated grey hat, and very dark low-luminance hair/boots.
Sandy terrain (163,127,95) has r-g=36, so it is excluded by the r-g>=50 gate.
"""
import os
import numpy as np
from PIL import Image

SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
F = [
    ("f1_29s", "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    ("f2_37s", "2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    ("f3_43s", "16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    ("f4_49s", "8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    ("f5_55s", "89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
]

CAM = {  # f1 -> fk screen displacement of a world point
    "f1_29s": (0, 0),
    "f2_37s": (0, 0),
    "f3_43s": (67, -144),
    "f4_49s": (224, 99),
    "f5_55s": (127, 115),
}

REGION = (380, 1080, 1000, 1535)   # x0,y0,x1,y1  bottom-left command panel zone
X0, Y0, X1, Y1 = REGION


def mask_of(a):
    r = a[:, :, 0].astype(np.int16)
    g = a[:, :, 1].astype(np.int16)
    b = a[:, :, 2].astype(np.int16)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    red = (r - g >= 50) & (r - b >= 60) & (g < 120)
    grey = (np.abs(r - g) < 14) & (np.abs(g - b) < 14) & (lum > 150) & (lum < 235)
    dark = (lum < 70) & (r >= g)
    return red, grey, dark, lum


print("=== chibi signature centroid per frame (fixed screen region %s) ===" % (REGION,))
print("%-8s %-28s %-22s %-22s" % ("frame", "RED-dress centroid/n", "GREY-hat centroid/n", "DARK centroid/n"))
cents = {}
for k, dd, n in F:
    im = Image.open(os.path.join(SHOTS, dd, n)).convert("RGB")
    a = np.asarray(im.crop(REGION), dtype=np.uint8)
    red, grey, dark, lum = mask_of(a)
    row = [k]
    for name, m in (("red", red), ("grey", grey), ("dark", dark)):
        if m.sum() > 200:
            ys, xs = np.nonzero(m)
            row.append("(%6.1f,%6.1f) n=%5d" % (xs.mean(), ys.mean(), m.sum()))
        else:
            row.append("n=%d (too few)" % m.sum())
    cents[k] = row
    print("%-8s %-28s %-22s %-22s" % tuple(row))

print()
print("=== does the character track the camera? ===")
print("predicted screen shift of a world feature (from measured camera):")
for k, _, _ in F:
    print("   %-8s cam=(%+4d,%+4d)" % (k, CAM[k][0], CAM[k][1]))
print()
print("measured shift of the RED-dress centroid relative to f1:")
for k, dd, n in F:
    im = Image.open(os.path.join(SHOTS, dd, n)).convert("RGB")
    a = np.asarray(im.crop(REGION), dtype=np.uint8)
    red, grey, dark, lum = mask_of(a)
    if red.sum() > 200:
        ys, xs = np.nonzero(red)
        cents[k] = (xs.mean(), ys.mean(), red.sum())
    else:
        cents[k] = None

if cents.get("f1_29s"):
    x1, y1, _ = cents["f1_29s"]
    for k, _, _ in F:
        if not cents[k]:
            print("   %-8s (red mask too weak)" % k)
            continue
        x, y, n = cents[k]
        print("   %-8s measured=(%+7.1f,%+7.1f)  camera=(%+4d,%+4d)  ratio=(%.2f,%.2f)"
              % (k, x - x1, y - y1, CAM[k][0], CAM[k][1],
                 (x - x1) / CAM[k][0] if CAM[k][0] else float("nan"),
                 (y - y1) / CAM[k][1] if CAM[k][1] else float("nan")))

print()
print("=== static-HUD control: same mask stats in the top-left resource bar ===")
CTRL = (0, 0, 700, 66)
for k, dd, n in F:
    im = Image.open(os.path.join(SHOTS, dd, n)).convert("RGB")
    a = np.asarray(im.crop(CTRL), dtype=np.uint8)
    red, grey, dark, lum = mask_of(a)
    print("   %-8s red=%5d grey=%5d dark=%5d" % (k, red.sum(), grey.sum(), dark.sum()))
