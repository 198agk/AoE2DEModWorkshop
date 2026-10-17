# -*- coding: utf-8 -*-
"""Recover the real HUD's on-screen scale by fitting the FOUR resource icons.

Failure history of earlier attempts (kept as warnings):
  v1 sliding_window_view template match -> broadcasting error: window axes are
     APPENDED, so an RGB image yields (H,W,h,w,3); the last axis is colour.
  v2 luminance dark-run detection -> locked onto TEXT edges, gave pitches
     [211,119,317,22,14] instead of real box spacing.
  v3 whole-plank template, scale-only search -> hit the search boundary at 0.60
     with MAD 60-80 (no real match); the plank cannot serve as a template
     because a screenshot may only show part of it.
  v4 icon fit with the plank pinned at ref x=0 (dx forced to 0) -> found 0.598
     but could not distinguish "genuinely smaller HUD" from "plank not at x=0".

This version frees all three parameters (scale, dx, dy) so those hypotheses are
separable, and it WRITES AN OVERLAY IMAGE so the fit can be checked by eye.

Layout constraint used (resourcepanel.json):
  box i (wood,food,gold,stone) ref rect = (15 + 200*i, 15, 84, 84)
The resource PNGs are 96x96 and are stretched into the 84x84 widget box, so the
template is resource_<n>.png resized to 84*scale.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import numpy as np
from PIL import Image

O = _HERE_PATH("_probe", "hud_render")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
ICONS = os.path.join(GAME, r"widgetui\textures\ingame\icons")
ATT = r"C:\Users\26913\.dsh\attachments\v1\objects"
SHOTS = [
    ("shot0", os.path.join(ATT, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")),
    ("shot1", os.path.join(ATT, "2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974")),
    ("shot2", os.path.join(ATT, "16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be")),
    ("shot3", os.path.join(ATT, "8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850")),
    ("shot4", os.path.join(ATT, "89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9")),
]
NAMES = ["wood", "food", "gold", "stone"]
SRC = [Image.open(os.path.join(ICONS, "resource_%s.png" % n)).convert("RGBA") for n in NAMES]
YMAX = 260          # only the top strip is searched
D = 4               # working downsample factor for the coarse pass

rep = []
rep.append("sources: " + ", ".join("resource_%s.png %s" % (NAMES[i], SRC[i].size) for i in range(4)))
rep.append("icon files are 96x96 and get stretched into the 84x84 widget box, so the match")
rep.append("template is resource_<n>.png resized to 84*scale (that stretch is what the game does).")
rep.append("predicted ref rects: box i = (15+200*i, 15, 84, 84)   template = 96px PNG -> 84*scale")
rep.append("coarse pass: downsample %d, step 2 on the coarse grid; then full-res refinement" % D)
rep.append("")

def score(arr, sc, dx, dy):
    """Mean |win - template| over each template's opaque pixels, averaged over the 4 icons.

    Everything here is expressed in the units of `arr` itself. That matters: the
    coarse pass reads a /D-downsampled array, so its scale is scale_full/D and its
    bs is round(84*scale_full/D). Passing a full-res scale with a coarse array (an
    earlier version of this file did exactly that) silently mis-sizes every
    template and makes the search meaningless.
    """
    bs = int(round(84.0 * sc))
    if bs < 4:
        return None
    build_templates(bs)
    tot, n = 0.0, 0
    for i in range(4):
        lx = int(round((15 + 200 * i) * sc)) + dx
        ly = int(round(15 * sc)) + dy
        if lx < 0 or ly < 0 or lx + bs > arr.shape[1] or ly + bs > arr.shape[0]:
            return None
        win = arr[ly:ly + bs, lx:lx + bs, :]
        te = TEMP_CACHE.get((i, bs))
        if te is None:
            return None
        m = te[1]
        if m.sum() < 8:
            return None
        tot += float(np.abs(win[m] - te[0][m]).mean())
        n += 1
    return tot / n if n else None

TEMP_CACHE = {}
def build_templates(size, full_src=True):
    for i in range(4):
        key = (i, size)
        if key not in TEMP_CACHE:
            t = SRC[i].resize((size, size), Image.LANCZOS)
            a = np.asarray(t, dtype=np.float64)
            TEMP_CACHE[key] = (a[:, :, :3], a[:, :, 3] > 200)
    return size

best_all = {}
for tag, path in SHOTS:
    im = Image.open(path).convert("RGB")
    W, H = im.size
    full = np.asarray(im, dtype=np.float64)
    coarse_img = full[::D, ::D, :]
    coarse_strip = coarse_img[:YMAX // D, :, :]

    # ---------- coarse ----------
    # All units here are coarse (i.e. /D) pixels: sc_c = sc_full / D.
    cb = (1e18, None, None, None)
    for sc_c in np.arange(0.30 / D, 0.96 / D, 0.01 / D):
        for dy_c in range(-3, 14):
            for dx_c in range(-10, 16):
                v = score(coarse_strip, sc_c, dx_c, dy_c)
                if v is not None and v < cb[0]:
                    cb = (v, sc_c, dx_c, dy_c)
    _, s0c, dx0c, dy0c = cb
    rep.append("   [coarse raw] scale_c=%.4f dx_c=%d dy_c=%d score=%.2f" % (s0c, dx0c, dy0c, cb[0]))
    s0, dx0, dy0 = s0c * D, dx0c * D, dy0c * D

    # ---------- full-res refinement ----------
    fb = (1e18, None, None, None)
    for s in np.arange(s0 - 0.02, s0 + 0.0201, 0.001):
        for dy in range(dy0 - 3 * D, dy0 + 3 * D + 1, 2):
            for dx in range(dx0 - 3 * D, dx0 + 3 * D + 1, 2):
                v = score(full[:YMAX, :, :], s, dx, dy)
                if v is not None and v < fb[0]:
                    fb = (v, s, dx, dy)
    sc, s, dx, dy = fb
    best_all[tag] = dict(scale=s, dx=dx, dy=dy, score=sc, W=W, H=H)

    rep.append("%s  %dx%d   W/3840=%.6f  H/2160=%.6f" % (tag, W, H, W / 3840.0, H / 2160.0))
    rep.append("   coarse best: scale=%.3f dx=%d dy=%d score=%.2f" % (s0, dx0, dy0, cb[0]))
    rep.append("   FULL   best: scale=%.4f dx=%d dy=%d score=%.2f" % (s, dx, dy, sc))
    bs = int(round(84.0 * s))
    centres = [round(((15 + 200 * i) * s + dx + bs / 2.0), 1) for i in range(4)]
    rep.append("   box size 84*s = %.1f px   box centres x = %s" % (bs, centres))
    rep.append("   observed pitch (centre-to-centre) = %.1f px  = 200*%.4f"
               % (centres[1] - centres[0], (centres[1] - centres[0]) / 200.0))
    rep.append("   layout-predicted rect of box0 at this scale: (%d,%d,%d,%d)"
               % (int(round(15 * s)) + dx, int(round(15 * s)) + dy, bs, bs))
    rep.append("")

    # ---------- overlay for visual verification ----------
    crop = im.crop((0, 0, min(W, 1000), 240))
    Z = 2
    big = crop.resize((crop.width * Z, crop.height * Z), Image.LANCZOS)
    px = big.load()
    def rect(x, y, w, h, col):
        for xx in range(max(0, x), min(big.width, x + w)):
            for yy in (y, y + h - 1):
                if 0 <= yy < big.height:
                    px[xx, yy] = col
        for yy in range(max(0, y), min(big.height, y + h)):
            for xx in (x, x + w - 1):
                if 0 <= xx < big.width:
                    px[xx, yy] = col
    for i in range(4):
        lx = (int(round((15 + 200 * i) * s)) + dx) * Z
        ly = (int(round(15 * s)) + dy) * Z
        rect(lx, ly, bs * Z, bs * Z, (255, 0, 255))
    # also mark the raw layout prediction with no offset, in cyan
    for i in range(4):
        lx = int(round((15 + 200 * i) * s)) * Z
        ly = int(round(15 * s)) * Z
        rect(lx, ly, bs * Z, bs * Z, (0, 255, 255))
    big.save(os.path.join(O, "ref_overlay_%s.png" % tag))
    rep.append("   wrote ref_overlay_%s.png (native 0,0-1000,240 at %dx; magenta=fitted, cyan=no-offset)" % (tag, Z))

if best_all:
    ss = [r["scale"] for r in best_all.values()]
    dxs = [r["dx"] for r in best_all.values()]
    dys = [r["dy"] for r in best_all.values()]
    rep.append("")
    rep.append("ACROSS SHOTS: mean scale=%.4f spread=%.4f   mean dx=%.1f  mean dy=%.1f"
               % (float(np.mean(ss)), float(np.max(ss) - np.min(ss)), float(np.mean(dxs)), float(np.mean(dys))))
    rep.append("naive expectation W/3840 = %.4f ; H/2160 = %.4f" % (2730 / 3840.0, 1535 / 2160.0))
    rep.append("ratio observed/naive = %.4f" % (float(np.mean(ss)) / (2730 / 3840.0)))

txt = "\n".join(rep)
open(os.path.join(O, "align_measure.txt"), "w", encoding="utf-8").write(txt)
print(txt)
