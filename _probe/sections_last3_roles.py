"""For each unresolved icons.json section value, show the referencing layout
file and the surrounding role (widget Name? Material? StateMaterials?).

The previous script said "layout_ref(1)" without saying which file or in what
role.  This narrows it to an actionable rule.  Read-only.
"""
import json
import os
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
    "StatIcons": ["stat_icon_armor", "stat_icon_convert", "stat_icon_food",
                  "stat_icon_hp", "stat_icon_wood", "stat_icon_gold", "stat_icon_stone"],
}


def walk_widgets(node, path, out):
    """Yield (widget_path, widget_dict) for every Widget in the tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "Widget" and isinstance(v, dict):
                out.append((path, v))
                walk_widgets(v, path + "/" + str(v.get("Name", "?")), out)
            else:
                walk_widgets(v, path + "/" + k, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_widgets(v, path + "[%d]" % i, out)


for sec, vals in VALUES.items():
    print("=" * 92)
    print(sec)
    print("=" * 92)
    for v in vals:
        print()
        print("  value: %s" % v)
        found = 0
        for fn in sorted(os.listdir(WIDGETUI)):
            if not fn.lower().endswith(".json"):
                continue
            p = os.path.join(WIDGETUI, fn)
            try:
                with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
                    txt = f.read()
            except Exception:
                continue
            if v not in txt:
                continue
            found += 1
            try:
                doc = json.loads(txt)
            except Exception as e:
                print("      %-34s (unparseable: %s)" % (fn, e))
                continue
            ws = []
            walk_widgets(doc, "", ws)
            # where exactly does the value appear inside the widget objects?
            roles = []
            for wpath, w in ws:
                for key in ("Name", "Material", "TextureRef", "Type"):
                    if w.get(key) == v:
                        roles.append("%s.%s" % (wpath or "/", key))
                sm = w.get("StateMaterials")
                if isinstance(sm, dict) and json.dumps(sm).find(v) >= 0:
                    roles.append("%s.StateMaterials" % (wpath or "/"))
                sm2 = w.get("mats")
                if isinstance(sm2, list) and v in sm2:
                    roles.append("%s.mats" % (wpath or "/"))
            print("      %-34s roles: %s" % (fn, roles[:4] if roles else "<string present but not as Name/Material/mats>"))
        if not found:
            print("      <no layout references it>")
