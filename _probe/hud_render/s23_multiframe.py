# -*- coding: utf-8 -*-
"""Remove the terrain term, then ask which source art was really drawn.

WHY THIS SCRIPT EXISTS
----------------------
Everything before it was built on an instrument with a noise floor equal to its
signal. Measured in s22: the four resource ICONS -- art independently confirmed
correct by overlay (ref_overlay_shot0.png) and by eye -- score MAD 56.8-68.1 under
the masked metric, the SAME band as every one of the 37 plank candidates
(41.8-74.6). So "the plank scores 71.55" is NOT evidence that the plank art is
wrong; it is evidence that masked MAD in this region cannot tell right art from
wrong art. (The workspace's own prior report records the same lesson: MAD/NCC is a
bad instrument for "which source was rendered".)

The reason is structural. The HUD is alpha-blended over live terrain:

    obs(x,y) = a(x,y)*A(x,y) + (1-a(x,y))*T(x,y)          A = HUD art, T = terrain

so any RGB comparison mixes in terrain that has nothing to do with the HUD.

THE FIX -- and it needs no new input
------------------------------------
Five real screenshots of the SAME game moment are available. The HUD is identical
across them (same resources, same age, same pop) but the CAMERA MOVES, so T differs
per shot while A is constant. Therefore, across the 5 shots:

    std_across_shots(x,y) = (1-a(x,y)) * std(T(x,y))

Two consequences, both used here:

  1. Where the HUD is fully OPAQUE (a=1) the 5 shots agree exactly -> std == 0.
     The set {std < t} is therefore an EMPIRICAL OPAQUE MASK of the real HUD, and
     the MEAN over the 5 shots at those pixels IS the real HUD art with the terrain
     term removed. This is the comparison the prior report demanded but never did.

  2. The std map is a function of (1-a) ONLY -- it is completely independent of the
     HUD's RGB tone. So correlating the std map against (255 - alpha) of a candidate
     is a TONE-FREE identity test: it asks "does this PNG's alpha silhouette match
     the alpha silhouette the real HUD actually has?" That question is immune to the
     dark/bright rendering discrepancy that broke every earlier attempt.
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

O = _HERE_PATH("_probe", "hud_render")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WID = os.path.join(GAME, "widgetui")
AT = r"C:\Users\26913\.dsh\attachments\v1\objects"
SHOTS = [
    os.path.join(AT, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    os.path.join(AT, "2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    os.path.join(AT, "16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    os.path.join(AT, "8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    os.path.join(AT, "89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
]
R = (0, 0, 1100, 220)   # resource-panel region; the timer at x>1400 is excluded
rep = []

# ------------------------------------------------------------------ load
ims = []
for p in SHOTS:
    if not os.path.exists(p):
        rep.append("MISSING %s" % p)
        continue
    im = Image.open(p).convert("RGB")
    ims.append(im.crop(R))
rep.append("loaded %d shots, each cropped to %s (region %dx%d)" % (len(ims), R, ims[0].width, ims[0].height))
stack = np.stack([np.asarray(i, dtype=np.float64) for i in ims])       # (K,h,w,3)
mean = stack.mean(axis=0)
std = stack.std(axis=0).mean(axis=2)                                   # (h,w), mean over RGB

# ------------------------------------------------------------------ sanity: is the HUD really static?
rep.append("")
rep.append("SANITY: is the HUD identical across shots? (mean over the 5 shots of known-opaque areas)")
# the wood icon's dark frame is unambiguously opaque HUD art
for (nm, bx, by, bw, bh) in (("wood icon frame", 10, 10, 40, 60),
                             ("timer area x=2200 (excluded from R)", 2200, 20, 200, 40)):
    if bx + bw <= R[2] or bx >= 2200:
        pass
for si, im in enumerate(ims):
    reg = np.asarray(im.crop((10, 10, 100, 70)), dtype=np.float64)
    rep.append("  shot%d  wood-icon region mean RGB = %6.2f %6.2f %6.2f" % (si, reg[:, :, 0].mean(), reg[:, :, 1].mean(), reg[:, :, 2].mean()))
# full-frame std, to show the camera really moved
rep.append("  -> full-frame std across shots (whole screenshot) = %.2f  (terrain/camera moves)"
           % np.stack([np.asarray(Image.open(p).convert("L"), dtype=np.float64) for p in SHOTS]).std(axis=0).mean())

# ------------------------------------------------------------------ empirical alpha mask
for t in (1.0, 2.0, 4.0, 8.0, 16.0):
    rep.append("")
    rep.append("std < %4.1f  -> %5.2f%% of the region is provably-opaque HUD (5 shots agree)"
               % (t, 100.0 * (std < t).mean()))
stat = std < 4.0
dyn = std > 24.0
rep.append("")
rep.append("opaque mask (std<4): %.2f%%   transparent-ish mask (std>24): %.2f%%   indeterminate: %.2f%%"
           % (100.0 * stat.mean(), 100.0 * dyn.mean(), 100.0 * (~stat & ~dyn).mean()))

# ------------------------------------------------------------------ candidates
M = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
mats = {}
for e in M["Materials"]:
    mats[e["MaterialDef"]["Name"]] = e["MaterialDef"]
atlas_by_name = {}
for e in M["AtlasTextures"]:
    atlas_by_name[e["AtlasDef"]["Name"]] = e["AtlasDef"]

cands = []
def add(lbl, path):
    if os.path.exists(path) and path not in [p for _, p in cands]:
        cands.append((lbl, path))
for t in atlas_by_name["CivAsia"]["Textures"]:
    add("CivAsia/" + t["RefName"], os.path.join(WID, *t["FileName"].split("/")))
for nm in sorted(mats):
    d = mats[nm]
    if not nm.endswith("ResourcePanel") and not nm.endswith("Topbar"):
        continue
    a = atlas_by_name.get(d.get("AtlasRef"))
    if not a:
        continue
    for t in a["Textures"]:
        if t["RefName"] == d["TextureRef"]:
            add(nm, os.path.join(WID, *t["FileName"].split("/")))

SC = 0.5980   # independently fitted HUD scale; used only to place the silhouette
rep.append("")
rep.append("TONE-FREE IDENTITY TEST -- corr( empirical std map , 1 - alpha of candidate )")
rep.append("(std map depends only on (1-a); it is independent of the HUD's RGB tone)")
rep.append("  %-36s %8s %9s  %s" % ("candidate", "corr", "alpha%", "note"))
rows = []
for lbl, p in cands:
    im = Image.open(p).convert("RGBA")
    tw, th = int(round(im.width * SC)), int(round(im.height * SC))
    if tw < 40 or th < 20:
        continue
    t = im.resize((tw, th), Image.LANCZOS)
    ta = np.asarray(t, dtype=np.float64)
    h, w = std.shape
    cw, ch = min(w, tw), min(h, th)
    a = ta[:ch, :cw, 3]
    s = std[:ch, :cw]
    opa_frac = 100.0 * (ta[:, :, 3] > 200).mean()
    # where the candidate says opaque, the real std should be ~0
    if (a > 200).sum() > 500 and (a <= 24).sum() > 500:
        inside = s[a > 200].mean()
        outside = s[a <= 24].mean()
        cc = float(np.corrcoef(s.ravel(), (255.0 - a).ravel())[0, 1])
        rows.append((cc, inside, outside, lbl, opa_frac, p))
rows.sort(reverse=True)
for cc, ins, outs, lbl, opa, p in rows[:14]:
    rep.append("  %-36s %+8.4f %8.1f%%  std_inside=%5.2f std_outside=%5.2f" % (lbl, cc, opa, ins, outs))

# ------------------------------------------------------------------ terrain-free RGB compare
rep.append("")
rep.append("TERRAIN-FREE RGB COMPARISON -- candidate art vs the 5-shot MEAN, restricted to")
rep.append("pixels where the real HUD is provably opaque (std<4). Terrain cannot enter here.")
rep.append("  %-36s %8s %9s %8s" % ("candidate", "MAD", "corr", "px used"))
rows2 = []
for lbl, p in cands:
    im = Image.open(p).convert("RGBA")
    tw, th = int(round(im.width * SC)), int(round(im.height * SC))
    t = im.resize((tw, th), Image.LANCZOS)
    ta = np.asarray(t, dtype=np.float64)
    h, w = std.shape
    cw, ch = min(w, tw), min(h, th)
    sub = ta[:ch, :cw]
    m = stat[:ch, :cw] & (sub[:, :, 3] > 200)
    if m.sum() < 300:
        continue
    x = sub[:, :, :3][m]
    y = mean[:ch, :cw][m]
    mad = float(np.abs(x - y).mean())
    cc = float(np.corrcoef(x.mean(axis=1), y.mean(axis=1))[0, 1]) if x.mean(axis=1).std() > 1e-6 else 0.0
    rows2.append((mad, cc, lbl, int(m.sum()), p))
rows2.sort()
for mad, cc, lbl, n, p in rows2[:14]:
    rep.append("  %-36s %8.2f %+9.4f %8d" % (lbl, mad, cc, n))

# ------------------------------------------------------------------ calibration control
rep.append("")
rep.append("CONTROL: the same terrain-free test on the four resource ICONS, whose rects are")
rep.append("layout-derived and whose art is known correct. This sets the FLOOR of the metric.")
for i, (nm, rel) in enumerate([("ResourceWood", r"textures\ingame\icons\resource_wood.png"),
                               ("ResourceFood", r"textures\ingame\icons\resource_food.png"),
                               ("ResourceGold", r"textures\ingame\icons\resource_gold.png"),
                               ("ResourceStone", r"textures\ingame\icons\resource_stone.png")]):
    im = Image.open(os.path.join(WID, rel)).convert("RGBA")
    tw, th = int(round(im.width * SC)), int(round(im.height * SC))
    t = im.resize((tw, th), Image.LANCZOS)
    ta = np.asarray(t, dtype=np.float64)
    lx, ly = int(round(15 * SC)) + int(round(200 * i * SC)), int(round(15 * SC))
    cw, ch = min(std.shape[1] - lx, tw), min(std.shape[0] - ly, th)
    if cw < 8 or ch < 8:
        continue
    sub = ta[:ch, :cw]
    m = stat[ly:ly + ch, lx:lx + cw] & (sub[:, :, 3] > 200)
    if m.sum() < 50:
        rep.append("  %-14s too few static+opaque px (%d)" % (nm, m.sum()))
        continue
    x = sub[:, :, :3][m]
    y = mean[ly:ly + ch, lx:lx + cw][m]
    rep.append("  %-14s MAD=%6.2f corr=%+.4f px=%d" % (nm, np.abs(x - y).mean(),
               np.corrcoef(x.mean(axis=1), y.mean(axis=1))[0, 1], m.sum()))

# ------------------------------------------------------------------ visuals
big = max(1000, ims[0].width)
pane = [("REAL 5-shot MEAN (terrain averaged out)", Image.fromarray(mean.astype(np.uint8))),
        ("REAL, provably-opaque px only (terrain removed)", Image.fromarray(np.where(stat[:, :, None], mean, 20).astype(np.uint8))),
        ("empirical std map x4 (bright = terrain shows through)", Image.fromarray(np.clip(std * 4, 0, 255).astype(np.uint8)).convert("RGB"))]
for lbl, p in cands:
    if lbl in ("CivAsia/CivAsiaResourcePanel", "CivAsia/CivAsiaTopbar"):
        im = Image.open(p).convert("RGBA")
        t = im.resize((int(round(im.width * SC)), int(round(im.height * SC))), Image.LANCZOS)
        flat = Image.new("RGB", (max(big, t.width), max(ims[0].height, t.height)), (95, 110, 80))
        flat.paste(t, (0, 0), t)
        pane.append((lbl + "  scaled 0.598", flat.crop((0, 0, big, ims[0].height))))
tot_h = sum(t.height + 20 for _, t in pane)
canvas = Image.new("RGB", (big, tot_h), (26, 26, 30))
d = ImageDraw.Draw(canvas)
yy = 0
for lbl, t in pane:
    canvas.paste(t, (0, yy))
    d.text((4, yy + 3), lbl, fill=(255, 255, 0))
    yy += t.height + 20
canvas.save(os.path.join(O, "cmp_terrain_free.png"))
rep.append("")
rep.append("wrote cmp_terrain_free.png %s" % (canvas.size,))
rep.append("wrote cmp_multiframe.txt")

txt = "\n".join(rep)
open(os.path.join(O, "cmp_multiframe.txt"), "w", encoding="utf-8").write(txt)
print(txt)
