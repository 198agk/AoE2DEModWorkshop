"""Check the explanation: the Chronicles six have their own DOCK building id.

`probe_building_reach.py` showed the donor's `Building ID` is unreachable from
the receiver on 1,659 unit grants and 253 tech grants, and NO donor choice fixes
it.  Every printed sample is one of the six Chronicles civilizations
(ACHAEMENIDS, ATHENIANS, MACEDONIANS, PURU, SPARTANS, THRACIANS) with
`Building ID=45`.  Earlier work already found those six are the odd ones out:
they are the only civs with no `Galley` row, because they have their own naval
line.

So the hypothesis is: `45` is the standard Dock; the Chronicles six use a
DIFFERENT building id for their dock, so a granted War Galley filed under 45 is
unreachable for them.  That makes the gap INHERENT to the data -- the honest
product move is a warning, not a cleverer donor rule.

Test: for each civ, what building ids do its tech rows use, and is 45 among them?
Then find what building node id 45 actually is in the standard civs.

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
CHRON = ("ACHAEMENIDS", "ATHENIANS", "MACEDONIANS", "PURU", "SPARTANS",
         "THRACIANS")


def main():
    trees = CT.load_trees(GAME)
    civs = sorted(trees)

    print("=== which civs have building node 45 in their tree? ===")
    has45 = [c for c in civs
             if any(str(r.get("Node ID")) == "45" for r in CT.rows_of(trees[c]))]
    ref45 = [c for c in civs
             if any(str(r.get("Building ID")) == "45"
                    for r in CT.unit_rows(trees[c]))]
    print("  node 45 present as a row      : %d civs" % len(has45))
    print("  ... of the Chronicles six     : %s"
          % [c for c in CHRON if c in has45])
    print("  used as a Building ID by      : %d civs" % len(ref45))
    print("  ... of the Chronicles six     : %s"
          % [c for c in CHRON if c in ref45])

    print("\n=== the Chronicles six: what building ids do their rows use? ===")
    for c in CHRON[:3]:
        ids = collections.Counter(str(r.get("Building ID"))
                                  for r in CT.unit_rows(trees[c]))
        print("  %-14s Building IDs: %s" % (c, sorted(ids)[:14]))
    print("  --- for comparison ---")
    for c in ("BRITONS", "FRANKS", "GOTHS"):
        ids = collections.Counter(str(r.get("Building ID"))
                                  for r in CT.unit_rows(trees[c]))
        print("  %-14s Building IDs: %s" % (c, sorted(ids)[:14]))

    print("\n=== what unit is filed under Building ID 45 in a standard civ? ===")
    for c in ("BRITONS",):
        rows = [r for r in CT.unit_rows(trees[c])
                if str(r.get("Building ID")) == "45"]
        print("  %s has %d rows with Building ID 45: %s"
              % (c, len(rows), [r.get("Name") for r in rows][:12]))

    print("\n=== does the Chronicles six use a different id for its dock? ===")
    # a dock trains Fishing Ship / Galley / Trade Cog; see where those sit
    for c in ("BRITONS",) + CHRON[:2]:
        finding = {}
        for r in CT.unit_rows(trees[c]):
            nm = r.get("Name")
            if nm in ("Trade Cog", "War Galley", "Fishing Ship", "Galley",
                      "Fire Ship", "Transport Ship"):
                finding.setdefault(nm, set()).add(str(r.get("Building ID")))
        print("  %-14s %s" % (c, {k: sorted(v) for k, v in sorted(finding.items())}))

    print("\n=== so: is the unreachable Building ID always a Chronicles civ? ===")
    uu = CT.UNIT_USE_TYPES
    nodes = sorted({r.get("Node ID") for c in civs for r in CT.unit_rows(trees[c])
                    if isinstance(r.get("Node ID"), int)})

    def its_buildings(civ):
        return {str(r.get("Node ID")) for r in CT.rows_of(trees[civ])} | \
               {str(r.get("Building ID")) for r in CT.unit_rows(trees[civ])}

    by_civ = collections.Counter()
    total = 0
    for n in nodes:
        dc, donor = CT.donor_row(trees, n, use_types=uu)
        if donor is None:
            continue
        db = str(donor.get("Building ID"))
        for civ in civs:
            if CT.can_build(trees[civ], n, uu):
                continue
            mine = its_buildings(civ)
            if mine and db not in mine:
                total += 1
                by_civ[civ] += 1
    print("  unreachable total: %d" % total)
    print("  by civ: %s" % by_civ.most_common(12))
    chron = sum(by_civ[c] for c in CHRON)
    print("  ... in the Chronicles six: %d (%.1f%%)"
          % (chron, 100.0 * chron / max(1, total)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
