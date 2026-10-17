"""Does the READ side agree with the WRITE side about who can build what?

`unit.availability` (write) answers "can civ X build unit Y" from
`CivTechTrees/<CIV>.json` -- the layer the engine actually reads.  `describe()`
(read) reports `civ_count` from the `.dat` unit records instead, which is a
DIFFERENT question: the record exists for every civ, but the tech tree is what
decides whether the player can build it.

So a unit-detail panel driven by `describe()` tells the user "63 civilizations"
for a unit that exactly one civilization can build.  This probe measures how
far apart the two answers are, per unit, before anything is changed.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402


def main():
    tk = A.open_toolkit()
    tk._ensure()
    trees = tk._trees()
    print("tree files:", len(trees))

    # Every unit-use node id in the corpus is a .dat unit id (measured before),
    # so the two layers can be joined directly.
    nodes = set()
    for t in trees.values():
        for r in CT.unit_rows(t):
            nodes.add(r.get("Node ID"))
    print("distinct unit nodes:", len(nodes))

    # Which civs the WRITE side would grant/revoke for each node.
    buildable = {}
    for civ, t in trees.items():
        for r in CT.unit_rows(t):
            if r.get("Node Status") == "ResearchedCompleted":
                buildable.setdefault(r.get("Node ID"), set()).add(civ)

    disagree = 0
    worse = []
    for uid in sorted(nodes):
        if uid is None:
            continue
        d = tk.describe(uid, kind="unit")
        if not isinstance(d, dict) or d.get("kind") != "unit":
            continue
        record_civs = d.get("civ_count") or 0
        tree_civs = len(buildable.get(uid, ()))
        if record_civs != tree_civs:
            disagree += 1
            worse.append((uid, d.get("name"), record_civs, tree_civs))

    print()
    print("units whose describe() civ_count != the civs that can build it: %d"
          % disagree)
    worse.sort(key=lambda x: (x[2] - x[3]), reverse=True)
    for uid, name, rec, tree in worse[:15]:
        print("  id %-5d %-22s describe says %-3d  tech tree says %d"
              % (uid, name or "?", rec, tree))

    # The unit-detail panel is the thing a UI shows; how many descriptions are
    # silently misleading in the direction that MATTERS (telling the user they
    # have more options than they do)?
    over = [w for w in worse if w[2] > w[3]]
    print()
    print("OVER-REPORTING (says more civs than can build it): %d" % len(over))
    print("UNDER-REPORTING: %d" % (len(worse) - len(over)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
