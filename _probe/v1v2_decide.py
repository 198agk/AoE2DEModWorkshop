# -*- coding: utf-8 -*-
"""Decide which emblem source the in-game score panel actually uses.
Renders: V1 (widgetui/textures/ingame/emblems) vs V2 (wpfg/resources/civ_emblems)
composited over light/dark, plus a tight crop of the score panel from the screenshot.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
from PIL import Image

G = r"D:\Games\Steam\steamapps\common\AoE2DE"
V1 = os.path.join(G, "widgetui", "textures", "ingame", "emblems")
V2 = os.path.join(G, "resources", "_common", "wpfg", "resources", "civ_emblems")
EMP = os.path.join(G, "resources", "_common", "wpfg", "resources", "empireicons")
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = _HERE_PATH("_shots", "ui")
os.makedirs(OUT, exist_ok=True)

print("=== V1 vs V2 pixel statistics (britons/chinese/celts) ===")
for name in ("britons", "chinese", "celts"):
    for tag, d in (("V1", V1), ("V2", V2)):
        p = os.path.join(d, name + ".png")
        if not os.path.exists(p):
            print("   %-3s %-8s MISSING" % (tag, name)); continue
        im = Image.open(p).convert("RGBA")
        r, g, b, a = im.split()
        import statistics
        mr = sum(r.getdata()) / (im.width * im.height)
        mg = sum(g.getdata()) / (im.width * im.height)
        mb = sum(b.getdata()) / (im.width * im.height)
        ma = sum(a.getdata()) / (im.width * im.height)
        nz = sum(1 for v in a.getdata() if v > 8) / (im.width * im.height)
        print("   %-3s %-8s %s  meanRGB=(%.1f,%.1f,%.1f) meanA=%.1f  opaqueFrac=%.3f"
              % (tag, name, im.size, mr, mg, mb, ma, nz))

print()
print("=== render V1 and V2 over light and dark backgrounds ===")
names = ["britons", "chinese", "celts", "vikings", "aztecs", "byzantines"]
CW, CH = 450, 280
sheet = Image.new("RGB", (CW * 4 + 30, CH * len(names) + 10), (40, 40, 40))
for i, n in enumerate(names):
    y = i * CH + 5
    for j, (tag, d) in enumerate([("V1", V1), ("V2", V2)]):
        p = os.path.join(d, n + ".png")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGBA")
        for k, bgc in enumerate([(230, 230, 230), (25, 25, 25)]):
            bg = Image.new("RGBA", im.size, bgc + (255,))
            comp = Image.alpha_composite(bg, im).convert("RGB")
            sheet.paste(comp, (10 + (j * 2 + k) * (CW + 5), y))
sheet.save(os.path.join(OUT, "v1v2_bgtest.png"))
print("   wrote v1v2_bgtest.png", sheet.size)
print("   column order per row: V1-on-LIGHT | V1-on-DARK | V2-on-LIGHT | V2-on-DARK")

print()
print("=== empireicons contents (36 files) ===")
if os.path.isdir(EMP):
    fs = sorted(os.listdir(EMP))
    print("   n=%d sample=%s" % (len(fs), fs[:6]))
    cell_w, cell_h = 128, 128
    cols = 6
    rows = (len(fs) + cols - 1) // cols
    sh = Image.new("RGB", (cols * cell_w, rows * cell_h), (30, 30, 30))
    for i, f in enumerate(fs):
        try:
            im = Image.open(os.path.join(EMP, f)).convert("RGBA")
        except Exception:
            continue
        im.thumbnail((cell_w - 8, cell_h - 8))
        bg = Image.new("RGBA", (cell_w, cell_h), (30, 30, 30, 255))
        bg.alpha_composite(im, ((cell_w - im.width) // 2, (cell_h - im.height) // 2))
        sh.paste(bg.convert("RGB"), ((i % cols) * cell_w, (i // cols) * cell_h))
    sh.save(os.path.join(OUT, "empireicons_sheet.png"))
    print("   wrote empireicons_sheet.png", sh.size)
else:
    print("   MISSING", EMP)

print()
print("=== locate the 5 original screenshots ===")
shots = {}
for root, ds, fs in os.walk(SHOTS):
    for f in fs:
        if len(f) == 64:
            shots[f[:8]] = os.path.join(root, f)
for k in ("0261b373", "2fe52823", "16175bb0", "8eeadcf8", "89bdabdd"):
    print("   %s -> %s" % (k, shots.get(k, "MISSING")))

f1 = shots.get("0261b373")
if f1:
    im = Image.open(f1).convert("RGB")
    print("   f1 size:", im.size)
    W, H = im.size
    # score panel region: bottom-right
    box = (int(W * 0.60), int(H * 0.58), W, int(H * 0.94))
    crop = im.crop(box)
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    crop.save(os.path.join(OUT, "scorepanel_shot_f1.png"))
    print("   wrote scorepanel_shot_f1.png", crop.size, "from box", box)
