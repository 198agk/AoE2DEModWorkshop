"""Which row does `donor_row` pick, and is its BUILDING/AGE right for the RECEIVER?

Measured earlier: 48 of 238 tech nodes have rows that are not identical across
civilizations, and the fields that move are gameplay-bearing (`Building ID` 21
nodes, `Age ID` 20).  A grant copies the donor row wholesale, so a granted tech
inherits the donor's building and age.  The question this probe answers is not
"is the donor row consistent" (it is not) but:

    for the civilization RECEIVING the tech, does the donor's Building ID /
    Age ID actually appear among that civ's OWN tech rows?

If it does not, the granted tech is filed under a building that civ never shows
and in an age that civ's tree may not use -- i.e. the grant produces a row the
civ's own tech tree UI cannot place.  That is a different and worse failure than
"a decorative name differs".

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
TU = CT.TECH_USE_TYPES
# Node Status is the thing the grant is CHANGING; per-civ display strings are
# not what this probe is about.  Everything else is the row.
_IGNORE = ("Node Status",)


def sig(row, ignore=_IGNORE):
    return tuple(sorted((k, str(v)) for k, v in row.items() if k not in ignore))


def main():
    trees = CT.load_trees(GAME)
    civs = sorted(trees)
    print("civs: %d" % len(civs))

    # --- every tech node, its row variants, and the donor the kernel picks ---
    nodes = set()
    for c in civs:
        for r in CT.tech_rows(trees[c]):
            nodes.add(r.get("Node ID"))
    nodes = sorted(n for n in nodes if isinstance(n, int))
    print("tech nodes: %d" % len(nodes))

    multi = []          # nodes whose rows vary
    donor_vs_major = []  # donor row's variant != the majority variant
    for n in nodes:
        rows = []
        for c in civs:
            r = CT.row_for(trees[c], n, TU)
            if r is not None:
                rows.append((c, r))
        variants = collections.Counter(sig(r) for _c, r in rows)
        if len(variants) > 1:
            multi.append((n, variants))
        donor_civ, donor = CT.donor_row(trees, n, use_types=TU)
        if donor is None:
            continue
        if len(variants) > 1:
            top, _cnt = variants.most_common(1)[0]
            if sig(donor) != top:
                donor_vs_major.append((n, donor_civ, sig(donor) != top))

    print("nodes whose row varies across civs: %d of %d" % (len(multi), len(nodes)))
    print("of those, donor row != the most common variant: %d"
          % len(donor_vs_major))
    for n, c, _ in donor_vs_major[:15]:
        dr = CT.row_for(trees[c], n, TU)
        print("   node %-5d donor=%-14s Building ID=%-6s Age ID=%-4s Name=%r"
              % (n, c, dr.get("Building ID"), dr.get("Age ID"), dr.get("Name")))

    # --- the decisive measurement: is the donor's building/age in the
    #     RECEIVER's own repertoire? ---
    # For each civ that CANNOT get node n today, look at the row it would
    # receive and compare Building ID / Age ID against the values that civ
    # already uses on its own tech rows.
    print("\n--- receiver repertoire ---")
    bad_b, bad_a, tot = 0, 0, 0
    worst = []
    for n in nodes:
        donor_civ, donor = CT.donor_row(trees, n, use_types=TU)
        if donor is None:
            continue
        db = str(donor.get("Building ID"))
        da = str(donor.get("Age ID"))
        for c in civs:
            if CT.can_build(trees[c], n, TU):
                continue          # already has it; no grant would happen
            tot += 1
            mine = CT.tech_rows(trees[c])
            bs = {str(r.get("Building ID")) for r in mine}
            as_ = {str(r.get("Age ID")) for r in mine}
            if bs and db not in bs:
                bad_b += 1
                if len(worst) < 12:
                    worst.append((c, n, "Building", db, sorted(bs)[:6]))
            if as_ and da not in as_:
                bad_a += 1
    print("grants that would happen (civ x node): %d" % tot)
    print("  ... where the donor's Building ID is NOT among that civ's own: %d"
          % bad_b)
    print("  ... where the donor's Age ID     is NOT among that civ's own: %d"
          % bad_a)
    for c, n, what, val, mine in worst:
        print("   %-14s node %-5d %s=%-6s its own: %s" % (c, n, what, val, mine))

    # --- is a better donor available? ---
    # For each (civ, node) grant, is there a donor whose Building ID is in the
    # receiver's repertoire, i.e. would a different choice be more correct?
    print("\n--- could a better donor be found? ---")
    better = 0
    for n in nodes:
        for c in civs:
            if CT.can_build(trees[c], n, TU):
                continue
            mine = CT.tech_rows(trees[c])
            bs = {str(r.get("Building ID")) for r in mine}
            if not bs:
                continue
            cur_c, cur = CT.donor_row(trees, n, use_types=TU)
            if cur is None:
                continue
            if str(cur.get("Building ID")) in bs:
                continue          # current donor is already fine
            # search all able civs for one whose row fits better
            for other in civs:
                if not CT.can_build(trees[other], n, TU):
                    continue
                r = CT.row_for(trees[other], n, TU)
                if r is not None and str(r.get("Building ID")) in bs:
                    better += 1
                    break
    print("grants where swapping the donor would fix the Building ID: %d of %d"
          % (better, tot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
