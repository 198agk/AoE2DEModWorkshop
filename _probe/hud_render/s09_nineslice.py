# -*- coding: utf-8 -*-
"""Census TextAnchor values; inspect Surround nine-slice piece sizes; verify UV-vs-PNG-source 1:1."""
import os, io, json, collections
from PIL import Image

W = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
rep = io.StringIO()
mj = json.load(open(os.path.join(W, "materials.json"), encoding="utf-8-sig"))
mats = {}
for e in mj["Materials"]:
    mats[e["MaterialDef"]["Name"]] = e["MaterialDef"]
atls = {}
for e in mj["AtlasTextures"]:
    atls[e["AtlasDef"]["Name"]] = e["AtlasDef"]
glbs = {}
for e in mj["GlobalTextures"]:
    glbs[e["TextureDef"]["Name"]] = e["TextureDef"]

def find_atlas_entry(matname):
    d = mats.get(matname)
    if not d or d.get("Type") != "Atlas":
        return None
    a = atls.get(d.get("AtlasRef"))
    if not a:
        return None
    for tx in a["Textures"]:
        if tx["RefName"] == d.get("TextureRef"):
            return (a, tx)
    return None

# --- nine-slice pieces ---
rep.write("=== nine-slice piece geometry (BlackPanel_* and friends) ===\n")
for slot in ["TL", "TC", "TR", "CL", "CC", "CR", "BL", "BC", "BR"]:
    nm = "BlackPanel_" + slot
    r = find_atlas_entry(nm)
    if not r:
        rep.write("  %-16s UNRESOLVED\n" % nm); continue
    a, tx = r
    p = os.path.join(W, tx["FileName"])
    sz = Image.open(p).size if os.path.exists(p) else None
    ux = (float(tx["imageBRX"]) - float(tx["imageTLX"])) * a["MaxWidth"]
    uy = (float(tx["imageBRY"]) - float(tx["imageTLY"])) * a["MaxHeight"]
    rep.write("  %-16s png=%-40s pngsize=%-10s uvExtentPx=(%.1f, %.1f)\n"
              % (nm, os.path.basename(tx["FileName"]), sz, ux, uy))

# --- verify 1:1 for a broad sample of materials ---
rep.write("\n=== UV extent vs PNG source size: 1:1 check ===\n")
ok = bad = missing = 0
badlist = []
for name, d in mats.items():
    if d.get("Type") != "Atlas":
        continue
    r = find_atlas_entry(name)
    if not r:
        continue
    a, tx = r
    fn = tx.get("FileName")
    if not fn:
        continue
    p = os.path.join(W, fn)
    if not os.path.exists(p):
        missing += 1; continue
    try:
        pw, ph = Image.open(p).size
    except Exception:
        missing += 1; continue
    ux = (float(tx["imageBRX"]) - float(tx["imageTLX"])) * a["MaxWidth"]
    uy = (float(tx["imageBRY"]) - float(tx["imageTLY"])) * a["MaxHeight"]
    if abs(ux - pw) <= 1.5 and abs(uy - ph) <= 1.5:
        ok += 1
    else:
        bad += 1
        if len(badlist) < 25:
            badlist.append((name, a["Name"], os.path.basename(fn), (pw, ph), (round(ux, 1), round(uy, 1))))
rep.write("1:1 OK=%d  MISMATCH=%d  missing-png=%d  (of %d Atlas materials)\n"
          % (ok, bad, missing, sum(1 for d in mats.values() if d.get("Type") == "Atlas")))
rep.write("mismatch samples (name, atlas, png, pngsize, uvExtentPx):\n")
for b in badlist:
    rep.write("   %s\n" % (b,))

# --- TextAnchor census ---
sj = json.load(open(os.path.join(OUT, "survey_types.json"), encoding="utf-8"))
rep.write("\n=== TextAnchor keys present (from survey widget_keys) ===\n")
rep.write("  %s\n" % {k: v for k, v in sj["widget_keys"].items() if "Text" in k or "Anchor" in k or k in ("Wrap","AutoSize","TextOffset","ValueBox","Bar","IconValues","Rotation","Format")})

# walk all files for TextAnchor values
ta = collections.Counter()
def rec(o):
    if isinstance(o, dict):
        if "TextAnchor" in o and isinstance(o["TextAnchor"], str):
            ta[o["TextAnchor"]] += 1
        for v in o.values():
            rec(v)
    elif isinstance(o, list):
        for v in o:
            rec(v)
for root, dirs, fns in os.walk(W):
    for fn in fns:
        if not fn.lower().endswith(".json") or fn == "materials.json":
            continue
        try:
            d = json.load(open(os.path.join(root, fn), encoding="utf-8-sig"))
        except Exception:
            continue
        rec(d)
rep.write("\n=== ALL TextAnchor values across widgetui ===\n")
for k, c in ta.most_common():
    rep.write("  %-16s %d\n" % (k, c))

open(os.path.join(OUT, "probe_nineslice.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
