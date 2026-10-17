# -*- coding: utf-8 -*-
"""FINAL resolution: the two emblems are DIFFERENT asset families.

Established:
  * Bottom command panel  -> commandpanel.json widget /BackgroundRight/CivEmblem,
    Material "CivEmblem" (no exact material by that name exists; materials.json
    has "CivEmblem<Civ>" with no separator -> the engine substitutes the civ name).
    Its atlas entry points at textures/ingame/emblems/lithuanians.png.
    The chibi mod replaces that file -> AND IT DID TAKE EFFECT (visual proof:
    chibi_vs_candidates.png shows the observed box == MOD lithuanians.png).
  * Top-right player list -> icons.json section InGameCivEmblem, whose values
    ("ingame_civ_emblems_<civ>") resolve to wpfg/resources/civ_emblems/<civ>.png.

So both must be checked against the SAME civ separately. Here: crop the player-list
emblem of row 1 (RemonBo, Lithuanians) and score it against all three candidate
sets, to show which family the PLAYER LIST uses.
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
MODDIR = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\182654_Age of Anime (Chibi Edition)\widgetui\textures\ingame\emblems"
V1 = os.path.join(GAME, "widgetui", "textures", "ingame", "emblems")
V2 = os.path.join(GAME, "resources", "_common", "wpfg", "resources", "civ_emblems")

F1 = os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
im = Image.open(F1).convert("RGB")

# player list block in the 2730x1535 screenshot: 7 rows visible, tight column of emblems
# from the earlier crop (2280,1010,2700,1500) at 3x the emblems sat around x 2500-2680
ROWS = [
    ("RemonBo",  (2555, 1020, 2645, 1082)),
    ("mingkang", (2555, 1073, 2645, 1135)),
    ("sunquan",  (2555, 1126, 2645, 1188)),
    ("majurian", (2555, 1179, 2645, 1241)),
    ("ingvar",   (2555, 1232, 2645, 1294)),
    ("eipa",     (2555, 1285, 2645, 1347)),
    ("dominik",  (2555, 1338, 2645, 1400)),
    ("cabelo",   (2555, 1391, 2645, 1453)),
]

def lum(a):
    return 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]

def best(crop_rgb, folder, want=None):
    ow, oh = crop_rgb.width, crop_rgb.height
    obs = np.asarray(crop_rgb, dtype=np.float32)
    ob_l = lum(obs)
    res = []
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".png"):
            continue
        try:
            s = np.asarray(Image.open(os.path.join(folder, fn)).convert("RGBA").resize((ow, oh), Image.LANCZOS), dtype=np.float32)
        except Exception:
            continue
        m = s[:, :, 3] > 60
        n = int(m.sum())
        if n < 100:
            continue
        a = ob_l[m] - ob_l[m].mean()
        b = lum(s)[m] - lum(s)[m].mean()
        den = np.sqrt((a * a).sum() * (b * b).sum())
        if den:
            res.append((float((a * b).sum() / den), fn))
    res.sort(reverse=True)
    top = res[:3]
    target = None
    if want:
        for r, fn in res:
            if fn == want:
                target = (r, res.index((r, fn)) + 1)
                break
    return top, target

print("=== TOP-RIGHT PLAYER LIST emblems: which family? ===")
sheet_tiles = []
for label, box in ROWS:
    c = im.crop(box)
    tm, _ = best(c, MODDIR)
    t1, _ = best(c, V1)
    t2, t2t = best(c, V2)
    print()
    print("  %-9s box=%s" % (label, box))
    print("     MOD best: %+0.4f %-22s | V1 best: %+0.4f %-22s | V2 best: %+0.4f %s"
          % (tm[0][0], tm[0][1], t1[0][0], t1[0][1], t2[0][0], t2[0][1]))
    sheet_tiles.append((label, c))
    if t2[0][0] > max(tm[0][0], t1[0][0]):
        print("     -> V2 (wpfg) wins")

print()
print("=== side-by-side: player-list row1 vs the three families' lithuanians ===")
obs1 = im.crop(ROWS[0][1])
ow, oh = obs1.size
tiles = [("PLAYERLIST row1 (observed)", obs1)]
for folder, tag in ((MODDIR, "MOD"), (V1, "V1"), (V2, "V2")):
    p = os.path.join(folder, "lithuanians.png")
    if os.path.exists(p):
        s = Image.open(p).convert("RGBA")
        bgs = Image.new("RGBA", s.size, (60, 55, 50, 255))
        bgs.alpha_composite(s)
        tiles.append(("%s lithuanians.png" % tag, bgs.convert("RGB").resize((ow, oh), Image.LANCZOS)))
Z = 3
sh = Image.new("RGB", (ow * Z * len(tiles), oh * Z + 20), (15, 15, 15))
d = ImageDraw.Draw(sh)
for i, (t, img) in enumerate(tiles):
    sh.paste(img.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 20))
    d.text((i * ow * Z + 4, 4), t, fill=(255, 255, 0))
sh.save(os.path.join(OUT, "playerlist_vs_families.png"))
print("wrote playerlist_vs_families.png", sh.size)

# and the same for the bottom command panel box, for a symmetric record
print()
print("=== side-by-side: BOTTOM command panel vs the three families' lithuanians ===")
obsb = im.crop((541, 1307, 861, 1506))
ow, oh = obsb.size
tiles = [("BOTTOM cmdpanel (observed)", obsb)]
for folder, tag in ((MODDIR, "MOD"), (V1, "V1"), (V2, "V2")):
    p = os.path.join(folder, "lithuanians.png")
    if os.path.exists(p):
        s = Image.open(p).convert("RGBA")
        bgs = Image.new("RGBA", s.size, (146, 120, 102, 255))
        bgs.alpha_composite(s)
        tiles.append(("%s lithuanians.png" % tag, bgs.convert("RGB").resize((ow, oh), Image.LANCZOS)))
Z = 2
sh = Image.new("RGB", (ow * Z * len(tiles), oh * Z + 20), (15, 15, 15))
d = ImageDraw.Draw(sh)
for i, (t, img) in enumerate(tiles):
    sh.paste(img.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 20))
    d.text((i * ow * Z + 4, 4), t, fill=(255, 255, 0))
sh.save(os.path.join(OUT, "bottom_vs_families.png"))
print("wrote bottom_vs_families.png", sh.size)
