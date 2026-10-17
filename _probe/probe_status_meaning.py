"""What do the three Node Status values actually MEAN for a unit row?

`has()` currently requires `ResearchedCompleted`, on the reasoning that
`ResearchRequired` is "reachable but not owned".  But Galley (21) is buildable by
every civ that has a Dock, and its row reads `ResearchRequired` for 56 civs --
so that rule would say nobody can build a Galley.

Either the rule is wrong, or the status means something other than "can build".
This probe decides it using units whose answer is already known:

  Galley / Fishing Ship  -> every civ with a Dock can build it
  Huskarl / Longbowman   -> exactly one civ can build it
  Villager               -> every civ has it
  Cannon Galleon         -> only some civs, and needs Chemistry

It cross-tabulates Node Status against Node Type, because a "UnitUpgrade" row
may be describing the upgrade CHAIN rather than buildability.
"""

import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

KNOWN = {
    21: "Galley (every dock civ)",
    13: "Fishing Ship (every dock civ)",
    83: "Villager (every civ)",
    4: "Archer (every civ)",
    41: "Huskarl (GOTHS only)",
    8: "Longbowman (BRITONS only)",
    755: "Tarkan (HUNS only)",
    420: "Cannon Galleon (some civs, needs Chemistry)",
    5: "Hand Cannoneer (some civs, needs Chemistry)",
    725: "Jaguar Warrior (AZTECS only)",
}


def main():
    tk = A.open_toolkit()
    tk._ensure()
    trees = tk._trees()

    print("=== status x node-type over ALL unit rows ===")
    ct = Counter()
    for t in trees.values():
        for r in CT.unit_rows(t):
            ct[(r.get("Node Type"), r.get("Node Status"))] += 1
    for k in sorted(ct, key=lambda x: (str(x[0]), str(x[1]))):
        print("  %-14s %-20s %d" % (k[0], k[1], ct[k]))

    print()
    print("=== known-answer units ===")
    for uid, label in sorted(KNOWN.items()):
        st = Counter()
        nt = Counter()
        for t in trees.values():
            for r in CT.unit_rows(t):
                if r.get("Node ID") == uid:
                    st[r.get("Node Status")] += 1
                    nt[r.get("Node Type")] += 1
        present = sum(st.values())
        print("  id %-5d %-42s rows=%-3d %s  types=%s"
              % (uid, label, present, dict(st), dict(nt)))

    print()
    print("=== which civs have NO Galley row (should be dock-less civs) ===")
    missing = [c for c, t in trees.items()
               if CT.row_for(t, 21) is None]
    print("  %d civs: %s" % (len(missing), missing))

    print()
    print("=== BRITONS: every unit row, in file order ===")
    for r in CT.unit_rows(trees["BRITONS"]):
        print("    NodeID=%-6s %-20s %-14s %s"
              % (r.get("Node ID"), str(r.get("Name"))[:20],
                 r.get("Node Type"), r.get("Node Status")))

    print()
    print("=== do any civs mark Galley NotAvailable? ===")
    na = [c for c, t in trees.items() if CT.node_status(t, 21) == "NotAvailable"]
    print("  %d civs: %s" % (len(na), na))
    print("=== do any civs mark Huskarl ResearchRequired? ===")
    rr = [c for c, t in trees.items() if CT.node_status(t, 41) == "ResearchRequired"]
    print("  %d civs: %s" % (len(rr), rr))
    return 0


if __name__ == "__main__":
    sys.exit(main())
