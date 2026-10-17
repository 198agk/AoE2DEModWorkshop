# -*- coding: utf-8 -*-
"""Is the player-list emblem art a THIRD family, or wpfg civ_emblems unpremultiplied?

Observed roster emblems (corrected band x=2656..2694, rows y=1088..1291) are
FULL-COLOUR heraldic shields (red castle field, gold coin, black/red crest,
gold eagle, blue/yellow pinwheel, silver helm, red cross shield, green/red
triangles). V1 (widgetui ingame/emblems) is tan engraved art. Chibi is anime.

Test: unpremultiply V2 (wpfg/resources/civ_emblems) and see whether it becomes
colour heraldry; compare against V1 and against the observed crops.
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
OUT = _HERE_PATH("_shots", "ui")
V1 = os.path.join(GAME, "widgetui", "textures", "ingame", "emblems")
V2 = os.path.join(GAME, "resources", "_common", "wpfg", "resources", "civ_emblems")
MOD = (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
       r"\subscribed\182654_Age of Anime (Chibi Edition)"
       r"\widgetui\textures\ingame\emblems")

CIVS = ["britons", "lithuanians", "teutons", "saracens", "vikings",
        "byzantines", "aztecs", "chinese", "poles", "bulgarians",
        "khitans", "jurchens"]

BG = (70, 60, 52)

def unpremult(im):
    a = np.asarray(im, dtype=np.float32)
    al = a[:, :, 3:4]
    with np.errstate(divide="ignore", invalid="ignore"):
        rgb = np.where(al > 0, a[:, :, :3] * 255.0 / np.maximum(al, 1e-6), 0.0)
    out = np.concatenate([np.clip(rgb, 0, 255), al], axis=2)
    return Image.fromarray(out.astype(np.uint8), "RGBA")

def load(path):
    return Image.open(path).convert("RGBA") if os.path.exists(path) else None

def onbg(im, size):
    s = im.resize(size, Image.LANCZOS)
    bg = Image.new("RGBA", size, BG + (255,))
    bg.alpha_composite(s)
    return bg.convert("RGB")

TW, TH = 200, 124
rows = []
print("%-12s %-28s %-28s" % ("civ", "V1 meanRGB/meanA", "V2-unpremult meanRGB/meanA"))
for c in CIVS:
    a = load(os.path.join(V1, c + ".png"))
    b = load(os.path.join(V2, c + ".png"))
    m = load(os.path.join(MOD, c + ".png"))
    if b is not None:
        s1 = "%s/%s" % (np.asarray(a.convert("RGB"), np.float32).reshape(-1, 3).mean(0).round(1) if a else "-",
                        round(float(np.asarray(a)[:, :, 3].mean()), 1) if a else "-")
        bu = unpremult(b)
        raw = np.asarray(b.convert("RGB"), np.float32).reshape(-1, 3).mean(0).round(1)
        s2 = "%s -> %s" % (raw, np.asarray(bu.convert("RGB"), np.float32).reshape(-1, 3).mean(0).round(1))
        print("%-12s %-28s %-28s" % (c, s1, s2))
    tiles = []
    tiles.append(onbg(a, (TW, TH)) if a else Image.new("RGB", (TW, TH), (25, 25, 25)))
    tiles.append(onbg(unpremult(b), (TW, TH)) if b else Image.new("RGB", (TW, TH), (25, 25, 25)))
    tiles.append(onbg(m, (TW, TH)) if m else Image.new("RGB", (TW, TH), (25, 25, 25)))
    rows.append((c, tiles))

W = TW * 3
H = (TH + 16) * len(rows)
sh = Image.new("RGB", (W, H), (12, 12, 12))
d = ImageDraw.Draw(sh)
hdrs = ["V1 widgetui/emblems", "V2 wpfg/civ_emblems UNPREMULT", "MOD chibi"]
for i, (c, tiles) in enumerate(rows):
    y = i * (TH + 16)
    d.text((4, y + 3), "%s   |   %s   |   %s" % (c, hdrs[1], hdrs[2]), fill=(255, 255, 0))
    for j, t in enumerate(tiles):
        sh.paste(t, (j * TW, y + 16))
sh.save(os.path.join(OUT, "family_sheet.png"))
print()
print("wrote family_sheet.png", sh.size)
