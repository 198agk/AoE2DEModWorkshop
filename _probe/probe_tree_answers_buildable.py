"""Before calling the tech tree authoritative for "who can build X", check that
it actually ANSWERS that question for units whose answer we know.

Galley (21) is buildable by every civilization that has a Dock.  If the tree
reports 0 for it, the tree is not answering "who can build this unit" -- it is
answering something else, and treating it as authoritative would replace one
wrong answer with another.
"""

import os
import sys
from collections import Counter

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

    for uid, label in ((21, "Galley 战船"), (83, "Villager 村民"),
                       (4, "Archer 步弓手"), (41, "Huskarl 近卫军"),
                       (13, "Fishing Ship 渔船"), (420, "Cannon Galleon")):
        st = Counter()
        use = Counter()
        for civ, t in trees.items():
            for r in CT.unit_rows(t):
                if r.get("Node ID") == uid:
                    st[r.get("Node Status")] += 1
                    use[r.get("Use Type")] += 1
        print("id %-5d %-22s rows seen: %s   use: %s"
              % (uid, label, dict(st) or "NONE", dict(use) or "-"))
        # does ANY row mention it, whatever the use type?
        any_use = Counter()
        for civ, t in trees.items():
            for r in CT.rows_of(t):
                if r.get("Node ID") == uid:
                    any_use[r.get("Use Type")] += 1
        print("             any use type: %s" % (dict(any_use) or "NONE"))

    print()
    print("--- what does the Dock look like? ---")
    # Dock building id 45?  find rows whose Name mentions Dock
    for civ in ("BRITONS",):
        t = trees[civ]
        for r in CT.rows_of(t):
            nm = str(r.get("Name") or "")
            if "Dock" in nm or "Galley" in nm:
                print("  %-10s NodeID=%-6s Use=%-9s NodeType=%-10s Status=%s"
                      % (civ, r.get("Node ID"), r.get("Use Type"),
                         r.get("Node Type"), r.get("Node Status")))

    print()
    print("--- status histogram over ALL unit rows ---")
    hist = Counter()
    for t in trees.values():
        for r in CT.unit_rows(t):
            hist[r.get("Node Status")] += 1
    print(" ", dict(hist))
    print("--- how many civs list Galley(21) under ANY use type ---")
    n = sum(1 for t in trees.values()
            for r in CT.rows_of(t) if r.get("Node ID") == 21)
    print("  rows:", n, "of", len(trees), "civs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
