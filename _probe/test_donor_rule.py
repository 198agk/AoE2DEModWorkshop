"""Verify the SHIPPED `donor_row` rule against the measurement.

`probe_donor_rules.py` measured the candidates on a local reimplementation.  This
checks the production function itself: every grant the UI could offer must now
copy the row variant the MAJORITY of civilizations use, so the receiver gets the
name and icon its neighbours show.  Before the change that was violated on 112
tech grants and 3 unit grants.

Also re-asserts the properties the old rule guaranteed, so the change cannot
quietly drop them: the donor can build it, the donor is deterministic, and the
donor still prefers a civ that already has it.

Read-only (calls the real aoe2mod API).  Asserts, exits non-zero on failure.
"""
import os
import _gamepaths as GP
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT  # noqa: E402

GAME = GP.GAME
FAILS = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(label)


def rowkey(r):
    return tuple(sorted((k, str(v)) for k, v in r.items() if k != "Node Status"))


def space(label, use_types, rowfn):
    trees = CT.load_trees(GAME)
    civs = sorted(trees)
    nodes = sorted({r.get("Node ID") for c in civs for r in rowfn(trees[c])
                    if isinstance(r.get("Node ID"), int)})
    maj = {}
    for n in nodes:
        rows = [CT.row_for(trees[c], n, use_types) for c in civs]
        rows = [r for r in rows if r is not None]
        if rows:
            maj[n] = collections.Counter(
                r.get("Name") for r in rows).most_common(1)[0][0]

    wrong, grants, not_able, nondet = 0, 0, 0, 0
    samples = []
    for n in nodes:
        c1, r1 = CT.donor_row(trees, n, use_types=use_types)
        c2, r2 = CT.donor_row(trees, n, use_types=use_types)
        if c1 != c2:
            nondet += 1
        if c1 is None:
            continue
        if not CT.can_build(trees[c1], n, use_types):
            not_able += 1
        for civ in civs:
            if CT.can_build(trees[civ], n, use_types):
                continue
            grants += 1
            if r1.get("Name") != maj.get(n):
                wrong += 1
                if len(samples) < 6:
                    samples.append((c1, n, r1.get("Name"), maj.get(n)))

    print("\n%s space (%d nodes, %d grants)" % (label, len(nodes), grants))
    check(wrong == 0,
          "every grant copies the MAJORITY row variant (no surprise renames)",
          "mismatches %d %s" % (wrong, samples))
    check(not_able == 0, "the donor is always a civ that can build it")
    check(nondet == 0, "the choice is deterministic across calls")

    # the ready-donor preference must survive
    pref_ok = pref_tot = 0
    for n in nodes:
        able = [c for c in civs if CT.can_build(trees[c], n, use_types)]
        if len(able) < 2:
            continue
        sts = {CT.node_status(trees[c], n, use_types) for c in able}
        if len(sts) < 2:
            continue
        pref_tot += 1
        if CT.donor_row(trees, n, use_types=use_types)[0] in [
                c for c in able
                if CT.node_status(trees[c], n, use_types) == "ResearchedCompleted"]:
            pref_ok += 1
    check(pref_tot == 0 or pref_ok == pref_tot,
          "a civ that already has it still beats one that needs research",
          "%d/%d" % (pref_ok, pref_tot))
    return grants


def main():
    print("donor_row rule check")
    u = space("Unit", CT.UNIT_USE_TYPES, CT.unit_rows)
    t = space("Tech", CT.TECH_USE_TYPES, CT.tech_rows)

    trees = CT.load_trees(GAME)
    for label, node, ut, expect in (("Huskarl", 41, CT.UNIT_USE_TYPES, "GOTHS"),
                                    ("Yeomen", 3, CT.TECH_USE_TYPES, "BRITONS")):
        c, r = CT.donor_row(trees, node, use_types=ut)
        check(c == expect, "%s's donor is still %s" % (label, expect), c)

    # the synthetic preference case the permanent suite asserts
    fake = {"A": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit", "Node Status": "ResearchRequired",
                 "Name String ID": 1}]},
            "B": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit", "Node Status": "ResearchedCompleted",
                 "Name String ID": 2}]},
            "C": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit", "Node Status": "NotAvailable",
                 "Name String ID": 3}]}}
    c, r = CT.donor_row(fake, 9, use_types=CT.UNIT_USE_TYPES)
    check(c == "B" and r is not None and r["Name String ID"] == 2,
          "synthetic: ready donor wins over merely researchable", (c, r))

    # and the new rank: when statuses TIE, the majority variant wins
    fake2 = {"A": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit", "Node Status": "ResearchedCompleted",
                 "Name String ID": 99, "Name": "Rare"}]},
             "B": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit", "Node Status": "ResearchedCompleted",
                 "Name String ID": 1, "Name": "Common"}]},
             "C": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit", "Node Status": "ResearchedCompleted",
                 "Name String ID": 1, "Name": "Common"}]}}
    c, r = CT.donor_row(fake2, 9, use_types=CT.UNIT_USE_TYPES)
    check(c == "B" and r["Name"] == "Common",
          "synthetic: on a status tie the majority variant wins, not 'A'", (c, r))

    print("\nDONOR RULE CHECKS PASSED" if not FAILS else "\nFAILED: %s" % FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
