# -*- coding: utf-8 -*-
"""FINAL confirmation + summary figure.

Row 1 owner = RemonBo, label reads (立陶宛) = Lithuanians.
Observed roster emblem = red shield with GOLD GEDIMINAS COLUMNS.
V3 lithuanians.png = red shield with gold Gediminas columns.
V3 britons.png     = red shield with three gold LIONS (the NCC's false winner).

So: put observed row1 next to both, at big magnification, plus V1 (chibi target)
for completeness. Then build the three-family summary sheet.
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

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = _HERE_PATH("_shots", "ui")
WJ = os.path.join(GAME, "widgetui")
V1 = os.path.join(WJ, "textures", "ingame", "emblems")
V2 = os.path.join(GAME, "resources", "_common", "wpfg", "resources", "civ_emblems")
V3 = os.path.join(WJ, "textures", "menu", "civs")
MOD = (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
       r"\subscribed\182654_Age of Anime (Chibi Edition)"
       r"\widgetui\textures\ingame\emblems")

F1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
shot = Image.open(F1).convert("RGBA")

def onbg(p, size=None, bg=(70, 60, 52)):
    im = Image.open(p).convert("RGBA")
    if size:
        im = im.resize(size, Image.LANCZOS)
    b = Image.new("RGBA", im.size, bg + (255,))
    b.alpha_composite(im)
    return b.convert("RGB")

# ---------- figure A: roster row1 vs candidates ----------
row = shot.crop((2648, 1070, 2704, 1106))  # generous, centred on row 1
ow, oh = row.size
b = Image.new("RGBA", (ow, oh), (70, 60, 52, 255))
b.alpha_composite(row)
rowc = b.convert("RGB")

tiles = [("OBSERVED roster row1\n(RemonBo = Lithuanians)", rowc),
         ("V3 menu/civs\nlithuanians.png", onbg(os.path.join(V3, "lithuanians.png"), (ow, oh))),
         ("V3 menu/civs\nbritons.png  (NCC's pick)", onbg(os.path.join(V3, "britons.png"), (ow, oh))),
         ("V1 ingame/emblems\nlithuanians.png", onbg(os.path.join(V1, "lithuanians.png"), (ow, oh))),
         ("MOD chibi\nlithuanians.png", onbg(os.path.join(MOD, "lithuanians.png"), (ow, oh)))]
Z = 10
sh = Image.new("RGB", (ow * Z * len(tiles), oh * Z + 34), (10, 10, 10))
d = ImageDraw.Draw(sh)
for i, (t, im) in enumerate(tiles):
    sh.paste(im.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 34))
    for j, line in enumerate(t.split("\n")):
        d.text((i * ow * Z + 5, 4 + j * 13), line, fill=(255, 255, 0))
sh.save(os.path.join(OUT, "roster_row1_COMPARE.png"))
print("wrote roster_row1_COMPARE.png", sh.size)

# ---------- figure B: the three emblem families + where each is used ----------
CIVS = ["britons", "lithuanians", "teutons", "franks", "vikings", "chinese",
        "aztecs", "poles", "berbers", "celts"]
BG = (62, 54, 47)

def g(d, c):
    p = os.path.join(d, c + ".png")
    if not os.path.exists(p) and c == "berbers":
        p = os.path.join(d, "berber.png")
    return p

TW, TH = 168, 105
cols = [
    ("V1  widgetui/textures/ingame/emblems\n-> atlas ingamepanels -> material CivEmblem<Civ>\n-> BOTTOM COMMAND PANEL  (chibi mod target)",
     V1, True),
    ("V2  wpfg/resources/civ_emblems\n-> icons.json CivEmblem/InGameCivEmblem values\n-> WPF menu layer (grey/graphic variant)",
     V2, False),
    ("V3  widgetui/textures/menu/civs\n-> atlas defaultwidgets -> material <Civ>Icon\n-> IN-GAME PLAYER ROSTER / TECH TREE  (vanilla in shot)",
     V3, False),
]
sh2 = Image.new("RGB", (TW * 3 + 24, (TH + 22) * len(CIVS) + 58), (10, 10, 10))
d2 = ImageDraw.Draw(sh2)
for i, (title, _, _) in enumerate(cols):
    for j, line in enumerate(title.split("\n")):
        d2.text((i * (TW + 8) + 6, 4 + j * 13), line, fill=(120, 220, 255) if j == 3 else (230, 230, 230))
for r, c in enumerate(CIVS):
    y = 58 + r * (TH + 22)
    d2.text((6, y + 3), c, fill=(255, 220, 0))
    for i, (title, folder, is_mod) in enumerate(cols):
        p = g(folder, c)
        if os.path.exists(p):
            img = onbg(p, (TW, TH), BG)
        else:
            img = Image.new("RGB", (TW, TH), (35, 35, 35))
        sh2.paste(img, (i * (TW + 8) + 4, y + 18))
sh2.save(os.path.join(OUT, "emblem_families_FINAL.png"))
print("wrote emblem_families_FINAL.png", sh2.size)

# ---------- numeric: prove V1 != V3 != V2 for the same civ ----------
print()
print("%-12s %-34s %-34s %-34s" % ("civ", "V1 meanRGB", "V2 meanRGB", "V3 meanRGB"))
for c in CIVS[:6]:
    out = []
    for folder in (V1, V2, V3):
        p = g(folder, c)
        if not os.path.exists(p):
            out.append("-")
            continue
        a = np.asarray(Image.open(p).convert("RGB"), np.float32).reshape(-1, 3).mean(0)
        out.append("[%5.1f %5.1f %5.1f]" % tuple(a))
    print("%-12s %-34s %-34s %-34s" % (c, out[0], out[1], out[2]))

# ---------- check: does ANY installed mod provide menu/civs or defaultwidgets override? ----------
MODROOT = r"C:\Users\26913\Games\Age of Empires 2 DE"
print()
print("=== mods providing either emblem family ===")
for base, subs, files in os.walk(os.path.join(MODROOT, "76561198406248391", "mods")):
    rel = base.replace(MODROOT, "")
    if rel.count(os.sep) > 5:
        subs[:] = []
        continue
    if any(k in base.lower() for k in ("emblems", "civs")) or "atlas" in base.lower():
        pngs = [f for f in files if f.lower().endswith((".png", ".dds"))]
        if pngs:
            print("   %-78s n=%d" % (rel[:78], len(pngs)))
