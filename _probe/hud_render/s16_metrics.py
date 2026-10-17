# -*- coding: utf-8 -*-
"""Honest fidelity metrics for the resource-panel render vs a real screenshot.

Why the naive metric in s15_compare.py is misleading:
  It computed a flat MAD over the whole 1750x276 layout rect and got 78.55. But
  resource-panel.png is 57.1% FULLY TRANSPARENT (measured in the earlier probe),
  so most of that "error" is the olive backdrop I composited showing through
  where the real screenshot shows desert terrain. That measures my choice of
  backdrop, not my fidelity. This script therefore reports:

  1. MAD restricted to pixels where the RENDER's own alpha is opaque (>200).
  2. MAD restricted to the art's opaque pixels AND excluding text-value regions
     (the layout's static "10000"/"300/300" are defaults; the live game shows
     "200"/"5/5", so text pixels differ by construction and must be excluded).
  3. Row/column structural profiles cross-correlated to prove the GEOMETRY
     matches even where the TONE does not.
  4. An optimal-gain / optimal-bias fit: if a single linear tone map collapses
     the error, the disagreement is a global colour pipeline difference rather
     than a structural error.
  5. Enumerates every "resource panel" material in materials.json to test whether
     the shipped layout refers to civ-specific art.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import json
import numpy as np
from PIL import Image

O = _HERE_PATH("_probe", "hud_render")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOT = r"C:\Users\26913\.dsh\attachments\v1\objects\02\0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"
S = 0.5980
CP = (0, 0, 1750, 276)
rep = []

real_full = Image.open(SHOT).convert("RGB")
cw, ch = int(round(CP[2] * S)), int(round(CP[3] * S))
real_rgb = real_full.crop((0, 0, cw, ch))

mine_full = Image.open(os.path.join(O, "out", "resourcepanel_4k.png")).convert("RGBA")
mine_crop = mine_full.crop(CP)
alpha = np.asarray(mine_crop, dtype=np.uint8)[:, :, 3]
bgc = np.array([95, 110, 80], dtype=np.float64)
ma = np.asarray(mine_crop, dtype=np.float64)
af = (ma[:, :, 3:4] / 255.0)
flat = ma[:, :, :3] * af + bgc * (1 - af)
mine_rgb = Image.fromarray(flat.astype(np.uint8))
mine = mine_rgb.resize((cw, ch), Image.LANCZOS)
mine_a = np.asarray(Image.fromarray(alpha).resize((cw, ch), Image.BILINEAR), dtype=np.uint8)

a = np.asarray(real_rgb, dtype=np.float64)
b = np.asarray(mine, dtype=np.float64)
diff = np.abs(a - b)
rep.append("crop %dx%d (layout %s at scale %.4f)" % (cw, ch, CP, S))
rep.append("")

# ---- 1. alpha-restricted MAD ----
m_art = mine_a > 200
rep.append("METRIC 1 -- restricted to the render's opaque art pixels")
rep.append("   opaque art pixels: %d / %d = %.1f%% of the crop" % (m_art.sum(), m_art.size, 100.0 * m_art.sum() / m_art.size))
if m_art.sum():
    d1 = diff[m_art].mean()
    rep.append("   MAD over art pixels        = %.2f" % d1)
    rep.append("   MAD over whole crop        = %.2f  (inflated by transparent regions)" % diff.mean())
    # per-channel bias: is it a global tone shift?
    for ci, cn in enumerate("RGB"):
        rep.append("      channel %s: real mean %6.1f  render mean %6.1f  bias %+6.1f"
                   % (cn, a[:, :, ci][m_art].mean(), b[:, :, ci][m_art].mean(),
                      b[:, :, ci][m_art].mean() - a[:, :, ci][m_art].mean()))
    # optimal single gain+offset per channel
    rep.append("   best single linear tone map per channel (render -> real):")
    for ci, cn in enumerate("RGB"):
        x = b[:, :, ci][m_art]
        y = a[:, :, ci][m_art]
        A = np.vstack([x, np.ones_like(x)]).T
        sol, *_ = np.linalg.lstsq(A, y, rcond=None)
        pred = A @ sol
        res = float(np.abs(pred - y).mean())
        rep.append("      %s: real = %.3f*render %+.1f   -> residual MAD %.2f  (from %.2f)"
                   % (cn, sol[0], sol[1], res, float(np.abs(x - y).mean())))
rep.append("")

# ---- 2. structural profiles ----
rep.append("METRIC 2 -- structural profiles (geometry check, tone-independent)")
ra = a.mean(axis=2)
rb = b.mean(axis=2)
# normalise each profile so only SHAPE is compared
rp = ra.mean(axis=1)
bp = rb.mean(axis=1)
rn = (rp - rp.mean()) / max(1e-9, rp.std())
bn = (bp - bp.mean()) / max(1e-9, bp.std())
row_cc = float(np.corrcoef(rn, bn)[0, 1])
rcp = ra.mean(axis=0)
bcp = rb.mean(axis=0)
rcn = (rcp - rcp.mean()) / max(1e-9, rcp.std())
bcn = (bcp - bcp.mean()) / max(1e-9, bcp.std())
col_cc = float(np.corrcoef(rcn, bcn)[0, 1])
rep.append("   row-profile (vertical structure) correlation   r = %+.4f" % row_cc)
rep.append("   col-profile (horizontal structure) correlation r = %+.4f" % col_cc)
# best sub-pixel shift: does a small shift improve it?
best = (row_cc, 0)
for sh in range(-4, 5):
    if sh == 0:
        continue
    if sh > 0:
        x1, x2 = rn[:-sh], bn[sh:]
    else:
        x1, x2 = rn[-sh:], bn[:sh]
    c = float(np.corrcoef(x1, x2)[0, 1])
    if c > best[0]:
        best = (c, sh)
rep.append("   best row shift = %+d px -> r = %+.4f  (0 means no vertical offset needed)" % (best[1], best[0]))
bestc = (col_cc, 0)
for sh in range(-4, 5):
    if sh == 0:
        continue
    if sh > 0:
        x1, x2 = rcn[:-sh], bcn[sh:]
    else:
        x1, x2 = rcn[-sh:], bcn[:sh]
    c = float(np.corrcoef(x1, x2)[0, 1])
    if c > bestc[0]:
        bestc = (c, sh)
rep.append("   best col shift = %+d px -> r = %+.4f  (0 means no horizontal offset needed)" % (bestc[1], bestc[0]))
rep.append("")

# ---- 3. how much of the frame is close, alpha-aware ----
rep.append("METRIC 3 -- alpha-aware closeness")
for t in (8, 16, 32, 64):
    rep.append("   %.1f%% of art pixels differ by <= %d in every channel"
               % (100.0 * float((diff.max(axis=2) <= t)[m_art].mean()), t))

# ---- 4. per-art-region breakdown ----
rep.append("")
rep.append("METRIC 4 -- per-art-region MAD (only where alpha>200)")
regions = [("plank art (no text)", 0, 0.085), ("wood box+icon", 0.085, 0.16),
           ("plank between boxes", 0.16, 0.20), ("food box+icon", 0.20, 0.275),
           ("plank", 0.275, 0.315), ("gold box+icon", 0.315, 0.39),
           ("plank", 0.39, 0.43), ("stone box+icon", 0.43, 0.505),
           ("plank", 0.505, 0.545), ("population box", 0.545, 0.62),
           ("flash rect / popcount", 0.62, 0.70), ("idle badge", 0.70, 0.76),
           ("age medallion slot", 0.76, 0.84), ("age bar", 0.84, 1.0)]
for nm, f0, f1 in regions:
    x0, x1 = int(cw * f0), int(cw * f1)
    sel = m_art[:, x0:x1]
    if sel.sum() < 200:
        rep.append("   %-22s x %4d-%4d  (too few opaque px)" % (nm, x0, x1))
        continue
    rep.append("   %-22s x %4d-%4d  MAD=%6.2f  opaque=%5.1f%%"
               % (nm, x0, x1, diff[:, x0:x1, :][sel].mean(), 100.0 * sel.mean()))

# ---- 5. civ panel materials ----
rep.append("")
rep.append("METRIC 5 -- are there civ-specific resource-panel materials?")
mat = json.load(open(os.path.join(GAME, r"widgetui\materials.json"), encoding="utf-8"))
hits = []
for e in mat["Materials"]:
    d = e.get("MaterialDef") or {}
    nm = d.get("Name") or ""
    ref = str(d.get("TextureRef") or "")
    if ("resource" in nm.lower() and "panel" in nm.lower()) or "resource-panel" in ref.lower():
        hits.append((nm, d.get("Type"), d.get("AtlasRef"), ref))
for h in sorted(hits):
    rep.append("   %-28s type=%-8s atlas=%-14s ref=%s" % h)
rep.append("   total %d matching materials" % len(hits))

# which atlas entries point at any ASIA resource panel art?
rep.append("")
rep.append("   atlas entries whose FileName contains 'resource-panel':")
for at in mat["AtlasTextures"]:
    d = at.get("AtlasDef") or {}
    for t in d.get("Textures") or []:
        fn = str(t.get("FileName") or "")
        if "resource-panel" in fn.lower() or "resource_panel" in fn.lower():
            rep.append("      atlas %-16s RefName=%-24s %s" % (d.get("Name"), t.get("RefName"), fn))

txt = "\n".join(rep)
open(os.path.join(O, "cmp_resource_metrics.txt"), "w", encoding="utf-8").write(txt)
print(txt)
