"""Do a NotAvailable row and an able row carry the same field VALUES?

`donor_row` currently returns the first civ in sorted order that has ANY row for
the node, whatever its status.  For 12 nodes that is a civ whose row reads
NotAvailable -- e.g. node 5 Hand Cannoneer, donor ACHAEMENIDS, while ATHENIANS
has a real one.  The copy inherits Building ID / Age ID / Picture Index from the
donor, so if those differ the granted unit is trained at the wrong building or
shows the wrong icon.

Measures, for each node where donor and first-able differ:
  * which fields differ between the two rows
  * how many distinct field-value sets exist across all rows of that node
"""

import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

INTEREST = ("Name", "Name String ID", "Picture Index", "Help String ID",
            "Building ID", "Age ID", "Link ID", "Link Node Type",
            "Trigger Tech ID", "Prerequisite IDs", "Prerequisite Types",
            "Node Type", "Use Type", "Draw Node Type", "Building upgraded from ID")


def able(status):
    return status is not None and status != "NotAvailable"


def main():
    tk = A.open_toolkit()
    tk._ensure()
    trees = tk._trees()
    nodes = sorted({r.get("Node ID") for t in trees.values()
                    for r in CT.unit_rows(t)})

    print("=== donor choice: first-sorted row vs first-sorted ABLE row ===")
    diff_nodes = 0
    for nid in nodes:
        cur, cur_row = CT.donor_row(trees, nid)
        if cur is None:
            continue
        if able(CT.node_status(trees[cur], nid)):
            continue
        good = None
        for c in sorted(trees):
            if able(CT.node_status(trees[c], nid)):
                good = c
                break
        good_row = CT.row_for(trees[good], nid) if good else None
        diffs = [f for f in INTEREST
                 if cur_row.get(f) != (good_row or {}).get(f)]
        if diffs:
            diff_nodes += 1
        print("  node %-5d donor %-13s(%s) vs %-13s(%s)  differ: %s"
              % (nid, cur, CT.node_status(trees[cur], nid), good,
                 CT.node_status(trees[good], nid) if good else "?",
                 diffs or "none"))
    print("  nodes where the two rows differ in an inherited field: %d"
          % diff_nodes)

    print()
    print("=== how many DISTINCT row-value signatures per node (over all civs) ===")
    many = []
    for nid in nodes:
        sig = defaultdict(list)
        for c in sorted(trees):
            r = CT.row_for(trees[c], nid)
            if r is None:
                continue
            key = tuple(str(r.get(f)) for f in INTEREST)
            sig[key].append((c, r.get("Node Status")))
        if len(sig) > 1:
            many.append((nid, len(sig), sig))
    print("  nodes whose rows are not identical across civs: %d of %d"
          % (len(many), len(nodes)))
    for nid, n, sig in many[:6]:
        print("    node %-5d %d distinct signatures" % (nid, n))
        for key, who in list(sig.items())[:4]:
            sts = sorted({s for _, s in who})
            print("        %-3d civs %s  statuses %s"
                  % (len(who), [c for c, _ in who][:3], sts))

    print()
    print("=== do rows differ ONLY by status? ===")
    only_status = 0
    for nid in nodes:
        sig = defaultdict(list)
        for c in sorted(trees):
            r = CT.row_for(trees[c], nid)
            if r is None:
                continue
            key = tuple(str(r.get(f)) for f in INTEREST)
            sig[key].append(r.get("Node Status"))
        if len(sig) > 1:
            continue
        only_status += 1
    print("  nodes where every row shares one signature (status is the only "
          "difference): %d of %d" % (only_status, len(nodes)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
