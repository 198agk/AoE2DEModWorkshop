# -*- coding: utf-8 -*-
"""Compute the on-screen rectangle of the command panel's CivEmblem widget.

commandpanel.json declares:
    {"Widget": {"Type": "Base", "Name": "CivEmblem",
                "ViewPort": {"xorigin":403,"yorigin":93,"width":450,"height":280,
                             "alignment":"TopLeft"},
                "StateMaterials": {"UserStates":1,"UserState0":{"Material":"CivEmblem"}}}}

xorigin/yorigin are relative to the parent widget/collection. So walk the tree
from the Collection and accumulate absolute 3840x2160 coordinates, then scale to
the 2730x1535 screenshots. Also list every widget whose Material resolves to the
ingamepanels atlas (i.e. anything the chibi mod could affect).
"""
import os
import json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CP = os.path.join(GAME, "widgetui", "commandpanel.json")
MATS = os.path.join(GAME, "widgetui", "materials.json")

REF_W, REF_H = 3840, 2160
SHOT_W, SHOT_H = 2730, 1535
SX = SHOT_W / REF_W
SY = SHOT_H / REF_H


def align_offset(al, w, h, pw, ph):
    """Return (dx,dy) so that the child lands correctly inside parent box pw x ph."""
    a = (al or "TopLeft").lower()
    if a == "topleft":
        return 0, 0
    if a == "topright":
        return pw - w, 0
    if a == "topcentre" or a == "topcenter":
        return (pw - w) // 2, 0
    if a == "centreleft" or a == "centerleft":
        return 0, (ph - h) // 2
    if a == "centreright" or a == "centerright":
        return pw - w, (ph - h) // 2
    if a == "centrecentre" or a == "centercenter":
        return (pw - w) // 2, (ph - h) // 2
    if a == "bottomleft":
        return 0, ph - h
    if a == "bottomright":
        return pw - w, ph - h
    if a == "bottomcentre" or a == "bottomcenter":
        return (pw - w) // 2, ph - h
    return 0, 0


data = json.load(open(CP, "r", encoding="utf-8"))
col = data["Collection"]
cvp = col["ViewPort"]
print("Collection ViewPort:", cvp)

cw = cvp.get("width", REF_W)
ch = cvp.get("height", REF_H)
ox = cvp.get("xorigin", 0)
oy = cvp.get("yorigin", 0)
print("base origin (%d,%d) size %dx%d" % (ox, oy, cw, ch))
print()

hits = []


def walk(widget, px, py, pw, ph, path):
    vp = widget.get("ViewPort") or {}
    w = vp.get("width", 0)
    h = vp.get("height", 0)
    dx, dy = align_offset(vp.get("alignment"), w, h, pw, ph)
    ax = px + vp.get("xorigin", 0) + dx
    ay = py + vp.get("yorigin", 0) + dy
    nm = widget.get("Name", "?")
    p = path + "/" + str(nm)

    mats = []

    def collect_sm(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "Material" and isinstance(v, str):
                    mats.append(v)
                else:
                    collect_sm(v)
        elif isinstance(node, list):
            for v in node:
                collect_sm(v)

    if "StateMaterials" in widget:
        collect_sm(widget["StateMaterials"])
    if nm == "CivEmblem" or "CivEmblem" in mats:
        hits.append((p, ax, ay, w, h, mats[:4], widget.get("Type")))

    for child in widget.get("ChildWidgets") or []:
        if "Widget" in child:
            walk(child["Widget"], ax, ay, w or pw, h or ph, p)


for item in col.get("Widgets") or []:
    if "Widget" in item:
        walk(item["Widget"], ox, oy, cw, ch, "")

print("=== widgets named CivEmblem or using a CivEmblem material ===")
for p, ax, ay, w, h, mats, t in hits:
    print("  %s" % p)
    print("     type=%s abs=(%d,%d) %dx%d  materials=%s" % (t, ax, ay, w, h, mats))
    if w and h:
        print("     -> screenshot px: x %d..%d  y %d..%d   (center %d,%d)"
              % (int(ax * SX), int((ax + w) * SX), int(ay * SY), int((ay + h) * SY),
                 int((ax + w / 2) * SX), int((ay + h / 2) * SY)))

print()
print("=== resolution table check: how many widgets total, and where is the panel? ===")
print("  CivEmblem material in materials.json:")
mj = json.load(open(MATS, "r", encoding="utf-8"))
found = 0
for m in mj["Materials"]:
    md = m.get("MaterialDef", {})
    if md.get("Name") == "CivEmblem":
        print("   ", json.dumps(md))
        found += 1
print("   exact-name matches:", found)
