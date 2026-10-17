"""Does the same donor bias exist in the UNIT space?

`probe_donor_rules.py` measured the tech space: the current rule (first able civ
in sorted order) hands the receiver a **different visible name** in 112 grants.
`donor_row` is ONE function serving both id spaces, so before changing its rule
I need to know whether the unit space has the same problem and whether the same
rule fixes it -- otherwise I would fix one space and silently move the other.

Same criteria, unit space (287 nodes, 3686 rows).

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
UU = CT.UNIT_USE_TYPES


def rowkey(r):
    return tuple(sorted((k, str(v)) for k, v in r.items() if k != "Node Status"))


def pick_A(trees, able, node):
    ready = [c for c in able
             if CT.node_status(trees[c], node, UU) == "ResearchedCompleted"]
    return (ready or able)[0]


def pick_B(trees, able, node):
    cnt = collections.Counter(rowkey(CT.row_for(trees[c], node, UU)) for c in able)
    top = cnt.most_common(1)[0][0]
    for c in able:
        if rowkey(CT.row_for(trees[c], node, UU)) == top:
            return c
    return able[0]


def main():
    trees = CT.load_trees(GAME)
    civs = sorted(trees)
    nodes = sorted({r.get("Node ID") for c in civs
                    for r in CT.unit_rows(trees[c])
                    if isinstance(r.get("Node ID"), int)})
    print("civs %d / unit nodes %d" % (len(civs), len(nodes)))

    # how many nodes even vary?
    vary = 0
    for n in nodes:
        keys = {rowkey(r) for c in civs
                for r in [CT.row_for(trees[c], n, UU)] if r is not None}
        if len(keys) > 1:
            vary += 1
    print("unit nodes whose row varies across civs: %d of %d" % (vary, len(nodes)))

    # majority Name per node
    maj = {}
    for n in nodes:
        rows = [CT.row_for(trees[c], n, UU) for c in civs]
        rows = [r for r in rows if r is not None]
        if rows:
            maj[n] = collections.Counter(r.get("Name") for r in rows).most_common(1)[0][0]

    stats = {k: collections.Counter() for k in "AB"}
    donors = {k: set() for k in "AB"}
    diff_picks = 0
    for n in nodes:
        able = [c for c in civs if CT.can_build(trees[c], n, UU)]
        if not able:
            continue
        a, b = pick_A(trees, able, n), pick_B(trees, able, n)
        if a != b:
            diff_picks += 1
        for civ in civs:
            if CT.can_build(trees[civ], n, UU):
                continue
            for tag, picked in (("A", a), ("B", b)):
                r = CT.row_for(trees[picked], n, UU)
                st = stats[tag]
                st["grants"] += 1
                if r.get("Name") != maj.get(n):
                    st["name_wrong"] += 1
                parents = str(r.get("Building upgraded from ID"))
                if parents not in ("None", "null", "-1", "0"):
                    st["has_upgrade_parent"] += 1
                donors[tag].add(picked)
        # count donors used

    print("\n%-4s %-8s %-12s %-20s %s"
          % ("rule", "grants", "name-wrong", "upgrade-parent", "donors-used"))
    for tag, label in (("A", "current"), ("B", "majority")):
        st = stats[tag]
        print("%-4s %-8d %-12d %-20d %d"
              % (tag, st["grants"], st["name_wrong"], st["has_upgrade_parent"],
                 len(donors[tag])))

    print("\nnodes where the two rules pick a different donor: %d" % diff_picks)
    print("\nunits whose majority Name differs from what the current pick "
          "(usually ACHAEMENIDS) supplies:")
    bad = []
    for n in nodes:
        able = [c for c in civs if CT.can_build(trees[c], n, UU)]
        if not able:
            continue
        a = pick_A(trees, able, n)
        ra = CT.row_for(trees[a], n, UU)
        if ra is not None and ra.get("Name") != maj.get(n):
            bad.append((n, a, ra.get("Name"), maj.get(n)))
    print("  %d" % len(bad))
    for n, c, got, want in bad[:15]:
        print("   node %-5d %-14s got=%-28r majority=%r" % (n, c, got, want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
