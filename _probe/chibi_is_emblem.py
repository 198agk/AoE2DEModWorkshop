# -*- coding: utf-8 -*-
"""DECISIVE: is the floating chibi the mod's CivEmblem, drawn by the command panel?

Established facts:
  * commandpanel.json widget "BackgroundRight/CivEmblem" (Type Base, Material
    "CivEmblem", 450x280) computes to ref (761..1211, 1839..2119)
    -> screenshot (541..861, 1307..1506).
  * In EVERY frame a chibi girl appears in exactly that box.
  * Measured camera shift between frames is up to (224,99) yet the chibi's red
    centroid moves <10 px -> the chibi is SCREEN-anchored (a UI widget).

Test: NCC of each mod emblem PNG (450x280, per-civ) against that box, with the
alpha mask of the PNG. The correct civ should match far better than the rest, and
far better than the vanilla V1/V2 emblems.
"""
import os
import numpy as np
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\ui"
os.makedirs(OUT, exist_ok=True)

MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\182654_Age of Anime (Chibi Edition)\widgetui\textures\ingame\emblems"
V1 = os.path.join(GAME, "widgetui", "textures", "ingame", "emblems")
V2 = os.path.join(GAME, "resources", "_common", "wpfg", "resources", "civ_emblems")

BOX = (541, 1307, 861, 1506)   # exact
f1 = Image.open(os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")).convert("RGB")
obs = np.asarray(f1.crop(BOX), dtype=np.float32)
oh, ow = obs.shape[:2]
print("observed box %dx%d  meanRGB=(%.1f,%.1f,%.1f)" % (ow, oh, obs[:, :, 0].mean(), obs[:, :, 1].mean(), obs[:, :, 2].mean()))


def lum(a):
    return 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]


def ncc_masked(x, y, m):
    """Normalised cross-correlation of x and y over mask m (fractional)."""
    n = m.sum()
    if n < 50:
        return float("nan"), 0
    xm = x[m].astype(np.float64)
    ym = y[m].astype(np.float64)
    xm = xm - xm.mean()
    ym = ym - ym.mean()
    den = np.sqrt((xm * xm).sum() * (ym * ym).sum())
    if den == 0:
        return float("nan"), int(n)
    return float((xm * ym).sum() / den), int(n)


def run(folder, label, limit=None):
    res = []
    files = sorted(os.listdir(folder))
    for fn in files:
        if not fn.lower().endswith(".png"):
            continue
        p = os.path.join(folder, fn)
        try:
            im = Image.open(p).convert("RGBA")
        except Exception as e:
            print("  skip %s (%s)" % (fn, e))
            continue
        src = im.resize((ow, oh), Image.LANCZOS)
        sa = np.asarray(src, dtype=np.float32)
        s_l = lum(sa)
        s_a = sa[:, :, 3]
        # mask: where the source art is actually present
        m = s_a > 40
        r, n = ncc_masked(lum(obs), s_l, m)
        if n:
            res.append((r, fn, n))
    res.sort(reverse=True)
    print()
    print("=== %s : top 8 by masked NCC ===" % label)
    for r, fn, n in res[:8]:
        print("   r=%+0.4f  %-24s maskpx=%d" % (r, fn, n))
    if len(res) > 8:
        print("   ... worst: r=%+0.4f  %s" % (res[-1][0], res[-1][1]))
    return res


rm = run(MOD, "MOD chibi emblems (182654) widgetui/textures/ingame/emblems")
r1 = run(V1, "VANILLA V1 widgetui/textures/ingame/emblems")
r2 = run(V2, "VANILLA V2 wpfg/resources/civ_emblems")

print()
print("=== verdict ===")
print("best MOD r = %+0.4f (%s)" % (rm[0][0], rm[0][1]))
print("best V1  r = %+0.4f (%s)" % (r1[0][0], r1[0][1]))
print("best V2  r = %+0.4f (%s)" % (r2[0][0], r2[0][1]))
