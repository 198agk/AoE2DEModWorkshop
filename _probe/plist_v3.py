# -*- coding: utf-8 -*-
"""DECISIVE: is the player-list roster emblem = V3 (widgetui/textures/menu/civs)?

Row 1 owner is RemonBo, civ 立陶宛 = Lithuanians. V3 lithuanians.png is a red
shield with gold Gediminas columns; the roster row-1 emblem looked exactly like
that. Confirm with (a) side-by-side, (b) masked NCC against V1/V2/V3, and
(c) confirm the roster shows the SAME art as the game's own menu civic shield.
"""
import os
import numpy as np
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\ui"
FAMS = {
    "V1 ingame/emblems": os.path.join(GAME, "widgetui", "textures", "ingame", "emblems"),
    "V2 wpfg/civ_emblems": os.path.join(GAME, "resources", "_common", "wpfg", "resources", "civ_emblems"),
    "V3 menu/civs": os.path.join(GAME, "widgetui", "textures", "menu", "civs"),
}
BG = (70, 60, 52)
F1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
im = Image.open(F1).convert("RGB")

X0, X1 = 2654, 2696
ROWY = [1088, 1117, 1146, 1175, 1204, 1233, 1262, 1291]
H2 = 16


def lum(x):
    return 0.299 * x[:, :, 0] + 0.587 * x[:, :, 1] + 0.114 * x[:, :, 2]


def ranked(crop, folder):
    ow, oh = crop.size
    ol = lum(np.asarray(crop, np.float32))
    out = []
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".png"):
            continue
        try:
            s = np.asarray(Image.open(os.path.join(folder, fn)).convert("RGBA")
                           .resize((ow, oh), Image.LANCZOS), np.float32)
        except Exception:
            continue
        m = s[:, :, 3] > 90
        if m.sum() < 80:
            continue
        A_ = ol[m] - ol[m].mean()
        B_ = lum(s)[m] - lum(s)[m].mean()
        den = np.sqrt((A_ * A_).sum() * (B_ * B_).sum())
        if den:
            out.append((float((A_ * B_).sum() / den), fn))
    out.sort(reverse=True)
    return out


print("=== masked NCC per row, best of each family ===")
for i, y in enumerate(ROWY):
    cr = im.crop((X0, y - H2, X1, y + H2))
    line = "  row%d y=%d " % (i + 1, y)
    tw = []
    for tag, d in FAMS.items():
        r = ranked(cr, d)[:1]
        line += "| %-8s %+0.3f %-14s " % (tag.split()[0], r[0][0], r[0][1])
        tw.append((r[0][0], tag.split()[0], r[0][1]))
    w = max(tw)
    print(line + "-> %s" % w[1])

# ---- figure: row1 observed vs V3/V1/V2 lithuanians ----
cr = im.crop((X0, ROWY[0] - H2, X1, ROWY[0] + H2))
ow, oh = cr.size
tiles = [("OBSERVED row1", cr)]
for tag, d in FAMS.items():
    p = os.path.join(d, "lithuanians.png")
    if os.path.exists(p):
        s = Image.open(p).convert("RGBA").resize((ow, oh), Image.LANCZOS)
        bg = Image.new("RGBA", (ow, oh), BG + (255,))
        bg.alpha_composite(s)
        tiles.append((tag, bg.convert("RGB")))
Z = 8
sh = Image.new("RGB", (ow * Z * len(tiles), oh * Z + 20), (12, 12, 12))
d = ImageDraw.Draw(sh)
for i, (t, mg) in enumerate(tiles):
    sh.paste(mg.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 20))
    d.text((i * ow * Z + 4, 4), "%s (lithuanians.png)" % t, fill=(255, 255, 0))
sh.save(os.path.join(OUT, "plist_row1_DECIDE.png"))
print()
print("wrote plist_row1_DECIDE.png", sh.size)
