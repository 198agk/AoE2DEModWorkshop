# -*- coding: utf-8 -*-
"""Independently locate the four resource icons and identify the plank art.

Two open contradictions this script resolves:

 A) GEOMETRY. s14_align2.py fitted scale=0.598 by matching icons but CONSTRAINED
    them to the layout's predicted pitch (200 ref px). If that constraint is wrong
    the whole fit is self-confirming. Here each of the four icons is matched
    INDEPENDENTLY over a wide x range with no pitch assumption, so the true box
    size and true pitch fall out of the data.

 B) TONE/ART. s16_metrics.py found the render is far darker than the reference
    (per-channel bias -24/-42/-51, optimal gain ~0.26-0.32). A pure linear tone
    gap that large suggests the game is not drawing the art I think it is. There
    are 17 candidate resource-panel materials (16 civ-specific + one generic), so
    this script scores ALL of them against the real screenshot and reports which
    one actually matches.

Also fixes the misleading profile metric: profiles are restricted to the plank
band (y < 70) so they measure the HUD, not the terrain below it.
"""
import os
import json
import numpy as np
from PIL import Image

O = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
ICONS = os.path.join(GAME, r"widgetui\textures\ingame\icons")
SHOT = r"C:\Users\26913\.dsh\attachments\v1\objects\02\0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"
NAMES = ["wood", "food", "gold", "stone"]
rep = []

shot = Image.open(SHOT).convert("RGB")
W, H = shot.size
arr = np.asarray(shot, dtype=np.float64)
rep.append("reference %s  %dx%d" % (os.path.basename(SHOT), W, H))
rep.append("")

# ---------------------------------------------------------------- A) geometry
rep.append("=" * 70)
rep.append("A) INDEPENDENT ICON LOCATION (no pitch constraint)")
rep.append("=" * 70)

def _ncc(win, tc, tm):
    a = win[tm] - win[tm].mean()
    b = tc[tm] - tc[tm].mean()
    den = np.sqrt((a * a).sum() * (b * b).sum())
    if den < 1e-9:
        return 1e9
    return float((a * b).sum() / den)

