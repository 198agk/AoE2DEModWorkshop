# -*- coding: utf-8 -*-
"""What art is ACTUALLY displayed behind the in-game resource panel?

The contradiction this settles:
  - the four resource ICONS match the real screenshot at MAD 12-16 (scale 0.598,
    no tone mapping), so there is NO global gamma/brightness difference;
  - yet the PLANK that resourcepanel.json names (CivAsiaResourcePanel ->
    ASIA/resource-panel.png) matches at MAD ~52-80, and NONE of the 17 candidate
    panel PNGs does better.

Two hypotheses remain:
  H1  the visible plank wood is a DIFFERENT texture layered under the resource
      panel (candidate: CivAsiaTopbar -> ASIA/topbar.png), showing through the
      transparent interior of resource-panel.png;
  H2  the resource panel's own art is right and my compositing is wrong.

Test: score EVERY CivAsia atlas entry plus all 17 resource-panel PNGs against the
real screenshot's bar region, masked to each candidate's own alpha>200, at the
independently-verified HUD scale 0.598. Then visually composite the leading
combination under the resource panel and compare with the real bar.
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
WID = os.path.join(GAME, "widgetui")
SHOT = r"C:\Users\26913\.dsh\attachments\v1\objects\02\0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"
SC = 0.5980
rep = []

shot = Image.open(SHOT).convert("RGB")
W, H = shot.size
arr = np.asarray(shot, dtype=np.float64)
rep.append("reference %dx%d ; HUD scale %s (independently fitted from icon geometry)" % (W, H, SC))
rep.append("")

M = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
mats = {}
for e in M["Materials"]:
    d = e["MaterialDef"]
    mats[d["Name"]] = d

# ---------------------------------------------------------------- candidates
cands = []  # (label, path)
for e in M["AtlasTextures"]:
    a = e["AtlasDef"]
    if a["Name"] == "CivAsia":
        for t in a["Textures"]:
            p = os.path.join(WID, *t["FileName"].split("/"))
            if os.path.exists(p):
                cands.append(("CivAsia/" + t["RefName"], p))
for nm in sorted(mats):
    d = mats[nm]
    if not nm.endswith("ResourcePanel"):
        continue
    a = None
    for e in M["AtlasTextures"]:
        if e["AtlasDef"]["Name"] == d.get("AtlasRef"):
            a = e["AtlasDef"]
            break
    if not a:
        continue
    for t in a["Textures"]:
        if t["RefName"] == d["TextureRef"]:
            p = os.path.join(WID, *t["FileName"].split("/"))
            if os.path.exists(p):
                cands.append((nm, p))
# dedupe by path
seen, uniq = set(), []
for lbl, p in cands:
    if p not in seen:
        seen.add(p)
        uniq.append((lbl, p))
cands = uniq
rep.append("candidates: %d distinct PNGs" % len(cands))

# ---------------------------------------------------------------- scoring
def score(path, rect):
    """Masked MAD of the scaled PNG against the screenshot inside rect."""
    im = Image.open(path).convert("RGBA")
    tw, th = int(round(im.width * SC)), int(round(im.height * SC))
    t = im.resize((tw, th), Image.LANCZOS)
    ta = np.asarray(t, dtype=np.float64)
    x0, y0, x1, y1 = rect
    # place the texture at the rect origin, clip to the screenshot
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(W, min(x1, x0 + tw)), min(H, min(y1, y0 + th))
    if cx1 - cx0 < 60 or cy1 - cy0 < 24:
        return None
    tas = ta[cy0 - y0:cy0 - y0 + (cy1 - cy0), cx0 - x0:cx0 - x0 + (cx1 - cx0)]
    win = arr[cy0:cy1, cx0:cx1]
    m = tas[:, :, 3] > 200
    if m.sum() < 1500:
        return None
    a3 = tas[:, :, :3]
    mad = float(np.abs(a3[m] - win[m]).mean())
    cc = float(np.corrcoef(a3[m].mean(axis=1), win[m].mean(axis=1))[0, 1]) if a3[m].mean(axis=1).std() > 1e-6 else 0.0
    return mad, cc, int(m.sum()), t

BAR = (0, 0, 2000, 200)
rows = []
for lbl, p in cands:
    r = score(p, BAR)
    if r:
        rows.append((r[0], r[1], lbl, p, r[2]))
rows.sort()
rep.append("")
rep.append("Scored against the real bar region %s, masked to each candidate's alpha>200:" % (BAR,))
rep.append("  %-38s %8s %9s %10s" % ("candidate", "MAD", "corr", "maskedpx"))
for mad, cc, lbl, p, n in rows[:20]:
    rep.append("  %-38s %8.2f %+9.4f %10d" % (lbl, mad, cc, n))

# reference: the four icons, which are known-correct
rep.append("")
rep.append("Known-good calibration (the four resource icons, layout-derived rects):")
for i, (nm, rel) in enumerate([("ResourceWood", r"textures\ingame\icons\resource_wood.png"),
                               ("ResourceFood", r"textures\ingame\icons\resource_food.png"),
                               ("ResourceGold", r"textures\ingame\icons\resource_gold.png"),
                               ("ResourceStone", r"textures\ingame\icons\resource_stone.png")]):
    p = os.path.join(WID, rel)
    im = Image.open(p).convert("RGBA")
    tw, th = int(round(im.width * SC)), int(round(im.height * SC))
    t = im.resize((tw, th), Image.LANCZOS)
    lx = int(round(15 * SC)) + int(round(200 * i * SC))
    ly = int(round(15 * SC))
    ta = np.asarray(t, dtype=np.float64)
    cx1, cy1 = min(W, lx + tw), min(H, ly + th)
    tas = ta[:cy1 - ly, :cx1 - lx]
    win = arr[ly:cy1, lx:cx1]
    m = tas[:, :, 3] > 200
    a3 = tas[:, :, :3]
    rep.append("  %-14s MAD=%.2f corr=%+.4f px=%d" % (nm, np.abs(a3[m] - win[m]).mean(),
               np.corrcoef(a3[m].mean(axis=1), win[m].mean(axis=1))[0, 1], m.sum()))

# ---------------------------------------------------------------- visual
top = rows[:6]
tiles = [("REAL", shot.crop((0, 0, 1400, int(round(276 * SC)))))]
for mad, cc, lbl, p, n in top:
    r = score(p, (0, 0, 1400, 200))
    if not r:
        continue
    t = r[3]
    flat = Image.new("RGB", t.size, (95, 110, 80))
    flat.paste(t, (0, 0), t)
    tiles.append(("%s  MAD=%.1f" % (lbl[:26], mad), flat))
tw = max(t.width for _, t in tiles)
hh = max(t.height for _, t in tiles)
stack = Image.new("RGB", (tw, len(tiles) * (hh + 20)), (28, 28, 32))
d = ImageDraw.Draw(stack)
for i, (lbl, t) in enumerate(tiles):
    stack.paste(t, (0, i * (hh + 20)))
    d.text((4, i * (hh + 20) + 3), lbl, fill=(255, 255, 0) if i else (255, 255, 255))
stack.save(os.path.join(O, "cmp_candidates_all.png"))
rep.append("")
rep.append("wrote cmp_candidates_all.png %s (%d tiles)" % (stack.size, len(tiles)))

txt = "\n".join(rep)
open(os.path.join(O, "candidates_all.txt"), "w", encoding="utf-8").write(txt)
print(txt)
