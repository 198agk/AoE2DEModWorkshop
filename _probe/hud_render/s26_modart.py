# -*- coding: utf-8 -*-
"""Inspect the 透明主题 mod's replacement panel art, and re-score correctly.

The mod '透明主题整合自用' (priority 2) ships
  widgetui/textures/ingame/panels/{AFRI,ANDE,ASIA,...}/resource-panel.png + topbar.png
which by the loose-PNG-overrides-atlas rule REPLACE the shipped atlas art.
All scored "too few px", i.e. nearly transparent -> consistent with a
'transparent theme' mod, but then the bright tan wood in the screenshot must
come from somewhere else. Find out what.
"""
import os
import numpy as np
from PIL import Image

O = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WID = os.path.join(GAME, "widgetui")
MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\550412_透明主题整合自用"
AT = r"C:\Users\26913\.dsh\attachments\v1\objects"
SHOTS = [os.path.join(AT, d, s) for d, s in [
    ("02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    ("2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    ("16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    ("8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    ("89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
]]
SC = 0.5980
rep = []


def stats(p, label):
    im = Image.open(p)
    im.load()
    a = np.asarray(im.convert("RGBA"), dtype=np.uint8)
    al = a[:, :, 3]
    rep.append("  %-58s %s mode=%s" % (label[:58], im.size, im.mode))
    if im.size[0] * im.size[1] > 0:
        rep.append("      alpha: mean=%.1f  ==0:%.1f%%  >200:%.1f%%  min=%d max=%d"
                   % (al.mean(), 100.0 * (al == 0).mean(), 100.0 * (al > 200).mean(), al.min(), al.max()))
        op = al > 200
        if op.sum():
            rep.append("      RGB over alpha>200: %.1f %.1f %.1f"
                       % tuple(a[:, :, i][op].mean() for i in range(3)))
    return im


rep.append("=== MOD panel art (透明主题整合自用) ===")
for civ in ("ASIA", "WEST", "AFRI"):
    for nm in ("resource-panel.png", "topbar.png"):
        p = os.path.join(MOD, "widgetui", "textures", "ingame", "panels", civ, nm)
        if os.path.exists(p):
            stats(p, "%s/%s" % (civ, nm))
rep.append("")
rep.append("=== VANILLA twins for comparison ===")
for civ in ("ASIA",):
    for nm in ("resource-panel.png", "topbar.png"):
        p = os.path.join(WID, "textures", "ingame", "panels", civ, nm)
        if os.path.exists(p):
            stats(p, "VANILLA %s/%s" % (civ, nm))
rep.append("")
rep.append("=== mod ships resource-panel_full.png too ===")
stats(os.path.join(MOD, "widgetui", "textures", "ingame", "panels", "resource-panel_full.png"), "resource-panel_full.png")
rep.append("")

# how many of the mod's widgetui pngs are named exactly like a vanilla atlas FileName?
rep.append("=== full mod widgetui inventory by subtree ===")
mw = os.path.join(MOD, "widgetui")
from collections import Counter
c = Counter()
n = 0
for dp, dn, fns in os.walk(mw):
    for f in fns:
        n += 1
        c[os.path.relpath(dp, mw)] += 1
rep.append("  total %d files in mod widgetui" % n)
for k, v in c.most_common(30):
    rep.append("    %-60s %d" % (k, v))
rep.append("")

st = np.stack([np.asarray(Image.open(p).convert("RGB").crop((0, 0, 1100, 200)), dtype=np.float64) for p in SHOTS])
rm = st.mean(axis=0)
rstd = st.std(axis=0).mean(axis=2)
op = rstd < 4.0
rep.append("real 5-shot mean; provably-opaque %.2f%%" % (100.0 * op.mean()))
rep.append("")


def score(im, box, use_alpha_only=False):
    tw, th = int(round(box[0] * SC)), int(round(box[1] * SC))
    ta = np.asarray(im.convert("RGBA").resize((tw, th), Image.LANCZOS), dtype=np.float64)
    ch, cw = min(rm.shape[0], th), min(rm.shape[1], tw)
    sub = ta[:ch, :cw]
    m = op[:ch, :cw]
    if not use_alpha_only:
        m = m & (sub[:, :, 3] > 200)
    if m.sum() < 100:
        return None
    x = sub[:, :, :3][m]; y = rm[:ch, :cw][m]
    return float(np.abs(x - y).mean()), float(np.corrcoef(x.mean(axis=1), y.mean(axis=1))[0, 1]), int(m.sum())


rep.append("SCORED vs real 5-shot mean, drawn into the 1750x276 widget box @ SC 0.598:")
rep.append("  %-52s %8s %8s %8s" % ("source", "MAD", "corr", "px"))
for label, p in [
    ("VANILLA ASIA/resource-panel.png", os.path.join(WID, r"textures\ingame\panels\ASIA\resource-panel.png")),
    ("VANILLA ASIA/topbar.png", os.path.join(WID, r"textures\ingame\panels\ASIA\topbar.png")),
    ("MOD ASIA/resource-panel.png", os.path.join(MOD, r"widgetui\textures\ingame\panels\ASIA\resource-panel.png")),
    ("MOD ASIA/topbar.png", os.path.join(MOD, r"widgetui\textures\ingame\panels\ASIA\topbar.png")),
    ("MOD WEST/resource-panel.png", os.path.join(MOD, r"widgetui\textures\ingame\panels\WEST\resource-panel.png")),
    ("MOD resource-panel_full.png", os.path.join(MOD, r"widgetui\textures\ingame\panels\resource-panel_full.png")),
]:
    if not os.path.exists(p):
        rep.append("  %-52s MISSING" % label[:52]); continue
    im = Image.open(p); im.load()
    a = score(im, (1750, 276))
    b = score(im, (1750, 276), use_alpha_only=True)
    fa = "(alpha-mask) MAD=%.2f corr=%+.4f px=%d" % b if b else "(alpha-mask: too few px)"
    if a:
        rep.append("  %-52s %8.2f %+8.4f %8d   %s" % (label[:52], a[0], a[1], a[2], fa))
    else:
        rep.append("  %-52s %8s %8s %8s   %s" % (label[:52], "-", "-", "-", fa))

# The bar may be the TOPBAR drawn into its own 3840x52 box instead.
rep.append("")
rep.append("ALTERNATIVE: topbar drawn into its OWN 3840x52 box (blanktoppanel.json),")
rep.append("compared only on y rows 0..31 (52*0.598):")
for label, p in [("VANILLA ASIA/topbar.png", os.path.join(WID, r"textures\ingame\panels\ASIA\topbar.png")),
                 ("MOD ASIA/topbar.png", os.path.join(MOD, r"widgetui\textures\ingame\panels\ASIA\topbar.png"))]:
    if not os.path.exists(p):
        continue
    im = Image.open(p); im.load()
    tw, th = int(round(3840 * SC)), int(round(52 * SC))
    ta = np.asarray(im.convert("RGBA").resize((tw, th), Image.LANCZOS), dtype=np.float64)
    ch, cw = min(rm.shape[0], th), min(rm.shape[1], tw)
    sub = ta[:ch, :cw]; m = op[:ch, :cw] & (sub[:, :, 3] > 200)
    if m.sum() < 100:
        rep.append("  %-52s too few px (n=%d)" % (label[:52], m.sum())); continue
    x = sub[:, :, :3][m]; y = rm[:ch, :cw][m]
    rep.append("  %-52s MAD=%6.2f corr=%+.4f px=%d" % (label[:52], np.abs(x - y).mean(),
                                                       np.corrcoef(x.mean(axis=1), y.mean(axis=1))[0, 1], m.sum()))

txt = "\n".join(rep)
open(os.path.join(O, "mod_art.txt"), "w", encoding="utf-8").write(txt)
print(txt)
