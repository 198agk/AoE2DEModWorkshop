# -*- coding: utf-8 -*-
"""Characterise the residual unresolved icons.json values.

Categories to explain:
  * literal "None" strings
  * Units/Techs/StatIcons that miss materials.json
  * civ_emblems_inca / civ_emblems_berber (singular vs plural naming)
  * CivSecondaryUniqueUnit composite "A,B" values
  * MenuIcons with no on-disk asset at all
Read-only.
"""
import os
import json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WJ = os.path.join(GAME, "widgetui")
WR = os.path.join(GAME, "resources", "_common", "wpfg", "resources")

icons = json.load(open(os.path.join(WJ, "icons.json"), encoding="utf-8"))
mats = json.load(open(os.path.join(WJ, "materials.json"), encoding="utf-8"))
matn = set()
for m in mats["Materials"]:
    matn.add((m.get("MaterialDef") or {}).get("Name"))

print("=== literal 'None' strings ===")
for sec in ("Buildings", "Techs"):
    none_keys = [k for k, v in icons[sec].items() if v == "None"]
    print("%-12s %d entries are the literal string 'None': %s"
          % (sec, len(none_keys), none_keys))

print()
print("=== civ_emblems residuals: singular vs plural on disk ===")
for stem in ("inca", "incas", "berber", "berbers"):
    p = os.path.join(WR, "civ_emblems", stem + ".png")
    print("  civ_emblems/%-8s.png  exists=%s" % (stem, os.path.exists(p)))
print("  values in icons.json:", [v for v in icons["CivEmblem"].values()
                                 if isinstance(v, str) and
                                 ("inca" in v or "berber" in v)])

print()
print("=== CivSecondaryUniqueUnit composite values ===")
comp = [(k, v) for k, v in icons["CivSecondaryUniqueUnit"].items()
        if isinstance(v, str) and "," in v]
print("  %d comma-joined values; sample: %s" % (len(comp), comp[:2]))
for k, v in comp[:2]:
    for part in v.split(","):
        print("     part %-22s in Materials=%s" % (part, part in matn))

print()
print("=== StatIcons unresolved ===")
bad = [v for v in icons["StatIcons"].values()
       if isinstance(v, str) and v and v not in matn]
print("  %d / %d not a material name" % (len(bad), len(icons["StatIcons"])))
print("  sample:", bad[:8])
# where do stat_icon_* actually live?
for v in bad[:6]:
    hits = []
    for base in (WR, os.path.join(WJ, "textures"), os.path.join(GAME, "resources")):
        for b, s, fs in os.walk(base):
            for f in fs:
                if v + ".png" == f or v + ".dds" == f:
                    hits.append(os.path.join(b, f).replace(GAME, "<GAME>"))
    print("   %-28s -> %s" % (v, hits[:2] or "MISSING"))

print()
print("=== Units/Techs unresolved: do their numbers exist at all? ===")
for sec in ("Units", "Techs"):
    bad = [v for v in icons[sec].values()
           if isinstance(v, str) and v and v not in matn]
    print("  %-8s %4d unresolved; first 6: %s" % (sec, len(bad), bad[:6]))
