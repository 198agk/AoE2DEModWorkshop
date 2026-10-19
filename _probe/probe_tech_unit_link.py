# -*- coding: utf-8 -*-
r"""What IS the relation behind a Tech row whose `Link ID` points at a Unit?

Closure demands that no row links to a node the same file does not have.  Shipped
files obey that across BOTH use types (probe_broken_chain checked only Unit rows).
There are 247 shipped Tech->Unit links, so deleting a unit can strand one.

This probe tests the only two stories that would justify what to do about them:

  STORY A  the tech row IS that unit's upgrade tech.  Then the row exists to
           display the unit, and the unit's removal should take the row too.
           Test: does unit.`Trigger Tech ID` == tech.`Node ID`?

  STORY B  the Link ID is a display/position link with no dependency meaning.
           Test: the counts above would be scattered, with no trigger match.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_tech_unit_link.py
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

match = 0
mismatch = 0
samples = []
per_unit_tech = collections.Counter()

for stem in sorted(trees):
    t = trees[stem]
    units = {}
    for r in CT.rows_of(t):
        if isinstance(r, dict) and r.get("Use Type") in CT.UNIT_USE_TYPES:
            units[_int(r.get("Node ID"), -2)] = r
    for r in CT.rows_of(t):
        if not isinstance(r, dict) or r.get("Use Type") not in CT.TECH_USE_TYPES:
            continue
        link = _int(r.get("Link ID"))
        u = units.get(link)
        if u is None:
            continue
        tt = _int(u.get("Trigger Tech ID"))
        per_unit_tech[link] += 1
        if tt == _int(r.get("Node ID")):
            match += 1
        else:
            mismatch += 1
            if len(samples) < 8:
                samples.append((stem, r.get("Node ID"), r.get("Name"),
                                link, u.get("Name"), tt))

print("A  do Tech->Unit links mean 'this is that unit's upgrade tech'?")
print("     Trigger Tech ID matches the tech's Node ID : %d" % match)
print("     does not match                            : %d" % mismatch)
for s in samples:
    print("     %-11s tech %-5s %-26s -> unit %-5s %-22s trig=%s" % s)

print()
print("B  how many unit ids are the target of more than one tech row?")
multi = {k: v for k, v in per_unit_tech.items() if v > 1}
print("     units targeted once : %d" % sum(1 for v in per_unit_tech.values()
                                            if v == 1))
print("     units targeted 2+   : %d  e.g. %s"
      % (len(multi), list(multi.items())[:5]))

print()
print("C  the Burgundians case in full")
t = trees["BURGUNDIANS"]
for r in CT.rows_of(t):
    if isinstance(r, dict) and _int(r.get("Node ID")) == 602:
        print("     tech row 602 keys: %s" % dict(r))
for r in CT.rows_of(t):
    if isinstance(r, dict) and _int(r.get("Node ID")) == 1699:
        print("     unit row 1699 keys: %s" % dict(r))

print()
print("TECH->UNIT LINK: see counts above.  If match dominates, the tech row is")
print("the unit's own upgrade tech and must go with the unit; otherwise closure")
print("would have to delete an unrelated research entry.")
sys.exit(0)
