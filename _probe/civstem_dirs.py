# -*- coding: utf-8 -*-
"""Targeted search: every file in the game tree whose basename matches a civ
stem, grouped by directory. Reveals ALL emblem families (V1, V2, and any third).
"""
import os

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

# stems used by V1/V2 for a representative set of civs (note irregular forms)
STEMS = ["britons", "berber", "berbers", "chinese", "vikings", "lithuanians",
         "teutons", "aztecs", "byzantines", "saracens", "poles", "khitans",
         "jurchens", "bulgarians", "franks", "goths", "celts", "magyars",
         "persians", "romans", "shu", "wei", "wu", "huns", "koreans",
         "mongols", "spanish", "turks", "italians", "malay", "khmer",
         "burmese", "cumans", "slavs", "incas", "mayans", "ethiopians",
         "malians", "portuguese", "bohemians", "sicilians", "burgundians",
         "dravidians", "bengalis", "gurjaras", "armenians", "georgians",
         "achaemenids", "athenians", "spartans", "macedonians", "thracians",
         "puru", "muisca", "mapuche", "tupi", "saxons", "varangians", "danes"]
SS = set(STEMS)

bydir = {}
for root, dirs, files in os.walk(GAME):
    low = root.lower()
    if "\\drs\\graphics" in low or "\\wwise\\" in low:
        dirs[:] = []
        continue
    got = []
    for f in files:
        b = os.path.splitext(f)[0].lower()
        if b in SS:
            got.append(f)
    if got:
        bydir[root.replace(GAME, "")] = got

print("directories containing civ-stem-named files (%d):" % len(bydir))
for k in sorted(bydir, key=lambda z: -len(bydir[z])):
    fs = sorted(bydir[k])
    exts = sorted({os.path.splitext(f)[1].lower() for f in fs})
    print()
    print("  %-70s n=%d  exts=%s" % (k, len(fs), ",".join(exts)))
    print("      %s" % (", ".join(fs[:14]) + (" ..." if len(fs) > 14 else "")))
