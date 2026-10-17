# -*- coding: utf-8 -*-
"""Does the shipped ATLAS DDS hold the same art as the PNG source tree?

Context: the four resource ICONS match the real screenshot well (per-icon MAD 12-16
at the measured HUD scale 0.598, and with NO gamma correction applied), but the
plank behind them does not match any of the 17 candidate PNGs (best MAD ~52-56,
which is the same as the icons' score under the equivalent masked metric, i.e. the
metric has a high floor and is not decisive on its own).

Because the icons match without any tone mapping, there is no GLOBAL gamma
difference. So one of these must be true:

  (a) the screenshot's HUD plank is not the CivAsia art at all (different civ), or
  (b) the ATLAS DDS -- which is what the engine actually samples -- holds a
      different revision of the art than the PNG tree, or
  (c) the screenshots were taken with a different game version / a mod.

This script tests (b) directly: decode the atlas DDS, crop the CivAsiaResourcePanel
entry by its normalized UV rect, and compare it against the PNG source, and against
the screenshot.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import numpy as np
from PIL import Image, ImageChops, ImageDraw

O = _HERE_PATH("_probe", "hud_render")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WID = os.path.join(GAME, "widgetui")
SHOT = r"C:\Users\26913\.dsh\attachments\v1\objects\02\0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"
rep = []

import json
M = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))

# Resolve the material FIRST, then follow its own AtlasRef. (A previous version of
# this script hardcoded atlas "ingamepanels" and silently found no entry, because
# CivAsiaResourcePanel's AtlasRef is actually "CivAsia" -- one of the 16 civ atlases.)
mat = None
for e in M["Materials"]:
    d = e["MaterialDef"]
    if d["Name"] == "CivAsiaResourcePanel":
        mat = d
        break
rep.append("material CivAsiaResourcePanel = %s" % mat)
atlas = None
for e in M["AtlasTextures"]:
    d = e["AtlasDef"]
    if d["Name"] == mat["AtlasRef"]:
        atlas = d
        break
rep.append("  AtlasRef=%s resolves to AtlasDef Name=%s" % (mat["AtlasRef"], atlas and atlas["Name"]))
rep.append("  UHDSource=%s" % atlas["UHDSource"])

# FileName/UHDSource values are relative to the widgetui\ directory.
dds = os.path.join(WID, *atlas["UHDSource"].split("/"))
rep.append("atlas file: %s" % os.path.relpath(dds, GAME))
rep.append("  size %d bytes" % os.path.getsize(dds))
try:
    im = Image.open(dds)
    rep.append("  Pillow opened: size=%s mode=%s format=%s" % (im.size, im.mode, im.format))
    im.load()
    rep.append("  loaded OK")
    im = im.convert("RGBA")
    ok = True
except Exception as e:
    rep.append("  Pillow FAILED: %s: %s" % (type(e).__name__, e))
    ok = False

if ok:
    a = np.asarray(im)
    rep.append("  mean RGB = %.1f %.1f %.1f ; mean alpha = %.1f"
               % (a[:, :, 0].mean(), a[:, :, 1].mean(), a[:, :, 2].mean(), a[:, :, 3].mean()))

    # locate the CivAsiaResourcePanel atlas entry in materials.json
    import json
    M = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
    atlas = None
    for e in M["AtlasTextures"]:
        d = e["AtlasDef"]
        if d["Name"] == "ingamepanels":
            atlas = d
            break
    mat = None
    for e in M["Materials"]:
        d = e["MaterialDef"]
        if d["Name"] == "CivAsiaResourcePanel":
            mat = d
            break
    rep.append("  material CivAsiaResourcePanel = %s" % mat)
    entry = None
    for t in atlas["Textures"]:
        if t["RefName"] == mat["TextureRef"]:
            entry = t
            break
    rep.append("  atlas entry = %s" % entry)
    if entry:
        MW, MH = int(atlas["MaxWidth"]), int(atlas["MaxHeight"])
        tlx = float(entry["imageTLX"]); tly = float(entry["imageTLY"])
        brx = float(entry["imageBRX"]); bry = float(entry["imageBRY"])
        r = (int(round(tlx * MW)), int(round(tly * MH)), int(round(brx * MW)), int(round(bry * MH)))
        rep.append("  atlas MaxW/H = %dx%d ; UV -> pixel rect %s (w=%d h=%d)"
                   % (MW, MH, r, r[2] - r[0], r[3] - r[1]))
        dds_crop = im.crop(r)
        dds_crop.save(os.path.join(O, "atlas_civasia_crop.png"))
        png = Image.open(os.path.join(WID, entry["FileName"])).convert("RGBA")
        rep.append("  PNG source %s %s" % (entry["FileName"], png.size))
        if png.size == dds_crop.size:
            x = np.asarray(png.convert("RGB"), dtype=np.float64)
            y = np.asarray(dds_crop.convert("RGB"), dtype=np.float64)
            m = (np.asarray(png)[:, :, 3] > 200) & (np.asarray(dds_crop)[:, :, 3] > 200)
            rep.append("  PNG vs ATLAS-DDS on commonly-opaque pixels (%d px): MAD=%.2f  corr=%+.4f"
                       % (m.sum(), np.abs(x[m] - y[m]).mean(),
                          np.corrcoef(x[m].mean(axis=1), y[m].mean(axis=1))[0, 1]))
            rep.append("  PNG    mean RGB %.1f %.1f %.1f   alpha>200 %.1f%%"
                       % (x[:, :, 0].mean(), x[:, :, 1].mean(), x[:, :, 2].mean(), 100.0 * (np.asarray(png)[:, :, 3] > 200).mean()))
            rep.append("  DDS    mean RGB %.1f %.1f %.1f   alpha>200 %.1f%%"
                       % (y[:, :, 0].mean(), y[:, :, 1].mean(), y[:, :, 2].mean(), 100.0 * (np.asarray(dds_crop)[:, :, 3] > 200).mean()))
        # compare both against the screenshot at HUD scale 0.598
        shot = Image.open(SHOT).convert("RGB")
        W, H = shot.size
        arr = np.asarray(shot, dtype=np.float64)
        sc = 0.5980
        tw, th = int(round(png.width * sc)), int(round(png.height * sc))
        row = []
        for tag, src in (("PNG", png), ("DDS", dds_crop)):
            t = src.resize((tw, th), Image.LANCZOS)
            ta = np.asarray(t, dtype=np.float64)
            lx, ly = 0, 0
            cx1, cy1 = min(W, lx + tw), min(H, ly + th)
            tas = ta[:cy1 - ly, :cx1 - lx]
            win = arr[ly:cy1, lx:cx1]
            m = tas[:, :, 3] > 200
            a3 = tas[:, :, :3]
            rep.append("  %s scaled %.3f -> %dx%d ; vs screenshot on mask: MAD=%.2f corr=%+.4f px=%d"
                       % (tag, sc, tw, th, np.abs(a3[m] - win[m]).mean(),
                          np.corrcoef(a3[m].mean(axis=1), win[m].mean(axis=1))[0, 1], m.sum()))
            row.append(Image.fromarray(a3.astype(np.uint8)))
        # build visual: real | png | dds
        rsub = shot.crop((0, 0, tw, th)).convert("RGB")
        stack = Image.new("RGB", (tw, th * 3 + 36), (20, 20, 24))
        stack.paste(rsub, (0, 0))
        stack.paste(row[0], (0, th + 18))
        stack.paste(row[1], (0, th * 2 + 36))
        d = ImageDraw.Draw(stack)
        d.text((4, 2), "REAL screenshot (0,0,%d,%d)" % (tw, th), fill=(255, 255, 255))
        d.text((4, th + 20), "PNG source tree, scaled 0.598", fill=(255, 255, 0))
        d.text((4, th * 2 + 38), "ATLAS UHD DDS crop, scaled 0.598", fill=(0, 255, 255))
        stack.save(os.path.join(O, "cmp_png_vs_atlas.png"))
        rep.append("  wrote cmp_png_vs_atlas.png %s" % (stack.size,))

txt = "\n".join(rep)
open(os.path.join(O, "atlas_vs_png.txt"), "w", encoding="utf-8").write(txt)
print(txt)
