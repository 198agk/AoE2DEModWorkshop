"""Compare donor-selection rules on the two things that reach the player.

`donor_row` currently picks `ready[0]` -- the alphabetically first civilization
that already has the tech.  That tiebreak was chosen for DETERMINISM, not for
meaning, and it is not neutral:

  * `ACHAEMENIDS` sorts first among the 62 and is a Chronicles civ, so it is the
    donor for 1,124 of 10,369 grants (10.8%), and Chronicles civs supply 27.8%.
  * node 45 is the loudest case: ACHAEMENIDS calls it **'Exorcism'**, the other
    56 civs call it **'Faith'**.  Granting node 45 hands the receiver a
    different VISIBLE NAME than the one the game shows its neighbours.
  * 292 grants file the tech under a `Building ID` absent from the receiver's
    tree (74 where another able civ would have fit).

So the rule is worth measuring rather than defending.  Three candidates:

  A. current   -- first able civ in sorted order (deterministic, meaningless)
  B. majority  -- the row variant the most civilizations use, then first civ
  C. majority+receiver -- majority variant, but prefer one whose Building ID is
                          in the RECEIVER's own tree; fall back to B

Criteria, over every (receiver civ x grantable node) pair the UI could offer:
  * NAME       -- is the granted `Name` what the majority of civs call it?
  * BUILDING   -- is the granted `Building ID` in the receiver's own tree?
                  (`absent` = unreachable, not merely mis-decorated)

Read-only.  Prints a comparison table, asserts nothing.
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


def rowkey(r):
    return tuple(sorted((k, str(v)) for k, v in r.items() if k != "Node Status"))


def pick_A(trees, able, node):
    """current rule: first sorted able civ (ready-first, as the kernel does)."""
    ready = [c for c in able
             if CT.node_status(trees[c], node, TU) == "ResearchedCompleted"]
    return (ready or able)[0]


def pick_B(trees, able, node):
    """majority row variant, then first civ that carries it."""
    cnt = collections.Counter(rowkey(CT.row_for(trees[c], node, TU)) for c in able)
    top = cnt.most_common(1)[0][0]
    for c in able:
        if rowkey(CT.row_for(trees[c], node, TU)) == top:
            return c
    return able[0]


def pick_C(trees, able, node, receiver):
    """majority variant, preferring rows whose Building ID the receiver has."""
    bs = {str(r.get("Building ID")) for r in CT.tech_rows(trees[receiver])}
    cnt = collections.Counter(rowkey(CT.row_for(trees[c], node, TU)) for c in able)
    order = [k for k, _n in cnt.most_common()]
    for k in order:
        for c in able:
            r = CT.row_for(trees[c], node, TU)
            if rowkey(r) == k and (not bs or str(r.get("Building ID")) in bs):
                return c
    return pick_B(trees, able, node)


def main():
    trees = CT.load_trees(GAME)
    civs = sorted(trees)
    nodes = sorted({r.get("Node ID") for c in civs
                    for r in CT.tech_rows(trees[c])
                    if isinstance(r.get("Node ID"), int)})

    # majority Name per node, over ALL civs (what a player would call it)
    maj_name = {}
    for n in nodes:
        rows = [CT.row_for(trees[c], n, TU) for c in civs]
        rows = [r for r in rows if r is not None]
        if rows:
            maj_name[n] = collections.Counter(r.get("Name") for r in rows).most_common(1)[0][0]

    stats = {k: collections.Counter() for k in "ABC"}
    donors = {k: set() for k in "ABC"}
    for n in nodes:
        able = [c for c in civs if CT.can_build(trees[c], n, TU)]
        if not able:
            continue
        global node
        node = n
        for civ in civs:
            if CT.can_build(trees[civ], n, TU):
                continue
            bs = {str(r.get("Building ID")) for r in CT.tech_rows(trees[civ])}
            for tag, picked in (("A", pick_A(trees, able, n)),
                                ("B", pick_B(trees, able, n)),
                                ("C", pick_C(trees, able, n, civ))):
                r = CT.row_for(trees[picked], n, TU)
                st = stats[tag]
                st["grants"] += 1
                if r.get("Name") != maj_name.get(n):
                    st["name_wrong"] += 1
                if bs and str(r.get("Building ID")) not in bs:
                    st["building_unreachable"] += 1
                st["_"] = 0
                donors[tag].add(picked)

    print("%-6s %-8s %-12s %-24s %s" % ("rule", "grants", "name-wrong",
                                        "building-unreachable", "donors-used"))
    for tag, label in (("A", "current"), ("B", "majority"), ("C", "maj+recv")):
        st = stats[tag]
        print("%-6s %-8d %-12d %-24d %d" % (
            tag, st["grants"], st["name_wrong"], st["building_unreachable"],
            len(donors[tag])))

    print("\ndistinct nodes whose majority Name differs from what ACHaemenids "
          "(the current favourite) would supply:")
    bad = [n for n in nodes
           if CT.row_for(trees["ACHAEMENIDS"], n, TU) is not None
           and CT.row_for(trees["ACHAEMENIDS"], n, TU).get("Name") != maj_name.get(n)]
    print("  %d: %s" % (len(bad), sorted(bad)[:20]))
    for n in sorted(bad)[:8]:
        print("   node %-5d ACHAEMENIDS=%-22r majority=%r"
              % (n, CT.row_for(trees["ACHAEMENIDS"], n, TU).get("Name"),
                 maj_name.get(n)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
