# -*- coding: utf-8 -*-
"""Resolve the two icons.json emblem sections against materials.json.

Data so far:
  icons.json  CivEmblem        (67)  values "civ_emblems_<civ>"
  icons.json  InGameCivEmblem  (63)  values "ingame_civ_emblems_<civ>"
  materials.json has 62 materials named "CivEmblem<Civ>" (no underscores)
      -> atlas "ingamepanels", FileName "textures/ingame/emblems/<civ>.png"
  exe contains "CivEmblem" x2 but neither "civ_emblems" nor "InGameCivEmblem".

Question: does either icons.json value NORMALISE to a real MaterialDef?
Try the plausible engine normalisations.
"""
import json
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
ICONS = os.path.join(GAME, "widgetui", "icons.json")
MATS = os.path.join(GAME, "widgetui", "materials.json")

icons = json.load(open(ICONS, "r", encoding="utf-8"))
mats = json.load(open(MATS, "r", encoding="utf-8"))

matnames = set()
for m in mats["Materials"]:
    d = m.get("MaterialDef") or m
    matnames.add(d.get("Name"))
print("materials.json: %d Materials, %d unique names" % (len(mats["Materials"]), len(matnames)))
print("  also keys:", list(mats.keys()))
print()

# every material name containing 'mblem'
embl = sorted(n for n in matnames if n and "mblem" in n.lower())
print("materials with 'mblem' in the name: %d" % len(embl))
print("  sample:", ", ".join(embl[:12]))
print()

# build the atlas FileName index for these materials
atlas_files = {}
for a in mats["AtlasTextures"]:
    d = a.get("AtlasDef") or a
    for t in d.get("Textures", []):
        atlas_files.setdefault(t.get("RefName"), []).append((d.get("Name"), t.get("FileName")))

print("Atlas entries whose RefName contains 'mblem':")
for k in sorted(atlas_files):
    if k and "mblem" in k.lower():
        print("  %-34s -> %s" % (k, atlas_files[k][:2]))
print()


def norm_variants(v):
    """Plausible engine normalisations of a logical name to a material name."""
    t = v.replace("_", " ")
    tc = "".join(w[:1].upper() + w[1:].lower() for w in t.split())
    return {
        "asis": v,
        "nounderscore": v.replace("_", ""),
        "titlecase": tc,
        "nounderscore_title": v.replace("_", "").title(),
        "upperfirst": v[:1].upper() + v[1:],
        "camel": "".join(w[:1].upper() + w[1:] for w in v.split("_")),
        "camel_lower2nd": "".join(w[:1].upper() + w[1:].lower() for w in v.split("_")),
    }


for secname in ("CivEmblem", "InGameCivEmblem", "CivTechTree", "CivHero"):
    sec = icons.get(secname) or {}
    if not isinstance(sec, dict):
        continue
    print("=== %s (n=%d) ===" % (secname, len(sec)))
    tally = {}
    for k, v in sec.items():
        if not v:
            continue
        for label, cand in norm_variants(v).items():
            if cand in matnames:
                tally[label] = tally.get(label, 0) + 1
    print("  normalisation -> hits in materials.json:")
    for label in sorted(tally, key=lambda x: -tally[x]):
        print("      %-20s %d" % (label, tally[label]))
    sample = [v for _, v in sorted(sec.items())[:3]]
    print("  sample values: %s" % sample)
    print()
