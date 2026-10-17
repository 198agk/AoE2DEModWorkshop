# -*- coding: utf-8 -*-
"""EXACT alpha solve -- no proxy bands, panel art cancels out.

Camera displacement (measured, ncc~0.98): f1->f2 (0,0), f1->f3 (67,-144),
f1->f4 (224,99), f1->f5 (127,115). Meaning: a world point seen at f1 screen
(x,y) is seen at fk screen (x+dx, y+dy).

Compositing:  obs_k(x,y) = a*A(x,y) + (1-a)*T_k(x,y)
where A is the fixed UI art and T_k the world behind it.
T_k(x,y) is the world at f1 coords (x-dx_k, y-dy_k).

Pick two frames whose occluded terrain is observable in f1. For the BOTTOM bar
at y=1200: f4 -> f1 y=1101, f5 -> f1 y=1085. Both are free terrain above the
HUD. Subtracting removes A entirely:

    obs_f4(x,1200) - obs_f5(x,1200) = (1-a) * [ f1(x-224,1101) - f1(x-127,1085) ]

So regressing the bar difference on the known terrain difference gives (1-a).
A terrain control region must yield slope 1.0 -- that validates the method.
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
L = {}
for k, (d, n) in F.items():
    L[k] = np.asarray(Image.open(os.path.join(SHOTS, d, n)).convert("L"), dtype=np.float64)

SH = {"f1": (0, 0), "f2": (0, 0), "f3": (67, -144), "f4": (224, 99), "f5": (127, 115)}


def sample(img, x, y):
    """Sample a 2-D array at float-free integer coords, clipped."""
    ys = np.clip(y, 0, img.shape[0] - 1)
    xs = np.clip(x, 0, img.shape[1] - 1)
    return img[ys, xs]


def solve(name, ys_screen, xs, ka="f4", kb="f5"):
    dxa, dya = SH[ka]
    dxb, dyb = SH[kb]
    X = np.asarray(xs)
    # observable terrain behind the panel, in f1 coordinates
    ya = ys_screen - dya
    yb = ys_screen - dyb
    Ta = sample(L["f1"], X - dxa, ya)
    Tb = sample(L["f1"], X - dxb, yb)
    dT = Ta - Tb
    dO = sample(L[ka], X, ys_screen) - sample(L[kb], X, ys_screen)
    ok = (ya >= 0) & (ya < L["f1"].shape[0]) & (yb >= 0) & (yb < L["f1"].shape[0])
    dT, dO = dT[ok], dO[ok]
    if dT.std() < 1e-6:
        return None
    slope = float(np.cov(dO, dT)[0, 1] / np.var(dT))
    r = float(np.corrcoef(dO, dT)[0, 1])
    resid = float(np.abs(dO - slope * dT).mean())
    print("  %-30s slope=%7.4f  r=%6.3f  1-a=%7.4f  alpha=%6.1f/255   resid=%.2f  n=%d"
          % (name, slope, r, slope, 255 * (1 - slope), resid, len(dT)))
    return slope


XS = np.arange(560, 1081)
print("=== alpha solve, f4 vs f5, bottom-bar rows ===")
print("    (control rows in free terrain must give slope ~1.0)")
print()
print("  CONTROL (free terrain, no panel):")
for y in (600, 800, 1000):
    solve("terrain y=%d" % y, y, XS)

print()
print("  MEASUREMENT (bottom HUD rows):")
res = {}
for y in (1180, 1200, 1220, 1250, 1300, 1350, 1400):
    res[y] = solve("bottom HUD y=%d" % y, y, XS)

print()
print("  MEASUREMENT (top bar rows, f1 vs f3 -- only f3 has observable terrain):")
# top bar: y_s - (-144) = y_s + 144 must be free terrain -> y_s < 1000-144
print("  (needs two frames with observable terrain; f3 is the only one for the")
print("   top bar, so A cannot cancel there -- use the f3-vs-f1 ratio estimate.)")
y_s = 30
dx3, dy3 = SH["f3"]
T3 = sample(L["f1"], XS - dx3, y_s - dy3)
T1_unobservable = None
dO13 = sample(L["f3"], XS, y_s) - sample(L["f1"], XS, y_s)
# terrain change magnitude, for scale
y_ref = 174
dT13 = T3 - sample(L["f1"], XS, y_ref)   # not valid (differs), report only magnitude
print("    |obs_f3-obs_f1| at y=30 : mean=%.2f" % float(np.abs(dO13).mean()))
print("    |T(f1 y=%d) - T(f1 y=%d)| : mean=%.2f  (world displacement scale)"
      % (y_ref, y_s, float(np.abs(dT13).mean())))
