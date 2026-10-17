# -*- coding: utf-8 -*-
r"""Two decisive artifacts found while looking for the panel's consumer.

1. `widgetui/futuravailableunits.json` is a STUB whose own text says the file moved
   to `resources/_common/dat/`.  A redirect stub is placed BY THE ENGINE AUTHORS to
   keep an old path working -- which means something asked for the old path at some
   point, and the engine now reads the new one.  Read it verbatim.

2. `screentechtree.json` has exactly 59 widgets with names like `UnitIcon`,
   `BuildingIcon`, `RegionalUnitIcon`, `UniqueUnitIcon`, `TechnologyLabel`.  Those
   are the tech-tree SCREEN's controls.  If the tech tree is drawn from the tree
   FILE (`CivTechTrees/<CIV>.json`), while the panel file carries names like
   `RequiredAge` and `PrereqTech`, then the panel is the tech tree's data and the
   two files serve different screens.

Pin the stub's text, and list the tech-tree screen's controls, so the screen
question stops being a guess.
"""
import json
import os

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WIDGETUI = os.path.join(GAME, "widgetui")

p = os.path.join(WIDGETUI, "futuravailableunits.json")
with open(p, "rb") as fh:
    raw = fh.read()
print("A  %s  (%d B)" % (p, len(raw)))
print("   verbatim: %r" % raw)
print()

# the sibling that WOULD be the real data if the stub were meant to be replaced
for name in ("paphosfutureavailableunits.json", "futuravailableunits.json",
             "materials.json", "morematerials.json"):
    q = os.path.join(WIDGETUI, name)
    if os.path.isfile(q):
        with open(q, "rb") as fh:
            r = fh.read()
        note = ""
        if len(r) < 400:
            note = "  <- a stub: %r" % r
        print("   widgetui/%-34s %9d B%s" % (name, len(r), note))
print()

print("B  the tech-tree screen's own controls (widget names in screentechtree.json)")
d = json.loads(open(os.path.join(WIDGETUI, "screentechtree.json"),
                    "rb").read().decode("utf-8-sig"))
names = []


def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "Name" and isinstance(v, str):
                names.append(v)
            walk(v)
    elif isinstance(o, list):
        for x in o:
            walk(x)


walk(d)
for n in sorted(set(names)):
    print("   %s" % n)
print("   total distinct widget names: %d" % len(set(names)))
print()

print("C  for contrast: the command panel's controls")
d2 = json.loads(open(os.path.join(WIDGETUI, "commandpanel.json"),
                     "rb").read().decode("utf-8-sig"))
names2 = []
walk2 = walk
_names2 = []
def walk3(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "Name" and isinstance(v, str):
                _names2.append(v)
            walk3(v)
    elif isinstance(o, list):
        for x in o:
            walk3(x)
walk3(d2)
for n in sorted(set(_names2)):
    print("   %s" % n)
print("   total distinct widget names: %d" % len(set(_names2)))
