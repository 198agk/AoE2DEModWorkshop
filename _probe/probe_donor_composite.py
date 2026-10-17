"""Does the majority rule survive the existing status preference?

`pick_B` in probe_donor_rules.py ignored status entirely, but `donor_row`
currently prefers a `ResearchedCompleted` donor over a `ResearchRequired` one,
and `test_civtechtrees_writer.py` asserts that preference on a synthetic case
(A=ResearchRequired, B=ResearchedCompleted -> B).

So the real candidate rule is a COMPOSITE:
    rank1 = status (ResearchedCompleted before ResearchRequired)
    rank2 = row-variant frequency (most civilizations' variant first)
    rank3 = civ name (determinism)

The risk: if ACHAEMENIDS is `ResearchedCompleted` on the nodes in question, a
status-first rule keeps picking it and the majority tiebreak never fires --
the "fix" would be dead code.  Measure before writing it.

Also reports whether the status preference is INHERITED at all: `grant` writes
`Node Status` explicitly, so the donor's own status is not copied.  If it is not
copied, preferring a ready donor is a tiebreak about the row's provenance, not
about what the receiver gets.

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


def rowkey(r):
    return tuple(sorted((k, str(v)) for k, v in r.items() if k != "Node Status"))


def measure(space, use_types):
    trees = CT.load_trees(GAME)
    civs = sorted(trees)
    if use_types == CT.UNIT_USE_TYPES:
        nodes = sorted({r.get("Node ID") for c in civs
                        for r in CT.unit_rows(trees[c])
                        if isinstance(r.get("Node ID"), int)})
    else:
        nodes = sorted({r.get("Node ID") for c in civs
                        for r in CT.tech_rows(trees[c])
                        if isinstance(r.get("Node ID"), int)})

    maj = {}
    for n in nodes:
        rows = [CT.row_for(trees[c], n, use_types) for c in civs]
        rows = [r for r in rows if r is not None]
        if rows:
            maj[n] = collections.Counter(
                r.get("Name") for r in rows).most_common(1)[0][0]

    def pick_status_first(able, n):
        ready = [c for c in able
                 if CT.node_status(trees[c], n, use_types) == "ResearchedCompleted"]
        return (ready or able)[0]

    def pick_composite(able, n):
        # rank1 status, rank2 majority variant, rank3 name
        cnt = collections.Counter(rowkey(CT.row_for(trees[c], n, use_types))
                                  for c in able)
        freq = {k: c for k, c in cnt.items()}
        def key(c):
            r = CT.row_for(trees[c], n, use_types)
            st = 0 if CT.node_status(trees[c], n, use_types) == "ResearchedCompleted" else 1
            return (st, -freq[rowkey(r)], c)
        return sorted(able, key=key)[0]

    res = {}
    for label, fn in (("status-first", pick_status_first),
                      ("composite", pick_composite)):
        wrong = 0
        grants = 0
        used = set()
        for n in nodes:
            able = [c for c in civs if CT.can_build(trees[c], n, use_types)]
            if not able:
                continue
            picked = fn(able, n)
            used.add(picked)
            r = CT.row_for(trees[picked], n, use_types)
            for civ in civs:
                if CT.can_build(trees[civ], n, use_types):
                    continue
                grants += 1
                if r.get("Name") != maj.get(n):
                    wrong += 1
        res[label] = (grants, wrong, len(used))
        print("%-8s space=%-4s grants=%-7d name-wrong=%-5d donors-used=%d"
              % (label, space, grants, wrong, len(used)))
    return res


def main():
    print("=== name mismatch vs the majority variant ===")
    u = measure("Unit", CT.UNIT_USE_TYPES)
    t = measure("Tech", CT.TECH_USE_TYPES)

    print("\n=== how often is the status preference even able to matter? ===")
    trees = CT.load_trees(GAME)
    civs = sorted(trees)
    for space, ut, nodefn in (("Unit", CT.UNIT_USE_TYPES, CT.unit_rows),
                              ("Tech", CT.TECH_USE_TYPES, CT.tech_rows)):
        nodes = sorted({r.get("Node ID") for c in civs for r in nodefn(trees[c])
                        if isinstance(r.get("Node ID"), int)})
        mixed = 0
        for n in nodes:
            able = [c for c in civs if CT.can_build(trees[c], n, ut)]
            if len(able) < 2:
                continue
            sts = {CT.node_status(trees[c], n, ut) for c in able}
            if len(sts) > 1:
                mixed += 1
        print("  %s: nodes where able civs DISAGREE on status: %d" % (space, mixed))

    print("\n=== is the donor's status inherited by grant()? ===")
    print("  grant() sets row['Node Status'] = status explicitly -> NOT inherited")
    print("  so the status preference only chooses WHICH row is copied, not")
    print("  what status the receiver ends up with")
    return 0


if __name__ == "__main__":
    sys.exit(main())
