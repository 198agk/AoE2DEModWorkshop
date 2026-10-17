# -*- coding: utf-8 -*-
"""Which widget/material draws the roster emblem? Resolve every material
reference in every widgetui json back to its source FileName, and report all
that land in textures/menu/civs (V3 family).
"""
import os
import json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WJ = os.path.join(GAME, "widgetui")

m = json.load(open(os.path.join(WJ, "materials.json"), encoding="utf-8-sig"))
mats = {x["MaterialDef"]["Name"]: x["MaterialDef"] for x in m["Materials"]}
byref = {}
for a in m["AtlasTextures"]:
    for t in a["AtlasDef"].get("Textures", []):
        byref[t.get("RefName")] = (a["AtlasDef"]["Name"], t.get("FileName", ""))
gref = {}
for g in m["GlobalTextures"]:
    gref[g["TextureDef"]["Name"]] = g["TextureDef"].get("FileName", "")


def src_of(name):
    md = mats.get(name)
    if md is None:
        return None
    tr = md.get("TextureRef") or name
    if md.get("Type") == "Atlas":
        return byref.get(tr)
    if md.get("Type") == "Texture":
        return ("GLOBAL", gref.get(tr))
    return (md.get("Type"), None)


def walk(node, path, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("Material", "MaterialName") and isinstance(v, str):
                s = src_of(v)
                if s and s[1] and "menu/civs" in str(s[1]):
                    out.append((path, v, s))
            walk(v, path + "/" + str(k), out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, path + "[%d]" % i, out)


total = 0
for fn in sorted(os.listdir(WJ)):
    if not fn.endswith(".json") or fn == "materials.json":
        continue
    p = os.path.join(WJ, fn)
    try:
        d = json.load(open(p, encoding="utf-8-sig"))
    except Exception:
        continue
    out = []
    walk(d, fn, out)
    if out:
        total += len(out)
        print("==", fn, len(out))
        seen = set()
        for path, mat, s in out:
            if (path, mat) in seen:
                continue
            seen.add((path, mat))
            seg = path.split("/Widgets/")[-1]
            print("    %-64s mat=%-24s atlas=%-16s %s" % (seg[:64], mat, s[0], s[1]))
print()
print("total menu/civs material references in widgetui layout json:", total)

print()
print("=== are all 79 <Civ>Icon materials present, incl. LithuaniansIcon? ===")
civ = sorted(n for n, md in mats.items() if src_of(n) and "menu/civs" in str(src_of(n)[1]))
print("n=%d" % len(civ))
print(civ[:80])
for probe in ["LithuaniansIcon", "BritonsIcon", "BerbersIcon"]:
    print("  %-18s -> %s" % (probe, src_of(probe)))
