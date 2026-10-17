"""Apply the official filename->RefName normalization to the unresolved
icons.json values and test against materials.json.

Known official rule (from texturestoatlasjson.ps1 / texturetotexturejson.ps1):
    filename -> ToTitleCase(ToLower()) -> strip '_' and '-' -> optional prefix

sections_last3_where.py showed 18 of 24 StatIcons and all 9 MenuIcons and both
Notification values are absent verbatim from materials.json, the tree, and the
exe.  Test normalization candidates instead.  Read-only.
"""
import json
import os
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WIDGETUI = os.path.join(GAME, "widgetui")

sys.stdout.reconfigure(encoding="utf-8")

mat = json.load(open(os.path.join(WIDGETUI, "materials.json"),
                     "r", encoding="utf-8-sig", errors="replace"))
mnames, trefs = {}, {}
for wrap in mat.get("Materials", []):
    md = wrap.get("MaterialDef") or {}
    n = md.get("Name")
    tr = md.get("TextureRef")
    if n:
        mnames[n.lower()] = n
    if tr:
        trefs[tr.lower()] = tr

# also index by "de-punctuated" form
def squash(s):
    return "".join(c for c in s.lower() if c.isalnum())

mat_squash = {}
for k, v in list(mnames.items()) + list(trefs.items()):
    mat_squash.setdefault(squash(k), v)


def titlecase_strip(s):
    parts = s.replace("-", "_").split("_")
    return "".join(p[:1].upper() + p[1:].lower() for p in parts if p)


VALUES = {
    "Notification": ["wonder_icon", "relic_icon"],
    "MenuIcons": ["submenu_button_base", "submenu_open_arrow_overlay",
                  "submenu_return_arrow_overlay", "submenu_open", "submenu_return",
                  "submenu_oligarchy", "submenu_democracy", "submenu_tyranny",
                  "mutually_exclusive_tech_unavailable"],
    "StatIcons": ["stat_icon_armor", "stat_icon_convert", "stat_icon_damage",
                  "stat_icon_food", "stat_icon_garrison", "stat_icon_gold",
                  "stat_icon_hp", "stat_icon_hpregen", "stat_icon_movement_speed",
                  "stat_icon_pierce_attack", "stat_icon_hploss", "stat_icon_range",
                  "stat_icon_range_armor", "stat_icon_reload_time", "stat_icon_stone",
                  "stat_icon_transport", "stat_icon_wood", "stat_icon_workrate"],
}

print("=" * 104)
print("normalization candidates vs materials.json Name/TextureRef")
print("=" * 104)
print("  rule: ToTitleCase(ToLower) segments -> concat; also try squash-match")
print()

for sec, vals in VALUES.items():
    print(sec)
    print("-" * 104)
    for v in vals:
        tc = titlecase_strip(v)
        cands = [
            ("as-is", v),
            ("TitleCase", tc),
            ("TitleCase+Icon", tc + "Icon"),
            ("Icon" + tc, "Icon" + tc),
            ("squash", squash(v)),
        ]
        hits = []
        for label, c in cands:
            if c.lower() in mnames:
                hits.append("%s -> materials.Name %r" % (label, mnames[c.lower()]))
            if c.lower() in trefs:
                hits.append("%s -> materials.TextureRef %r" % (label, trefs[c.lower()]))
        if not hits and squash(v) in mat_squash:
            hits.append("squash-match -> %r" % mat_squash[squash(v)])
        print("  %-34s %s" % (v, "; ".join(hits) if hits else "<no candidate matches>"))
    print()

# show the StatIcons* family that DOES exist, to see the shape
print("=" * 104)
print("materials.json names containing 'stat'")
print("=" * 104)
for k in sorted(set(list(mnames.values()) + list(trefs.values()))):
    if "stat" in k.lower():
        print("   ", k)
