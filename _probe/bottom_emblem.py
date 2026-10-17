# -*- coding: utf-8 -*-
"""POSITIVE test: does the BOTTOM command-panel emblem show the chibi mod?

Reference resolution is 3840x2160; the screenshots are 2730x1535 (scale 0.7109).
commandpanel.json declares a widget "CivEmblem" (Type Base, Material "CivEmblem",
ViewPort 450x280). The chibi mod's own description says it replaces "the
Civilization Emblems in the bottom UI ingame" -- i.e. THAT widget -- while my
earlier analysis looked at the TOP-RIGHT player-list emblem, which is a
different asset family (wpfg/resources/civ_emblems).

So: crop the bottom HUD strip from each frame, upscale, and look for a chibi
figure. Also build a side-by-side of the bottom panel region across frames.
"""
import os
import numpy as np
from PIL import Image

SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\ui"
os.makedirs(OUT, exist_ok=True)

F = {
    "f1_29s": ("02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    "f2_37s": ("2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    "f3_43s": ("16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    "f4_49s": ("8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    "f5_55s": ("89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
}

W, H = 2730, 1535
# bottom HUD strip: everything below y=1150
STRIP = (0, 1150, W, H)
imgs = []
for k, (d, n) in F.items():
    im = Image.open(os.path.join(SHOTS, d, n)).convert("RGB")
    c = im.crop(STRIP)
    imgs.append((k, c))

# stacked overview so all five are visible at once
sx = 1.0
stack = Image.new("RGB", (int(W * sx), int((H - 1150) * sx) * len(imgs)), (0, 0, 0))
for i, (k, c) in enumerate(imgs):
    stack.paste(c.resize((int(c.width * sx), int(c.height * sx)), Image.LANCZOS), (0, i * int((H - 1150) * sx)))
stack.save(os.path.join(OUT, "bottom_strip_all5.png"))
print("wrote bottom_strip_all5.png", stack.size)

# the command panel's own area (left-bottom quadrant) magnified per frame
CP = (0, 1150, 1200, H)
panels = []
for k, (d, n) in F.items():
    im = Image.open(os.path.join(SHOTS, d, n)).convert("RGB")
    panels.append((k, im.crop(CP)))
pw, ph = panels[0][1].size
sheet = Image.new("RGB", (pw * 2, ph * 3), (20, 20, 20))
for i, (k, c) in enumerate(panels):
    x = (i % 2) * pw
    y = (i // 2) * ph
    sheet.paste(c, (x, y))
sheet.save(os.path.join(OUT, "cmdpanel_5frames.png"))
print("wrote cmdpanel_5frames.png", sheet.size)

# magnified bottom-CENTRE (where the civ name label + emblem live)
BC = (900, 1150, 1800, H)
for k, (d, n) in F.items():
    im = Image.open(os.path.join(SHOTS, d, n)).convert("RGB")
    c = im.crop(BC)
    c.resize((c.width * 2, c.height * 2), Image.LANCZOS).save(
        os.path.join(OUT, "bc_%s.png" % k))
print("wrote bc_*.png x%d" % len(F))

# Any chibi-like saturated red/white blob in the bottom strip? report stats
for k, (d, n) in F.items():
    im = Image.open(os.path.join(SHOTS, d, n)).convert("RGB")
    a = np.asarray(im.crop(STRIP), dtype=np.int16)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    # the chibi girl wears a strong red dress: r much greater than g and b
    red = (r > 120) & (r - g > 40) & (r - b > 40)
    print("  %-8s bottom-strip strong-red pixels: %6d (%.3f%%)  meanRGB=(%.1f,%.1f,%.1f)"
          % (k, int(red.sum()), 100.0 * red.mean(), a[:, :, 0].mean(), a[:, :, 1].mean(), a[:, :, 2].mean()))
