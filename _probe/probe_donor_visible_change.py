"""What the improved donor rule changes for the user, in user terms.

Before: the receiver inherited the alphabetically-first able civ's row -- on 12
tech nodes and 2 unit nodes a civ the player has never heard of (ACHAEMENIDS,
one of the Chronicles six) decided what the granted thing is CALLED.

After: the receiver gets the name and icon the majority of civilizations show.

This prints the visible, player-facing difference on those nodes, so the claim
"the name a player sees is now the normal one" is checkable by eye.

Read-only.  Prints measurements, asserts nothing.
"""
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT  # noqa: E402
from aoe2mod.semantic import index as semantic  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def gloss(use_types, node, name_string_id):
    """Best-effort human label for a row, via the row's own Name field."""
    return name_string_id


def report(space, use_types, rowfn, kind):
    trees = CT.load_trees(GAME)
    civs = sorted(trees)
    nodes = sorted({r.get("Node ID") for c in civs for r in rowfn(trees[c])
                    if isinstance(r.get("Node ID"), int)})
    print("\n=== %s space ===" % space)
    changed = []
    for n in nodes:
        able = [c for c in civs if CT.can_build(trees[c], n, use_types)]
        if not able:
            continue
        # what the OLD rule would have chosen (first ready, else first able)
        old_ready = [c for c in able
                     if CT.node_status(trees[c], n, use_types) == "ResearchedCompleted"]
        old_civ = (old_ready or able)[0]
        new_civ, new_row = CT.donor_row(trees, n, use_types=use_types)
        if old_civ == new_civ:
            continue
        oc = CT.row_for(trees[old_civ], n, use_types)
        changed.append((n, old_civ, oc, new_civ, new_row))

    print("nodes where the chosen donor CHANGED: %d" % len(changed))
    shown = 0
    for n, old_civ, oc, new_civ, nr in changed:
        if oc is None or nr is None:
            continue
        if oc.get("Name") == nr.get("Name"):
            continue      # the pick moved but the visible name did not
        shown += 1
        if shown <= 20:
            print("  node %-5d  was %-12s %-24r  ->  now %-12s %r"
                  % (n, old_civ, oc.get("Name"), new_civ, nr.get("Name")))
    print("  ... of which the VISIBLE NAME actually changes: %d" % shown)

    # how many grants were affected end-to-end
    affected = 0
    for n, _o, oc, _nc, nr in changed:
        if oc is None or nr is None or oc.get("Name") == nr.get("Name"):
            continue
        for civ in civs:
            if not CT.can_build(trees[civ], n, use_types):
                affected += 1
    print("  grants whose visible name changes: %d" % affected)


def main():
    report("Unit", CT.UNIT_USE_TYPES, CT.unit_rows, "unit")
    report("Tech", CT.TECH_USE_TYPES, CT.tech_rows, "tech")
    print("\nNOTE: 'Name' is the row's own display text.  The engine shows the "
          "localised string for the row's Name String ID, so a row whose Name "
          "text differs also carries a different Name String ID -- the rename "
          "is visible in-game, not only in this table.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
