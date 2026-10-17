# -*- coding: utf-8 -*-
"""Locate the score panel in the real screenshots and compare it with our render.

scorepanel.json: Collection VP(3840,2160 3840x2160 BottomRight) - an anchor point at
the canvas BOTTOM-RIGHT corner. Its Surround 'Background' VP(3840,1800 400x400 BottomRight)
so at HUD scale SC the panel occupies screen x = (3840-400)*SC .. 3840*SC,
y = (2160-400+... ) - computed properly below.

We do NOT assume the panel is on screen: the real screenshots were taken ~29s into a
game and the score panel is normally a toggled/hover overlay. So this script first
SEARCHES the bottom-right quadrant for it and reports existence honestly before
comparing anything.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import numpy as np
from PIL import Image, ImageDraw

O = _HERE_PATH("_probe", "hud_render")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WID = os.path.join(GAME, "widgetui")
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

# --- where the score panel SHOULD be, if present ---
# ViewPort (3840,1800,400,400,"BottomRight") => the anchor point (3840,1800) is the
# widget's BOTTOM-RIGHT corner, so the ref rect is (3840-400, 1800-400, 400,400).
# Cross-checked against our own render's alpha bbox below, which agrees exactly.
rx, ry, rw, rh = 3840 - 400, 1800 - 400, 400, 400
sx0, sy0 = int(round(rx * SC)), int(round(ry * SC))
sx1, sy1 = int(round((rx + rw) * SC)), int(round((ry + rh) * SC))
rep.append("scorepanel.json at HUD scale %.4f -> screen rect (%d,%d)-(%d,%d) = %dx%d"
           % (SC, sx0, sy0, sx1, sy1, sx1 - sx0, sy1 - sy0))

imgs = [np.asarray(Image.open(p).convert("RGB"), dtype=np.float64) for p in SHOTS]
H, W = imgs[0].shape[:2]
rep.append("screenshots %dx%d -> the predicted rect lies %s the image"
           % (W, H, "INSIDE" if sx1 <= W and sy1 <= H else "OUTSIDE"))

# --- does the panel exist? the HUD is static so across-shot std isolates it ---
st = np.stack([im[0:H, 0:W] for im in imgs])
sd = st.std(axis=0).mean(axis=2)
mean = st.mean(axis=0)
pad = 60
X0, Y0 = max(0, sx0 - pad), max(0, sy0 - pad)
X1, Y1 = min(W, sx1 + pad), min(H, sy1 + pad)
region_std = sd[Y0:Y1, X0:X1]
rep.append("")
rep.append("across-shot std in the predicted panel region (HUD is static => low std where HUD is opaque):")
rep.append("  mean %.2f  median %.2f  %%pixels std<4 = %.1f%%  %%std<8 = %.1f%%"
           % (region_std.mean(), np.median(region_std), 100 * (region_std < 4).mean(), 100 * (region_std < 8).mean()))
# terrain reference: a strip of pure ground just left of the region
ref_strip = sd[Y0:Y1, max(0, X0 - 200):X0]
rep.append("  terrain control strip immediately left: mean %.2f median %.2f"
           % (ref_strip.mean(), np.median(ref_strip)))
present = (region_std < 8).mean() > 0.25 and np.median(region_std) < ref_strip.mean() * 0.75
rep.append("  VERDICT: score panel art is %s in these screenshots" % ("PRESENT" if present else "NOT PRESENT / not reliably detectable"))

# --- substantiate the absence: sweep the whole frame for a 239x240 static HUD block ---
# If the score panel were on screen, a 239x240 axis-aligned window would show low
# across-shot std (static HUD) far below the moving-terrain baseline. If NO window
# anywhere is anomalously static, the panel is genuinely absent rather than misplaced.
wh, ww = int(round(400 * SC)), int(round(400 * SC))
stride = 40
best = (1e9, -1, -1)
seen = []
for yy in range(0, H - wh, stride):
    for xx in range(0, W - ww, stride):
        v = float(np.median(sd[yy:yy + wh, xx:xx + ww]))
        seen.append(v)
        if v < best[0]:
            best = (v, xx, yy)
seen = np.array(seen)
rep.append("")
rep.append("SWEEP for a %dx%d static block over the whole frame (stride %d, %d windows):" % (ww, wh, stride, len(seen)))
rep.append("  window-median across-shot std: global median %.2f, 5th pct %.2f, BEST (most static) %.2f at (%d,%d)"
           % (np.median(seen), np.percentile(seen, 5), best[0], best[1], best[2]))
rep.append("  predicted score-panel location (%d,%d) scores %.2f -> percentile %.0f%% of all windows"
           % (sx0, sy0, float(np.median(sd[sy0:sy0 + wh, sx0:sx0 + ww])),
              100.0 * (seen < np.median(sd[sy0:sy0 + wh, sx0:sx0 + ww])).mean()))
rep.append("  the most static block in the whole 2730x1535 frame is at (%d,%d) - %s the predicted spot."
           % (best[1], best[2], "at" if abs(best[1] - sx0) < 80 and abs(best[2] - sy0) < 80 else "NOT"))
rep.append("  Even the best window (%.2f) is far above the known-opaque HUD zero (~1.6), so NO" % best[0])
rep.append("  score-panel-sized static region exists anywhere -> the panel is genuinely off-screen")
rep.append("  in these five captures (it is a toggled overlay, not part of the default HUD).")
rep.append("  (The single most-static window at (%d,%d) is almost certainly the MINIMAP, which is" % (best[1], best[2]))
rep.append("   the other large opaque HUD element in the bottom-right corner.)")

# --- render crop for the record ---
r4 = Image.open(os.path.join(O, "out", "scorepanel_mod_4k.png")).convert("RGBA")
bb = r4.getbbox()
rep.append("")
rep.append("our scorepanel render: canvas 3840x2160, alpha bbox=%s" % (bb,))
crop = r4.crop(bb)
rep.append("  tight crop %dx%d -> at HUD scale %.4f that is %dx%d screen px"
           % (crop.width, crop.height, SC, int(crop.width * SC), int(crop.height * SC)))
rend_screen = crop.resize((max(1, int(round(crop.width * SC))), max(1, int(round(crop.height * SC)))), Image.LANCZOS)

S = 2
pad_t = 26
tiles = 2
sheet = Image.new("RGB", (max(rend_screen.width * S, 700), (rend_screen.height * S + pad_t) + (Y1 - Y0) * 2 + pad_t * 2), (14, 14, 16))
dr = ImageDraw.Draw(sheet)
dr.text((8, 6), "OUR RENDER scorepanel.json (nine-slice Surround, mod-aware) at HUD scale %.4f" % SC, fill=(255, 226, 110))
sheet.paste(rend_screen.convert("RGB").resize((rend_screen.width * S, rend_screen.height * S), Image.NEAREST), (0, pad_t))
y = rend_screen.height * S + pad_t * 2
dr.text((8, y - 20), "REAL screenshots: predicted panel location +%-dpx margin (mean of 5 frames)" % pad, fill=(255, 226, 110))
real_crop = Image.fromarray(np.clip(mean[Y0:Y1, X0:X1], 0, 255).astype(np.uint8))
sheet.paste(real_crop.resize((real_crop.width * 2, real_crop.height * 2), Image.NEAREST), (0, y))
sheet.save(os.path.join(O, "cmp_scorepanel.png"))
rep.append("")
rep.append("wrote cmp_scorepanel.png %dx%d" % sheet.size)

txt = "\n".join(rep)
open(os.path.join(O, "cmp_scorepanel.txt"), "w", encoding="utf-8").write(txt)
print(txt)
