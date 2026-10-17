# -*- coding: utf-8 -*-
"""Decisive: which layer actually names "ingame_civ_emblems_<civ>"?

The name appears in icons.json (InGameCivEmblem section) but is NOT a
MaterialDef in materials.json, and no file on disk is called that. If a WPF
XAML resource dictionary references it, the emblem is drawn by the WPF layer
from resources/_common/wpfg/resources/civ_emblems/<civ>.png -- which is why
replacing widgetui/textures/ingame/emblems/*.png does not show up.
"""
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
NEEDLES = ["ingame_civ_emblems", "civ_emblems", "InGameCivEmblem", "CivEmblem", "ingame_civ_emblem"]

roots = [
    os.path.join(GAME, "resources", "_common", "wpfg"),
    os.path.join(GAME, "widgetui"),
    os.path.join(GAME, "modes"),
]

hits = {}
for root in roots:
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if not f.lower().endswith((".xaml", ".json", ".txt", ".ps", ".xml")):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, GAME)
            try:
                txt = open(p, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for nd in NEEDLES:
                if nd in txt:
                    hits.setdefault(nd, []).append((rel, txt.count(nd)))

for nd in NEEDLES:
    lst = hits.get(nd, [])
    print("=== %-22s %d file(s)" % (nd, len(lst)))
    for rel, c in sorted(lst, key=lambda t: -t[1])[:14]:
        print("      %-70s x%d" % (rel, c))
    print()

# For the strongest hit, show the actual referencing lines.
print("=== sample referencing lines (xaml first) ===")
shown = 0
for root in roots:
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if not f.lower().endswith((".xaml", ".json")):
                continue
            p = os.path.join(dp, f)
            try:
                lines = open(p, "r", encoding="utf-8", errors="ignore").read().splitlines()
            except Exception:
                continue
            for i, ln in enumerate(lines, 1):
                if "civ_emblem" in ln.lower():
                    rel = os.path.relpath(p, GAME)
                    print("  %s:%d" % (rel, i))
                    print("      %s" % ln.strip()[:200])
                    shown += 1
                    if shown >= 25:
                        raise SystemExit
