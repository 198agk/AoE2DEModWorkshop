"""Does describe() now answer "who can build this" with the tech-tree layer?

Runs the whole unit-node space and compares the new read-side field against the
layer directly, plus the known-answer units.  Before this change describe() had
no availability field at all and its `civ_count` (a .dat record count) was 63 for
every node including Huskarl, which exactly one civ can build.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

CASES = [
    (4, "Archer", "every civ"),
    (83, "Villager", "every civ"),
    (41, "Huskarl", "GOTHS only"),
    (8, "Longbowman", "BRITONS only"),
    (21, "War Galley", "56 dock civs, ResearchRequired"),
    (5, "Hand Cannoneer", "mixed statuses"),
]


def main():
    tk = A.open_toolkit()
    tk._ensure()
    trees = tk._trees()
    bad = 0

    print("=== known-answer units ===")
    for uid, label, note in CASES:
        d = tk.describe(uid)
        av = d.get("availability")
        print("  id %-5d %-16s %-34s holders=%-3s builders=%-3s absent=%-3s "
              "blocked=%-3s pending=%-3s"
              % (uid, label, note,
                 av["holder_count"] if av else "-",
                 av["builder_count"] if av else "-",
                 len(av["absent_from"]) if av else "-",
                 len(av["blocked_in"]) if av else "-",
                 len(av["pending_in"]) if av else "-"))

    print()
    print("=== whole node space vs the layer ===")
    nodes = sorted({r.get("Node ID") for t in trees.values()
                    for r in CT.unit_rows(t)})
    mism = 0
    for nid in nodes:
        d = tk.describe(nid)
        av = d.get("availability")
        want_b = CT.builders(trees, nid)
        want_h = CT.owners(trees, nid)
        if av is None:
            print("  id %d: describe has no availability but the layer does" % nid)
            mism += 1
            continue
        if av["builders"] != want_b or av["holders"] != want_h:
            mism += 1
            if mism < 6:
                print("  id %d mismatch: builders %d/%d holders %d/%d"
                      % (nid, len(av["builders"]), len(want_b),
                         len(av["holders"]), len(want_h)))
    print("  nodes %d   mismatches %d" % (len(nodes), mism))
    bad += mism

    print()
    print("=== the old instrument, for contrast ===")
    d = tk.describe(41)
    print("  Huskarl: .dat civ_count=%d  (records, not builders)  builders=%d"
          % (d["civ_count"], d["availability"]["builder_count"]))
    over = sum(1 for nid in nodes
               if tk.describe(nid).get("availability") is not None
               and tk.describe(nid)["civ_count"]
               != len(CT.builders(trees, nid)))
    print("  nodes where the .dat record count != builder count: %d of %d"
          % (over, len(nodes)))

    print()
    print("=== units in no tech tree at all ===")
    no_tree = [i for i in (1, 10, 12, 41) if tk.describe(i).get("availability")
               is None]
    print("  describe(%s) availability is None: %s" % (no_tree, True))

    print()
    if bad:
        print("READ-SIDE AVAILABILITY: %d MISMATCHES" % bad)
        return 1
    print("READ-SIDE AVAILABILITY: AGREES WITH THE LAYER ON ALL %d NODES"
          % len(nodes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
