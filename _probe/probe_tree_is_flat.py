"""Can the tree layer even BE the build panel?

Reinterprets the 2026-10-14 in-game result.  The tree rewrite did nothing while
the `.dat` in the same mod worked, and `linkedTechs.json` is overridden by three
working mods on this machine -- so DAT-adjacent JSON override is not broken in
general.  Two hypotheses remain:

  H1  the tree files ARE the build-panel gate, and the engine simply does not
      consult a mod's copy of that particular path;
  H2  the tree files are a different model (the tech-tree SCREEN's flat
      capability list), and the build panel reads something else -- which would
      explain the null result without any override bug.

A structural fact separates them.  The build panel is per BUILDING: you click a
Barracks and it lists what the Barracks makes.  So a build-panel model must not
claim a unit is available whose producing building the civ does not have.  This
probe counts, over every shipped tree, the rows that read ``ResearchedCompleted``
(a unit the civ "has") whose ``Building ID`` is NOT itself in that civ's tree --
either as a Node ID or as any row's own Building ID.

If that count is large, a tree row cannot mean "you can build this here", and H2
is supported.  If it is zero, the tree is internally consistent with a
per-building reading and H1 stays alive.

HONESTY: this is a STRUCTURAL argument about the shipped data, not an in-game
observation.  It cannot prove which file the panel reads.  The second smoke mod
(`_probe/build_smoke2_mod.py`, installed as prio 1 on 2026-10-14) tests the
other candidate directly.
"""

import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                                  # noqa: E402
from aoe2mod.game import civtechtrees as CT              # noqa: E402


def main():
    tk = A.open_toolkit()
    trees = CT.load_trees(tk.game_root)
    print("tree files: %d" % len(trees))

    total_rows = 0
    ready_rows = 0
    unreachable = []
    per_civ = collections.Counter()
    no_bldg_field = 0

    for civ in sorted(trees):
        tree = trees[civ]
        for row in CT.unit_rows(tree):
            total_rows += 1
            if row.get("Node Status") != "ResearchedCompleted":
                continue
            ready_rows += 1
            bid = row.get("Building ID")
            if bid is None:
                no_bldg_field += 1
                continue
            if not CT.reaches_building(tree, bid):
                unreachable.append((civ, row.get("Node ID"), bid,
                                    row.get("Name")))
                per_civ[civ] += 1

    print()
    print("unit rows: %d" % total_rows)
    print("  reading ResearchedCompleted (the civ 'has' it): %d" % ready_rows)
    print("  ...with no Building ID field: %d" % no_bldg_field)
    print("  ...whose producing building is NOT in that civ's own tree: %d"
          % len(unreachable))
    if ready_rows:
        print("  = %.1f%% of the civ's 'owned' units"
              % (100.0 * len(unreachable) / ready_rows))
    print()
    print("distinct civs affected: %d of %d" % (len(per_civ), len(trees)))
    if per_civ:
        print("most affected: %s" % per_civ.most_common(6))
    print()
    print("sample rows (civ, unit, building id, name):")
    for r in unreachable[:14]:
        print("   %-14s unit %-5s -> building %-6s %s" % r)

    print()
    print("=" * 74)
    if len(unreachable) > ready_rows * 0.05:
        print("VERDICT: a tree row CANNOT mean 'this civ can build this here'.")
        print("         %d of %d 'owned' units have no building to come out of,"
              % (len(unreachable), ready_rows))
        print("         so the tree is a flat capability list (H2), not the")
        print("         per-building build panel.  The null in-game result needs")
        print("         no override bug to be explained.")
    else:
        print("VERDICT: the tree is internally consistent with a per-building")
        print("         reading (H1 stays alive) -- only %d exception(s)."
              % len(unreachable))
    print()
    print("NOT PROVEN either way: which file the running game's build panel")
    print("reads.  That needs the second smoke mod's in-game result.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
