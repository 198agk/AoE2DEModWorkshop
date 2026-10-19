# -*- coding: utf-8 -*-
r"""The exact Poles-the-Dock instruction: what each layer promises, side by side.

Everything the user has to do for the cheap test must be spelled out precisely,
so this prints, for POLES and building 45 (Dock):

  * every unit the TREE grants there, and every unit the PANEL lists there,
  * the same for the Techs space, so the upgrade arrow is accounted for,
  * and the specific disagreement (Cannon Galleon chain: 420 -> 691, tech 376).

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_poles_dock.py
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
tree = trees["POLES"]
pk = BP.civ_key_for(panels, "POLES")
obj = panels[pk]["obj"]

print("A  POLES tree, Dock(45), unit space")
tree_units = {}
for r in CT.rows_of(tree):
    if isinstance(r, dict) and _int(r.get("Building ID")) == 45 \
            and r.get("Use Type") in CT.UNIT_USE_TYPES:
        tree_units[_int(r.get("Node ID"))] = r
        print("     %-5s %-26s %-20s age=%s link=%s trig=%s"
              % (r.get("Node ID"), r.get("Name"), r.get("Node Status"),
                 r.get("Age ID"), r.get("Link ID"), r.get("Trigger Tech ID")))

print()
print("B  POLES tree, Dock(45), tech space")
tree_techs = {}
for r in CT.rows_of(tree):
    if isinstance(r, dict) and _int(r.get("Building ID")) == 45 \
            and r.get("Use Type") in CT.TECH_USE_TYPES:
        tree_techs[_int(r.get("Node ID"))] = r
        print("     %-5s %-26s %-20s age=%s"
              % (r.get("Node ID"), r.get("Name"), r.get("Node Status"),
                 r.get("Age ID")))

print()
print("C  POLES panel, Dock(45)")
blk = BP.building_block(obj, pk, 45)
if blk is None:
    print("     the panel gives POLES no Dock block at all")
else:
    pu = {_int(e.get("ID")): e for e in (blk.get("Units") or [])}
    pt = {_int(e.get("ID")): e for e in (blk.get("Techs") or [])}
    for k, e in sorted(pu.items()):
        print("     Unit %-5s %-26s RequiredAge=%s PrereqTech=%s"
              % (k, e.get("Name"), e.get("RequiredAge"), e.get("PrereqTech")))
    for k, e in sorted(pt.items()):
        print("     Tech %-5s %-26s RequiredAge=%s PrereqTech=%s"
              % (k, e.get("Name"), e.get("RequiredAge"), e.get("PrereqTech")))

print()
print("D  the disagreement, isolated")
print("     tree: Cannon Galleon (420)?  %s"
      % (420 in tree_units,))
for nid in (420, 691):
    r = tree_units.get(nid)
    print("     tree unit %-5s -> %s" % (nid, None if r is None else
                                        (r.get("Name"), r.get("Node Status"))))
print("     panel lists 691 Elite Cannon Galleon? %s" % (691 in pu))
print("     panel lists 420 Cannon Galleon?      %s" % (420 in pu))
print("     panel lists tech 376 (Elite upgrade)? %s" % (376 in pt))
print("     tree lists tech 376?                  %s" % (376 in tree_techs))
if 376 in pt:
    print("     panel tech 376 entry: %s"
          % {k: pt[376].get(k) for k in
             ("ID", "Name", "RequiredAge", "PrereqTech")})
sys.exit(0)
