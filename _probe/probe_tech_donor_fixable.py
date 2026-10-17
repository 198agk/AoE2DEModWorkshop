"""Is a receiver-compatible donor always AVAILABLE, or is the gap inherent?

`probe_tech_donor_bias.py` showed 292 grants where the donor's `Building ID` is
absent from the receiving civ's tree -- i.e. the granted tech would be filed
under a building that civ cannot reach, so the grant produces a row its own tech
tree UI cannot place.  That is gameplay-bearing, not decorative.

Before calling it a defect to fix, measure whether a BETTER CHOICE EXISTS.  If
some able civ's row fits the receiver, the rule is at fault and `donor_row`
should be told who the receiver is.  If no able civ fits, the gap is inherent to
the data and the honest product answer is a warning, not a fix.

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


def main():
    trees = CT.load_trees(GAME)
    civs = sorted(trees)
    nodes = sorted({r.get("Node ID") for c in civs
                    for r in CT.tech_rows(trees[c])
                    if isinstance(r.get("Node ID"), int)})

    # For every grant the UI can offer, is there ANY able donor whose row fits?
    fixable = inherent = already_ok = 0
    inherent_nodes = collections.Counter()
    fit_by_majority = 0
    for n in nodes:
        able = [c for c in civs if CT.can_build(trees[c], n, TU)]
        if not able:
            continue
        for civ in civs:
            if CT.can_build(trees[civ], n, TU):
                continue
            bs = {str(r.get("Building ID")) for r in CT.tech_rows(trees[civ])}
            if not bs:
                continue
            cur_c, cur = CT.donor_row(trees, n, use_types=TU)
            if cur is not None and str(cur.get("Building ID")) in bs:
                already_ok += 1
                continue
            fits = [c for c in able
                    if str((CT.row_for(trees[c], n, TU) or {}).get("Building ID"))
                    in bs]
            if fits:
                fixable += 1
            else:
                inherent += 1
                inherent_nodes[n] += 1
    tot = fixable + inherent + already_ok
    print("grants: %d" % tot)
    print("  donor already fits the receiver                     : %d" % already_ok)
    print("  a DIFFERENT able civ fits -> the RULE is at fault   : %d" % fixable)
    print("  NO able civ fits -> inherent to the data            : %d" % inherent)
    print("\nnodes where the gap is inherent (top 12): %s"
          % inherent_nodes.most_common(12))
    print("distinct nodes affected inherently: %d" % len(inherent_nodes))

    # Same question for the RECEIVER-AWARE rule: how many nodes would it even
    # help on, and does choosing per-receiver break determinism?
    print("\n--- what a receiver-aware rule would change ---")
    changed = 0
    for n in nodes:
        able = [c for c in civs if CT.can_build(trees[c], n, TU)]
        if not able:
            continue
        for civ in civs:
            if CT.can_build(trees[civ], n, TU):
                continue
            bs = {str(r.get("Building ID")) for r in CT.tech_rows(trees[civ])}
            if not bs:
                continue
            cur_c, cur = CT.donor_row(trees, n, use_types=TU)
            if cur is None:
                continue
            picks = [c for c in able
                     if str((CT.row_for(trees[c], n, TU) or {}).get("Building ID"))
                     in bs]
            best = picks[0] if picks else cur_c
            if best != cur_c:
                changed += 1
    print("grants where a receiver-aware rule picks a different donor: %d"
          % changed)

    # --- does the majority variant track the receiver better? ---
    print("\n--- for reference: majority-variant Building ID per node ---")
    agree_all = disagree = same_across = 0
    for n in nodes:
        rows = [(c, CT.row_for(trees[c], n, TU)) for c in civs]
        rows = [(c, r) for c, r in rows if r is not None]
        bids = {str(r.get("Building ID")) for _c, r in rows}
        if len(bids) == 1:
            same_across += 1
        else:
            disagree += 1
    print("tech nodes whose Building ID is constant across all civs: %d of %d"
          % (same_across, same_across + disagree))
    return 0


if __name__ == "__main__":
    sys.exit(main())
