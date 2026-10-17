# -*- coding: utf-8 -*-
"""DECISIVE TEST: is the screenshot's resource panel the VANILLA art or the MOD's
semi-transparent replacement?

Physics. If the engine composites the panel over terrain:
      observed_i = a*A + (1-a)*T_i          (i = screenshot index)
then across the 5 same-moment shots the panel term a*A is CONSTANT and only the
terrain term moves, so
      std_i(observed) = (1-a) * std_i(T)
i.e. the per-pixel across-shot standard deviation is a DIRECT, TONE-FREE readout of
(1-alpha) -- completely independent of any texture's RGB.

So: bin pixels of the bar region by a candidate texture's own (1-alpha) and measure
the mean across-shot std in each bin.

  * VANILLA ASIA/resource-panel.png has 41.3% of pixels at alpha>200 -> (1-a)~0.
    If vanilla is what the game drew, those bins MUST have std ~ 0.
  * The MOD's replacement is capped at alpha=128 -> (1-a) >= 0.5 everywhere, so
    NO bin can have std near 0.
A terrain control strip below the bar gives std_T to convert the observed std into
an estimated (1-alpha) and compare it with each candidate's declared alpha.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import numpy as np
from PIL import Image

O = _HERE_PATH("_probe", "hud_render")
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

R = (0, 0, 1100, 200)
st = np.stack([np.asarray(Image.open(p).convert("RGB").crop(R), dtype=np.float64) for p in SHOTS])
rm = st.mean(axis=0)
sd = st.std(axis=0).mean(axis=2)
H, W = sd.shape
rep.append("region %s  mean across-shot std = %.2f" % (str(R), sd.mean()))
rep.append("")

# ---- known-opaque widget rects (screen space), to exclude from the alpha test ----
def box(x, y, w, h, align="CentreCentre"):
    if align == "CentreCentre":
        return (x - w // 2, y - h // 2, w, h)
    return (x, y, w, h)

KNOWN = [box(57 + 200 * i, 57, 84, 84) for i in range(4)]          # 4 resource icons
KNOWN += [box(856, 57, 86, 84), box(1080, 57, 70, 70), box(1200, 62, 141, 122)]  # pop/idle/ageup
KNOWN += [box(1250, 57, 378, 52, "CentreLeft")]                    # age bar
KNOWN += [box(108, 60, 100, 34, "CentreLeft"), box(308, 60, 100, 34, "CentreLeft"),
          box(508, 60, 100, 34, "CentreLeft"), box(710, 60, 100, 34, "CentreLeft")]  # storage labels
KNOWN += [box(910, 60, 130, 34, "CentreLeft"), box(900, 60, 140, 72, "CentreLeft")]  # popcount/flash
excl = np.zeros((H, W), bool)
for (x, y, w, h) in KNOWN:
    x0 = max(0, int(round(x * SC))); y0 = max(0, int(round(y * SC)))
    x1 = min(W, int(round((x + w) * SC))); y1 = min(H, int(round((y + h) * SC)))
    if x1 > x0 and y1 > y0:
        excl[y0:y1, x0:x1] = True
rep.append("excluded known-opaque widget rects: %.1f%% of region" % (100.0 * excl.mean()))
rep.append("")

# ---- terrain control strip: rows below the plank (plank bottom = 276*0.598 = 165) ----
ctrl = sd[176:200, 0:1100]
sd_T = float(np.median(ctrl[~excl[176:200, 0:1100]]))
rep.append("TERRAIN CONTROL rows 176..199: median across-shot std = %.2f  (n=%d)"
           % (sd_T, int((~excl[176:200, 0:1100]).sum())))
rep.append("  -> a pixel with panel alpha a should show std ~= (1-a)*%.2f" % sd_T)
rep.append("")

CANDIDATES = [
    ("VANILLA ASIA/resource-panel.png", os.path.join(WID, r"textures\ingame\panels\ASIA\resource-panel.png"), (1750, 276), (0, 0)),
    ("MOD     ASIA/resource-panel.png", os.path.join(MOD, r"widgetui\textures\ingame\panels\ASIA\resource-panel.png"), (1750, 276), (0, 0)),
    ("MOD     WEST/resource-panel.png", os.path.join(MOD, r"widgetui\textures\ingame\panels\WEST\resource-panel.png"), (1750, 276), (0, 0)),
    ("VANILLA ingamepanels/resource-panel_full.png", os.path.join(WID, r"textures\ingame\panels\resource-panel_full.png"), (1935, 228), (0, 0)),
    ("VANILLA ASIA/topbar.png", os.path.join(WID, r"textures\ingame\panels\ASIA\topbar.png"), (3840, 52), (0, 0)),
    ("MOD     ASIA/topbar.png", os.path.join(MOD, r"widgetui\textures\ingame\panels\ASIA\topbar.png"), (3840, 52), (0, 0)),
]

rep.append("BIN MEAN across-shot std by the candidate's own (255-alpha)/255.")
rep.append("A CORRECT candidate must show a monotonic rise and, crucially, its")
rep.append("most-opaque bin must be near 0 if its alpha reaches 255.")
rep.append("")
for label, path, rbox, at in CANDIDATES:
    if not os.path.exists(path):
        rep.append("  %-46s MISSING" % label[:46]); continue
    im = Image.open(path); im.load()
    tw, th = int(round(rbox[0] * SC)), int(round(rbox[1] * SC))
    a = np.asarray(im.convert("RGBA").resize((tw, th), Image.LANCZOS), dtype=np.float64)[:, :, 3]
    canvas = np.zeros((H, W), np.float64)          # 0 = "no texture here"
    present = np.zeros((H, W), bool)
    ox, oy = int(round(at[0] * SC)), int(round(at[1] * SC))
    h2 = min(th, H - oy); w2 = min(tw, W - ox)
    if h2 > 0 and w2 > 0:
        canvas[oy:oy + h2, ox:ox + w2] = a[:h2, :w2]
        present[oy:oy + h2, ox:ox + w2] = True
    ta = canvas / 255.0
    # mean declared (1-alpha) over the texture's own present pixels
    rep.append("  %s" % label)
    rep.append("      declared alpha: min=%d max=%d  present px=%.1f%%  mean(1-a) over present=%.3f"
               % (int(canvas[present].min()), int(canvas[present].max()),
                  100.0 * present.mean(), float((1 - ta)[present].mean())))
    rep.append("      %-14s %8s %10s %10s" % ("(1-a) bin", "n px", "obs std", "pred std"))
    edges = [0.0, 0.01, 0.1, 0.25, 0.5, 0.75, 1.01]
    ok_mono = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        m = present & (~excl) & (1 - ta >= lo) & (1 - ta < hi)
        if m.sum() < 150:
            continue
        obs = float(sd[m].mean())
        pred = ((lo + min(hi, 1.0)) / 2.0) * sd_T
        ok_mono.append((lo, obs))
        rep.append("      %-14s %8d %10.2f %10.2f" % ("[%.2f,%.2f)" % (lo, hi), int(m.sum()), obs, pred))
    if len(ok_mono) >= 2:
        xs = np.array([b for b, _ in ok_mono]); ys = np.array([v for _, v in ok_mono])
        slope = float(np.polyfit(xs, ys, 1)[0])
        rep.append("      FIT obs_std = %.2f * (1-a) + %.2f   (terrain control std_T=%.2f)"
                   % (slope, float(np.polyfit(xs, ys, 1)[1]), sd_T))
    # single decisive number: std in the most-opaque bin present
    m255 = present & (~excl) & (canvas >= 250)
    if m255.sum() >= 150:
        rep.append("      *** alpha>=250 bin: n=%d  obs std=%.2f  (vanilla-opaque -> must be ~0) ***"
                   % (int(m255.sum()), float(sd[m255].mean())))
    m128 = present & (~excl) & (canvas >= 120) & (canvas <= 128)
    if m128.sum() >= 150:
        rep.append("      *** alpha in 120..128 bin: n=%d  obs std=%.2f ***"
                   % (int(m128.sum()), float(sd[m128].mean())))
    rep.append("")

rep.append("REFERENCE: what does the UNAMBIGUOUSLY-OPAQUE art look like?")
for i in range(4):
    x, y, w, h = KNOWN[i]
    x0, y0 = int(round(x * SC)), int(round(y * SC))
    x1, y1 = x0 + int(round(w * SC)), y0 + int(round(h * SC))
    rep.append("  resource icon %d (%s box) obs std = %.2f" % (i, "wood food gold stone".split()[i], float(sd[y0:y1, x0:x1].mean())))
for i, nm in ((4, "population box"), (5, "idle badge"), (6, "age-up button"), (7, "age bar")):
    x, y, w, h = KNOWN[i]
    x0, y0 = int(round(x * SC)), int(round(y * SC))
    x1, y1 = x0 + int(round(w * SC)), y0 + int(round(h * SC))
    rep.append("  %-16s obs std = %.2f" % (nm, float(sd[y0:y1, x0:x1].mean())))

txt = "\n".join(rep)
open(os.path.join(O, "mod_alpha_test.txt"), "w", encoding="utf-8").write(txt)
print(txt)
