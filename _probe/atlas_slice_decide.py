# -*- coding: utf-8 -*-
"""DECISIVE: decode the actual ingamepanels atlas slice for civ emblems and
compare pixel-wise against V1 (widgetui) and V2 (wpfg) source PNGs."""
import os, json
from PIL import Image

G = r"D:\Games\Steam\steamapps\common\AoE2DE"
W = os.path.join(G, "widgetui")
V1 = os.path.join(W, "textures", "ingame", "emblems")
V2 = os.path.join(G, "resources", "_common", "wpfg", "resources", "civ_emblems")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\ui"
os.makedirs(OUT, exist_ok=True)

mats = json.load(open(os.path.join(W, "materials.json"), "r", encoding="utf-8"))
atlas = None
for a in mats["AtlasTextures"]:
    if a["AtlasDef"]["Name"] == "ingamepanels":
        atlas = a["AtlasDef"]; break

print("=== ingamepanels sources ===")
for k in ("UHDSource", "HDSource", "DefaultSource", "MaxWidth", "MaxHeight", "Cached"):
    print("   %-14s %s" % (k, atlas.get(k)))

# map RefName -> uv rect
def f(v):
    return float(v) if isinstance(v, str) else float(v)

rect = {t["RefName"]: (f(t["imageTLX"]), f(t["imageTLY"]), f(t["imageBRX"]), f(t["imageBRY"]),
                       t.get("FileName"))
        for t in atlas["Textures"] if t["RefName"].startswith("CivEmblem")}
print("   CivEmblem entries in atlas:", len(rect))
for k in ("CivEmblemBritons", "CivEmblemChinese", "CivEmblemCelts", "CivEmblemVikings", "CivEmblemBerbers"):
    print("     %-22s %s" % (k, rect.get(k)))

# open the three DDS levels
levels = {}
for tag, key in (("SD", "DefaultSource"), ("HD", "HDSource"), ("UHD", "UHDSource")):
    p = atlas.get(key)
    if not p:
        continue
    fp = os.path.join(W, p.replace("/", os.sep))
    if not os.path.exists(fp):
        print("   %s missing" % tag); continue
    try:
        im = Image.open(fp); im.load()
        levels[tag] = im
        print("   %s %-46s mode=%-6s %s" % (tag, os.path.basename(fp), im.mode, im.size))
    except Exception as e:
        print("   %s open failed: %r" % (tag, e))

def slice_of(tag, ref):
    im = levels.get(tag)
    if im is None or ref not in rect:
        return None
    u = rect[ref]
    Wd, Hd = im.size
    x0 = int(round(u[0] * Wd)); y0 = int(round(u[1] * Hd))
    x1 = int(round(u[2] * Wd)); y1 = int(round(u[3] * Hd))
    return im.convert("RGBA").crop((x0, y0, x1, y1))

rows = ["britons", "chinese", "celts", "vikings"]
CW, CH = 450, 280
sheet = Image.new("RGB", (CW * 3 + 20, CH * len(rows) + 12), (25, 25, 25))

def load(d, n):
    p = os.path.join(d, n + ".png")
    return Image.open(p).convert("RGBA") if os.path.exists(p) else None

print()
print("=== pixel stats + MAD: atlas(SD) slice vs V1 vs V2 ===")
for i, n in enumerate(rows):
    ref = "CivEmblem" + n[0].upper() + n[1:]
    sl = slice_of("SD", ref)
    v1 = load(V1, n); v2 = load(V2, n)
    line = "   %-9s" % n
    for tag, im in (("atlasSD", sl), ("V1", v1), ("V2", v2)):
        if im is None:
            line += "  %s=MISSING" % tag; continue
        a = im.convert("RGBA").resize((450, 280), Image.LANCZOS)
        px = list(a.getdata())
        mr = sum(p[0] for p in px) / len(px)
        mg = sum(p[1] for p in px) / len(px)
        mb = sum(p[2] for p in px) / len(px)
        ma = sum(p[3] for p in px) / len(px)
        line += "  %s=(%.1f,%.1f,%.1f,a%.1f)" % (tag, mr, mg, mb, ma)
    print(line)
    if sl is not None and v1 is not None and v2 is not None:
        s = sl.convert("RGBA").resize((450, 280), Image.LANCZOS)
        a1 = v1.convert("RGBA").resize((450, 280), Image.LANCZOS)
        a2 = v2.convert("RGBA").resize((450, 280), Image.LANCZOS)
        for tag, o in (("V1", a1), ("V2", a2)):
            sp = list(s.getdata()); op = list(o.getdata())
            tot = 0; cnt = 0
            for k in range(len(sp)):
                if sp[k][3] < 8 and op[k][3] < 8:
                    continue
                tot += abs(sp[k][0] - op[k][0]) + abs(sp[k][1] - op[k][1]) + abs(sp[k][2] - op[k][2])
                cnt += 1
            print("             MAD(atlasSlice, %s) over art px = %.2f  (n=%d)" % (tag, tot / max(cnt, 1) / 3, cnt))

    # composite sheet
    for j, im in enumerate((sl, v1, v2)):
        if im is None:
            continue
        a = im.convert("RGBA").resize((CW, CH), Image.LANCZOS)
        bg = Image.new("RGBA", (CW, CH), (25, 25, 25, 255))
        sheet.paste(Image.alpha_composite(bg, a).convert("RGB"), (10 + j * (CW + 5), i * CH + 6))

sheet.save(os.path.join(OUT, "atlas_vs_src.png"))
print()
print("   wrote atlas_vs_src.png", sheet.size, "(cols: atlasSD | V1 widgetui | V2 wpfg)")
