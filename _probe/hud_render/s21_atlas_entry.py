# -*- coding: utf-8 -*-
"""Decisive test for the plank mismatch: WHAT art does the CivAsia atlas actually hold?

A prior report in this workspace (`UI贴图模组能力目录v1.md` §9) records this exact
offline-HUD task as FAILED, and one of its explicit "must redo" instructions is:

    ② 按 `TextureRef` 反查图集取艺术（不要按 `Name`）
       (resolve art by TextureRef, not by Name)

That is a real trap and s20 stepped straight into it: looking up RefName
"CivAsiaResourcePanel" inside the CivAsia atlas returned None. So the atlas entry
NAMES do not necessarily equal the material's TextureRef. If the true entry points
at a different FileName, then the PNG I have been comparing against all along is the
WRONG ART, which would explain why no candidate plank matched at MAD ~52-56 while the
icons matched at MAD 12-16.

This script dumps every CivAsia atlas entry, resolves CivAsiaResourcePanel by
TextureRef and by Name, crops the ATLAS DDS by the normalized UV rect, and puts
atlas-crop / PNG / real-screenshot side by side.
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
rep = []

M = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
rep.append("materials.json: Materials=%d AtlasTextures=%d GlobalTextures=%d"
           % (len(M["Materials"]), len(M["AtlasTextures"]), len(M["GlobalTextures"])))
rep.append("")

# ---- 1. dump every CivAsia atlas entry ------------------------------------
atlas = None
for e in M["AtlasTextures"]:
    if e["AtlasDef"]["Name"] == "CivAsia":
        atlas = e["AtlasDef"]
        break
rep.append("AtlasDef CivAsia: MaxW=%s MaxH=%s UHDSource=%s"
           % (atlas["MaxWidth"], atlas["MaxHeight"], atlas["UHDSource"]))
rep.append("  Textures[] count = %d" % len(atlas["Textures"]))
rep.append("")
rep.append("  %-3s %-42s %s" % ("#", "RefName", "FileName"))
for i, t in enumerate(atlas["Textures"]):
    rep.append("  %-3d %-42s %s" % (i, t["RefName"], t["FileName"]))
rep.append("")

# ---- 2. resolve the material several ways ---------------------------------
mats = {e["MaterialDef"]["Name"]: e["MaterialDef"] for e in M["Materials"]}
mat = mats["CivAsiaResourcePanel"]
rep.append("material CivAsiaResourcePanel: TextureRef=%r AtlasRef=%r" % (mat["TextureRef"], mat["AtlasRef"]))
byref = [t for t in atlas["Textures"] if t["RefName"] == mat["TextureRef"]]
byname = [t for t in atlas["Textures"] if t.get("FileName", "").lower().find("resource-panel") >= 0]
sub = [t for t in atlas["Textures"] if "resource" in t["RefName"].lower() or "panel" in t["RefName"].lower()]
rep.append("  entries whose RefName == TextureRef(%r) : %d" % (mat["TextureRef"], len(byref)))
rep.append("  entries whose FileName mentions 'resource-panel' : %d" % len(byname))
rep.append("  entries mentioning 'resource'/'panel' in RefName : %s" % [t["RefName"] for t in sub])
rep.append("")

# ---- 3. crop the atlas DDS and compare against the PNG --------------------
dds_path = os.path.join(WID, *atlas["UHDSource"].split("/"))
im = Image.open(dds_path); im.load(); im = im.convert("RGBA")
rep.append("atlas %s -> %s mode=%s" % (atlas["UHDSource"], im.size, "RGBA-converted"))
MW, MH = int(atlas["MaxWidth"]), int(atlas["MaxHeight"])

def uvrect(t):
    return (int(round(float(t["imageTLX"]) * MW)), int(round(float(t["imageTLY"]) * MH)),
            int(round(float(t["imageBRX"]) * MW)), int(round(float(t["imageBRY"]) * MH)))

target = (byref or sub or [None])[0]
rep.append("CHOSEN atlas entry (by TextureRef first): %s" % target)
if target:
    r = uvrect(target)
    rep.append("  UV rect -> pixel rect %s (w=%d h=%d)" % (r, r[2] - r[0], r[3] - r[1]))
    dds_crop = im.crop(r)
    dds_crop.save(os.path.join(O, "atlas_civasia_crop.png"))
    png = Image.open(os.path.join(WID, *target["FileName"].split("/"))).convert("RGBA")
    rep.append("  PNG %s %s" % (target["FileName"], png.size))
    if png.size == dds_crop.size:
        px = np.asarray(png); dx = np.asarray(dds_crop)
        m = (px[:, :, 3] > 200) & (dx[:, :, 3] > 200)
        rep.append("  PNG-vs-ATLAS on commonly-opaque px (%d): MAD=%.2f" % (
            m.sum(), np.abs(px[:, :, :3][m].astype(float) - dx[:, :, :3][m].astype(float)).mean() if m.sum() else -1))
        rep.append("  PNG  alpha>200 %.1f%%  mean RGB %.1f %.1f %.1f"
                   % (100.0 * (px[:, :, 3] > 200).mean(), px[:, :, 0].mean(), px[:, :, 1].mean(), px[:, :, 2].mean()))
        rep.append("  DDS  alpha>200 %.1f%%  mean RGB %.1f %.1f %.1f"
                   % (100.0 * (dx[:, :, 3] > 200).mean(), dx[:, :, 0].mean(), dx[:, :, 1].mean(), dx[:, :, 2].mean()))

        # side by side with the real screenshot at the verified HUD scale
        shot = Image.open(SHOT).convert("RGB")
        W, H = shot.size
        arr = np.asarray(shot, dtype=np.float64)
        sc = 0.5980
        tw, th = int(round(png.width * sc)), int(round(png.height * sc))
        tiles = []
        for tag, src in (("PNG source tree", png), ("ATLAS DDS crop", dds_crop)):
            t = src.resize((tw, th), Image.LANCZOS)
            ta = np.asarray(t, dtype=np.float64)
            cy1, cx1 = min(H, th), min(W, tw)
            tas = ta[:cy1, :cx1]
            win = arr[:cy1, :cx1]
            mk = tas[:, :, 3] > 200
            a3 = tas[:, :, :3]
            if mk.sum():
                rep.append("  %-16s scaled to %dx%d -> vs REAL on mask: MAD=%.2f corr=%+.4f px=%d"
                           % (tag, tw, th, np.abs(a3[mk] - win[mk]).mean(),
                              np.corrcoef(a3[mk].mean(axis=1), win[mk].mean(axis=1))[0, 1], mk.sum()))
            flat = Image.new("RGB", (tw, th), (95, 110, 80))
            flat.paste(t, (0, 0), t)
            tiles.append(flat)
        real = shot.crop((0, 0, tw, th)).convert("RGB")
        stack = Image.new("RGB", (tw, th * 3 + 40), (20, 20, 24))
        for i, t in enumerate([real] + tiles):
            stack.paste(t, (0, i * (th + 20)))
        d = ImageDraw.Draw(stack)
        d.text((4, 2), "REAL screenshot", fill=(255, 255, 255))
        d.text((4, th + 22), "PNG source tree", fill=(255, 255, 0))
        d.text((4, th * 2 + 42), "ATLAS DDS crop (alpha composited on olive)", fill=(0, 255, 255))
        stack.save(os.path.join(O, "cmp_png_vs_atlas.png"))
        rep.append("  wrote cmp_png_vs_atlas.png %s" % (stack.size,))

txt = "\n".join(rep)
open(os.path.join(O, "atlas_vs_png.txt"), "w", encoding="utf-8").write(txt)
print(txt)
