# -*- coding: utf-8 -*-
"""Are `Node ID`s a single namespace?  (The reader's own test says no.)

`test_civtechtrees.py` reported that Tarkan (755) appears to be owned by both
HUNS and BURGUNDIANS, and Berserk (692) by both VIKINGS and LITHUANIANS.  Both
are civ-exclusive units, so something is wrong -- and the first probe already
hinted at it: node id 8 (Longbowman) appeared as `Use Type: Unit` in ONE civ and
`Use Type: Tech` in 62.

So the hypothesis is that `Node ID` is not one namespace: the SAME integer is a
unit id in one row and a tech id in another, and only `Use Type` (or
`Node Type`) says which space a row is in -- exactly the trap `effect_rows`
already documents for the packed attribute ids 8/9.

This file prints the colliding rows so the fix is written against facts.
"""
import json
import os
import sys
from collections import defaultdict

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CT = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")


def main():
    interesting = {8: "Longbowman", 41: "Huskarl", 692: "Berserk",
                   755: "Tarkan", 725: "Jaguar", 83: "Villager", 4: "Archer"}
    for fn in sorted(os.listdir(CT)):
        with open(os.path.join(CT, fn), encoding="utf-8") as fh:
            j = json.load(fh)
        civ = fn[:-5]
        for e in j.get("civ_techs_units") or ():
            if not isinstance(e, dict):
                continue
            nid = e.get("Node ID")
            if nid in interesting:
                print("%-11s id=%-5s %-11s UseType=%-9s NodeType=%-16s status=%-20s Name=%s"
                      % (civ, nid, interesting[nid], e.get("Use Type"),
                         e.get("Node Type"), e.get("Node Status"), e.get("Name")))
        # done per file to keep output grouped
    print()
    print("=== does (Node ID) alone collide across Use Type? ===")
    collide = defaultdict(set)
    for fn in sorted(os.listdir(CT)):
        with open(os.path.join(CT, fn), encoding="utf-8") as fh:
            j = json.load(fh)
        for e in j.get("civ_techs_units") or ():
            if isinstance(e, dict) and e.get("Node ID") is not None:
                collide[e["Node ID"]].add(e.get("Use Type"))
    multi = {k: v for k, v in collide.items() if len(v) > 1}
    print("node ids appearing under more than one Use Type: %d" % len(multi))
    for k in sorted(multi)[:15]:
        print("   id %-5d -> %s" % (k, sorted(multi[k])))
    print()
    print("=== how many rows per Use Type, corpus-wide ===")
    ut = defaultdict(int)
    for fn in sorted(os.listdir(CT)):
        with open(os.path.join(CT, fn), encoding="utf-8") as fh:
            j = json.load(fh)
        for e in j.get("civ_techs_units") or ():
            if isinstance(e, dict):
                ut[e.get("Use Type")] += 1
    print("   %s" % dict(ut))
    return 0


if __name__ == "__main__":
    sys.exit(main())
