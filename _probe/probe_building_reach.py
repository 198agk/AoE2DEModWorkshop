"""Is the donor's `Building ID` reachable from the RECEIVER, in both spaces?

`probe_tech_donor_fixable.py` measured the tech space: 292 of 10,369 grants file
the granted tech under a `Building ID` that appears nowhere in the receiving
civ's tree -- so its own tech-tree UI cannot place the row.  74 of those could be
fixed by a different donor choice; 277 (overlapping) are inherent to the data.

This does the same measurement for the UNIT space, because `Building ID` on a
unit row means "trained at", so an unreachable building means the granted unit
has no place to be produced.  If the unit space shows the same shape, the honest
product move is a WARNING, not a silent copy.

Read-only.  Prints measurements, asserts nothing.
"""
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def node_ids(nodes, rowfn, civs, trees):
    return sorted({r.get("Node ID") for c in civs for r in rowfn(trees[c])
                   if isinstance(r.get("Node ID"), int)})


def measure(label, use_types, rowfn):
    trees = CT.load_trees(GAME)
    civs = sorted(trees)
    nodes = node_ids(None, rowfn, civs, trees)

    # building ids this civ has anywhere in either list
    def its_buildings(civ):
        return {str(r.get("Node ID")) for r in CT.rows_of(trees[civ])
                if r.get("Use Type") == "Building"} | \
               {str(r.get("Building ID")) for r in rowfn(trees[civ])}

    unreachable = fixable = inherent = ok = nofield = 0
    samples = []
    for n in nodes:
        dc, donor = CT.donor_row(trees, n, use_types=use_types)
        if donor is None:
            continue
        db = donor.get("Building ID")
        if db is None:
            nofield += 1
            continue
        db = str(db)
        for civ in civs:
            if CT.can_build(trees[civ], n, use_types):
                continue
            mine = its_buildings(civ)
            if not mine or db in mine:
                ok += 1
                continue
            unreachable += 1
            if len(samples) < 8:
                samples.append((civ, n, db, CT.row_for(trees[dc], n, use_types).get("Name")))
            able = [c for c in civs if CT.can_build(trees[c], n, use_types)]
            if any(str((CT.row_for(trees[c], n, use_types) or {}).get("Building ID")) in mine
                   for c in able):
                fixable += 1
            else:
                inherent += 1

    tot = ok + unreachable
    print("\n=== %s space: %d grants ===" % (label, tot))
    print("  donor's Building ID reachable from the receiver : %d" % ok)
    print("  NOT reachable                                   : %d (%.2f%%)"
          % (unreachable, 100.0 * unreachable / max(1, tot)))
    print("      ... a different donor would reach it         : %d" % fixable)
    print("      ... no donor reaches it (inherent)           : %d" % inherent)
    print("  nodes whose donor row has no Building ID field  : %d" % nofield)
    for civ, n, db, name in samples:
        print("   %-14s node %-5d Building ID=%-6s (%r)" % (civ, n, db, name))


def main():
    measure("Unit", CT.UNIT_USE_TYPES, CT.unit_rows)
    measure("Tech", CT.TECH_USE_TYPES, CT.tech_rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
