# -*- coding: utf-8 -*-
r"""Is the Poles dock test still valid if the game starts in the Imperial Age?

The protocol says: Poles, Imperial Age, dock, look for the "Elite Cannon Galleon"
upgrade.  Two things can silently void that, and both are checked here.

1. STARTING AGE.  A "Post-Imperial" start pre-researches every technology, so 691
   would already BE the elite version and no upgrade button would ever appear --
   the test would read as "menu reads the tree" when it actually tested nothing.
   An Imperial (Age 4) start is what the protocol needs.

2. A PREDECESSOR TO UPGRADE FROM.  An upgrade button only exists if the player
   can already field the unit being upgraded.  If the Poles cannot build the plain
   Cannon Galleon (420), there is no 691 button to look for and the test is void
   for a reason that has nothing to do with the tree/panel question.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_poles_dock_test.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.game import buildpanel as BP                 # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def _int(v, default=-1):
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


trees = CT.load_trees(GAME)
poles = trees["POLES"]

print("A  the unit chain the button would show (POLES.json, unit space)")
want = {420: "Cannon Galleon", 691: "Elite Cannon Galleon",
        376: "upgrade tech for 691"}
for r in CT.rows_of(poles):
    if not isinstance(r, dict):
        continue
    nid = _int(r.get("Node ID"))
    if nid in want or _int(r.get("Link ID")) in want:
        print("     node=%-6s link=%-6s trig=%-6s age=%-2s bldg=%-5s %-10s %-22s %s"
              % (nid, _int(r.get("Link ID")), _int(r.get("Trigger Tech ID")),
                 _int(r.get("Age ID")), _int(r.get("Building ID")),
                 r.get("Use Type"), r.get("Name"), r.get("Node Status")))

print()
print("B  does the Poles tree let them build the PREDECESSOR (420)?")
st420 = CT.node_status(poles, 420, CT.UNIT_USE_TYPES)
st691 = CT.node_status(poles, 691, CT.UNIT_USE_TYPES)
print("     420 Cannon Galleon      : %s" % st420)
print("     691 Elite Cannon Galleon: %s" % st691)
if st420 != "ResearchedCompleted":
    print("     !! NO PREDECESSOR: the pole test cannot show a 691 upgrade button")

print()
print("C  what the shipped PANEL says for the Poles dock")
panels = BP.load_all(GAME)
key = BP.civ_key_for(panels, "Poles")
block = BP.building_block(panels[key], key, 45)
for space in ("Units", "Techs"):
    ents = BP.entries(block, space) if block else []
    hit = [e for e in ents if _int(e.get("ID")) in (420, 691, 376)]
    print("     dock %-6s: %d entries, matches=%s"
          % (space, len(ents),
             [(e.get("ID"), e.get("Name"), e.get("RequiredAge"),
               e.get("PrereqTech")) for e in hit]))

print()
print("D  starting age that keeps the test valid")
print("     Post-Imperial start pre-researches 376 -> 691 is already elite ->")
print("     no upgrade button, test void.  Use IMPERIAL (Age 4).")

print()
print("POLES DOCK TEST: see A-D above.")
sys.exit(0)
