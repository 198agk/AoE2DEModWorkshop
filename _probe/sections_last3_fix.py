"""Correct-nesting resolution for the last icons.json values.

BUG FOUND: materials.json's AtlasTextures entries are `{"AtlasDef": {...}}`
wrapped, and the Textures[] array lives INSIDE AtlasDef.  sections_last3_pin.py
used `at.get("Textures")` on the OUTER dict -> always None -> every StatIcons
material printed "-> None".  That was a probe bug, not a missing mapping.

This script walks the correct nesting and therefore gives the real answer.
Read-only.
"""
import json
import os
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
W = os.path.join(GAME, "widgetui")

sys.stdout.reconfigure(encoding="utf-8")

mat = json.load(open(os.path.join(W, "materials.json"),
                     "r", encoding="utf-8-sig", errors="replace"))

# ---- correct walk ----------------------------------------------------------
ref_to_file = {}        # RefName -> FileName
ref_to_atlas = {}       # RefName -> atlas name
for wrap in mat.get("AtlasTextures", []):
    ad = wrap.get("AtlasDef") or {}
    aname = ad.get("Name")
    for t in ad.get("Textures", []):
        rn = t.get("RefName")
        if rn:
            ref_to_file[rn] = t.get("FileName")
            ref_to_atlas[rn] = aname
for gt in mat.get("GlobalTextures", []):
    td = gt.get("TextureDef") or {}
    if td.get("Name"):
        ref_to_file.setdefault(td["Name"], td.get("FileName"))
        ref_to_atlas.setdefault(td["Name"], "<global>")

print("atlas textures indexed: %d" % len(ref_to_file))

matdefs = {}
for wrap in mat.get("Materials", []):
    md = wrap.get("MaterialDef") or {}
    if md.get("Name"):
        matdefs[md["Name"]] = md

print("material defs: %d" % len(matdefs))


def show(name):
    md = matdefs.get(name)
    if not md:
        return "<no such material>"
    key = md.get("TextureRef") or name
    return "%s  type=%s  atlas=%s  file=%s" % (
        name, md.get("Type"), ref_to_atlas.get(key), ref_to_file.get(key))


print()
print("=" * 96)
print("StatIcons* real FileNames")
print("=" * 96)
for n in sorted(matdefs):
    if n.startswith("StatIcons"):
        print("   %s" % show(n))

print()
print("=" * 96)
print("Wonder / Relic / Menu candidates")
print("=" * 96)
for pat in ("Wonder", "Relic", "indicator"):
    print("  -- %s --" % pat)
    for n in sorted(matdefs):
        if pat.lower() in n.lower():
            print("     %s" % show(n))
    print()

print("=" * 96)
print("SubMenu* materials")
print("=" * 96)
for n in sorted(matdefs):
    if n.lower().startswith("submenu"):
        print("   %s" % show(n))

# ---- reverse: which FileName is the icons.json value near? -----------------
print()
print("=" * 96)
print("FileName reverse index for indicator_wonder / indicator_relic / hpRegen")
print("=" * 96)
for target in ("indicator_wonder.png", "indicator_relic.png", "hpRegen.png"):
    print("  %s:" % target)
    for rn, fn in ref_to_file.items():
        if fn and fn.lower().endswith(target.lower()):
            print("     RefName=%-34s file=%s  atlas=%s" % (rn, fn, ref_to_atlas.get(rn)))
