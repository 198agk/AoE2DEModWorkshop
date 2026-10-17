# -*- coding: utf-8 -*-
"""Probe the combined_*.png glyph atlas content: which channel carries the glyph mask?"""
import os, io, json, struct, collections
from PIL import Image
import numpy as np

FD = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\fonts"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
rep = io.StringIO()

recs = json.load(open(os.path.join(OUT, "combined_box_records.json"), encoding="utf-8"))
bys = {r["code"]: r for r in recs}

pages = {}
for i in range(6):
    p = os.path.join(FD, "combined_%04d.png" % i)
    if os.path.exists(p):
        pages[i] = Image.open(p).convert("RGB")
rep.write("pages loaded: %s\n" % {k: v.size for k, v in pages.items()})

def report_glyph(ch):
    r = bys[ord(ch)]
    pg = pages.get(r["atlas"])
    W, H = int(round(r["W"])), int(round(r["H"]))
    x0 = int(round(r["u0"] * pg.size[0])); y0 = int(round(r["v0"] * pg.size[1]))
    x1 = int(round(r["u1"] * pg.size[0])); y1 = int(round(r["v1"] * pg.size[1]))
    crop = pg.crop((x0, y0, x1, y1))
    a = np.asarray(crop).astype(int)
    rep.write("\nglyph %r code=%d atlas=%d W=%s H=%s px=(%d,%d)-(%d,%d) cropsize=%s\n"
              % (ch, r["code"], r["atlas"], r["W"], r["H"], x0, y0, x1, y1, crop.size))
    rep.write("  expected fractional uv size: %.4f x %.4f -> %.1f x %.1f px\n"
              % (r["u1"] - r["u0"], r["v1"] - r["v0"],
                 (r["u1"] - r["u0"]) * pg.size[0], (r["v1"] - r["v0"]) * pg.size[1]))
    for ci, cn in enumerate("RGB"):
        ch_ = a[:, :, ci]
        rep.write("  chan %s: min=%d max=%d mean=%.1f uniq=%d\n"
                  % (cn, ch_.min(), ch_.max(), ch_.mean(), len(np.unique(ch_))))
    # If R==G==B it's greyscale; then the mask is luminance
    rep.write("  R==G==B everywhere? %s\n" % bool(np.all(a[:, :, 0] == a[:, :, 1]) and np.all(a[:, :, 1] == a[:, :, 2])))
    rep.write("  overall page channel means: R=%.1f G=%.1f B=%.1f\n" % tuple(
        np.asarray(pg).astype(float).reshape(-1, 3).mean(axis=0)))

for ch in "A0a5":
    report_glyph(ch)

# stats over whole page 0
pg = pages[0]
a = np.asarray(pg).astype(int)
rep.write("\n=== page 0 overall: shape=%s ===\n" % (a.shape,))
rep.write("  channel means R=%.2f G=%.2f B=%.2f\n" % tuple(a.reshape(-1, 3).mean(axis=0)))
rep.write("  fraction of pixels that are pure black: %.3f\n" % float((a.sum(axis=2) == 0).mean()))
rep.write("  fraction pure white: %.3f\n" % float((a.min(axis=2) == 255).mean()))
# histogram of R channel
h = np.bincount(a[:, :, 0].ravel(), minlength=256)
rep.write("  R hist: 0->%d  255->%d  1..254->%d\n" % (h[0], h[255], h[1:255].sum()))

# compare DDS version
try:
    d = Image.open(os.path.join(FD, "combined_0000.DDS"))
    d = d.convert("RGBA")
    da = np.asarray(d).astype(int)
    rep.write("\n=== combined_0000.DDS RGBA ===\n")
    rep.write("  alpha mean=%.1f min=%d max=%d ; R mean=%.1f\n"
              % (da[:, :, 3].mean(), da[:, :, 3].min(), da[:, :, 3].max(), da[:, :, 0].mean()))
    hh = np.bincount(da[:, :, 3].ravel(), minlength=256)
    rep.write("  A hist: 0->%d  255->%d  1..254->%d\n" % (hh[0], hh[255], hh[1:255].sum()))
except Exception as e:
    rep.write("DDS read failed: %s\n" % e)

open(os.path.join(OUT, "font_atlas_probe.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())

# export a magnified sample of the text atlas for visual inspection
crop = pages[0].crop((0, 0, 512, 128)).resize((1024, 256), Image.NEAREST)
crop.save(os.path.join(OUT, "font_atlas_sample.png"))
crop2 = pages[5].crop((0, 1500, 600, 2000)).resize((600, 500), Image.NEAREST)
crop2.save(os.path.join(OUT, "font_atlas_sample_p5.png"))
print("wrote font_atlas_sample.png / font_atlas_sample_p5.png")
