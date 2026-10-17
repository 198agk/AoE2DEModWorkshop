# -*- coding: utf-8 -*-
"""Decisive test: WHERE and AT WHAT SCALE does the shipped plank art actually appear?

Prior failures on this exact question, and why each was wrong:

  s13 v1  sliding_window_view NCC -> broadcasting error. Window axes are APPENDED:
          an RGB image yields (H,W,h,w,3), so the colour axis lands LAST.
  s13 v2  luminance dark-run detection -> found text edges, not box frames,
          giving pitches like [211,119,317,22,14].
  s13 v3  whole-plank template match, no alpha mask -> hit the search boundary at
          scale 0.60 with MAD 60-80. The plank PNG is ~57% TRANSPARENT, so an
          unmasked RGB comparison spends most of its error budget on the
          transparent holes (where the screenshot shows terrain, not art).
  s14     icon fit with the pitch constrained to the layout's 200 ref px -> found
          scale 0.598, but a self-confirming constraint proves nothing on its own.
  s17     independent NCC per icon over all sizes -> degenerate: it preferred
          tiny 18-39 px squares that happened to score well, i.e. masked NCC at
          small template sizes is not discriminative here.
  s18     scoring all 17 civ panels inside a rect DERIVED from the s17 result ->
          meaningless, because that rect came from the degenerate s17 geometry.
  s19 v1  masked match returned None for EVERY candidate -> the sub-sliced
          template kept 4 channels (RGBA after resize) while the screenshot
          window had 3, so `ta.shape != win.shape` bailed before the mask was
          ever counted. FIXED HERE by slicing `[:, :, :3]` for the comparison
          and keeping `[:, :, 3]` only as the mask.

So this script re-does the one well-posed test: TEMPLATE MATCH THE PLANK WITH ITS
ALPHA AS A MASK, searching scale and offset jointly. Masking is the whole point --
it is the same class of mistake as comparing a normalized atlas UV rect against a
standalone PNG (the bug that caused UV_OUT_OF_RANGE on 17/19 materials).
"""
import os
import numpy as np
from PIL import Image, ImageDraw

O = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOT = r"C:\Users\26913\.dsh\attachments\v1\objects\02\0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"
PANE = os.path.join(GAME, r"widgetui\textures\ingame\panels\ASIA\resource-panel.png")

rep = []
shot = Image.open(SHOT).convert("RGB")
W, H = shot.size
arr = np.asarray(shot, dtype=np.float64)
pane = Image.open(PANE).convert("RGBA")
PW, PH = pane.size
pa0 = np.asarray(pane, dtype=np.float64)
rep.append("reference %dx%d" % (W, H))
rep.append("template %s %dx%d" % (os.path.relpath(PANE, GAME), PW, PH))
rep.append("template alpha>200 covers %.1f%% of its area" % (100.0 * (pa0[:, :, 3] > 200).mean()))
rep.append("")

# Resize each scale ONCE (this was 30600 redundant resizes in s19 v1).
CACHE = {}
def tpl(scale):
    if scale not in CACHE:
        t = pane.resize((int(round(PW * scale)), int(round(PH * scale))), Image.LANCZOS)
        CACHE[scale] = np.asarray(t, dtype=np.float64)
    return CACHE[scale]

def match(scale, ox, oy):
    """Masked mean-|diff| of the scaled plank placed with its top-left at (ox,oy).

    The plank may hang off the image edge; clip BOTH the template and the window
    by the same amounts rather than rejecting the candidate.
    """
    ta = tpl(scale)
    th_, tw_ = ta.shape[0], ta.shape[1]
    if tw_ < 40 or th_ < 20:
        return None
    cx0, cy0 = max(0, ox), max(0, oy)
    cx1, cy1 = min(W, ox + tw_), min(H, oy + th_)
    if cx1 - cx0 < 40 or cy1 - cy0 < 20:
        return None
    sx0, sy0 = cx0 - ox, cy0 - oy
    tas = ta[sy0:sy0 + (cy1 - cy0), sx0:sx0 + (cx1 - cx0)]
    win = arr[cy0:cy1, cx0:cx1]
    if tas.shape[:2] != win.shape[:2]:
        return None
    m = tas[:, :, 3] > 200
    n = int(m.sum())
    if n < 2000:
        return None
    x = tas[:, :, :3][m]          # <-- the fix: 3 channels, alpha used only as mask
    y = win[m]
    mad = float(np.abs(x - y).mean())
    xg, yg = x.mean(axis=1), y.mean(axis=1)
    cc = float(np.corrcoef(xg, yg)[0, 1]) if (xg.std() > 1e-6 and yg.std() > 1e-6) else 0.0
    return mad, cc, n

best = (1e18, 0.0, -1.0, 0, 0, 0)
for scale in np.arange(0.20, 1.041, 0.01):
    for oy in range(-40, 140, 8):
        for ox in range(-60, 100, 8):
            r = match(scale, ox, oy)
            if r and r[0] < best[0]:
                best = (r[0], r[1], float(scale), ox, oy, r[2])
