# -*- coding: utf-8 -*-
"""Visual + numeric: what do the vanilla vs MOD resource panels actually look like,
and does compositing the MOD art over plausible terrain explain the observed bar?
"""
import os
import numpy as np
from PIL import Image

O = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WID = os.path.join(GAME, "widgetui")
MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\550412_透明主题整合自用"
AT = r"C:\Users\26913\.dsh\attachments\v1\objects"
SHOT0 = os.path.join(AT, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
SHOTS = [os.path.join(AT, d, s) for d, s in [
    ("02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    ("2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    ("16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    ("8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    ("89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
]]
SC = 0.5980

vp = os.path.join(WID, r"textures\ingame\panels\ASIA\resource-panel.png")
mp = os.path.join(MOD, r"widgetui\textures\ingame\panels\ASIA\resource-panel.png")
vi = Image.open(vp); vi.load(); vi = vi.convert("RGBA")
mi = Image.open(mp); mi.load(); mi = mi.convert("RGBA")

# 1) side-by-side of the art itself over a mid-grey (so alpha is visible as tone)
print("vanilla", vi.size, "mod", mi.size)
BG = Image.new("RGBA", vi.size, (128, 128, 128, 255))
b = 0.55
sheet = Image.new("RGB", (int(1750 * b), int(276 * b * 3) + 24), (20, 20, 20))
sheet.paste(Image.alpha_composite(BG, vi).convert("RGB").resize((int(1750 * b), int(276 * b)), Image.LANCZOS), (0, 0))
sheet.paste(Image.alpha_composite(BG, mi).convert("RGB").resize((int(1750 * b), int(276 * b)), Image.LANCZOS), (0, int(276 * b) + 12))
sheet.paste(Image.alpha_composite(BG, vi).convert("RGB").point(lambda v: v).resize((int(1750 * b), int(276 * b)), Image.LANCZOS), (0, int(276 * b * 2) + 24))
# third slot: mod art over the REAL shot0 terrain
sh = Image.open(SHOT0).convert("RGB")
terr = sh.crop((0, 0, 1750, 276))       # rough terrain guess (the bar area of shot0)
sheet.paste(Image.alpha_composite(terr.convert("RGBA"), mi).convert("RGB").resize((int(1750 * b), int(276 * b)), Image.LANCZOS), (0, int(276 * b * 2) + 24))
sheet.save(os.path.join(O, "mod_art_compare.png"))

# 2) is the mod art a straight alpha-scaled copy of vanilla? per-pixel RGB diff where both >0
va = np.asarray(vi, dtype=np.float64); ma = np.asarray(mi, dtype=np.float64)
same_rgb = (np.abs(va[:, :, :3] - ma[:, :, :3]).max(axis=2) < 6)
print("pixels where RGB identical (tol 6): %.1f%% of 1750x276" % (100.0 * same_rgb.mean()))
both = (va[:, :, 3] > 0) & (ma[:, :, 3] > 0)
print("pixels where both alpha>0: %.1f%%" % (100.0 * both.mean()))
print("of those, RGB identical: %.1f%%" % (100.0 * same_rgb[both].mean()))
ratio = ma[:, :, 3][both] / np.maximum(va[:, :, 3][both], 1)
print("alpha ratio mod/vanilla where both>0: mean=%.3f median=%.3f p10=%.3f p90=%.3f"
      % (ratio.mean(), np.median(ratio), np.percentile(ratio, 10), np.percentile(ratio, 90)))
print("vanilla alpha hist:", {int(k): int(v) for k, v in zip(*np.unique(va[:, :, 3], return_counts=True))})
print("mod alpha hist:", {int(k): int(v) for k, v in zip(*np.unique(ma[:, :, 3], return_counts=True))})

# 3) build composites for both hypotheses over REAL terrain from each shot, then compare
#    to that shot. Terrain behind the bar is unknown, but we can bound the test by using
#    the terrain patch just BELOW the bar (rows 165..165+276*SC?)
st = np.stack([np.asarray(Image.open(p).convert("RGB").crop((0, 0, 1100, 200)), dtype=np.float64) for p in SHOTS])
rm = st.mean(axis=0)
sd = st.std(axis=0).mean(axis=2)
op = sd < 4.0
print("\nprovably-opaque %.2f%%" % (100.0 * op.mean()))

tw, th = int(round(1750 * SC)), int(round(276 * SC))

def comp(im, terrain_rows_below):
    a = np.asarray(im.convert("RGBA").resize((tw, th), Image.LANCZOS), dtype=np.float64)
    T = terrain_rows_below
    al = a[:, :, 3:4] / 255.0
    out = al * a[:, :, :3] + (1 - al) * T
    return out

# terrain estimate: median of the rows just below the bar in each shot (165..199), broadcast
terr_patch = st[:, 176:200, :, :].reshape(len(SHOTS), -1, 3)
terr_med = np.median(terr_patch, axis=1).reshape(len(SHOTS), 1, 3)          # (5,1,3)
T_mean = terr_med.mean(axis=0).reshape(1, 3)
print("terrain-below median RGB per shot:", np.round(terr_med.reshape(-1, 3), 1).tolist())

for label, im in (("VANILLA", vi), ("MOD", mi)):
    pred = comp(im, T_mean)[:200, :1100]
    m = op[:200, :1100]
    x = pred[m]; y = rm[m]
    print("  %-8s alpha-composite over terrain-below: MAD=%6.2f corr=%+.4f px=%d"
          % (label, np.abs(x - y).mean(), np.corrcoef(x.mean(axis=1), y.mean(axis=1))[0, 1], m.sum()))
    # also: opaque-only region of this candidate
    aa = np.asarray(im.convert("RGBA").resize((tw, th), Image.LANCZOS), dtype=np.float64)[:, :, 3][:200, :1100]
    m2 = m & (aa >= 250)
    if m2.sum() > 100:
        print("           restricted to its alpha>=250: MAD=%6.2f corr=%+.4f px=%d"
              % (np.abs(pred[m2] - rm[m2]).mean(),
                 np.corrcoef(pred[m2].mean(axis=1), rm[m2].mean(axis=1))[0, 1], m2.sum()))
    m3 = m & (aa >= 100) & (aa <= 160)
    if m3.sum() > 100:
        print("           restricted to its 100<=alpha<=160: MAD=%6.2f corr=%+.4f px=%d"
              % (np.abs(pred[m3] - rm[m3]).mean(),
                 np.corrcoef(pred[m3].mean(axis=1), rm[m3].mean(axis=1))[0, 1], m3.sum()))

# 4) What IS the real bar's own mean, over the vanilla-opaque footprint?
vaa = np.asarray(vi.resize((tw, th), Image.LANCZOS), dtype=np.float64)[:, :, 3][:200, :1100]
m = vaa >= 250
print("\nreal mean RGB over the VANILLA-opaque footprint (%.1f%% of region): %.1f %.1f %.1f"
      % (100.0 * m.mean(), rm[m][:, 0].mean(), rm[m][:, 1].mean(), rm[m][:, 2].mean()))
ma2 = np.asarray(mi.resize((tw, th), Image.LANCZOS), dtype=np.float64)
print("vanilla RGB over that footprint: %.1f %.1f %.1f"
      % tuple(va[:, :, i][np.asarray(np.asarray(vi.resize((tw, th), Image.LANCZOS), dtype=np.float64)[:, :, 3][:200, :1100] >= 250)].mean() for i in range(3)))
