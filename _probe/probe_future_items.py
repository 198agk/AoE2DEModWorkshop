# -*- coding: utf-8 -*-
r"""THE THIRD HYPOTHESIS: `futuravailableunits.json` is the FUTURE-ITEMS PREVIEW,
not the build menu.

Every framing so far has been binary -- "does the menu read the tree or the panel?"
But the file's own name says something narrower: **future** available units, and the
canvas has a UI option literally called `EnableFutureItemsDisplay` ("显示未来的物品",
string id 8898).  That is the AoE2 feature where a technology/unit you cannot build
yet is drawn as a GREYED-OUT icon.

If that is what this file is, the whole question dissolves:

    the MENU (what you can click)  <- the tree / the .dat
    the GREY PREVIEW               <- futuravailableunits.json

and the 11 kind-P pairs stop being contradictions: the panel legitimately lists
units the tree refuses, because listing "what you cannot have yet" is its job.

Evidence for it, all of which is checkable:

  A  the panel carries DISPLAY-ONLY fields (`PrereqTech`, `PrereqIconSet`,
     `PrereqIconIndex`, `PrereqStyle`, `PrereqStringID`) that a menu does not need
     and that the tree does not have -- they say "you need X", i.e. a preview.
  B  the panel omits the basic buildings every civ can build (already measured:
     Barracks/Mill/House/... in 0 of 62 civs), so it cannot be the construction
     menu.
  C  the option exists in `widgetui\screenoptions.json` with a default state.  If it
     defaults OFF, the user's test could not show any preview at all.
  D  the panel should be a SUPERSET of what the tree grants (current + future),
     whereas a menu source would match it closely.

Measure the direction of the mismatch and report what the option says.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

print("A  the display-only fields on panel entries")
KINDS = ("PrereqTech", "PrereqIconSet", "PrereqIconIndex", "PrereqStyle",
         "PrereqStringID", "RequiredUnitID", "RequiredAge")
seen = Counter()
total = 0
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        obj = rec["obj"]
        for blk in BP.buildings(obj, disp):
            for e in (blk.get(BP.UNITS_KEY) or []) + (blk.get(BP.TECHS_KEY) or []):
                total += 1
                for k in KINDS:
                    if k in e:
                        seen[k] += 1
print("   panel entries: %d" % total)
for k in KINDS:
    print("      %-18s present on %5d entries" % (k, seen[k]))
print("   -> the tree has NONE of these fields; they exist to say 'you need X'")

print()
print("B  does the tree carry the same display fields?")
tfields = Counter()
for t in trees.values():
    for r in CT.rows_of(t):
        for k in r:
            tfields[k] += 1
for k in KINDS:
    print("      %-18s in tree rows: %d" % (k, tfields.get(k, 0)))

print()
print("C  the screen option")
so = os.path.join(GAME, "widgetui", "screenoptions.json")
txt = open(so, "rb").read().decode("utf-8-sig", "replace")
obj = json.loads(txt)
found = []


def walk(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            if isinstance(v, str) and "future" in v.lower():
                found.append((path + "/" + k, v))
            walk(v, path + "/" + k)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            walk(v, "%s[%d]" % (path, i))
    elif isinstance(x, str) and "future" in x.lower():
        found.append((path, x))


walk(obj)
for p, v in found:
    print("   %s" % p)
    print("      %r" % v)

print()
print("D  the DIRECTION of the mismatch: is the panel a superset of the tree?")
# For every (civ, unit) pair: tree grant vs panel listing, across ALL buildings.
grant_only, panel_only, both = 0, 0, 0
rows = []
for stem, tree in sorted(trees.items()):
    disp = next((d for d in sorted(panels)
                 if CT.civ_file_stem(d) == stem), None)
    if disp is None:
        continue
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    listed = {e.get("ID") for blk in BP.buildings(obj, disp)
              for e in (blk.get(BP.UNITS_KEY) or [])}
    for r in CT.unit_rows(tree):
        uid = r.get("Node ID")
        if uid is None:
            continue
        ok = r.get("Node Status") in ("ResearchedCompleted", "ResearchRequired")
        inpanel = uid in listed
        if ok and inpanel:
            both += 1
        elif ok and not inpanel:
            grant_only += 1
        elif not ok and inpanel:
            panel_only += 1
        else:
            continue
        rows.append((stem, uid, r.get("Node Status"), inpanel))
print("   tree grants AND panel lists : %d" % both)
print("   tree grants, panel SILENT   : %d" % grant_only)
print("   tree REFUSES, panel lists   : %d" % panel_only)
print()
print("   A menu source would show panel_only near 0 (the menu must not offer")
print("   refused units).  A preview source shows panel_only large.")

print()
print("E  the refused-but-listed entries, grouped by the tree status")
c = Counter(r[2] for r in rows if not (r[2] in ("ResearchedCompleted",
                                               "ResearchRequired")) and r[3])
print("   %s" % dict(c))
print()
print("F  and the granted-but-silent ones -- which building do they sit in?")
silent = []
for stem, tree in sorted(trees.items()):
    disp = next((d for d in sorted(panels)
                 if CT.civ_file_stem(d) == stem), None)
    if disp is None:
        continue
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    listed = {e.get("ID") for blk in BP.buildings(obj, disp)
              for e in (blk.get(BP.UNITS_KEY) or [])}
    for r in CT.unit_rows(tree):
        uid = r.get("Node ID")
        if uid is None or uid in listed:
            continue
        if r.get("Node Status") not in ("ResearchedCompleted", "ResearchRequired"):
            continue
        silent.append((stem, uid, r.get("Building ID"), r.get("Node Status")))
print("   granted-but-silent: %d" % len(silent))
print("   by building: %s" % Counter(s[2] for s in silent).most_common(10))
print("   samples: %s" % silent[:12])
