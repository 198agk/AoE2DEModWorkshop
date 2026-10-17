# -*- coding: utf-8 -*-
"""Settle: are icons.json section names ENGINE-consumed, and what uses CivEmblem?

Facts so far:
  * Both CivEmblem ("civ_emblems_<civ>") and InGameCivEmblem
    ("ingame_civ_emblems_<civ>") normalise onto the SAME wpfg asset family
    resources/_common/wpfg/resources/civ_emblems/<civ>.png
    (63/65 and 60/62 respectively; the remainder are empty/dummy entries).
  * widgetui/textures/ingame/emblems/*.png are the source images for the
    ingamepanels ATLAS materials "CivEmblem<Civ>" -- a different namespace.
  * exe has 0 occurrences of "civ_emblems" and "InGameCivEmblem".

Now: does the exe know ANY of these section names? If it knows some but not
others, that tells us which tables the engine actually parses.
And what are the 2 commandpanel.json references to CivEmblem?
"""
import os
import re
import json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")

data = open(EXE, "rb").read()
print("exe size %d" % len(data))
print()
print("=== section / table name presence in exe ===")
names = ["CivEmblem", "InGameCivEmblem", "CivTechTree", "CivHero", "StatIcons",
         "CivUniqueUnit", "CivSecondaryUniqueUnit", "MapIcons", "History",
         "Notification", "MenuIcons", "Buildings", "Units", "Techs",
         "icons.json", "civ_emblems", "ingame_civ_emblems", "civ_techtree",
         "civ_hero", "menu_techtree", "uniticons", "usericons", "mapicons",
         "empireicons", "history", "Icons"]
for n in names:
    c = data.count(n.encode())
    print("  %-26s %3d" % (n, c))

print()
print("=== what surrounds the bare 'CivEmblem' hits? ===")
for needle in [b"CivEmblem"]:
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        seg = data[max(0, i - 120):i + 120]
        txt = "".join(chr(c) if 32 <= c < 127 else "." for c in seg)
        print("  @0x%08x %s" % (i, txt))
        start = i + 1

print()
print("=== commandpanel.json: the 2 CivEmblem references ===")
cp = os.path.join(GAME, "widgetui", "commandpanel.json")
txt = open(cp, "r", encoding="utf-8", errors="ignore").read()
lines = txt.splitlines()
for i, ln in enumerate(lines, 1):
    if "CivEmblem" in ln:
        lo = max(1, i - 12)
        hi = min(len(lines), i + 12)
        print("  --- around line %d ---" % i)
        for j in range(lo, hi + 1):
            mark = ">>" if j == i else "  "
            print("  %s %5d  %s" % (mark, j, lines[j - 1].strip()[:160]))
