# -*- coding: utf-8 -*-
"""Focused probes: texture alpha stats, FontIndex-by-file, missing atlas entries, glyph table, backdrop."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, struct, collections
from PIL import Image

W = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
FD = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\fonts"
OUT = _HERE_PATH("_probe", "hud_render")
rep = io.StringIO()

# ---- 1. alpha stats of resolved textures ----
rep.write("=== texture alpha stats (is alpha straight, or INVERSE?) ===\n")
probe = [
    ("BlackPanel_TL/ingamepanels", "textures/ingame/panels/npanel_tl_4k.png"),
    ("BlackPanel_CC/ingamepanels", "textures/ingame/panels/npanel_c_4k.png"),
    ("ResourceWood", "textures/ingame/icons/resource_wood.png"),
    ("Population", "textures/ingame/icons/pop.png"),
    ("CivAsiaResourcePanel", "textures/ingame/panels/ASIA/resource-panel.png"),
    ("AgeBar", "textures/ingame/panels/loadingbar_full.png"),
    ("IdleVillagerNormal", "textures/ingame/icons/idle-villager_normal.png"),
]
for label, rel in probe:
    p = os.path.join(W, rel)
    if not os.path.exists(p):
        rep.write("  %-34s MISSING %s\n" % (label, rel)); continue
    im = Image.open(p).convert("RGBA")
    a = im.getchannel("A")
    h = a.histogram()
    n = im.size[0]*im.size[1]
    rep.write("  %-34s %s alpha: min=%d max=%d mean=%.1f  a==0:%.1f%% a==255:%.1f%%\n"
              % (label, im.size, min(i for i in range(256) if h[i]), max(i for i in range(256) if h[i]),
                 sum(i*h[i] for i in range(256))/n, 100.0*h[0]/n, 100.0*h[255]/n))
    # corner pixel
    rep.write("      px(0,0)=%s  centre=%s\n" % (im.getpixel((0,0)), im.getpixel((im.size[0]//2, im.size[1]//2))))

# ---- 2. FontIndex per file ----
sj = json.load(open(os.path.join(OUT, "survey_types.json"), encoding="utf-8"))
shown = collections.Counter()
where = collections.defaultdict(list)
for r in sj["font_records"]:
    fi = r["FontIndex"]
    where[fi].append(r["file"])
for fi in sorted(where, key=lambda x: (x is None, x)):
    c = collections.Counter(where[fi])
    rep.write("\n=== FontIndex %s : %d blocks in %d files ===\n" % (fi, len(where[fi]), len(c)))
    for f, n in c.most_common(12):
        rep.write("   %-58s %d\n" % (f, n))

# ---- 3. find AgeupCastleAge in any atlas ----
mj = json.load(open(os.path.join(W, "materials.json"), encoding="utf-8-sig"))
atls = {e["AtlasDef"]["Name"]: e["AtlasDef"] for e in mj["AtlasTextures"]}
rep.write("\n=== search every atlas Textures[] for RefName 'AgeupCastleAge' ===\n")
found = []
for an, a in atls.items():
    for tx in a["Textures"]:
        if "ageup" in tx["RefName"].lower():
            found.append((an, tx["RefName"], tx["FileName"]))
for f in found:
    rep.write("   %s\n" % (f,))
if not found:
    rep.write("   NONE anywhere\n")
rep.write("=== ALL textures whose FileName mentions 'age' in ingamepanels ===\n")
for tx in atls["ingamepanels"]["Textures"]:
    if "age" in tx["FileName"].lower():
        rep.write("   %-34s %s\n" % (tx["RefName"], tx["FileName"]))

# ---- 4. glyphs ----
recs = json.load(open(os.path.join(OUT, "combined_box_records.json"), encoding="utf-8"))
rep.write("\n=== combined.box glyph records for selected codepoints ===\n")
bys = {r["code"]: r for r in recs}
rep.write("  'A'(65) present=%s  'a'(97) present=%s\n" % (65 in bys, 97 in bys))
for ch in "Aa0 .,!|()-gjy$zZ9":
    r = bys.get(ord(ch))
    if r:
        rep.write("  %-4r W=%6.1f H=%6.1f XO=%8.3f YO=%8.3f adv=%8.3f atlas=%d uv=(%.5f,%.5f)-(%.5f,%.5f)\n"
                  % (ch, r["W"], r["H"], r["XO"], r["YO"], r["adv"], r["atlas"],
                     r["u0"], r["v0"], r["u1"], r["v1"]))
    else:
        rep.write("  %-4r ABSENT\n" % ch)
rep.write("\n  HAdvance for chars of interest: %s\n" %
          {ch: round(bys[ord(ch)]["adv"], 3) for ch in "Aa0W., " if ord(ch) in bys})
asc = [r for r in recs if 32 <= r["code"] < 127]
if asc:
    rep.write("  ASCII-present glyphs: %d ; max H=%.1f ; YO range %.2f..%.2f\n" % (
        len(asc), max(r["H"] for r in asc),
        min(r["YO"] for r in asc), max(r["YO"] for r in asc)))
else:
    rep.write("  NO codepoints in 32..126 — code array parse is wrong.\n")
rep.write("  code array min=%d max=%d n=%d unique=%d\n" % (
    min(r["code"] for r in recs), max(r["code"] for r in recs), len(recs),
    len(set(r["code"] for r in recs))))
rep.write("  first 20 codes: %s\n" % [r["code"] for r in recs[:20]])
# how many ascii codepoints present
present = sum(1 for c in range(32, 127) if c in bys)
rep.write("  ASCII 32..126 present: %d/95\n" % present)
rep.write("  LATIN letters A-Z: %d/26, a-z: %d/26, digits: %d/10\n" % (
    sum(1 for c in range(65, 91) if c in bys),
    sum(1 for c in range(97, 123) if c in bys),
    sum(1 for c in range(48, 58) if c in bys)))
rep.write("  YO range over ASCII: %.2f .. %.2f\n" % (
    min(bys[c]["YO"] for c in range(32, 127) if c in bys),
    max(bys[c]["YO"] for c in range(32, 127) if c in bys)))

# ---- 5. backdrop candidates ----
rep.write("\n=== candidate backdrop textures in widgetui/textures ===\n")
for pat in ["loading", "panel", "background", "black", "mainmenu"]:
    hits = []
    for root, dirs, fns in os.walk(os.path.join(W, "textures")):
        for fn in fns:
            if pat in fn.lower() and fn.lower().endswith(".png"):
                hits.append(os.path.relpath(os.path.join(root, fn), W))
    rep.write("  '%s': %d e.g. %s\n" % (pat, len(hits), hits[:4]))

open(os.path.join(OUT, "probe_focused.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
