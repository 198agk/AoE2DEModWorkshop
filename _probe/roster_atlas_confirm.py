# -*- coding: utf-8 -*-
"""CONFIRM: roster emblem = material "<Civ>Icon" -> atlas defaultwidgets ->
textures/menu/civs/<civ>.png. Decode the SHIPPED atlas slice and compare it to
(a) the roster crop from the screenshot and (b) the loose V3 png.

This closes the loop: it proves the shipped atlas is the pixel source, and that
the loose V3 png is the build input (i.e. the override target).
"""
import os
import json
import numpy as np
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\ui"
WJ = os.path.join(GAME, "widgetui")

m = json.load(open(os.path.join(WJ, "materials.json"), encoding="utf-8-sig"))
mats = {x["MaterialDef"]["Name"]: x["MaterialDef"] for x in m["Materials"]}
atlas = {a["AtlasDef"]["Name"]: a["AtlasDef"] for a in m["AtlasTextures"]}

F1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
shot = Image.open(F1).convert("RGB")

ROWY = [1088, 1117, 1146, 1175, 1204, 1233, 1262, 1291]
X0, X1 = 2654, 2696
H2 = 16

# player civs, in the roster's own order (from the screenshot labels)
# 1 RemonBo 立陶宛 Lithuanians, 8 明康 ?, 7 孙权 ?, 6 马约里安 ?,
# 5 英格瓦尔·维德福利 ?, 3 艾伊帕 ?, 2 多明尼各·塞沃 ?, 4 卡贝洛·德·韦尔哈 ?
# Only row1's civ is known for sure (label shows 立陶宛).
PROBE = ["Lithuanians"]

ad = atlas["defaultwidgets"]
src = ad.get("DefaultSource") or ad.get("HDSource") or ad.get("UHDSource")
ap = os.path.join(GAME, "widgetui", src.replace("/", os.sep))
aimg = Image.open(ap).convert("RGBA")
Wd, Ht = aimg.size
print("defaultwidgets atlas (%s) = %s  %s" % (src, aimg.size, aimg.mode))

print()
print("%-18s %-24s %-30s %s" % ("material", "atlas slice box", "MAD(slice,roster)",
                                "MAD(V3png,roster)"))
for civ in PROBE:
    name = civ + "Icon"
    md = mats[name]
    tr = md.get("TextureRef") or name
    ent = next(t for t in ad["Textures"] if t["RefName"] == tr)
    u0, v0, u1, v1 = (float(ent["imageTLX"]), float(ent["imageTLY"]),
                      float(ent["imageBRX"]), float(ent["imageBRY"]))
    box = (int(round(u0 * Wd)), int(round(v0 * Ht)),
           int(round(u1 * Wd)), int(round(v1 * Ht)))
    sl = aimg.crop(box)
    roster = shot.crop((X0, ROWY[0] - H2, X1, ROWY[0] + H2)).convert("RGBA")
    ow, oh = roster.size
    slr = sl.resize((ow, oh), Image.LANCZOS)
    p3 = os.path.join(WJ, ent["FileName"].replace("/", os.sep))
    v3r = Image.open(p3).convert("RGBA").resize((ow, oh), Image.LANCZOS)

    def mad(a, b):
        aa, bb = np.asarray(a, np.float32), np.asarray(b, np.float32)
        m_ = (aa[:, :, 3] > 40) | (bb[:, :, 3] > 40)
        if m_.sum() == 0:
            return -1
        return float(np.abs(aa[:, :, :3][m_] - bb[:, :, :3][m_]).mean())

    # roster is blended over terrain, so also compare after alpha-ignoring mean removal
    def ncc(a, b):
        aa = np.asarray(a, np.float32)[:, :, :3].mean(2)
        bb = np.asarray(b, np.float32)[:, :, :3].mean(2)
        aa = aa - aa.mean()
        bb = bb - bb.mean()
        d = np.sqrt((aa * aa).sum() * (bb * bb).sum())
        return float((aa * bb).sum() / d) if d else 0.0

    print("%-18s %-24s MAD %6.2f  ncc %+0.3f      MAD %6.2f  ncc %+0.3f"
          % (name, str(box), mad(slr, roster), ncc(slr, roster),
             mad(v3r, roster), ncc(v3r, roster)))

    # figure
    tiles = [("ROSTER row1 observed", roster), ("atlas slice %s" % name, slr),
             ("loose V3 %s" % ent["FileName"].split("/")[-1], v3r)]
    Z = 8
    sh = Image.new("RGB", (ow * Z * 3, oh * Z + 20), (12, 12, 12))
    d = ImageDraw.Draw(sh)
    for i, (t, im) in enumerate(tiles):
        aa = np.asarray(im.convert("RGBA"), np.float32)
        bg = Image.new("RGBA", (ow, oh), (70, 60, 52, 255))
        bg.alpha_composite(im.convert("RGBA") if im.mode != "RGBA" else im)
        sh.paste(bg.convert("RGB").resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 20))
        d.text((i * ow * Z + 4, 4), t, fill=(255, 255, 0))
    sh.save(os.path.join(OUT, "roster_atlas_confirm.png"))
    print("   wrote roster_atlas_confirm.png", sh.size)
