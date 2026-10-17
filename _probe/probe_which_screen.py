# -*- coding: utf-8 -*-
r"""What screen does the panel file feed?  Search the widgetui layouts for it.

Round 45 proved the panel is NOT the complete villager build menu (it omits the
Barracks, House, Mill and Lumber Camp for every civ).  Round 46 proved it is not a
pure projection of the `.dat` train locations either.  So what is it?

The panel's own shape says "producer building -> what that building makes".  Two
screens have that shape:

  * the **tech tree preview** (`widgetui/screentechtree.json`),
  * the **command panel** (`widgetui/commandpanel.json`) -- the button grid.

An earlier pass reported `RegionalUnit` appears in `screentechtree.json` (as
`RegionalUnitIcon` / `TTKeyRegionalUnit`) and **0 times** in `commandpanel.json`.
Look for the decisive link instead of a hint: does any layout name the FILE, or a
control whose data is per-producer-building?
"""
import json
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WIDGETUI = os.path.join(GAME, "widgetui")

NEEDLES = ["futuravailable", "futureavailable", "FutureAvailable",
           "availableunits", "AvailableUnits", "paphosfuture"]
print("A  does any widgetui layout NAME the panel file?")
hits = 0
for fn in sorted(os.listdir(WIDGETUI)):
    if not fn.endswith(".json"):
        continue
    p = os.path.join(WIDGETUI, fn)
    with open(p, "rb") as fh:
        t = fh.read().decode("utf-8-sig", "replace")
    for nd in NEEDLES:
        if nd in t:
            hits += 1
            i = t.find(nd)
            print("   %-34s %-18s ...%s..." % (fn, nd, t[max(0, i - 90):i + 90]
                                               .replace("\r\n", " ")))
print("   total lines naming it: %d" % hits)

print()
print("B  controls whose name suggests a producer-building display")
for fn in ("screentechtree.json", "commandpanel.json", "screencivtechtree.json"):
    p = os.path.join(WIDGETUI, fn)
    if not os.path.isfile(p):
        print("   %-32s (absent)" % fn)
        continue
    with open(p, "rb") as fh:
        t = fh.read().decode("utf-8-sig", "replace")
    print("   %-32s %7d B" % (fn, len(t)))
    for nd in ("RegionalUnit", "BuildingTech", "BuildingNonTech", "Node Type",
               "Use Type", "TrainLocation", "PrereqTech", "RequiredAge",
               "TechTreePreview", "CommandPanel"):
        n = t.count(nd)
        if n:
            print("        %-18s %d" % (nd, n))

print()
print("C  what a widget in screentechtree.json actually references")
p = os.path.join(WIDGETUI, "screentechtree.json")
d = json.loads(open(p, "rb").read().decode("utf-8-sig"))
names, materials, types = [], [], {}
def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "Name" and isinstance(v, str):
                names.append(v)
            elif k == "Material" and isinstance(v, str):
                materials.append(v)
            elif k == "Type" and isinstance(v, str):
                types[v] = types.get(v, 0) + 1
            walk(v)
    elif isinstance(o, list):
        for x in o:
            walk(x)
walk(d)
print("   widgets: %d   distinct names: %d" % (len(names), len(set(names))))
print("   widget types: %s" % sorted(types.items(), key=lambda kv: -kv[1])[:10])
print("   names mentioning tech/tree/unit/building:")
for n in sorted(set(names)):
    if re.search(r"tech|tree|unit|build", n, re.I):
        print("        %s" % n)
