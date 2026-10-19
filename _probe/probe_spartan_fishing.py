# -*- coding: utf-8 -*-
r"""The Spartans Fishing Ship: a DARK AGE test, if it is real.

`probe_cheap_subjects` found one kind-T survivor at age 1: SPARTANS, building
2172, unit 13 (Fishing Ship) -- the tree says the Spartans may build it, the
panel never lists it.  If that holds up, the user needs no age-up at all: start a
game, build whatever building 2172 is, look for the Fishing Ship button.

Everything here is a check that the test would not be void:

  * what IS building 2172, and can the Spartans actually build it at age 1?
  * is the unit's chain really silent in the panel (globally, not just in the
    building the tree names)?
  * does the tree row carry a Trigger Tech ID whose tech the panel names?  (If the
    upgrade tech is researchable from the panel, the button could appear through
    the Techs channel even with no unit row.)
  * is 13 the Dock's own Fishing Ship, or something else that merely shares the id?

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_spartan_fishing.py
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
sp = trees["SPARTANS"]
panels = BP.load_all(GAME)

print("A  the Spartans' rows for unit 13 and for building 2172 (unit space)")
for r in CT.rows_of(sp):
    if not isinstance(r, dict):
        continue
    if r.get("Use Type") in CT.UNIT_USE_TYPES and _int(r.get("Node ID")) == 13:
        print("     %s" % {k: r.get(k) for k in
                          ("Node ID", "Name", "Node Status", "Age ID",
                           "Building ID", "Trigger Tech ID", "Link ID")})
print("     anything upgrading from 13: %s"
      % [(r.get("Node ID"), r.get("Name")) for r in CT.rows_of(sp)
         if isinstance(r, dict) and _int(r.get("Link ID")) == 13])

print()
print("B  building 2172 in the Spartans' BUILDINGS space")
for r in CT.rows_of(sp):
    if not isinstance(r, dict):
        continue
    if r.get("Use Type") not in CT.UNIT_USE_TYPES and _int(r.get("Node ID")) == 2172:
        print("     %s" % {k: r.get(k) for k in
                          ("Node ID", "Name", "Node Status", "Age ID",
                           "Building ID", "Trigger Tech ID")})
b2172 = CT.row_for(sp, 2172, ("Building", "Tech"))
print("     row_for(2172, Building/Tech): %s"
      % (None if b2172 is None else b2172.get("Name")))

print()
print("C  is unit 13 silent in the WHOLE shipped panel, every civilization?")
hits = []
for name, rec in panels.items():
    obj = rec["obj"]
    for blk in BP.buildings(obj, name):
        for space in ("Units", "Techs"):
            for e in (blk.get(space) or []):
                if _int(e.get("ID")) == 13:
                    hits.append((name, blk.get("ID"), space))
print("     occurrences of id 13 anywhere in the panel: %d" % len(hits))
for h in hits[:10]:
    print("     %s" % (h,))

print()
print("D  what does the panel call building 2172 for the Spartans, and does the")
print("   panel list the Spartans at all?")
pk = BP.civ_key_for(panels, "SPARTANS")
print("     panel key: %r" % pk)
if pk:
    obj = panels[pk]["obj"]
    ids = sorted(_int(b.get("ID")) for b in BP.buildings(obj, pk))
    print("     building ids the panel gives the Spartans: %s" % ids)
    print("     does it include 2172? %s" % (2172 in ids))
    for b in BP.buildings(obj, pk):
        if _int(b.get("ID")) == 45:
            print("     Dock(45) Units: %s"
                  % [(_int(e.get('ID')), e.get('Name'))
                     for e in (b.get('Units') or [])])

print()
print("E  the honest risk: unit 13's real home is the Dock (45).  If the panel")
print("   lists the Spartans' Dock without a Fishing Ship, then the tree/panel")
print("   disagreement is genuinely about the MENU and the test is valid at age 1.")
sys.exit(0)
