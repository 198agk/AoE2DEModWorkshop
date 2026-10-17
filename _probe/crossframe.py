# -*- coding: utf-8 -*-
"""DECISIVE cross-frame test: is the in-game HUD actually alpha-blended?
If a HUD panel region is transparent, its pixels must CHANGE across frames
whenever the terrain behind it changes. If opaque, it stays pixel-stable.
Compare 5 frames of the same session (29/37/43/49/55 s).
"""
import os
import numpy as np
from PIL import Image

SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\ui"
os.makedirs(OUT, exist_ok=True)

F = {
    "0261b373": ("02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    "2fe52823": ("2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    "16175bb0": ("16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    "8eeadcf8": ("8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    "89bdabdd": ("89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
}
frames = {}
for k, (d, n) in F.items():
    p = os.path.join(SHOTS, d, n)
    im = Image.open(p).convert("RGB")
    frames[k] = np.asarray(im, dtype=np.int16)
    print("loaded", k, im.size)

base_k = "0261b373"
base = frames[base_k]

REGIONS = {
    "TOPBAR_left_resources":   (6, 6, 700, 66),
    "TOPBAR_right_clock":      (2100, 6, 2724, 66),
    "BOTTOM_cmdpanel_wood":    (560, 1180, 1080, 1300),
    "BOTTOM_cmdpanel_empty":   (620, 1330, 900, 1420),
    "BOTTOM_left_decor":       (20, 1180, 180, 1450),
    "SCOREPANEL_box":          (2090, 780, 2560, 1000),
    "SCOREPANEL_dark":         (2620, 800, 2700, 1180),
    "MINIMAP_frame":           (1560, 1180, 2700, 1500),
    "WORLD_terrain_mid":       (900, 500, 1500, 900),
    "WORLD_terrain_top":       (1800, 100, 2300, 300),
}

print()
print("=== per-region mean |diff| vs frame1, averaged over the other 4 frames ===")
print("%-26s %8s %8s %8s   %s" % ("region", "meanD", "p99D", "frac>8", "verdict"))
summary = []
for name, (x0, y0, x1, y1) in REGIONS.items():
    b = base[y0:y1, x0:x1]
    ds = []
    for k in frames:
        if k == base_k:
            continue
        o = frames[k][y0:y1, x0:x1]
        d = np.abs(o - b).mean(axis=2)
        ds.append(d)
    D = np.mean(ds, axis=0)
    meanD = float(D.mean())
    p99 = float(np.percentile(D, 99))
    frac = float((D > 8).mean())
    verdict = "OPAQUE/static" if meanD < 2.0 and frac < 0.02 else ("PARTLY CHANGING" if meanD < 12 else "CHANGING")
    summary.append((meanD, name, verdict))
    print("%-26s %8.2f %8.1f %8.3f   %s" % (name, meanD, p99, frac, verdict))

print()
print("=== heatmaps of change (saved) ===")
for name, (x0, y0, x1, y1) in REGIONS.items():
    b = base[y0:y1, x0:x1]
    acc = np.zeros(b.shape[:2], dtype=np.float32)
    for k in frames:
        if k == base_k:
            continue
        o = frames[k][y0:y1, x0:x1]
        acc += np.abs(o - b).mean(axis=2)
    acc /= 4.0
    hm = np.clip(acc / 40.0 * 255, 0, 255).astype(np.uint8)
    Image.fromarray(hm, "L").resize((hm.shape[1] * 2, hm.shape[0] * 2), Image.NEAREST).save(
        os.path.join(OUT, "chg_%s.png" % name))
print("   wrote", len(REGIONS), "change heatmaps to _shots/ui/chg_*.png")
