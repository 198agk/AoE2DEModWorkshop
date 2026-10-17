# -*- coding: utf-8 -*-
"""FINAL fidelity measurement: art vs art, terrain removed, sizes taken from ViewPort.

THREE DEFECTS IN MY EARLIER MEASUREMENTS, ALL NOW FIXED
------------------------------------------------------
1. WRONG TEMPLATE SIZE. I resized candidate textures to `texture.width * SC`
   (e.g. a 96x96 icon -> 57 px). But the engine draws a material INTO THE WIDGET'S
   ViewPort BOX, so the correct screen size is `box_ref_px * SC`. For the four
   resource icons the box is 84x84 ref px -> 50 px, not 57. That 14% size error
   alone moved the icons' MAD from ~12-16 (s13, box-sized) to 56-68 (s22/s23,
   texture-sized) -- i.e. my recent numbers measured my own sizing bug, not the art.

2. TERRAIN CONTAMINATION. obs = a*A + (1-a)*T. Comparing my render (flat backdrop)
   against a screenshot (terrain backdrop) mixes T into the error. Fixed by using
   the FIVE real screenshots of the same game moment: the HUD is constant across
   them while the camera moves, so `std_across_shots = (1-a)*std(T)`. Hence
   `std < t` is an EMPIRICAL OPAQUE MASK and the 5-shot MEAN over it is the real
   HUD art with terrain averaged out. This is the calibration the prior report in
   this workspace asked for but never had.

3. NO FLOOR. I never established what MAD a KNOWN-CORRECT widget scores. Without
   that floor, "plank scored 71" is meaningless. The control is included here.
"""
import os
import json
import numpy as np
from PIL import Image, ImageDraw

O = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WID = os.path.join(GAME, "widgetui")
AT = r"C:\Users\26913\.dsh\attachments\v1\objects"
SHOTS = [
    os.path.join(AT, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    os.path.join(AT, "2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    os.path.join(AT, "16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    os.path.join(AT, "8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    os.path.join(AT, "89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
]
SC = 0.5980          # HUD scale, independently fitted and confirmed on all 5 shots
CROP = (0, 0, 1100, 200)
rep = []

# ---------------------------------------------------------------- real reference
means = []
for p in SHOTS:
    means.append(np.asarray(Image.open(p).convert("RGB").crop(CROP), dtype=np.float64))
st = np.stack(means)
real_mean = st.mean(axis=0)
real_std = st.std(axis=0).mean(axis=2)
opaque = real_std < 4.0
rep.append("REAL REFERENCE from %d screenshots cropped to %s" % (len(SHOTS), CROP))
rep.append("  provably-opaque (std<4) = %.2f%% of the region" % (100.0 * opaque.mean()))
rep.append("")

# ---------------------------------------------------------------- my render
rend = Image.open(os.path.join(O, "out", "resourcepanel_4k.png")).convert("RGBA")
# scale the 3840x2160 reference-space render into screenshot space
rw = Image.new("RGBA", (rend.width, rend.height))
rw.paste(rend, (0, 0))
scaled = rw.resize((int(round(rend.width * SC)), int(round(rend.height * SC))), Image.LANCZOS)
rsub = scaled.crop(CROP)
ra = np.asarray(rsub, dtype=np.float64)
rep.append("RENDER: out/resourcepanel_4k.png cropped to %s then scaled by %.4f -> %s"
           % (CROP, SC, rsub.size))
rep.append("")

# ---------------------------------------------------------------- the metric
def compare(mask, label):
    if mask.sum() < 50:
        rep.append("  %-46s too few px (%d)" % (label, mask.sum()))
        return None
    x = ra[:, :, :3][mask]
    y = real_mean[mask]
    mad = float(np.abs(x - y).mean())
    cc = float(np.corrcoef(x.mean(axis=1), y.mean(axis=1))[0, 1]) if x.mean(axis=1).std() > 1e-6 else 0.0
    rep.append("  %-46s MAD=%6.2f corr=%+.4f px=%5d   renderRGB=(%5.1f%5.1f%5.1f) realRGB=(%5.1f%5.1f%5.1f)"
               % (label, mad, cc, mask.sum(), x[:, 0].mean(), x[:, 1].mean(), x[:, 2].mean(),
                  y[:, 0].mean(), y[:, 1].mean(), y[:, 2].mean()))
    return mad

rep.append("TERRAIN-FREE art-vs-art comparison, masked to (render alpha>200) AND (real std<4):")
both = (ra[:, :, 3] > 200) & opaque
compare(both, "ALL art pixels")
rep.append("")
rep.append("  per-widget (render rects scaled by SC=%.4f, i.e. ref px x 0.598):" % SC)
# layout rects in ref px for resourcepanel.json, from the widget tree
REG = [
    ("Background plank (CivAsiaResourcePanel)", (0, 0, 1750, 276)),
    ("Wood icon box", (15, 15, 99, 99)),
    ("WoodStorage label '10000'", (108, 60, 208, 94)),
    ("Food icon box", (215, 15, 299, 99)),
    ("FoodStorage label '10000'", (308, 60, 408, 94)),
    ("Gold icon box", (415, 15, 499, 99)),
    ("GoldStorage label '10000'", (508, 60, 608, 94)),
    ("Stone icon box", (615, 15, 699, 99)),
    ("StoneStorage label '10000'", (710, 60, 810, 94)),
    ("Population box", (813, 15, 899, 99)),
    ("PopulationCount '300/300'", (910, 60, 1040, 94)),
    ("PopulationFlash rect", (830, 24, 970, 96)),
    ("Idle badge (70x70 CentreCentre @1080,57)", (1045, 22, 1115, 92)),
    ("AgeUp button (141x122 @1200,62)", (1130, 1, 1271, 123)),
    ("AgeBar (378x52 @1250,57)", (1061, 31, 1439, 83)),
]
mads = []
for lbl, (x0, y0, x1, y1) in REG:
    sx0, sy0 = int(round(x0 * SC)), int(round(y0 * SC))
    sx1, sy1 = int(round(x1 * SC)), int(round(y1 * SC))
    sx1, sy1 = min(sx1, ra.shape[1]), min(sy1, ra.shape[0])
    if sx1 <= sx0 or sy1 <= sy0:
        continue
    m = np.zeros(ra.shape[:2], dtype=bool)
    m[sy0:sy1, sx0:sx1] = True
    m &= (ra[:, :, 3] > 200) & opaque
    r = compare(m, "    " + lbl)
    if r is not None:
        mads.append((r, lbl))

# ---------------------------------------------------------------- CONTROL: metric floor
rep.append("")
rep.append("CONTROL -- metric FLOOR, using art that is KNOWN to be correct (the four resource")
rep.append("icons, placed by the layout's own ViewPort geometry, sized to the ViewPort BOX):")
for i, (nm, rel) in enumerate([("ResourceWood", r"textures\ingame\icons\resource_wood.png"),
                               ("ResourceFood", r"textures\ingame\icons\resource_food.png"),
                               ("ResourceGold", r"textures\ingame\icons\resource_gold.png"),
                               ("ResourceStone", r"textures\ingame\icons\resource_stone.png")]):
    im = Image.open(os.path.join(WID, rel)).convert("RGBA")
    # DRAW INTO THE BOX: ViewPort is 84x84 ref px -> 84*SC screen px (NOT 96*SC)
    bs = int(round(84 * SC))
    t = im.resize((bs, bs), Image.LANCZOS)
    ta = np.asarray(t, dtype=np.float64)
    lx = int(round(15 * SC)) + int(round(200 * i * SC))
    ly = int(round(15 * SC))
    ch, cw = min(ra.shape[0] - ly, bs), min(ra.shape[1] - lx, bs)
    sub = ta[:ch, :cw]
    m = np.zeros(ra.shape[:2], dtype=bool)
    m[ly:ly + ch, lx:lx + cw] = True
    m &= opaque
    if m.sum() < 50:
        rep.append("  %-14s too few static px (%d)" % (nm, m.sum()))
        continue
    x = sub[:, :, :3][m[ly:ly + ch, lx:lx + cw]]
    y = real_mean[m]
    rep.append("  %-14s box-sized %dpx  MAD=%6.2f corr=%+.4f px=%d"
               % (nm, bs, np.abs(x - y).mean(),
                  np.corrcoef(x.mean(axis=1), y.mean(axis=1))[0, 1], m.sum()))
rep.append("")
rep.append("  (for contrast, the SAME icons sized to texture.width*SC = %d px instead of the box:)" % int(round(96 * SC)))
for i, (nm, rel) in enumerate([("ResourceWood", r"textures\ingame\icons\resource_wood.png"),
                               ("ResourceFood", r"textures\ingame\icons\resource_food.png")]):
    im = Image.open(os.path.join(WID, rel)).convert("RGBA")
    ws = int(round(im.width * SC))
    t = im.resize((ws, ws), Image.LANCZOS)
    ta = np.asarray(t, dtype=np.float64)
    lx = int(round(15 * SC)) + int(round(200 * i * SC))
    ly = int(round(15 * SC))
    ch, cw = min(ra.shape[0] - ly, ws), min(ra.shape[1] - lx, ws)
    sub = ta[:ch, :cw]
    m = np.zeros(ra.shape[:2], dtype=bool)
    m[ly:ly + ch, lx:lx + cw] = True
    m &= opaque
    x = sub[:, :, :3][m[ly:ly + ch, lx:lx + cw]]
    y = real_mean[m]
    rep.append("  %-14s texture-sized %dpx  MAD=%6.2f  <-- the sizing bug" % (nm, ws, np.abs(x - y).mean()))

# ---------------------------------------------------------------- visuals
rep.append("")
rep.append("TOP 5 worst regions by MAD:")
for mad, lbl in sorted(mads, reverse=True)[:5]:
    rep.append("  %6.2f  %s" % (mad, lbl.strip()))

tiles = [("REAL (5-shot mean, terrain averaged out)", Image.fromarray(real_mean.astype(np.uint8)))]
tiles.append(("REAL provably-opaque px only", Image.fromarray(np.where(opaque[:, :, None], real_mean, 24).astype(np.uint8))))
flat = Image.new("RGB", rsub.size, (95, 110, 80))
flat.paste(rsub, (0, 0), rsub)
tiles.append(("RENDER out/resourcepanel_4k.png at 0.598", flat))
bl = Image.new("RGB", rsub.size, (95, 110, 80))
bl.paste(rsub, (0, 0), rsub)
tiles.append(("50/50 blend render over real", Image.blend(bl, tiles[0][1], 0.5)))
d = Image.new("RGB", (rsub.width, sum(t.height + 20 for _, t in tiles)), (26, 26, 30))
dr = ImageDraw.Draw(d)
yy = 0
for lbl, t in tiles:
    d.paste(t, (0, yy))
    dr.text((4, yy + 3), lbl, fill=(255, 255, 0))
    yy += t.height + 20
d.save(os.path.join(O, "cmp_final_side_by_side.png"))
rep.append("")
rep.append("wrote cmp_final_side_by_side.png %s" % (d.size,))

txt = "\n".join(rep)
open(os.path.join(O, "fidelity_final.txt"), "w", encoding="utf-8").write(txt)
print(txt)
