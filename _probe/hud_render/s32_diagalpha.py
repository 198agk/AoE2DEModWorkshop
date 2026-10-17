# -*- coding: utf-8 -*-
"""Diagnose why the 'well-conditioned + render alpha>200' subset scores MAD 69.9
while the four resource icons (individually verified correct) score 11.8-14.7.
Purpose: never report a number whose composition I cannot name."""
import os
import numpy as np
from PIL import Image

O = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WID = os.path.join(GAME, "widgetui")
AT = r"C:\Users\26913\.dsh\attachments\v1\objects"
SHOTS = [os.path.join(AT, d, s) for d, s in [
    ("02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    ("2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    ("16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    ("8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    ("89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
]]
SC = 0.5980
BW, BH = 1750, 276
TW, TH = int(round(BW * SC)), int(round(BH * SC))

st = np.stack([np.asarray(Image.open(p).convert("RGB").crop((0, 0, TW, TH)), dtype=np.float64) for p in SHOTS])
rm = st.mean(axis=0)
A = np.asarray(Image.open(os.path.join(WID, r"textures\ingame\panels\ASIA\resource-panel.png"))
               .convert("RGBA").resize((TW, TH), Image.LANCZOS), dtype=np.float64)

low = np.stack([np.asarray(Image.open(p).convert("RGB").crop((0, TH, 400, TH + 120)), dtype=np.float64) for p in SHOTS])
lo_p = np.percentile(low.reshape(-1, 3), 5, axis=0)
hi_p = np.percentile(low.reshape(-1, 3), 95, axis=0)
T_raw = (rm - 0.502 * A[:, :, :3]) / 0.498
oob2 = ((T_raw < lo_p * 0.6) | (T_raw > hi_p * 1.35)).any(axis=2)
T = np.clip(np.where(oob2[:, :, None], np.clip(T_raw, lo_p * 0.6, hi_p * 1.35), T_raw), 0, 255)

R = np.asarray(Image.open(os.path.join(O, "out", "resourcepanel_mod_4k.png")).convert("RGBA")
               .crop((0, 0, BW, BH)).resize((TW, TH), Image.LANCZOS), dtype=np.float64)
aR = R[:, :, 3:4] / 255.0
comp = aR * R[:, :, :3] + (1 - aR) * T
am = aR[:, :, 0]
m = (am > 0.78) & (~oob2)
d = np.abs(comp - rm).mean(axis=2)
print("subset alpha>0.78 & well-conditioned: px=%d  MAD=%.2f" % (m.sum(), d[m].mean()))
print()
print("alpha histogram over the footprint:")
for lo, hi in ((0, 0.02), (0.02, 0.5), (0.5, 0.78), (0.78, 0.99), (0.99, 1.01)):
    mm = (am >= lo) & (am < hi)
    print("  alpha %4.2f-%.2f : %7d px  MAD=%s" % (lo, hi, mm.sum(),
          "%.2f" % d[mm].mean() if mm.sum() else "-"))
print()
print("per-region on the alpha>0.78 subset (ref rects, CentreCentre where noted):")
REG = [("Wood icon", 57 - 42, 15, 84, 84), ("Food icon", 257 - 42, 15, 84, 84),
       ("Gold icon", 457 - 42, 15, 84, 84), ("Stone icon", 657 - 42, 15, 84, 84),
       ("Population box", 856 - 43, 15, 86, 84), ("Idle button", 1080 - 35, 22, 70, 70),
       ("PopulationFlash", 830, 24, 140, 72), ("AgeBar", 1250, 31, 378, 52),
       ("AgeTextLabel", 1250, 31, 380, 50)]
acc = 0
for nm, x, y, w, h in REG:
    x0 = max(0, int(round(x * SC))); y0 = max(0, int(round(y * SC)))
    x1 = min(TW, int(round((x + w) * SC))); y1 = min(TH, int(round((y + h) * SC)))
    mm = m[y0:y1, x0:x1]
    if mm.sum() == 0:
        print("  %-16s %6d px  (none in subset)" % (nm, 0)); continue
    acc += int(mm.sum())
    cc = float(np.corrcoef(comp[y0:y1, x0:x1][mm].reshape(-1), rm[y0:y1, x0:x1][mm].reshape(-1))[0, 1])
    print("  %-16s %6d px  MAD=%7.2f corr=%+.4f  mean aR=%.2f" % (nm, mm.sum(), d[y0:y1, x0:x1][mm].mean(), cc,
          am[y0:y1, x0:x1][mm].mean()))
print("  sum of regions = %d px vs subset %d px (overlap/remainder %d)" % (acc, m.sum(), m.sum() - acc))
