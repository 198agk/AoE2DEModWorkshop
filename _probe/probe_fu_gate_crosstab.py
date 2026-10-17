"""The follow-up that decides it: what does the panel file DO with tree status?

Roadmap result: 2812 of 2827 (civ, unit) triples put the unit under the same
Building ID the tree gives -- 99.47%.  But the panel also carries research-gating
display fields (`PrereqTech`/`PrereqStringID`/`PrereqStyle`/`PrereqIconSet`/
`PrereqIconIndex`, 295 entries each), which means it CAN express "gated behind a
tech".  So my earlier line -- "it has no place to express a research gate, so it
is not an availability model" -- was too strong and has to be retested.

The cross-tab does that:

  * if `PrereqTech == 295` lines up with the tree's `ResearchRequired` rows, the
    panel KNOWS about research gates and deliberately renders them;
  * if it lines up with something else, the gates it knows about are not the
    tree's, and the two files have different sources.

Also dumped: the 15 building mismatches, and RequiredAge vs the tree's Age ID.

Run:  python _probe/probe_fu_gate_crosstab.py
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

FU_REL = os.path.join("resources", "_common", "dat", "futuravailableunits.json")
NODE_IDS = None  # filled below


def unit_entries(fu, trees, by_tree):
    """Yield (civ, building_id, entry, tree_row_or_None) for UNIT entries only.

    "Unit" here means: the id is one the tree models as a unit somewhere.  The
    panel also files BUILDINGS under building 118, and comparing those to unit
    rows produced 1072 phantom rows earlier.
    """
    for civ in sorted(by_tree):
        for blk in fu[by_tree[civ]].get("Buildings", []):
            bid = blk.get("ID")
            for u in blk.get("Units", []):
                uid = u.get("ID")
                if uid not in NODE_IDS:
                    continue
                yield civ, bid, u, CT.row_for(trees[civ], uid)


def main():
    global NODE_IDS
    tk = A.open_toolkit()
    fu = json.loads(open(os.path.join(tk.game_root, FU_REL), "rb")
                    .read().decode("utf-8-sig"))
    trees = CT.load_trees(tk.game_root)
    by_tree = {}
    for k in fu:
        cand = CT.civ_file_stem(k)
        if cand in trees:
            by_tree[cand] = k

    NODE_IDS = set()
    for civ in trees:
        for r in CT.unit_rows(trees[civ]):
            NODE_IDS.add(r.get("Node ID"))
    print("unit ids the tree models anywhere: %d" % len(NODE_IDS))

    entries = list(unit_entries(fu, trees, by_tree))
    print("panel UNIT entries: %d" % len(entries))
    print()

    # ---- cross-tab: tree status x PrereqTech presence ----------------------
    tab = Counter()
    for civ, bid, u, row in entries:
        st = row.get("Node Status") if row is not None else "(no tree row)"
        tab[(st, "PrereqTech" in u)] += 1
    print("tree status x panel PrereqTech:")
    for (st, has), n in sorted(tab.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        print("  %-18s PrereqTech=%-5s %5d" % (st, has, n))
    print()

    # ---- do the panel's gates match the tree's? ---------------------------
    rr = [e for e in entries
          if e[3] is not None and e[3].get("Node Status") == "ResearchRequired"]
    print("tree rows whose status is ResearchRequired: %d" % len(rr))
    print("  of those, listed in the panel : %d"
          % sum(1 for e in rr))
    print("  carrying a PrereqTech         : %d"
          % sum(1 for e in rr if "PrereqTech" in e[2]))
    gated = [e for e in entries if "PrereqTech" in e[2]]
    print("panel entries carrying a PrereqTech: %d" % len(gated))
    print("  of those, tree status is ResearchRequired: %d"
          % sum(1 for e in gated
                if e[3] is not None and e[3].get("Node Status") == "ResearchRequired"))
    print("  of those, tree status is ResearchedCompleted: %d"
          % sum(1 for e in gated
                if e[3] is not None and e[3].get("Node Status") == "ResearchedCompleted"))
    print("  of those, tree status is NotAvailable: %d"
          % sum(1 for e in gated
                if e[3] is not None and e[3].get("Node Status") == "NotAvailable"))
    print("  of those, no tree row: %d"
          % sum(1 for e in gated if e[3] is None))
    print()

    # ---- the 15 building mismatches ---------------------------------------
    print("building mismatches (panel Bucket vs tree Building ID):")
    for civ, bid, u, row in entries:
        if row is None:
            continue
        tb = row.get("Building ID")
        if tb is not None and int(tb) != int(bid):
            print("  %-14s unit %-5s %-24s panel bldg %-5s tree bldg %-5s"
                  % (civ, u.get("ID"), u.get("Name"), bid, tb))
    print()

    # ---- RequiredAge vs tree Age ID ---------------------------------------
    same = diff = norow = noage = 0
    for civ, bid, u, row in entries:
        if row is None:
            norow += 1
            continue
        ta = row.get("Age ID")
        if ta is None or u.get("RequiredAge") is None:
            noage += 1
            continue
        if int(ta) == int(u["RequiredAge"]):
            same += 1
        else:
            diff += 1
    print("RequiredAge vs tree Age ID: same %d / differ %d / no row %d / no age %d"
          % (same, diff, norow, noage))
    return 0


if __name__ == "__main__":
    sys.exit(main())
