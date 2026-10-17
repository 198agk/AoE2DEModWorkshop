# -*- coding: utf-8 -*-
r"""Match the screen's STATE vocabulary against the two files' vocabularies.

`screentechtree.json` has controls named for states a tech-tree node can be in:

    NotAvailIcon / NotAvailParent
    NotResearchLabel / ResearchLabel
    UpgradeRequiredIcon / UpgradeRequiredParent
    TechnologyLabel
    RegionalTech / RegionalUnitIcon / RegionalBuildingIcon
    UniqueUnitIcon / UniqueBuildingIcon / UniqueTechIcon
    UnitIcon / BuildingIcon / TechIcon
    Age1Icon..Age4Icon / Age1Label..Age4Label

A screen is populated from whichever file speaks its vocabulary.  So compare:

  * the TREE file's `Node Status` values,
  * the PANEL file's `PrereqStyle` values (and any other small enum it carries),

against those control names.  Whichever file's enum matches the screen's names is
the file that drives it -- vocabulary is evidence, not a hint.
"""
import json
import os
from collections import Counter

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WIDGETUI = os.path.join(GAME, "widgetui")
DAT = os.path.join(GAME, "resources", "_common", "dat")

# --- the screen's state names -------------------------------------------------
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
names = sorted(set(names))
STATEW = [n for n in names
          if any(w in n for w in ("NotAvail", "Upgrade", "Research", "Label"))]
print("A  screentechtree.json state/label controls:")
for n in STATEW:
    print("   %s" % n)

# --- the TREE file's enum -----------------------------------------------------
trees = {}
tdir = os.path.join(DAT, "CivTechTrees")
for fn in sorted(os.listdir(tdir)):
    if fn.endswith(".json") and fn != "civTechTrees.json":
        j = json.loads(open(os.path.join(tdir, fn), "rb")
                       .read().decode("utf-8-sig"))
        trees[fn] = j

status = Counter()
usetype = Counter()
nodetype = Counter()
for fn, j in trees.items():
    for key in ("civ_techs_units", "civ_techs_buildings"):
        for r in (j.get(key) or []):
            status[r.get("Node Status")] += 1
            usetype[r.get("Use Type")] += 1
            nodetype[r.get("Node Type")] += 1
print()
print("B  TREE file enums (%d civ files)" % len(trees))
print("   Node Status : %s" % dict(status))
print("   Use Type    : %s" % dict(usetype))
print("   Node Type   : %s" % dict(sorted(nodetype.items(),
                                      key=lambda kv: -kv[1])[:14]))

# --- the PANEL file's enums ---------------------------------------------------
pj = json.loads(open(os.path.join(DAT, "futuravailableunits.json"), "rb")
                .read().decode("utf-8-sig"))
pk = Counter()
styles = Counter()
iconset = Counter()
keys = Counter()
n_entries = 0
for civ, blk in pj.items():
    if not isinstance(blk, dict):
        continue
    for b in (blk.get("Buildings") or []):
        for space in ("Units", "Techs"):
            for e in (b.get(space) or []):
                n_entries += 1
                for k in e:
                    keys[k] += 1
                if "PrereqStyle" in e:
                    styles[e["PrereqStyle"]] += 1
                if "PrereqIconSet" in e:
                    iconset[e["PrereqIconSet"]] += 1
print()
print("C  PANEL file enums (%d civs, %d entries)" % (len(pj), n_entries))
print("   entry keys  : %s" % dict(keys))
print("   PrereqStyle : %s" % dict(styles))
print("   PrereqIconSet: %s" % dict(iconset))

print()
print("D  verdict by vocabulary")
tree_words = set(str(s) for s in status)
panel_words = set(str(s) for s in styles)
screen_words = set(STATEW)
print("   tree statuses : %s" % sorted(tree_words))
print("   panel styles  : %s" % sorted(panel_words))
print("   screen names  : %s" % sorted(screen_words))
for label, words in (("TREE", tree_words), ("PANEL", panel_words)):
    overlap = {w for w in words
               if any(w.lower().replace("available", "avail").startswith(
                   s.lower()[:6]) for s in screen_words)}
    print("   %-5s status words echoed by the screen: %s" % (label, sorted(overlap)))
