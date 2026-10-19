# -*- coding: utf-8 -*-
r"""What does `Link ID` mean on a row whose `Use Type` is Tech?

`test_revoke_chain_closed` found 168 revocations whose dangling reference is a
`Tech` row: e.g. BURGUNDIANS has a Tech row 602 with `Link ID = 1699`, and
revoking the unit 1699 left that tech row pointing at nothing.

Before deciding whether the cascade must delete tech rows too, measure what the
relation actually is in the SHIPPED corpus:

  * do Tech rows carry `Link ID` at all, and how often?
  * when they do, does the id they point at belong to a Unit row or a Tech row?
  * is the pair (tech -> unit) explained by the tech being the unit's upgrade tech?

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_tech_link_id.py
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def _int(v, default=-1):
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


trees = CT.load_trees(GAME)

tech_rows = 0
tech_with_link = 0
link_target_kind = collections.Counter()
examples = []
for stem in sorted(trees):
    t = trees[stem]
    unit_ids = set()
    tech_ids = set()
    for r in CT.rows_of(t):
        if not isinstance(r, dict):
            continue
        if r.get("Use Type") in CT.UNIT_USE_TYPES:
            unit_ids.add(_int(r.get("Node ID"), -2))
        elif r.get("Use Type") in CT.TECH_USE_TYPES:
            tech_ids.add(_int(r.get("Node ID"), -2))
    for r in CT.rows_of(t):
        if not isinstance(r, dict) or r.get("Use Type") not in CT.TECH_USE_TYPES:
            continue
        tech_rows += 1
        link = _int(r.get("Link ID"))
        if link < 0:
            continue
        tech_with_link += 1
        if link in unit_ids:
            link_target_kind["unit"] += 1
            if len(examples) < 6:
                examples.append((stem, r.get("Node ID"), r.get("Name"), link))
        elif link in tech_ids:
            link_target_kind["tech"] += 1
        else:
            link_target_kind["NOTHING"] += 1

print("A  how often do Tech rows carry a Link ID?")
print("     tech rows total          : %d" % tech_rows)
print("     tech rows with a Link ID : %d" % tech_with_link)
print("     target kind              : %s" % dict(link_target_kind))

print()
print("B  examples (civ, tech node, tech name, the id it links to)")
for e in examples:
    print("     %-12s %-6s %-28s -> %s" % e)

print()
print("C  is the linked unit the tech's own subject?  (tech 602 = Burgundian "
      "unique tech?)")
t = trees["BURGUNDIANS"]
for r in CT.rows_of(t):
    if isinstance(r, dict) and _int(r.get("Node ID")) in (602, 1699):
        print("     %s" % {k: r.get(k) for k in
                          ("Node ID", "Link ID", "Name", "Use Type",
                           "Trigger Tech ID", "Node Status")})

print()
print("TECH LINK ID: tech rows do carry Link IDs pointing at units; a revoke")
print("that deletes a unit must therefore also close tech rows, or the tech row")
print("dangles.  Whether the corpus tolerates that is measured above.")
sys.exit(0)
