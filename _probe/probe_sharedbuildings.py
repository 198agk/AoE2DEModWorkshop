# -*- coding: utf-8 -*-
r"""If the panel is not the build menu, what is?  Try `sharedbuildings.json`.

The panel's `Builder` (118) block lists 18 buildings and omits 11 the civ can
definitely build -- Barracks (12), Mill (68), House (70), Palisade (72), Dock (45),
Lumber Camp (562), Mining Camp (584), Outpost (598), Palisade Gate (792),
Bombard Tower (236) -- and those 11 appear NOWHERE in that civilization's panel.
Britons can unquestionably build a Barracks.  So the panel cannot be the whole
build menu.

`resources/_common/dat/sharedbuildings.json` is the other per-civ building list
this project has catalogued (2,956 lines in the shipped file).  If it supplies the
missing 11, then the build menu is fed by MORE THAN the panel, and a write to the
panel alone cannot add or remove a basic building -- which is exactly the kind of
thing the product must know before promising "let the Britons build X".
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHARED = os.path.join(GAME, "resources", "_common", "dat", "sharedbuildings.json")

print("sharedbuildings.json exists: %s" % os.path.isfile(SHARED))
with open(SHARED, "rb") as fh:
    raw = fh.read()
print("size: %d B" % len(raw))
text = raw.decode("utf-8-sig")
obj = json.loads(text)
print("top-level type: %s" % type(obj).__name__)
if isinstance(obj, dict):
    keys = sorted(obj)
    print("top-level keys (%d): %s" % (len(keys), keys[:20]))
    k0 = keys[0]
    print()
    print("sample entry %r:" % k0)
    print(json.dumps(obj[k0], ensure_ascii=False)[:1200])
print()

print("=== does the .dat say what a villager can build, and is that the source? ===")
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
stem, disp = "BRITONS", "Britons"
tree = trees[stem]
obj_p = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
p118 = {e.get("ID") for e in (
    next(b for b in BP.buildings(obj_p, disp) if b.get("ID") == 118)
    .get(BP.UNITS_KEY) or [])}
trows = {r.get("Node ID"): r for r in CT.rows_of(tree)
         if r.get("Use Type") == "Building"}
missing = sorted(set(trows) - p118)
print("Britons buildings in the tree but NOT in the panel's Builder block:")
for b in missing:
    present_in_shared = None
    if isinstance(obj, dict):
        # look for the id anywhere in the shared structure
        s = json.dumps(obj, ensure_ascii=False)
        present_in_shared = ('"ID": %d' % b) in s or ('"%d"' % b) in s
    print("   %-6s %-22s Node Type=%-20s appears in sharedbuildings: %s"
          % (b, trows[b].get("Name"), trows[b].get("Node Type"),
             present_in_shared))
