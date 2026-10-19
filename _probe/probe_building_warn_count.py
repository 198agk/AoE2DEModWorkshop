"""Count the receiver-aware Building ID warnings the SHIPPED grant() emits.

The docstring in `grant` cites how many grants get the new sentence. Those
numbers must come from the shipped predicate (`reaches_building`, which accepts
the id as a node id OR as a referenced Building ID), not from an earlier probe
that tested something slightly narrower.

Read-only.  Prints counts so the docstring and the docs can quote real numbers.
"""
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
#: The receiver-aware sentence's marker.  It was English until 2026-10-20; this
#: probe counts the sentences the SHIPPED `grant` emits, so the marker has to be
#: the shipped wording -- otherwise every count silently becomes zero, which
#: reads exactly like "the data has no such grants".
MARK = "科技树里根本没有这座建筑"


def main():
    trees = CT.load_trees(GAME)
    civs = sorted(trees)
    for label, ut, rowfn in (("Unit", CT.UNIT_USE_TYPES, CT.unit_rows),
                             ("Tech", CT.TECH_USE_TYPES, CT.tech_rows)):
        nodes = sorted({r.get("Node ID") for c in civs for r in rowfn(trees[c])
                        if isinstance(r.get("Node ID"), int)})
        grants = warned = 0
        by_civ = collections.Counter()
        ex = []
        for n in nodes:
            dc, donor = CT.donor_row(trees, n, use_types=ut)
            if donor is None:
                continue
            for civ in civs:
                if CT.can_build(trees[civ], n, ut):
                    continue
                grants += 1
                probe = {k: (list(v) if isinstance(v, list) else v)
                         for k, v in trees[civ].items()}
                probe.pop("path", None)
                _row, warns = CT.grant(probe, n, donor, use_types=ut)
                if any(MARK in w for w in warns):
                    warned += 1
                    by_civ[civ] += 1
                    if len(ex) < 5:
                        ex.append((civ, n, donor.get("Building ID"),
                                   donor.get("Name")))
        print("\n=== %s space ===" % label)
        print("  grants                    : %d" % grants)
        print("  with the new warning      : %d (%.2f%%)"
              % (warned, 100.0 * warned / max(1, grants)))
        print("  civs affected             : %d of %d"
              % (len(by_civ), len(civs)))
        print("  most affected             : %s" % by_civ.most_common(6))
        for civ, n, b, nm in ex:
            print("   %-14s node %-5d Building ID=%-6s (%r)" % (civ, n, b, nm))

    # the verified-by-hand case must warn
    n, civ = 775, "ARMENIANS"
    dc, donor = CT.donor_row(trees, n, use_types=CT.UNIT_USE_TYPES)
    probe = {k: (list(v) if isinstance(v, list) else v)
             for k, v in trees[civ].items()}
    probe.pop("path", None)
    _r, w = CT.grant(probe, n, donor, use_types=CT.UNIT_USE_TYPES)
    hit = [x for x in w if MARK in x]
    print("\nhand-verified case ARMENIANS node 775 (Missionary from SPANISH):")
    print("  warns: %s" % bool(hit))
    print("  %s" % hit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
