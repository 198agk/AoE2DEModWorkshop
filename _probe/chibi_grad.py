# -*- coding: utf-8 -*-
"""Gradient-based match (immune to the smooth terrain blend term).

obs = a*A + (1-a)*T.  T is smooth/low-frequency terrain, A is line art.
=> gradients of obs are dominated by a*grad(A). So NCC on gradient magnitude
identifies the source art without needing to know a or T.

Player label reads "RemonBo (立陶宛)" = Lithuanians -> check lithuanians.png
explicitly as well as the full ranked list.
"""
import os
import numpy as np
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\ui"
MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\182654_Age of Anime (Chibi Edition)\widgetui\textures\ingame\emblems"
V1 = os.path.join(GAME, "widgetui", "textures", "ingame", "emblems")
V2 = os.path.join(GAME, "resources", "_common", "wpfg", "resources", "civ_emblems")
BOX = (541, 1307, 861, 1506)

f1 = Image.open(os.path.join(SHOTS, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")).convert("RGB")
obs = np.asarray(f1.crop(BOX), dtype=np.float32)
oh, ow = obs.shape[:2]


def lum(a):
    return 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]


def grad_mag(l):
    gy, gx = np.gradient(l)
    return np.sqrt(gx * gx + gy * gy)


ob_l = lum(obs)
ob_g = grad_mag(ob_l)


def ncc(x, y, m):
    n = int(m.sum())
    if n < 200:
        return float("nan"), 0
    a = x[m].astype(np.float64)
    b = y[m].astype(np.float64)
    a -= a.mean()
    b -= b.mean()
    den = np.sqrt((a * a).sum() * (b * b).sum())
    if den == 0:
        return float("nan"), n
    return float((a * b).sum() / den), n


def run(folder, label):
    res = []
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".png"):
            continue
        try:
            im = Image.open(os.path.join(folder, fn)).convert("RGBA")
        except Exception:
            continue
        sa = np.asarray(im.resize((ow, oh), Image.LANCZOS), dtype=np.float32)
        m = sa[:, :, 3] > 60                       # art mask
        m_er = m.copy()
        # erode by 2 to avoid boundary artefacts
        for _ in range(2):
            m_er = (m_er & np.roll(m_er, 1, 0) & np.roll(m_er, -1, 0)
                    & np.roll(m_er, 1, 1) & np.roll(m_er, -1, 1))
        r, n = ncc(ob_g, grad_mag(lum(sa)), m_er)
        if n:
            res.append((r, fn, n))
    res.sort(reverse=True)
    print()
    print("=== %s : gradient-NCC, top 10 ===" % label)
    for r, fn, n in res[:10]:
        print("     r=%+0.4f  %-24s maskpx=%d" % (r, fn, n))
    if len(res) > 10:
        print("     ... min r=%+0.4f (%s)" % (res[-1][0], res[-1][1]))
    return res


rm = run(MOD, "MOD chibi emblems 182654")
r1 = run(V1, "VANILLA V1 widgetui emblems")
r2 = run(V2, "VANILLA V2 wpfg civ_emblems")

for nm, res in (("MOD", rm), ("V1", r1), ("V2", r2)):
    hit = [r for r, fn, _ in res if fn == "lithuanians.png"]
    print("%s lithuanians.png rank=%s r=%s" % (
        nm, next((i + 1 for i, (_, fn, _) in enumerate(res) if fn == "lithuanians.png"), None),
        ("%+0.4f" % hit[0]) if hit else "n/a"))

print()
print("=== verdict ===")
print("MOD best  %+0.4f  %s" % (rm[0][0], rm[0][1]))
print("V1  best  %+0.4f  %s" % (r1[0][0], r1[0][1]))
print("V2  best  %+0.4f  %s" % (r2[0][0], r2[0][1]))

# side-by-side: observed box vs the named candidates, at the same scale
names = ["lithuanians.png", "malay.png", "saracens.png"]
tiles = [("OBSERVED(blended)", Image.fromarray(obs.astype(np.uint8)))]
for nm in names:
    for folder, tag in ((MOD, "MOD"), (V1, "V1")):
        p = os.path.join(folder, nm)
        if os.path.exists(p):
            im = Image.open(p).convert("RGBA")
            bg = Image.new("RGBA", im.size, (146, 120, 102, 255))
            bg.alpha_composite(im)
            tiles.append(("%s %s" % (tag, nm), bg.convert("RGB").resize((ow, oh), Image.LANCZOS)))
            break
Z = 2
sheet = Image.new("RGB", (ow * Z * len(tiles), oh * Z + 22), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for i, (t, im) in enumerate(tiles):
    sheet.paste(im.resize((ow * Z, oh * Z), Image.LANCZOS), (i * ow * Z, 22))
    d.text((i * ow * Z + 6, 5), t, fill=(255, 255, 0))
sheet.save(os.path.join(OUT, "chibi_vs_candidates.png"))
print("wrote chibi_vs_candidates.png", sheet.size)
