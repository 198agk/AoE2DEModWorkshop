# -*- coding: utf-8 -*-
"""Build the real-vs-render side-by-side comparison for the resource panel.

Alignment comes from s14_align2.py, which fitted (scale, dx, dy) by matching the
four resource icons against the layout's predicted rects:

    scale = 0.5980, dx = 0, dy = 0      (identical on all 5 reference shots)

Layout-space crop for the resource panel is (0,0,1750,276) -- the extent of the
CivAsiaResourcePanel Background Base. Note the HUD in a screenshot is only
0.598 of layout scale, NOT the 2730/3840 = 0.7109 naive screen ratio: the game
applies its own HUD scale on top of the backbuffer scale, so the two must be
measured, not assumed.

Outputs
  cmp_resource_stack.png   real above, render below, at 3x
  cmp_resource_overlay.png real and render blended 50/50 (geometry check)
  cmp_resource_diff.png    per-pixel |diff| heat map (fidelity check)
  cmp_resource.txt         numeric summary
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageChops

O = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
SHOT = r"C:\Users\26913\.dsh\attachments\v1\objects\02\0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"

S = 0.5980          # measured HUD scale (s14_align2.py)
DX = DY = 0         # measured offset
CP = (0, 0, 1750, 276)  # layout-space extent of the resource panel background

Z = 3               # zoom for the stacked view
rep = []

real_full = Image.open(SHOT).convert("RGB")
cw, ch = int(round(CP[2] * S)), int(round(CP[3] * S))
real = real_full.crop((DX, DY, DX + cw, DY + ch))
rep.append("reference: shot0 %s" % (real_full.size,))
rep.append("measured HUD scale S=%.4f  offset=(%d,%d)" % (S, DX, DY))
rep.append("layout crop %s -> screen %dx%d" % (CP, cw, ch))

mine_full = Image.open(os.path.join(O, "out", "resourcepanel_4k.png")).convert("RGBA")
mine_crop = mine_full.crop(CP)
bg = Image.new("RGB", mine_crop.size, (95, 110, 80))
bg.paste(mine_crop, (0, 0), mine_crop)
mine = bg.resize((cw, ch), Image.LANCZOS)
rep.append("render: resourcepanel_4k.png cropped to %s, alpha over (95,110,80), resized to %dx%d" % (CP, cw, ch))

# ---------- stacked ----------
pad, lab = 8, 22
stack = Image.new("RGB", (cw, ch * 2 + pad * 3 + lab * 2), (28, 28, 32))
stack.paste(real, ((cw - cw) // 2, lab + pad))
stack.paste(mine, (0, ch + lab * 2 + pad * 2))
d = ImageDraw.Draw(stack)
d.text((6, 4), "REAL  AoE2 DE screenshot %s  crop 0,0-%d,%d at HUD scale %.4f" % (real_full.size, cw, ch, S), fill=(255, 255, 255))
d.text((6, ch + lab + pad * 2 + 4), "RENDER  resourcepanel.json  (hudrender.py, 3840x2160 ref space)", fill=(255, 255, 0))
stack.resize((stack.width * Z, stack.height * Z), Image.LANCZOS).save(os.path.join(O, "cmp_resource_stack.png"))
rep.append("")
rep.append("wrote cmp_resource_stack.png  %dx%d (native %dx%d at %dx)" % (stack.width * Z, stack.height * Z, stack.width, stack.height, Z))

# ---------- geometry overlay + diff ----------
ov = Image.blend(real.convert("RGB"), mine.convert("RGB"), 0.5)
ov.resize((ov.width * Z, ov.height * Z), Image.LANCZOS).save(os.path.join(O, "cmp_resource_overlay.png"))

a = np.asarray(real.convert("RGB"), dtype=np.int16)
b = np.asarray(mine.convert("RGB"), dtype=np.int16)
diff = np.abs(a - b).astype(np.uint8)
mad = float(diff.mean())
heat = np.clip(diff.astype(np.int32).sum(axis=2) * 2, 0, 255).astype(np.uint8)
Image.fromarray(heat).convert("RGB").resize((heat.shape[1] * Z, heat.shape[0] * Z), Image.NEAREST).save(
    os.path.join(O, "cmp_resource_diff.png"))
rep.append("wrote cmp_resource_overlay.png %dx%d and cmp_resource_diff.png (per-pixel |diff| sum*2, nearest %dx)" % (ov.width * Z, ov.height * Z, Z))
rep.append("")

# ---------- where the difference lives ----------
rep.append("GLOBAL mean absolute difference (0-255): %.2f" % mad)
bands = [("plank left+scrollwork", 0, 0.09), ("wood icon", 0.09, 0.16), ("food icon", 0.20, 0.28),
         ("gold icon", 0.32, 0.40), ("stone icon", 0.44, 0.52), ("population box", 0.56, 0.66),
         ("idle badge + ageup", 0.66, 0.82), ("age bar (red)", 0.82, 1.0)]
rep.append("")
rep.append("per-band mean absolute difference:")
for nm, f0, f1 in bands:
    x0, x1 = int(cw * f0), int(cw * f1)
    if x1 <= x0:
        continue
    band = float(diff[:, x0:x1, :].mean())
    rep.append("   %-22s x %4d-%4d  MAD=%6.2f" % (nm, x0, x1, band))

# column profile of the difference to locate structural (not texture) error
colp = diff.mean(axis=(0, 2))
worst = int(np.argmax(colp))
rep.append("")
rep.append("worst column x=%d (MAD %.2f) ; column MAD percentiles 50/90/99 = %.1f / %.1f / %.1f"
           % (worst, colp[worst], np.percentile(colp, 50), np.percentile(colp, 90), np.percentile(colp, 99)))

# how much of the frame is near-identical?
for t in (8, 16, 32, 64):
    frac = float((diff.max(axis=2) <= t).mean()) * 100.0
    rep.append("   %.1f%% of pixels differ by <= %d in every channel" % (frac, t))

txt = "\n".join(rep)
open(os.path.join(O, "cmp_resource.txt"), "w", encoding="utf-8").write(txt)
print(txt)
