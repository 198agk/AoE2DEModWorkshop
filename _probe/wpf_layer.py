# -*- coding: utf-8 -*-
"""Test: do the icons.json "logical" sections map onto wpfg asset directories?

Observed:
  CivEmblem       values "civ_emblems_<civ>"        -> resources/_common/wpfg/resources/civ_emblems/<civ>.png  (60/63)
  CivTechTree     values "menu_techtree_<civ>"
  CivHero         values "civ_hero_<civ>"
  InGameCivEmblem values "ingame_civ_emblems_<civ>"

Hypothesis H: value  <a>_<b>_<...>_<name>  maps to
              resources/_common/wpfg/resources/<a>_<b>_.../<name>.png
i.e. the LAST underscore-separated token is the file stem and everything before
it is a path, all under wpfg/resources/. If H holds for all four sections, then
these four are WPF-layer asset tables, NOT material references -- which explains
why replacing widgetui/textures/ingame/emblems/*.png does not change the player
list, and why "ingame_civ_emblems_*" matches nothing on disk.
"""
import json
import os

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
ICONS = os.path.join(GAME, "widgetui", "icons.json")
WPF = os.path.join(GAME, "resources", "_common", "wpfg", "resources")

icons = json.load(open(ICONS, "r", encoding="utf-8"))

print("=== wpfg/resources subdirectories that could match ===")
subs = sorted(d for d in os.listdir(WPF) if os.path.isdir(os.path.join(WPF, d)))
for d in subs:
    n = len(os.listdir(os.path.join(WPF, d)))
    print("  %-34s %d files" % (d, n))
print()


def try_resolve(value):
    """Return list of candidate existing paths under wpfg for one icon value."""
    if not value:
        return []
    toks = value.split("_")
    out = []
    for cut in range(len(toks) - 1, 0, -1):
        d = "_".join(toks[:cut])
        stem = "_".join(toks[cut:])
        for ext in (".png", ".jpg", ".dds"):
            p = os.path.join(WPF, d, stem + ext)
            if os.path.exists(p):
                out.append(os.path.relpath(p, GAME))
    return out


SECTIONS = ["CivEmblem", "InGameCivEmblem", "CivTechTree", "CivHero",
            "CivUniqueUnit", "CivSecondaryUniqueUnit", "MapIcons", "History",
            "Notification", "MenuIcons"]

for s in SECTIONS:
    sec = icons.get(s)
    if not isinstance(sec, dict) or not sec:
        continue
    tot = hit = 0
    ex = {}
    for k, v in sec.items():
        if not v:
            continue
        tot += 1
        r = try_resolve(v)
        if r:
            hit += 1
            if len(ex) < 3:
                ex[v] = r
    print("=== %-24s %3d/%3d resolved to wpfg ==" % (s, hit, tot))
    for v, r in ex.items():
        print("      %-34s -> %s" % (v, r[0]))
    print()

# Also: does stripping a leading "ingame_" change the answer for InGameCivEmblem?
print("=== InGameCivEmblem: strip 'ingame_' then resolve ===")
sec = icons.get("InGameCivEmblem") or {}
tot = hit = 0
for k, v in sorted(sec.items()):
    if not v:
        continue
    tot += 1
    r = try_resolve(v.replace("ingame_", "", 1))
    if r:
        hit += 1
        if tot <= 4:
            print("      %-40s -> %s" % (v, r[0]))
print("  %d/%d resolved after stripping 'ingame_'" % (hit, tot))
