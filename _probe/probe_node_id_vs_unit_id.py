# -*- coding: utf-8 -*-
"""Is a CivTechTrees `Use Type: Unit` node id the same number as the .dat unit id?

This is the assumption every availability intent rests on: the user says "let the
Britons build the Huskarl", the UI resolves "Huskarl" to a .dat unit id (41), and
the tree layer then has to find the row for 41.  If the two id spaces are not the
same, that lookup silently finds nothing (or the wrong unit), and the whole
feature reports "no civilization has it" for units that plainly exist.

It cannot be assumed just because the five unique units happen to line up:
`Node ID` shares one integer space with tech nodes (see probe_nodeid_namespace),
and an id that is a valid unit in the .dat may also be a valid TECH node in the
same file.  So measure both directions:
  * every unit node id that is NOT a .dat unit id   -> cannot ever be granted
  * every .dat unit id that has no unit node anywhere -> cannot be addressed
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.dat import locate as L                              # noqa: E402
from aoe2mod.game import civtechtrees as CT                      # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    import aoe2mod.api as A
    tk = A.open_toolkit()
    tk._ensure()
    dat_unit_ids = set()
    for c in tk._civs:
        for u in c.get("units", []):
            dat_unit_ids.add(u.get("id"))

    trees = CT.load_trees(GAME)
    node_ids = set()
    unit_node_ids = set()
    for t in trees.values():
        for r in CT.rows_of(t):
            node_ids.add(r.get("Node ID"))
        for r in CT.unit_rows(t):
            unit_node_ids.add(r.get("Node ID"))

    print("dat unit ids          : %d" % len(dat_unit_ids))
    print("all node ids (any use): %d" % len(node_ids))
    print("unit-use node ids     : %d" % len(unit_node_ids))
    print()

    not_units = sorted(n for n in unit_node_ids if n not in dat_unit_ids)
    print("unit-use node ids that are NOT a .dat unit id: %d %s"
          % (len(not_units), not_units[:20]))
    print()

    # The reverse direction is the important one: how many units a user can pick
    # from the semantic index would have no row anywhere, i.e. a "let civ X build
    # Y" request that can never succeed no matter which civ is named.
    import aoe2mod.semantic.index as semantic
    ix = semantic.index()
    named_units = [e for e in ix.units.values() if e.resolved]
    unaddressable = sorted(e.id for e in named_units if e.id not in unit_node_ids)
    print("RESOLVED (named) units in the semantic index: %d" % len(named_units))
    print("  of those with NO unit node in any civ file: %d" % len(unaddressable))
    if unaddressable:
        sample = ", ".join("%d %s" % (i, ix.get("unit", i).display)
                           for i in unaddressable[:12])
        print("  sample: %s" % sample)
    print()

    # And the format that actually gets written: a unit node's Name String ID
    # resolves through the same string table the rest of the product uses.
    from aoe2mod.intent import compiler as C
    rows = CT.row_for(trees["BRITONS"], 41)
    print("BRITONS Huskarl row: %s" % (rows,))
    print()
    print("VERDICT: a unit node id IS the .dat unit id for %d ids; %d named units"
          % (len(unit_node_ids & dat_unit_ids), len(unaddressable)))
    print("are unaddressable and the intent must refuse them with that reason,")
    print("not with 'unknown unit'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
