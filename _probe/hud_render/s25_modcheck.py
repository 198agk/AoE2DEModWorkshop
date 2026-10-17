# -*- coding: utf-8 -*-
"""Scan the enabled mods for UI texture replacements of the resource panel.

Corrected from s25: mod-status.json lives at
  <profile>\76561198406248391\mods\mod-status.json
and its Path values are RELATIVE to that mods\ directory (e.g.
"subscribed//550412_<title>"), not absolute.
"""
import os
import json
import numpy as np
from PIL import Image

O = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WID = os.path.join(GAME, "widgetui")
MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
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

st = np.stack([np.asarray(Image.open(p).convert("RGB").crop((0, 0, 1100, 200)), dtype=np.float64) for p in SHOTS])
rm = st.mean(axis=0)
op = st.std(axis=0).mean(axis=2) < 4.0
rep.append("real mean from %d shots; provably-opaque %.2f%%" % (len(SHOTS), 100.0 * op.mean()))
rep.append("")

ms = json.load(open(os.path.join(MODS, "mod-status.json"), encoding="utf-8-sig"))
enabled = []
for e in ms["Mods"]:
    rel = e["Path"].replace("//", os.sep).replace("/", os.sep)
    ap = os.path.join(MODS, rel)
    rep.append("Enabled=%-5s prio=%-3s exists=%-5s %s" % (e["Enabled"], e["Priority"], os.path.isdir(ap), e["Title"]))
    rep.append("      -> %s" % ap)
    if e["Enabled"] and os.path.isdir(ap):
        enabled.append((e["Title"], e["Priority"], ap))
rep.append("")

TARGETS = ("resource-panel", "resource_panel", "topbar", "resourcepanel")
hits = []
rep.append("walking %d enabled mods for UI panel textures:" % len(enabled))
for title, prio, root in enabled:
    n_all = n_png = 0
    found = []
    for dp, dn, fns in os.walk(root):
        for f in fns:
            n_all += 1
            low = f.lower()
            if low.endswith(".png"):
                n_png += 1
            if any(t in low for t in TARGETS):
                found.append(os.path.join(dp, f))
    rep.append("  prio %-3s %-46s files=%-6d png=%-6d name-hits=%d" % (prio, title[:46], n_all, n_png, len(found)))
    for p in found:
        rel = os.path.relpath(p, root)
        rep.append("        MATCH %s  (%d B)" % (rel, os.path.getsize(p)))
        hits.append((title, prio, p))
    # also check whether the mod ships a widgetui tree at all
    for dp, dn, fns in os.walk(root):
        if os.path.basename(dp).lower() == "widgetui":
            rep.append("        ships widgetui tree at %s (%d files)" % (os.path.relpath(dp, root), len(fns)))
rep.append("")
rep.append("total name-hits: %d" % len(hits))
rep.append("")


def score(im, box=(1750, 276)):
    im = im.convert("RGBA")
    tw, th = int(round(box[0] * SC)), int(round(box[1] * SC))
    ta = np.asarray(im.resize((tw, th), Image.LANCZOS), dtype=np.float64)
    ch, cw = min(rm.shape[0], th), min(rm.shape[1], tw)
    sub = ta[:ch, :cw]
    m = op[:ch, :cw] & (sub[:, :, 3] > 200)
    if m.sum() < 300:
        return None
    x = sub[:, :, :3][m]; y = rm[:ch, :cw][m]
    return float(np.abs(x - y).mean()), float(np.corrcoef(x.mean(axis=1), y.mean(axis=1))[0, 1]), int(m.sum()), im.size


rep.append("SCORED (drawn into the 1750x276 widget box at x0.598, vs real 5-shot mean on opaque mask):")
r = score(Image.open(os.path.join(WID, r"textures\ingame\panels\ASIA\resource-panel.png")))
rep.append("  %-56s MAD=%6.2f corr=%+.4f px=%6d %s" % ("VANILLA ASIA/resource-panel.png", r[0], r[1], r[2], r[3]))
for title, prio, p in hits:
    try:
        r = score(Image.open(p))
    except Exception as e:
        rep.append("  %-56s unreadable: %s" % (os.path.basename(p)[:56], e))
        continue
    if r is None:
        rep.append("  %-56s (too few px)" % os.path.basename(p)[:56])
        continue
    rep.append("  %-56s MAD=%6.2f corr=%+.4f px=%6d %s" % (os.path.basename(p)[:56], r[0], r[1], r[2], r[3]))

txt = "\n".join(rep)
open(os.path.join(O, "mod_check.txt"), "w", encoding="utf-8").write(txt)
print(txt)
