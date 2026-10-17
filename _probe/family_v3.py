# -*- coding: utf-8 -*-
"""The third emblem family: widgetui/textures/menu/civs.
Render it next to V1 and V2 for the same civs, and measure colour content.
Also crop row-8 (green/red triangles shield) and row-1 (red castle) of the
player list to compare directly.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import numpy as np
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = _HERE_PATH("_shots", "ui")
V1 = os.path.join(GAME, "widgetui", "textures", "ingame", "emblems")
V2 = os.path.join(GAME, "resources", "_common", "wpfg", "resources", "civ_emblems")
V3 = os.path.join(GAME, "widgetui", "textures", "menu", "civs")

CIVS = ["britons", "lithuanians", "teutons", "saracens", "vikings",
        "byzantines", "aztecs", "chinese", "poles", "bulgarians",
        "khitans", "jurchens", "berbers", "franks", "goths", "celts"]

BG = (70, 60, 52)

def load(p):
    return Image.open(p).convert("RGBA") if os.path.exists(p) else None

def onbg(im, size):
    s = im.resize(size, Image.LANCZOS)
    bg = Image.new("RGBA", size, BG + (255,))
    bg.alpha_composite(s)
    return bg.convert("RGB")

def sat_of(im):
    a = np.asarray(im, np.float32)
    m = a[:, :, 3] > 60
    if m.sum() < 50:
        return 0.0, 0
    rgb = a[:, :, :3][m]
    return float((rgb.max(1) - rgb.min(1)).mean()), int(m.sum())

print("%-12s %-16s %-16s %-16s" % ("civ", "V1 ingame/emblems", "V2 wpfg", "V3 menu/civs"))
for c in CIVS:
    out = []
    for d in (V1, V2, V3):
        p = os.path.join(d, c + ".png")
        if not os.path.exists(p) and c == "berbers":
            p = os.path.join(d, "berber.png")
        im = load(p)
        out.append("-" if im is None else "sat %.1f n%d" % sat_of(im))
    print("%-12s %-16s %-16s %-16s" % (c, out[0], out[1], out[2]))

TW, TH = 190, 118
rows = []
for c in CIVS:
    tiles = []
    for d in (V1, V2, V3):
        p = os.path.join(d, c + ".png")
        if not os.path.exists(p) and c == "berbers":
            p = os.path.join(d, "berber.png")
        im = load(p)
        tiles.append(onbg(im, (TW, TH)) if im else Image.new("RGB", (TW, TH), (25, 25, 25)))
    rows.append((c, tiles))

sh = Image.new("RGB", (TW * 3, (TH + 16) * len(rows)), (12, 12, 12))
d = ImageDraw.Draw(sh)
for i, (c, tiles) in enumerate(rows):
    y = i * (TH + 16)
    d.text((4, y + 3), "%s   [V1 ingame/emblems]   [V2 wpfg/civ_emblems]   [V3 menu/civs]" % c,
           fill=(255, 255, 0))
    for j, t in enumerate(tiles):
        sh.paste(t, (j * TW, y + 16))
sh.save(os.path.join(OUT, "family_v3.png"))
print()
print("wrote family_v3.png", sh.size)

# ---- and the observed roster emblem crops, same civs, for direct eyes ----
F1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
im = Image.open(F1).convert("RGB")
# rows detected in the corrected band
ROWY = [1088, 1117, 1146, 1175, 1204, 1233, 1262, 1291]
X0, X1 = 2656, 2694
H2 = 15
obs = [im.crop((X0 - 2, y - H2, X1 + 2, y + H2)) for y in ROWY]
ow, oh = obs[0].size
Z = 5
sh2 = Image.new("RGB", (ow * Z * len(obs), oh * Z + 18), (12, 12, 12))
d = ImageDraw.Draw(sh2)
for i, o in enumerate(obs):
    sh2.paste(o.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 18))
    d.text((i * ow * Z + 3, 3), "row%d y%d" % (i + 1, ROWY[i]), fill=(255, 255, 0))
sh2.save(os.path.join(OUT, "plist_obs_rows.png"))
print("wrote plist_obs_rows.png", sh2.size)
