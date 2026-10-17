# -*- coding: utf-8 -*-
"""Pin the exact icons.json -> disk-file rule, both forms, with counts.

Form 1 (prefix-stripped): CivEmblem/InGameCivEmblem -> wpfg civ_emblems/<civ>.png
Form 2 (whole value = filename): CivTechTree/History/CivUniqueUnit -> <dir>/<value>.png
Also resolve Buildings/Units/Techs through materials.json (atlas route).
Read-only.
"""
import os
import json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WJ = os.path.join(GAME, "widgetui")
WR = os.path.join(GAME, "resources", "_common", "wpfg", "resources")

icons = json.load(open(os.path.join(WJ, "icons.json"), encoding="utf-8"))
mats = json.load(open(os.path.join(WJ, "materials.json"), encoding="utf-8"))

mat_by_name, atlas_of = {}, {}
for m in mats["Materials"]:
    md = m.get("MaterialDef") or {}
    mat_by_name[md.get("Name")] = md
atlas_of = {}
for a in mats["AtlasTextures"]:
    ad = a.get("AtlasDef") or {}
    for t in ad.get("Textures", []):
        atlas_of.setdefault(t["RefName"], []).append((ad["Name"], t["FileName"]))


def exists(p):
    return os.path.exists(p)


def form2(val, subdir):
    p = os.path.join(WR, subdir, val + ".png")
    return p if exists(p) else None


print("=== Form 2: whole value IS the filename ===")
for sec, sub in (("CivTechTree", "civ_techtree"), ("History", "history"),
                 ("CivUniqueUnit", "usericons")):
    vals = [v for k, v in icons.get(sec, {}).items()
            if isinstance(v, str) and v]
    ok = [v for v in vals if form2(v, sub)]
    miss = [v for v in vals if not form2(v, sub)]
    print("%-22s %-14s %3d/%3d resolved   sample_miss=%s"
          % (sec, sub, len(ok), len(vals), miss[:3]))

print()
print("=== Form 1: strip a prefix, remainder is the stem ===")
for sec, subdir, prefixes in (
        ("CivEmblem", "civ_emblems", ["civ_emblems_"]),
        ("InGameCivEmblem", "civ_emblems", ["ingame_civ_emblems_", "civ_emblems_"]),
        ("CivHero", "civ_hero", ["civ_hero_"])):
    vals = [v for k, v in icons.get(sec, {}).items() if isinstance(v, str) and v]
    hit = []
    for v in vals:
        for pre in prefixes:
            if v.startswith(pre):
                p = os.path.join(WR, subdir, v[len(pre):] + ".png")
                if exists(p):
                    hit.append(v)
                break
    print("%-22s %-14s %3d/%3d resolved (subdir may not exist: %s)"
          % (sec, subdir, len(hit), len(vals), os.path.isdir(os.path.join(WR, subdir))))

print()
print("=== Buildings / Units / Techs via materials.json ===")
for sec in ("Buildings", "Units", "Techs"):
    vals = [v for k, v in icons.get(sec, {}).items() if isinstance(v, str) and v]
    inmat = [v for v in vals if v in mat_by_name]
    withfile = [v for v in inmat if atlas_of.get(
        (mat_by_name[v].get("TextureRef") or v))]
    print("%-12s %4d entries  in Materials: %4d  -> atlas FileName: %4d"
          % (sec, len(vals), len(inmat), len(withfile)))
    if withfile:
        smp = withfile[:3]
        for s in smp:
            md = mat_by_name[s]
            print("      %-34s -> %s" % (s, atlas_of.get(
                (md.get("TextureRef") or s))[:1]))

print()
print("=== unresolved remainder ===")
for sec in ("MapIcons", "Notification", "MenuIcons", "StatIcons"):
    vals = [v for k, v in icons.get(sec, {}).items() if isinstance(v, str) and v]
    print("%-14s %3d entries, %d empty, sample=%s"
          % (sec, len(icons.get(sec, {})), len(icons.get(sec, {})) - len(vals),
             vals[:3]))