def find_icon(name, D=4):
    """Coarse-to-fine NCC search. A flat brute force over all sizes/positions is
    ~2.5M masked NCC evaluations per icon, which is far too slow; the coarse pass
    at 1/D resolution cuts that by ~D^3 and the refinement recovers the exact
    position. Coordinates are converted back to full-res pixels at the end."""
    src = Image.open(os.path.join(ICONS, "resource_%s.png" % name)).convert("RGBA")
    small = arr[::D, ::D, :]
    hs, ws = small.shape[0], small.shape[1]
    xmax_c = min(ws, 1300 // D)

    # ---- coarse ----
    cb = (1e18, None, None, None)
    for size in range(max(4, 26 // D), 130 // D + 1, 1):
        t = np.asarray(src.resize((size, size), Image.LANCZOS), dtype=np.float64)
        tc, tm = t[:, :, :3], t[:, :, 3] > 200
        if tm.sum() < 20:
            continue
        for y in range(0, min(hs - size, 170 // D), 1):
            for x in range(0, max(1, xmax_c - size), 1):
                win = small[y:y + size, x:x + size, :]
                if win.shape != tc.shape:
                    continue
                ncc = _ncc(win, tc, tm)
                if ncc < cb[0]:
                    cb = (ncc, size, x, y)
    if cb[1] is None:
        return (1e9, None, None, None)
    _, cs, cx, cy = cb

    # ---- refine at full resolution ----
    fb = (1e18, None, None, None)
    for size in range(max(8, cs * D - 2 * D), cs * D + 2 * D + 1):
        t = np.asarray(src.resize((size, size), Image.LANCZOS), dtype=np.float64)
        tc, tm = t[:, :, :3], t[:, :, 3] > 200
        if tm.sum() < 30:
            continue
        for y in range(max(0, cy * D - 2 * D), min(H - size, cy * D + 2 * D + 1)):
            for x in range(max(0, cx * D - 2 * D), min(W - size, cx * D + 2 * D + 1)):
                win = arr[y:y + size, x:x + size, :]
                if win.shape != tc.shape:
                    continue
                ncc = _ncc(win, tc, tm)
                if ncc < fb[0]:
                    fb = (ncc, size, x, y)
    return fb

found = {}
for nm in NAMES:
    ncc, size, x, y = find_icon(nm)
    found[nm] = (x, y, size, ncc)
    rep.append("   %-6s best NCC=%.4f  size=%3d  at (%3d,%3d)  centre x=%6.1f"
               % (nm, -ncc, size, x, y, x + size / 2.0))
size = [found[n][2] for n in NAMES]
xs = [found[n][0] for n in NAMES]
ys = [found[n][1] for n in NAMES]
rep.append("   matched sizes: %s   (84 ref px would be the same value for all four)" % size)
rep.append("   matched x:     %s" % xs)
rep.append("   matched y:     %s" % ys)
s_box = float(np.mean(size))
rep.append("")
rep.append("   mean matched size %.1f px -> 84 ref px maps to %.1f px => scale %.4f"
           % (s_box, s_box, s_box / 84.0))
if len(set(size)) == 1:
    rep.append("   (all four matched the SAME size, which is what the layout predicts)")
else:
    rep.append("   (sizes differ by up to %d px -- expected: the four icons are different" % (max(size) - min(size)))
    rep.append("    pictures, so a masked-NCC over each one independently need not agree exactly.)")
meas_pitch = None
if len(xs) == 4:
    pb = [xs[i + 1] - xs[i] for i in range(3)]
    rep.append("   measured left-edge pitches: %s" % pb)
    rep.append("   mean pitch = %.1f px  ->  200 ref px maps to %.1f px  => scale = %.4f"
               % (float(np.mean(pb)), float(np.mean(pb)), float(np.mean(pb)) / 200.0))
    meas_pitch = float(np.mean(pb))
    rep.append("   CONSISTENCY: size-derived scale %.4f vs pitch-derived scale %.4f  (delta %+.4f)"
               % (s_box / 84.0, float(np.mean(pb)) / 200.0, s_box / 84.0 - float(np.mean(pb)) / 200.0))
    rep.append("   NOTE layout pitch is 200 ref px (57->257->457->657), so this is a hard constraint.")
rep.append("")

# ---------------------------------------------------------------- B) art identity
rep.append("=" * 70)
rep.append("B) WHICH PANEL ART DOES THE GAME ACTUALLY DRAW?")
rep.append("=" * 70)

mat = json.load(open(os.path.join(GAME, r"widgetui\materials.json"), encoding="utf-8"))
# map material name -> FileName via its atlas
def file_for_ref(atlas_name, ref):
    for at in mat["AtlasTextures"]:
        d = at.get("AtlasDef") or {}
        if d.get("Name") != atlas_name:
            continue
        for t in d.get("Textures") or []:
            if t.get("RefName") == ref:
                return t.get("FileName")
    return None

cands = []
for e in mat["Materials"]:
    d = e.get("MaterialDef") or {}
    nm = d.get("Name") or ""
    if d.get("Type") == "Atlas" and "ResourcePanel" in nm:
        fn = file_for_ref(d.get("AtlasRef"), d.get("TextureRef"))
        if fn:
            cands.append((nm, fn))
rep.append("   %d candidate panel textures" % len(cands))
rep.append("")

# Evaluation window derived from the MEASURED geometry, never from a layout guess.
sc = s_box / 84.0
pw = int(round(1750 * sc))
ph = int(round(276 * sc))
x0 = xs[0] - int(round(15 * sc))
y0 = ys[0] - int(round(15 * sc))
x0 = max(0, x0)
y0 = max(0, y0)
if x0 + pw > W:
    pw = W - x0
if y0 + ph > H:
    ph = H - y0
rep.append("   evaluation window on the screenshot: (%d,%d) %dx%d" % (x0, y0, pw, ph))
real_crop = arr[y0:y0 + ph, x0:x0 + pw, :]
rep.append("")
rep.append("   %-28s %-6s %-9s %s" % ("material", "MAD", "corr", "source PNG"))
res = []
for nm, fn in cands:
    p = os.path.join(GAME, "widgetui", fn.replace("/", os.sep))
    if not os.path.exists(p):
        res.append((9999.0, 0.0, nm, fn + " (MISSING)"))
        continue
    im = Image.open(p).convert("RGBA")
    a = np.asarray(im, dtype=np.float64)
    al = a[:, :, 3]
    # ignore fully transparent source pixels: they are not art, they are holes
    m = al > 200
    t = im.resize((pw, ph), Image.LANCZOS)
    ta = np.asarray(t, dtype=np.float64)
    tm = ta[:, :, 3] > 200
    if tm.sum() < 500:
        res.append((9999.0, 0.0, nm, fn))
        continue
    x = ta[:, :, :3][tm]
    y = real_crop[tm]
    mad = float(np.abs(x - y).mean())
    cc = float(np.corrcoef(x.mean(axis=1), y.mean(axis=1))[0, 1]) if len(x) > 2 else 0.0
    res.append((mad, cc, nm, fn))
res.sort()
for mad, cc, nm, fn in res:
    rep.append("   %-28s %-6.2f %+.4f  %s" % (nm, mad, cc, fn))
rep.append("")
rep.append("   -> lowest MAD wins. If the winner is NOT the material the shipped")
rep.append("      resourcepanel.json names, the layout is civ-parameterised at runtime.")
rep.append("      resourcepanel.json names: CivAsiaResourcePanel")

# ---------------------------------------------------------------- C) fixed profiles
rep.append("")
rep.append("=" * 70)
rep.append("C) STRUCTURAL PROFILE CORRELATION, RESTRICTED TO THE PLANK BAND")
rep.append("=" * 70)
rep.append("   (the earlier whole-crop profiles were dominated by terrain below the")
rep.append("    plank, which is why the column correlation read a meaningless ~0.00)")
mine_full = Image.open(os.path.join(O, "out", "resourcepanel_4k.png")).convert("RGBA")
mc = mine_full.crop((0, 0, 1750, 276))
af = np.asarray(mc, dtype=np.float64)[:, :, 3:4] / 255.0
bgc = np.array([95, 110, 80], dtype=np.float64)
flat = np.asarray(mc, dtype=np.float64)[:, :, :3] * af + bgc * (1 - af)
mine = Image.fromarray(flat.astype(np.uint8)).resize((pw, ph), Image.LANCZOS)
b = np.asarray(mine, dtype=np.float64)

band = 70
ra, rb = real_crop[:band].mean(axis=2), b[:band].mean(axis=2)
for axis, lbl in ((1, "row (vertical)"), (0, "col (horizontal)")):
    pa, pb_ = ra.mean(axis=axis), rb.mean(axis=axis)
    na = (pa - pa.mean()) / max(1e-9, pa.std())
    nb = (pb_ - pb_.mean()) / max(1e-9, pb_.std())
    r = float(np.corrcoef(na, nb)[0, 1])
    bestr = (r, 0)
    for sh in range(-6, 7):
        if sh == 0:
            continue
        if sh > 0:
            x1, x2 = na[:-sh], nb[sh:]
        else:
            x1, x2 = na[-sh:], nb[:sh]
        if len(x1) < 8:
            continue
        c = float(np.corrcoef(x1, x2)[0, 1])
        if c > bestr[0]:
            bestr = (c, sh)
    rep.append("   %-16s r = %+.4f   best shift %+d px -> r = %+.4f" % (lbl, r, bestr[1], bestr[0]))

txt = "\n".join(rep)
open(os.path.join(O, "align_art.txt"), "w", encoding="utf-8").write(txt)
print(txt)
