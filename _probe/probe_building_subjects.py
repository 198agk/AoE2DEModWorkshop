# -*- coding: utf-8 -*-
r"""Can the tree-vs-panel question be settled by the BUILD menu, in the Dark Age?

The observation card has always framed the question as "which file drives the
button grid of the build menu".  Unit grids cost a game to reach (every kind-P
survivor is Age 4, i.e. Imperial).  Buildings are different: a House or a
Barracks is one click away in the Dark Age.

So this probe looks for BUILDING-space disagreements:

  kind-PB  tree says the building is NotAvailable, panel lists the building
  kind-TB  tree says the building is buildable, panel never lists the building

and flags the cheapest ones.  A caveat is printed too: the panel is a
"what does this building produce" file, so absence might mean "produces
nothing" rather than "cannot be built".  The probe measures how often the panel
omits buildings that obviously exist (House, Mill, Lumber Camp) to see whether
that caveat is fatal.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_building_subjects.py
"""
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.game import buildpanel as BP                 # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

# Buildings every civilization in the game can make from the Dark Age on.  If
# the panel omits these, then "absent from the panel" cannot mean "unbuildable".
SANITY = {70: "House", 68: "Mill", 562: "Lumber Camp", 584: "Mining Camp",
          12: "Barracks", 87: "Archery Range", 101: "Stable", 103: "Blacksmith",
          104: "Monastery", 109: "Town Center", 209: "University",
          234: "Castle", 276: "Wonder", 598: "Siege Workshop", 199: "Fish Trap"}


def _int(v, default=-1):
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

panel_buildings = {}
for name, rec in panels.items():
    obj = rec["obj"]
    panel_buildings[name] = {_int(b.get("ID")) for b in BP.buildings(obj, name)}


def _panel(civ):
    k = BP.civ_key_for(panels, civ)
    return (k, panel_buildings.get(k, set()))


print("A  sanity: does the panel list the buildings that obviously exist?")
sample = []
for civ in ("BRITONS", "FRANKS", "POLES", "SPARTANS"):
    k, ids = _panel(civ)
    missing = {bid: nm for bid, nm in SANITY.items() if bid not in ids}
    print("     %-9s panel key=%-10s buildings=%-3d missing obvious: %s"
          % (civ, k, len(ids), missing or "none"))
    sample.append((civ, k, ids))

print()
print("B  per-civilization count of tree BUILDING rows vs panel building blocks")
rows = []
for civ in sorted(trees):
    k, ids = _panel(civ)
    if k is None:
        continue
    tree_b = {}
    for r in CT.rows_of(trees[civ]):
        if isinstance(r, dict) and r.get("Use Type") == "Building":
            nid = _int(r.get("Node ID"))
            tree_b[nid] = (r.get("Node Status"), _int(r.get("Age ID")),
                           r.get("Name"))
    only_tree = sorted(n for n, (st, age, nm) in tree_b.items()
                       if st == "ResearchedCompleted" and n not in ids)
    only_panel = sorted(n for n in ids if n not in tree_b)
    rows.append((civ, len(tree_b), len(ids), len(only_tree), len(only_panel)))
for r in rows[:8]:
    print("     %-12s tree_b=%-3d panel_b=%-3d tree_only=%-3d panel_only=%-3d" % r)

print()
print("C  kind-TB candidates: tree grants the building, panel never lists it")
cand = []
for civ in sorted(trees):
    k, ids = _panel(civ)
    if k is None:
        continue
    for r in CT.rows_of(trees[civ]):
        if not isinstance(r, dict) or r.get("Use Type") != "Building":
            continue
        nid = _int(r.get("Node ID"))
        if r.get("Node Status") == "ResearchedCompleted" and nid not in ids:
            cand.append((_int(r.get("Age ID")), civ, nid, r.get("Name"), k))
cand.sort()
for c in cand[:20]:
    print("     age %-2s %-12s bldg %-5s %-26s (panel key %s)" % c)
print("     total kind-TB: %d   distinct buildings: %s"
      % (len(cand), dict(collections.Counter(c[2] for c in cand))))

print()
print("D  kind-PB candidates: tree says NotAvailable, panel lists the building")
cand2 = []
for civ in sorted(trees):
    k, ids = _panel(civ)
    if k is None:
        continue
    for r in CT.rows_of(trees[civ]):
        if not isinstance(r, dict) or r.get("Use Type") != "Building":
            continue
        nid = _int(r.get("Node ID"))
        if r.get("Node Status") == "NotAvailable" and nid in ids:
            cand2.append((_int(r.get("Age ID")), civ, nid, r.get("Name"), k))
cand2.sort()
for c in cand2[:20]:
    print("     age %-2s %-12s bldg %-5s %-26s (panel key %s)" % c)
print("     total kind-PB: %d" % len(cand2))

print()
print("E  cheapest per kind")
if cand:
    print("     kind-TB cheapest: age %s, %s, building %s %s"
          % (cand[0][0], cand[0][1], cand[0][2], cand[0][3]))
if cand2:
    print("     kind-PB cheapest: age %s, %s, building %s %s"
          % (cand2[0][0], cand2[0][1], cand2[0][2], cand2[0][3]))
sys.exit(0)
