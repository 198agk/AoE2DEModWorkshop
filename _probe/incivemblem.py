# -*- coding: utf-8 -*-
"""Test the InGameCivEmblem -> wpfg civ_emblems/<civ>.png hypothesis.

Evidence motivating this:
  * icons.json has a section "InGameCivEmblem" with 62 entries whose VALUES look
    like "ingame_civ_emblems_britons".
  * No file in the whole tree contains the literal "ingame_civ_emblems", and the
    name is NOT a MaterialDef in materials.json (checked earlier) -> the name is
    not resolved through the material system.
  * resources/_common/wpfg/resources/civ_emblems/ contains 65 PNGs at exactly
    450x280, and they are the PREMULTIPLIED twins of widgetui/textures/ingame/
    emblems/*.png (V2 = V1 * alpha), which is the WPF compositing convention.
  * The in-game player list shows a VISIBLE antique emblem (not premultiplied-
    dark), and ships no mod that touches civ_emblems/ -> it reads vanilla.

If the 62 InGameCivEmblem values map 1:1 onto civ_emblems/<civ>.png, then the
score-panel emblem path is the WPF layer, which explains why replacing
widgetui/textures/ingame/emblems/*.png (what the chibi mod does) is invisible
in the player list.
"""
import json
import os
import glob

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WPFG_EMB = os.path.join(GAME, "resources", "_common", "wpfg", "resources", "civ_emblems")
WIDGET_EMB = os.path.join(GAME, "widgetui", "textures", "ingame", "emblems")
ICONS = os.path.join(GAME, "widgetui", "icons.json")

print("=== icons.json sections ===")
with open(ICONS, "r", encoding="utf-8") as fh:
    icons = json.load(fh)
for k in icons:
    v = icons[k]
    n = len(v) if isinstance(v, (dict, list)) else "-"
    print("  %-22s %s  n=%s" % (k, type(v).__name__, n))

sec = icons.get("InGameCivEmblem") or {}
if not sec:
    # section may be nested under a wrapper
    for k in icons:
        if isinstance(icons[k], dict) and "InGameCivEmblem" in icons[k]:
            sec = icons[k]["InGameCivEmblem"]
            print("  (found nested under %r)" % k)
            break

print()
print("=== InGameCivEmblem entries: %d ===" % len(sec))
items = sorted(sec.items(), key=lambda kv: kv[0])
for k, v in items[:8]:
    print("  %-6s -> %s" % (k, v))
print("  ...")

# Candidate resolutions
cands = {
    "wpfg_resource": lambda v: os.path.join(WPFG_EMB, v.split("_emblems_")[-1] + ".png"),
    "wpfg_plural": lambda v: os.path.join(WPFG_EMB, v.split("_emblems_")[-1].rstrip("s") + "s.png"),
    "widgetui": lambda v: os.path.join(WIDGET_EMB, v.split("_emblems_")[-1] + ".png"),
}
print()
print("=== resolution test (does the constructed path exist?) ===")
for cname, fn in cands.items():
    hit = 0
    miss = []
    for k, v in items:
        p = fn(v)
        if os.path.exists(p):
            hit += 1
        else:
            miss.append(v)
    print("  %-14s %d/%d" % (cname, hit, len(items)))
    if miss[:5]:
        print("      miss e.g. %s" % ", ".join(miss[:5]))

print()
print("=== raw directory contents ===")
wp = sorted(os.path.basename(p) for p in glob.glob(os.path.join(WPFG_EMB, "*.png")))
wd = sorted(os.path.basename(p) for p in glob.glob(os.path.join(WIDGET_EMB, "*.png")))
print("  wpfg civ_emblems : %d files" % len(wp))
print("    %s" % ", ".join(wp[:14]))
print("  widgetui emblems : %d files" % len(wd))
print("    %s" % ", ".join(wd[:14]))

# Which civ tokens appear in the icon values but not on disk, and vice versa?
tok_icon = set(v.split("_emblems_")[-1] for _, v in items)
tok_wpfg = set(os.path.splitext(f)[0] for f in wp)
tok_widg = set(os.path.splitext(f)[0] for f in wd)
print()
print("  icon tokens not in wpfg : %s" % sorted(tok_icon - tok_wpfg))
print("  wpfg tokens not in icon : %s" % sorted(tok_wpfg - tok_icon))
print("  icon tokens not in widget: %s" % sorted(tok_icon - tok_widg))
print("  widget tokens not in icon: %s" % sorted(tok_widg - tok_icon))
