# -*- coding: utf-8 -*-
r"""Is MUISCA even playable by this user?  And a systematic gate sweep.

Two questions:

1. `MUISCA` was recommended as GAME 1's civilization.  It is a late-DLC civ, and a
   player who does not own that DLC cannot pick it -- which would make the
   recommendation unusable for a reason none of the four gate classes covers.
   Check what the shipped data says about DLC ownership per civ.

2. The four gates were found one at a time, each after a wasted test.  Sweep EVERY
   field in both layers that could suppress a subject, and report which ones apply
   to the recommended pair.  A systematic sweep is what should have replaced
   discovering gates by losing experiments.
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
DAT = os.path.join(GAME, "resources", "_common", "dat")

print("A  what does civilizations.json say about the recommended civs?")
p = os.path.join(DAT, "civilizations.json")
obj = json.loads(open(p, "rb").read().decode("utf-8-sig"))
print("   top-level type: %s" % type(obj).__name__)
if isinstance(obj, dict):
    print("   top-level keys: %s" % sorted(obj)[:12])
    civs = obj.get("civilization_list") or obj
else:
    civs = obj
if isinstance(civs, dict):
    it = list(civs.values())
else:
    it = civs
print("   entries: %d" % len(it))
# `sorted(it[0])` fails when the entry is a dict -- sorted() on a dict yields its
# KEYS, but `sorted(it[0])` where it[0] is a dict is fine... unless it[0] is itself
# a list of dicts.  Ask for the keys directly instead of sorting the object.
_first = it[0] if it else None
print("   first entry type: %s" % type(_first).__name__)
if isinstance(_first, dict):
    print("   keys of the first entry: %s" % sorted(_first))
elif isinstance(_first, list):
    print("   first entry is a LIST of %d; first element keys: %s"
          % (len(_first), sorted(_first[0]) if _first
             and isinstance(_first[0], dict) else "?"))
print()
WANT = ("Muisca", "Mapuche", "Tupi", "Sicilians", "Spartans", "Puru", "Jurchens")
for name in WANT:
    hit = None
    for e in it:
        vals = [str(v) for v in e.values() if isinstance(v, (str, int, float))]
        if any(name.lower() in v.lower() for v in vals):
            hit = e
            break
    if hit is None:
        print("   %-12s NOT FOUND in civilizations.json" % name)
    else:
        keep = {k: v for k, v in hit.items()
                if k.lower() in ("name", "name_string_id", "era", "dlc",
                                 "dlc_name", "expansion", "id", "tech_tree_name",
                                 "unique_unit", "unique_tech")}
        print("   %-12s %s" % (name, keep))

print()
print("B  which tree civs have NO panel file coverage and no DLC hint?")
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
covered = set()
for _pk, rec in sorted(panels.items()):
    for k in rec["obj"]:
        if isinstance(k, str):
            covered.add(CT.civ_file_stem(k))
uncovered = sorted(set(trees) - covered)
print("   tree civs: %d   panel-covered (of those): %d   not covered: %d %s"
      % (len(trees), len(covered & set(trees)), len(uncovered), uncovered))

print()
print("C  SYSTEMATIC GATE SWEEP for the recommended pair")
# Every suppression mechanism found so far, in one place.
GATES = [
    ("age (RequiredAge)", "panel entry RequiredAge vs the age the user will be in"),
    ("research (PrereqTech)", "panel entry's PrereqTech must be reachable"),
    ("channel (Techs vs Units)", "the unit must not be named in the other array"),
    ("upgrade tech (Trigger Tech ID)", "the unit's own upgrade must be reachable "
                                       "in the layer that promises it"),
    ("building ownership", "the civ's tree must list the producing building"),
    ("display name", "the subject must have a zh/en name to be recognisable"),
    ("name collision", "the two subjects must not share a display name"),
]
print("   %-32s %s" % ("gate", "applies to"))
for g, note in GATES:
    print("   %-32s %s" % (g, note))

print()
print("D  the recommended pair, checked against every gate")
CHECKS = [
    ("MUISCA", "Muisca", 12, 359, 429, 4, "GAME 1"),
    ("SICILIANS", "Sicilians", 49, 588, 320, 4, "GAME 2"),
]
for stem, disp, bid, uid, tt, age, label in CHECKS:
    tree = trees[stem]
    pk = BP.panel_path_for(GAME, disp)[1]
    o = panels[pk]["obj"]
    b_e = BP.find_entry(o, disp, uid, BP.UNITS_KEY)[1]
    techs = set()
    units = set()
    for blk in BP.buildings(o, disp):
        if blk.get("ID") == bid:
            techs = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
            units = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
    own = {r.get("Node ID") for r in CT.rows_of(tree)
           if r.get("Use Type") == "Building"}
    row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
    print("   --- %s: %s / %s / unit %s ---" % (label, stem, disp, uid))
    print("      tree status        : %r" % CT.node_status(tree, uid,
                                                          CT.UNIT_USE_TYPES))
    print("      producing building : %s (tree owns it: %s)"
          % (bid, bid in own))
    print("      panel entry        : %r" % (b_e,))
    print("      panel RequiredAge  : %r   target age: %s"
          % ((b_e or {}).get("RequiredAge"), age))
    print("      panel PrereqTech   : %r"
          % ((b_e or {}).get("PrereqTech"),))
    print("      unit in panel Units: %s ; upgrade tech %s in panel Techs: %s"
          % (uid in units, tt, tt in techs))
    print("      tree upgrade tech  : %r"
          % (CT.node_status(tree, tt, CT.TECH_USE_TYPES) if tt else None))
    print("      display name       : %r"
          % ((b_e or {}).get("Name") or (row or {}).get("Name")))
    print("      row Prerequisite IDs: %r"
          % ((row or {}).get("Prerequisite IDs"),))
    print()
