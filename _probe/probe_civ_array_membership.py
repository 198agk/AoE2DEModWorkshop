"""Is a unit's membership in the civ's OWN .dat unit array the gate?

An earlier probe asked "is every tree row present in the civ's .dat array" and
the answer was always yes, which made membership look information-free.

That is the wrong question.  The civ unit arrays have DIFFERENT SIZES
(min 2164 Achaemenids, max 2693 Gaia), so membership genuinely varies.  The
question that matters is the converse one:

    for a unit some civs can build and others cannot,
    do the "can" civs contain it in their array and the "cannot" civs not?

Hand Cannoneer (unit 5) is the canonical case: 24 civs can build it, 38 cannot,
and the effect layer says all 63 have it enabled.

This probe reports the cross-tab of (membership, tree status) so the two
candidate gates are compared against each other rather than each against a
conclusion.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                     # noqa: E402
import aoe2mod.game.civtechtrees as CT      # noqa: E402

tk = A.open_toolkit()
tk._ensure()

civs = tk._civs
trees = tk._trees()

print("dat civs: %d" % len(civs))

sizes = [(len(c["units"]), c["name"]) for c in civs]
sizes.sort()
print("civ unit-array sizes: min %d (%s)  max %d (%s)"
      % (sizes[0][0], sizes[0][1], sizes[-1][0], sizes[-1][1]))

have = [set(u["id"] for u in c["units"]) for c in civs]
all_ids = set()
for s in have:
    all_ids |= s
print("distinct unit ids across all civs : %d" % len(all_ids))
print("ids in EVERY civ                  : %d" % sum(1 for i in all_ids if all(i in s for s in have)))
print("ids in SOME but not every civ     : %d" % sum(1 for i in all_ids if not all(i in s for s in have)))


def tree_status(civ_name, node_id):
    t = trees.get(CT.civ_file_stem(civ_name))
    return CT.node_status(t, node_id) if t else None


def tree_can(civ_name, node_id):
    t = trees.get(CT.civ_file_stem(civ_name))
    return CT.can_build(t, node_id) if t else False


def audit(unit_id, label):
    print()
    print("=== unit %d (%s) ===" % (unit_id, label))
    absent = [civs[i]["name"] for i in range(len(civs)) if unit_id not in have[i]]
    print("  present in own .dat array : %d civs" % (len(civs) - len(absent)))
    print("  ABSENT from own .dat array: %d civs %s" % (len(absent), absent[:14]))

    buckets = {}
    for i, c in enumerate(civs):
        key = (tree_status(c["name"], unit_id), unit_id in have[i])
        buckets.setdefault(key, []).append(c["name"])
    for (st, mem), names in sorted(buckets.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        print("  tree=%-18s in_dat=%-5s : %3d civs  %s"
              % (st, mem, len(names), names[:6]))

    agree = sum(1 for c in civs if (unit_id in have[list(civs).index(c)])
                == tree_can(c["name"], unit_id))
    print("  membership == tree.can_build : %d / %d" % (agree, len(civs)))


audit(5, "Hand Cannoneer")
audit(21, "War Galley")
audit(8, "Longbowman")
audit(83, "Villager")