rep.append("COARSE masked search (scale 0.20-1.04 step .01, offset step 8):")
rep.append("   best MAD=%.2f corr=%+.4f scale=%.3f offset=(%d,%d) maskedpx=%d" % best)
_, _, bsc, box_, boy, _ = best

best = (1e18, 0.0, -1.0, 0, 0, 0)
for scale in np.arange(bsc - 0.02, bsc + 0.0201, 0.002):
    for oy in range(boy - 10, boy + 11, 2):
        for ox in range(box_ - 10, box_ + 11, 2):
            r = match(scale, ox, oy)
            if r and r[0] < best[0]:
                best = (r[0], r[1], float(scale), ox, oy, r[2])
rep.append("FINE masked search:")
rep.append("   best MAD=%.2f corr=%+.4f scale=%.4f offset=(%d,%d) maskedpx=%d" % best)
mad, cc, sc, ox, oy, _ = best
rep.append("")
rep.append("Implied geometry at this scale: plank occupies screenshot (%d,%d) %dx%d"
           % (ox, oy, int(round(PW * sc)), int(round(PH * sc))))
rep.append("   -> 84 ref px box would be %.1f screen px ; 200 ref px pitch would be %.1f px"
           % (84 * sc, 200 * sc))
rep.append("   -> naive backbuffer scale W/3840 = %.4f ; measured HUD scale = 0.5980" % (W / 3840.0))
rep.append("")
rep.append("For calibration, the SAME masked metric applied to the four resource ICONS")
rep.append("(whose shipped art visibly matches) over their layout-derived rects:")
icons = [("ResourceWood", r"textures\ingame\icons\resource_wood.png"),
         ("ResourceFood", r"textures\ingame\icons\resource_food.png"),
         ("ResourceGold", r"textures\ingame\icons\resource_gold.png"),
         ("ResourceStone", r"textures\ingame\icons\resource_stone.png")]
for i, (nm, rel) in enumerate(icons):
    im = Image.open(os.path.join(GAME, "widgetui", rel)).convert("RGBA")
    s2 = 0.5980
    rsz = im.resize((int(round(im.width * s2)), int(round(im.height * s2))), Image.LANCZOS)
    a2 = np.asarray(rsz, dtype=np.float64)
    lx, ly = int(round(15 * s2)) + int(round(200 * i * s2)), int(round(15 * s2))
    cx1, cy1 = min(W, lx + a2.shape[1]), min(H, ly + a2.shape[0])
    tas = a2[:cy1 - ly, :cx1 - lx]
    win = arr[ly:cy1, lx:cx1]
    m = tas[:, :, 3] > 200
    if m.sum() < 100:
        rep.append("   %-14s no mask" % nm)
        continue
    x = tas[:, :, :3][m]
    y = win[m]
    rep.append("   %-14s MAD=%.2f  corr=%+.4f  maskedpx=%d"
               % (nm, np.abs(x - y).mean(), np.corrcoef(x.mean(axis=1), y.mean(axis=1))[0, 1] if x.std() > 1e-6 else 0.0, m.sum()))

# ---------------------------------------------------------------- visual proof
tw, th = int(round(PW * sc)), int(round(PH * sc))
cx0, cy0 = max(0, ox), max(0, oy)
cx1, cy1 = min(W, ox + tw), min(H, oy + th)
sub = shot.crop((cx0, cy0, cx1, cy1)).convert("RGB")
ta = tpl(sc)
sx0, sy0 = cx0 - ox, cy0 - oy
tas = ta[sy0:sy0 + (cy1 - cy0), sx0:sx0 + (cx1 - cx0)]
tm = Image.fromarray(tas.astype(np.uint8))
rgb = Image.new("RGB", sub.size, (95, 110, 80))
rgb.paste(tm, (0, 0), tm)
comp = Image.new("RGB", (sub.width, sub.height * 3 + 36), (20, 20, 24))
comp.paste(sub, (0, 0))
comp.paste(rgb, (0, sub.height + 18))
comp.paste(Image.blend(sub, rgb, 0.5), (0, sub.height * 2 + 36))
d = ImageDraw.Draw(comp)
d.text((4, 2), "REAL screenshot", fill=(255, 255, 255))
d.text((4, sub.height + 20), "SHIPPED CivAsiaResourcePanel at best masked fit (scale %.3f)" % sc, fill=(255, 255, 0))
d.text((4, sub.height * 2 + 38), "50/50 blend", fill=(0, 255, 255))
comp.save(os.path.join(O, "cmp_plank_fit.png"))
rep.append("")
rep.append("wrote cmp_plank_fit.png (%dx%d: real / best-fit art / blend)" % comp.size)

txt = "\n".join(rep)
open(os.path.join(O, "plank_fit.txt"), "w", encoding="utf-8").write(txt)
print(txt)
