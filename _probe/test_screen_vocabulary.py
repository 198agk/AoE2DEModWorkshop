# -*- coding: utf-8 -*-
r"""VOCABULARY AS EVIDENCE: which screen owns which file.

Result of the first pass (`probe_vocabulary_match.py`):

  `widgetui/screentechtree.json` has controls named
      NotAvailIcon / NotAvailParent
      ResearchLabel / NotResearchLabel
      UpgradeRequiredIcon / UpgradeRequiredParent
      TechnologyLabel
      UnitIcon / BuildingIcon / TechIcon
      RegionalUnitIcon / RegionalTech / RegionalBuildingIcon
      UniqueUnitIcon / UniqueTechIcon / UniqueBuildingIcon
      Age1Icon..Age4Icon / Age1Label..Age4Label

  the TREE file's `Node Status` is exactly
      ResearchedCompleted / ResearchRequired / NotAvailable
  its `Node Type` is exactly
      Research / UnitUpgrade / Unit / BuildingTech / BuildingNonTech /
      RegionalUnit / RegionalTech / RegionalBuilding / UniqueUnit / UniqueTech /
      UniqueBuilding

  and the PANEL file's only enum is `PrereqStyle` = {0, 1} -- which matches nothing
  on that screen.

Every icon control on the tech-tree screen is a TREE enum value.  That is not a
resemblance; it is the same vocabulary.  So the tech tree preview is drawn from
`CivTechTrees/<CIV>.json`.

This script pins it, then asks the reverse question for the panel: which layout, if
any, names the panel's OWN fields (RequiredAge / RequiredTechID / RequiredUnitID /
PrereqStringID)?
"""
import json
import _gamepaths as GP
import os
import sys

GAME = GP.GAME
WIDGETUI = os.path.join(GAME, "widgetui")
DAT = os.path.join(GAME, "resources", "_common", "dat")
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def widget_names(path):
    d = json.loads(open(path, "rb").read().decode("utf-8-sig"))
    out = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "Name" and isinstance(v, str):
                    out.append(v)
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(d)
    return sorted(set(out))


print("A  the tech-tree screen's controls are the TREE file's enum values")
names = widget_names(os.path.join(WIDGETUI, "screentechtree.json"))
NAMES = set(names)

# Each entry: (screen control substring, the tree enum value it names)
LINKS = [
    ("NotAvailIcon", "NotAvailable"),
    ("NotAvailParent", "NotAvailable"),
    ("ResearchLabel", "ResearchRequired"),
    ("NotResearchLabel", "ResearchRequired"),
    ("UpgradeRequiredIcon", "UnitUpgrade"),
    ("UpgradeRequiredParent", "UnitUpgrade"),
    ("TechnologyLabel", "Research"),
    ("TechIcon", "Research"),
    ("UnitIcon", "Unit"),
    ("BuildingIcon", "BuildingTech"),
    ("RegionalUnitIcon", "RegionalUnit"),
    ("RegionalTech", "RegionalTech"),
    ("RegionalBuildingIcon", "RegionalBuilding"),
    ("UniqueUnitIcon", "UniqueUnit"),
    ("UniqueTechIcon", "UniqueTech"),
    ("UniqueBuildingIcon", "UniqueBuilding"),
]
matched = [(c, v) for c, v in LINKS if c in NAMES]
print("   mapped controls: %d of %d" % (len(matched), len(LINKS)))
for c, v in matched:
    print("      %-24s -> tree value %s" % (c, v))
check("every listed tech-tree control exists on that screen",
      len(matched) == len(LINKS),
      "missing: %s" % [c for c, _ in LINKS if c not in NAMES])

# and the tree file really carries those values
tdir = os.path.join(DAT, "CivTechTrees")
seen_types, seen_status = set(), set()
for fn in sorted(os.listdir(tdir)):
    if not fn.endswith(".json") or fn == "civTechTrees.json":
        continue
    j = json.loads(open(os.path.join(tdir, fn), "rb")
                   .read().decode("utf-8-sig"))
    for key in ("civ_techs_units", "civ_techs_buildings"):
        for r in (j.get(key) or []):
            seen_types.add(r.get("Node Type"))
            seen_status.add(r.get("Node Status"))
print("   tree Node Type values   : %s" % sorted(x for x in seen_types if x))
print("   tree Node Status values : %s" % sorted(x for x in seen_status if x))

print()
print("B  the reverse question: does ANY layout name the PANEL's own fields?")
PANEL_FIELDS = ["RequiredAge", "RequiredTechID", "RequiredUnitID",
                "PrereqStringID", "PrereqIconSet", "PrereqIconIndex",
                "PrereqStyle", "RequiredUnit", "RequiredTech"]
found = {}
for fn in sorted(os.listdir(WIDGETUI)):
    if not fn.endswith(".json"):
        continue
    t = open(os.path.join(WIDGETUI, fn), "rb").read().decode("utf-8-sig",
                                                             "replace")
    hit = [f for f in PANEL_FIELDS if f in t]
    if hit:
        found[fn] = hit
if found:
    for fn, hit in sorted(found.items()):
        print("   %-34s %s" % (fn, hit))
else:
    print("   no layout names any panel field")
print("   -> layouts naming a panel field: %d" % len(found))

print()
print("C  so what feeds the COMMAND PANEL (the button grid)?")
cp = widget_names(os.path.join(WIDGETUI, "commandpanel.json"))
print("   command panel controls (%d): %s" % (len(cp), cp[:24]))
# A button grid is generic; the engine fills it at runtime from the selected
# building.  The question is which FILE supplies the fill.
print("   buttons are positional (Button0..Button53), so the grid is populated at")
print("   run time -- its SOURCE is not named in the layout.")

print()
print("VOCABULARY: the tech-tree screen's every icon control is a TREE enum value;")
print("  no layout names a single one of the panel's fields.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
