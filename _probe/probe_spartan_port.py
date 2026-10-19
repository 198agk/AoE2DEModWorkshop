# -*- coding: utf-8 -*-
r"""What is the Spartans' Port (2172) allowed to make, per each of the two layers?

`probe_spartan_fishing` showed the tree gives SPARTANS a building 2172 "Port"
that can make Fishing Ship (13) at Age 1, while the panel -- for every other
civilization -- puts 13 in the Dock (45).  Before offering this as a Dark Age
test, three things must be true:

  1. the Spartans' panel entry for 2172 is silent about 13 (the disagreement),
  2. 2172 is not simply a duplicate of the Dock (else the test measures the
     Dock's button grid, which the panel DOES fill),
  3. no upgrade chain around 13 can produce the button through the Techs channel.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_spartan_port.py
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
panels = BP.load_all(GAME)
sp = trees["SPARTANS"]
pk = BP.civ_key_for(panels, "SPARTANS")
obj = panels[pk]["obj"]

print("A  the Spartans' panel blocks around the Port")
for bid in (2171, 2172, 45):
    blk = BP.building_block(obj, pk, bid)
    if blk is None:
        print("     %s: ABSENT from the panel" % bid)
        continue
    print("     %s %r  Units=%s  Techs=%s"
          % (bid, blk.get("Name"),
             [(_int(e.get("ID")), e.get("Name")) for e in (blk.get("Units") or [])],
             [(_int(e.get("ID")), e.get("Name")) for e in (blk.get("Techs") or [])]))

print()
print("B  what the TREE says the Port can make (unit rows whose Building ID is 2172)")
for r in CT.rows_of(sp):
    if isinstance(r, dict) and _int(r.get("Building ID")) == 2172:
        print("     %-5s %-26s status=%-20s age=%s"
              % (r.get("Node ID"), r.get("Name"), r.get("Node Status"),
                 r.get("Age ID")))

print()
print("C  the tree's own building rows: is 2172 a Dock in disguise, or its own thing?")
for r in CT.rows_of(sp):
    if isinstance(r, dict) and _int(r.get("Node ID")) in (45, 2171, 2172):
        print("     %-5s %-26s status=%-20s age=%s use=%s"
              % (r.get("Node ID"), r.get("Name"), r.get("Node Status"),
                 r.get("Age ID"), r.get("Use Type")))

print()
print("D  where does unit 13 live in the TREE for a normal docked civ (Britons)?")
br = trees["BRITONS"]
for r in CT.rows_of(br):
    if isinstance(r, dict) and _int(r.get("Node ID")) == 13:
        print("     Britons: %s" % {k: r.get(k) for k in
                                    ("Node ID", "Name", "Node Status", "Age ID",
                                     "Building ID", "Link ID", "Trigger Tech ID")})

print()
print("E  upgrade chains touching 13 anywhere in the Spartans' tree")
for r in CT.rows_of(sp):
    if isinstance(r, dict) and (_int(r.get("Link ID")) == 13
                                or _int(r.get("Trigger Tech ID")) == 13):
        print("     %s" % {k: r.get(k) for k in
                          ("Node ID", "Name", "Link ID", "Trigger Tech ID",
                           "Use Type", "Building ID", "Node Status")})

print()
print("F  verdict inputs")
pport = BP.building_block(obj, pk, 2172)
port_units = set(_int(e.get("ID")) for e in (pport.get("Units") or [])) if pport else set()
port_techs = set(_int(e.get("ID")) for e in (pport.get("Techs") or [])) if pport else set()
print("     panel Port(2172) lists unit 13? %s" % (13 in port_units))
print("     panel Port(2172) Units: %s" % sorted(port_units))
print("     panel Port(2172) Techs: %s" % sorted(port_techs))
dock = BP.building_block(obj, pk, 45)
print("     panel Dock(45) exists? %s  Units: %s"
      % (dock is not None,
         sorted(_int(e.get("ID")) for e in (dock.get("Units") or [])) if dock else None))
sys.exit(0)
