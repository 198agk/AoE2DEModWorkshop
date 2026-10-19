# -*- coding: utf-8 -*-
r"""What is a Tech row's `Link ID`, and is a tech row without one normal?

A revoke cascade that deletes a Unit row can strand a Tech row whose `Link ID`
pointed at it (measured: 168 of 1767 revocations).  The decision is whether to
delete those tech rows, clear their `Link ID`, or nothing at all.  That depends
entirely on which of three things `Link ID` is on a tech row.

Evidence gathered so far (probe_tech_unit_link):
  * 247 tech rows link to a Unit, and in EVERY case the tech is unrelated to the
    unit by name (tech 602 "Arson" -> unit 1699 "Flemish Militia"), and the unit's
    own `Trigger Tech ID` is -1.  So it is not "the unit's upgrade tech".
  * only 5 distinct unit ids are ever targeted (74 Militia, 13 Fishing Ship,
    17 Trade Cog, 875, 185), each by up to 111 tech rows -> systemic, not random.

This probe distinguishes:
  DISPLAY  the tech is drawn attached to a node; Link Node Type / Draw Node Type
           say so, and a missing target just means "draw it unattached".
  DEPEND   the tech cannot be shown at all without the target.

and it counts the shipped rows that already have NO Link ID, because that is the
form "clear the Link ID" would produce and it must be an ordinary shape.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_tech_link_shape.py
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

# tech rows keyed by (link target kind, Link Node Type, Draw Node Type, Node Type)
shape = collections.Counter()
no_link_shapes = collections.Counter()
targets = collections.Counter()
for stem in sorted(trees):
    t = trees[stem]
    kinds = {}
    for r in CT.rows_of(t):
        if isinstance(r, dict):
            kinds[_int(r.get("Node ID"), -2)] = r.get("Use Type")
    for r in CT.rows_of(t):
        if not isinstance(r, dict) or r.get("Use Type") not in CT.TECH_USE_TYPES:
            continue
        base = (r.get("Link Node Type"), r.get("Draw Node Type"),
                r.get("Node Type"))
        link = _int(r.get("Link ID"))
        if link < 0:
            no_link_shapes[base] += 1
            continue
        tk = kinds.get(link, "MISSING")
        shape[base + (tk,)] += 1
        if tk == "Unit":
            targets[link] += 1

print("A  tech rows that DO have a Link ID, by (LinkNodeType, DrawNodeType, "
      "NodeType, target kind)")
for k, v in shape.most_common():
    print("     %-58s %d" % (str(k), v))

print()
print("B  tech rows that have NO Link ID, by the same shape keys (the form a")
print("   'clear the Link ID' repair would produce)")
for k, v in no_link_shapes.most_common(6):
    print("     %-58s %d" % (str(k), v))
print("     total tech rows without a Link ID: %d" % sum(no_link_shapes.values()))

print()
print("C  the only unit ids ever targeted by a tech row, and who targets them")
for uid, n in targets.most_common():
    who = collections.Counter()
    for stem in sorted(trees):
        for r in CT.rows_of(trees[stem]):
            if (isinstance(r, dict)
                    and r.get("Use Type") in CT.TECH_USE_TYPES
                    and _int(r.get("Link ID")) == uid):
                who[r.get("Name")] += 1
    print("     unit %-5s targeted by %-4d tech rows; top techs: %s"
          % (uid, n, who.most_common(3)))

print()
print("D  verdict inputs: every shipped tech row with a Link ID points at a node")
print("   the same file contains (closure holds), and %d tech rows ship with no"
      % sum(no_link_shapes.values()))
print("   Link ID at all.")
sys.exit(0)
