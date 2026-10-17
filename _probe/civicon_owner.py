# -*- coding: utf-8 -*-
"""Find the widget that draws the in-game player-list emblem (V3 / <Civ>Icon).

Dump, for every widgetui json containing "CivIcon", the widget Name / Type /
ViewPort / Material context. Also dump the scorepanel + commandpanel structure
so we can tell which json owns the roster rows.
"""
import os
import json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WJ = os.path.join(GAME, "widgetui")


def walk(node, path, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "Material" and isinstance(v, str) and "CivIcon" in v:
                out.append((path, v))
            if k == "Name" and isinstance(v, str):
                pass
            walk(v, path + "/" + str(k), out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, path + "[%d]" % i, out)


for fn in sorted(os.listdir(WJ)):
    if not fn.endswith(".json") or fn in ("materials.json", "icons.json"):
        continue
    p = os.path.join(WJ, fn)
    try:
        with open(p, "r", encoding="utf-8-sig") as f:
            d = json.load(f)
    except Exception:
        continue
    txt = open(p, "r", encoding="utf-8-sig", errors="replace").read()
    if "CivIcon" not in txt:
        continue
    out = []
    walk(d, fn, out)
    print("==", fn, " CivIcon materials found:", len(out))
    for path, mat in out[:12]:
        # trim the path to the last widget-ish segment
        seg = path.split("/Widgets/")[-1]
        print("    %-70s -> %s" % (seg[:70], mat))

print()
print("=== which json references role/roster/player-list naming ===")
KEY = ["Roster", "PlayerList", "ScoreRow", "PlayerRow", "ScorePanel", "row_"]
for fn in sorted(os.listdir(WJ)):
    if not fn.endswith(".json"):
        continue
    p = os.path.join(WJ, fn)
    txt = open(p, "r", encoding="utf-8-sig", errors="replace").read()
    hits = {k: txt.count(k) for k in KEY if k in txt}
    if hits:
        print("  %-46s %s" % (fn, hits))
