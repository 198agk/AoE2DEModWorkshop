"""Exhaustive last-resort resolution for the 11 remaining icons.json values.

Remaining unresolved after all rule-based attempts:
  Notification: wonder_icon, relic_icon
  MenuIcons:    submenu_button_base, submenu_open_arrow_overlay,
                submenu_return_arrow_overlay, submenu_open, submenu_return,
                submenu_oligarchy, submenu_democracy, submenu_tyranny,
                mutually_exclusive_tech_unavailable
  StatIcons:    stat_icon_hpregen   (the other 23 resolved to StatIcons<X>)

Strategy: substring search over (a) every file path in the game tree,
(b) every material name / textureref, (c) the atlas TextureRef names, then
show what actually contains the token.  Also check whether the engine treats
these as runtime-computed names by looking for the *prefix* families.
Read-only.
"""
import json
import os
import re
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WIDGETUI = os.path.join(GAME, "widgetui")

sys.stdout.reconfigure(encoding="utf-8")

VALUES = {
    "Notification": ["wonder_icon", "relic_icon"],
    "MenuIcons": ["submenu_button_base", "submenu_open_arrow_overlay",
                  "submenu_return_arrow_overlay", "submenu_open", "submenu_return",
                  "submenu_oligarchy", "submenu_democracy", "submenu_tyranny",
                  "mutually_exclusive_tech_unavailable"],
    "StatIcons": ["stat_icon_hpregen"],
}

# ---- path index -------------------------------------------------------------
paths = []
for root, dirs, files in os.walk(GAME):
    for fn in files:
        paths.append(os.path.relpath(os.path.join(root, fn), GAME))
print("paths indexed: %d" % len(paths))

# ---- materials --------------------------------------------------------------
mat = json.load(open(os.path.join(WIDGETUI, "materials.json"),
                     "r", encoding="utf-8-sig", errors="replace"))
matnames = set()
for wrap in mat.get("Materials", []):
    md = wrap.get("MaterialDef") or {}
    for k in ("Name", "TextureRef"):
        if md.get(k):
            matnames.add(md[k])
print("material names: %d" % len(matnames))

def tokens(v):
    return [t for t in re.split(r"[_\-]+", v) if t]

for sec, vals in VALUES.items():
    print()
    print("=" * 100)
    print(sec)
    print("=" * 100)
    for v in vals:
        print()
        print("  ---- %s ----" % v)
        # (a) path substring
        hits = [p for p in paths if v.lower() in p.lower()]
        if hits:
            print("     path-substring hits (%d):" % len(hits))
            for h in hits[:6]:
                print("        ", h)
        else:
            print("     path-substring: none")
        # (b) material name containing the significant token(s)
        toks = tokens(v)
        key = toks[-1] if toks else v
        cand = sorted(n for n in matnames if key.lower() in n.lower())
        if cand:
            print("     materials containing %r (%d): %s" % (key, len(cand), cand[:10]))
        else:
            print("     materials containing %r: none" % key)
        # (c) any path containing ALL tokens
        allhits = [p for p in paths if all(t.lower() in p.lower() for t in toks)]
        if allhits:
            print("     path containing ALL tokens (%d): %s" % (len(allhits), allhits[:4]))

# ---- what does the widgetui tree actually have for these families? ----------
print()
print("=" * 100)
print("families present in materials.json")
print("=" * 100)
for pref in ("Wonder", "Relic", "Submenu", "SubMenu", "Menu", "Mutually", "Tech",
             "StatIcons"):
    fam = sorted(n for n in matnames if n.lower().startswith(pref.lower()))
    print("  %-12s %3d  %s" % (pref, len(fam), fam[:8]))
