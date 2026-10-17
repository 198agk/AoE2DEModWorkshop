# -*- coding: utf-8 -*-
"""Identify which civ's resource-panel plank art the reference screenshot shows.

Established geometry (s14_align2.py, verified visually in ref_overlay_shot0.png):
the HUD is drawn at scale 0.5980 with offset (0,0), so the resource panel occupies
screenshot rect (0,0,1046,165). The four resource icons match at MAD 14.4 there,
i.e. the icons are the shipped art and the geometry is right.

But the PLANK beneath/around them matches badly (MAD ~60 over the whole bar), and
a single linear tone map does not fix it (residual 34-48). That is the signature of
a DIFFERENT TEXTURE, not a tone/gamma difference -- resourcepanel.json names
CivAsiaResourcePanel, which is a civ-specific atlas entry, and there are 17
candidates. This script scores all 17 over the correct window, masking to each
candidate's own opaque pixels (so the 57%-transparent regions of the source PNG
are excluded rather than counted as error), and writes a visual stack so the
ranking can be checked by eye.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import json
import numpy as np
from PIL import Image, ImageDraw

O = _HERE_PATH("_probe", "hud_render")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOT = r"C:\Users\26913\.dsh\attachments\v1\objects\02\0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"
S = 0.5980
CW, CH = int(round(1750 * S)), int(round(276 * S))   # 1046 x 165
rep = []

real = Image.open(SHOT).convert("RGB")
crop = real.crop((0, 0, CW, CH))
real_a = np.asarray(crop, dtype=np.float64)

mat = json.load(open(os.path.join(GAME, r"widgetui\materials.json"), encoding="utf-8"))

def file_for(matname):
    for e in mat["Materials"]:
        d = e.get("MaterialDef") or {}
        if d.get("Name") != matname:
            continue
        if d.get("Type") != "Atlas":
            return None
        for at in mat["AtlasTextures"]:
            ad = at.get("AtlasDef") or {}
            if ad.get("Name") != d.get("AtlasRef"):
                continue
            for t in ad.get("Textures") or []:
                if t.get("RefName") == d.get("TextureRef"):
                    return t.get("FileName")
    return None

cands = []
for e in mat["Materials"]:
    d = e.get("MaterialDef") or {}
    nm = d.get("Name") or ""
    if d.get("Type") == "Atlas" and "ResourcePanel" in nm:
        fn = file_for(nm)
        if fn:
            cands.append((nm, fn))

rep.append("reference crop = screenshot (0,0,%d,%d) at measured HUD scale %.4f" % (CW, CH, S))
rep.append("%d candidate plank textures; masking to each candidate's own alpha>200" % len(cands))
rep.append("")
rep.append("%-28s %7s %8s %8s   %s" % ("material", "MAD", "corr", "opaque%", "source"))

rows = []
for nm, fn in cands:
    p = os.path.join(GAME, "widgetui", fn.replace("/", os.sep))
    if not os.path.exists(p):
        rows.append((9999.0, 0.0, 0.0, nm, fn + " MISSING", None))
        continue
    im = Image.open(p).convert("RGBA")
    t = im.resize((CW, CH), Image.LANCZOS)
    ta = np.asarray(t, dtype=np.float64)
    m = ta[:, :, 3] > 200
    if m.sum() < 500:
        rows.append((9999.0, 0.0, 0.0, nm, fn, t))
        continue
    x = ta[:, :, :3][m]
    y = real_a[m]
    mad = float(np.abs(x - y).mean())
    # correlation on the per-pixel luminance, which is robust to a linear tone map
    xg = x.mean(axis=1)
    yg = y.mean(axis=1)
    if xg.std() > 1e-6 and yg.std() > 1e-6:
        cc = float(np.corrcoef(xg, yg)[0, 1])
    else:
        cc = 0.0
    rows.append((mad, cc, 100.0 * m.mean(), nm, fn, t))

rows.sort(key=lambda r: r[0])
for mad, cc, op, nm, fn, t in rows:
    rep.append("%-28s %7.2f %+8.4f %7.1f%%   %s" % (nm, mad, cc, op, fn))

rep.append("")
rep.append("For reference, the shipped layout names CivAsiaResourcePanel:")
for mad, cc, op, nm, fn, t in rows:
    if nm == "CivAsiaResourcePanel":
        rep.append("   CivAsiaResourcePanel rank = %d of %d, MAD=%.2f, corr=%+.4f"
                   % (rows.index((mad, cc, op, nm, fn, t)) + 1, len(rows), mad, cc))
        break

# ---- visual stack: real on top, then the ranked candidates at the SAME rect ----
SHOW = 8
Z = 1
pad = 6
lab = 16
st = Image.new("RGB", (CW, (CH + pad + lab) * (SHOW + 1) + pad), (20, 20, 24))
d = ImageDraw.Draw(st)
d.text((4, 2), "REAL screenshot, crop (0,0,%d,%d)" % (CW, CH), fill=(255, 255, 255))
st.paste(crop, (0, pad + lab))
yy = (CH + pad + lab)
for mad, cc, op, nm, fn, t in rows[:SHOW]:
    rgb = Image.new("RGB", (CW, CH), (95, 110, 80))
    rgb.paste(t, (0, 0), t)
    d.text((4, yy + 2), "%-30s MAD=%.1f  corr=%+.3f" % (nm, mad, cc), fill=(255, 255, 0))
    st.paste(rgb, (0, yy + pad + lab - 4))
    yy += CH + pad + lab
st.save(os.path.join(O, "cmp_plank_candidates.png"))
rep.append("")
rep.append("wrote cmp_plank_candidates.png (real + top %d candidates at identical rect)" % SHOW)

txt = "\n".join(rep)
open(os.path.join(O, "plank_identity.txt"), "w", encoding="utf-8").write(txt)
print(txt)
