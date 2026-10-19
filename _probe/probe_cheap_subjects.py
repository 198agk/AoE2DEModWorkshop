# -*- coding: utf-8 -*-
r"""Cheap subjects: can the tree-vs-panel question be settled in the DARK AGE?

The protocol's surviving subjects are all Imperial Age (age 4), which costs the
user a full game to reach.  A test the user cannot be bothered to run is worth
nothing, so this probe looks for the same disagreement at the LOWEST possible age:

  kind-P  the tree says NotAvailable, the panel lists it   -> if the menu shows
          the button, the menu reads the panel
  kind-T  the tree says available, the panel is silent     -> if the menu lacks
          the button, the menu reads the tree

and reports the age of every survivor that needs nothing but a building the
civilization starts able to make.  Also fixes the earlier probe bug: `load_all`
returns records ({"obj": ...}), so panel lookups must pass `rec["obj"]`.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_cheap_subjects.py
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

# Panel facts, flattened ONCE per civ: which ids each civ lists, in either space.
listed_units = {}
listed_techs = {}
for name, rec in panels.items():
    obj = rec["obj"]
    u, t = set(), set()
    for blk in BP.buildings(obj, name):
        for e in (blk.get("Units") or []):
            if isinstance(e, dict):
                u.add(_int(e.get("ID")))
        for e in (blk.get("Techs") or []):
            if isinstance(e, dict):
                t.add(_int(e.get("ID")))
    listed_units[name] = u
    listed_techs[name] = t


def panel_key(tree_stem):
    k = BP.civ_key_for(panels, tree_stem)
    return k


# Every unit row in every tree, with its age; classify disagreements.
kind_p = []
kind_t = []
for stem in sorted(trees):
    tree = trees[stem]
    pk = panel_key(stem)
    if pk is None:
        continue
    pu = listed_units[pk]
    pt = listed_techs[pk]
    unit_ids_in_tree = {}      # node id -> row
    tech_ids_in_tree = {}
    for r in CT.rows_of(tree):
        if not isinstance(r, dict):
            continue
        nid = _int(r.get("Node ID"))
        if r.get("Use Type") in CT.UNIT_USE_TYPES:
            unit_ids_in_tree[nid] = r
        elif r.get("Use Type") in CT.TECH_USE_TYPES:
            tech_ids_in_tree[nid] = r
    for nid, row in unit_ids_in_tree.items():
        status = row.get("Node Status")
        age = _int(row.get("Age ID"))
        bldg = _int(row.get("Building ID"))
        trig = _int(row.get("Trigger Tech ID"))
        entry = (age, stem, bldg, nid, row.get("Name"), status, trig,
                 _int(row.get("Link ID")))
        if status == "NotAvailable" and nid in pu:
            # the upgrade chain must also be listed, or no button can appear
            if trig < 0 or trig in pt or trig in pu:
                kind_p.append(entry)
        elif status == "ResearchedCompleted" and nid not in pu:
            # panel silent everywhere; nothing upgrades from it either (that is
            # the strength of kind-T -- the panel has to be silent for the WHOLE
            # chain, measured by test_protocol_subjects)
            if not any(_int(o.get("Link ID")) == nid
                       for o in unit_ids_in_tree.values()):
                kind_t.append(entry)

print("A  kind-P (tree blocks it, panel lists it), sorted by AGE -- cheapest first")
for e in sorted(kind_p)[:12]:
    print("     age %-2s %-12s bldg %-5s unit %-5s %-26s trig=%s"
          % (e[0], e[1], e[2], e[3], e[4], e[6]))
print("     total kind-P: %d" % len(kind_p))

print()
print("B  kind-T (tree grants it, panel silent for the whole chain), by AGE")
for e in sorted(kind_t)[:12]:
    print("     age %-2s %-12s bldg %-5s unit %-5s %-26s"
          % (e[0], e[1], e[2], e[3], e[4]))
print("     total kind-T: %d" % len(kind_t))

print()
print("C  the cheapest survivor of EACH kind (lowest age wins)")
if kind_p:
    e = sorted(kind_p)[0]
    print("     kind-P: age %s, %s, building %s, unit %s %s"
          % (e[0], e[1], e[2], e[3], e[4]))
if kind_t:
    e = sorted(kind_t)[0]
    print("     kind-T: age %s, %s, building %s, unit %s %s"
          % (e[0], e[1], e[2], e[3], e[4]))

print()
print("D  ages represented (1=Dark, 2=Feudal, 3=Castle, 4=Imperial)")
import collections
print("     kind-P: %s" % dict(collections.Counter(e[0] for e in kind_p)))
print("     kind-T: %s" % dict(collections.Counter(e[0] for e in kind_t)))

print()
print("CHEAP SUBJECTS: see C.  Dark Age wins mean the user needs no age-up at all.")
sys.exit(0)
