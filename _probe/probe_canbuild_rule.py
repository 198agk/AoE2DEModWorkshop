"""Measure the blast radius of the corrected "can build" rule.

Decision from probe_status_meaning.py:
    ResearchedCompleted = has it from the start
    ResearchRequired    = reachable by research  -> CAN build (after research)
    NotAvailable        = never
    no row              = never

So can_build = row present and status != NotAvailable.  `has()` today says
ResearchedCompleted only, and `owners()` defaults to it.

Four things to measure before touching code:

  1. how many nodes NO civ can build (all rows NotAvailable) -- the answer a
     grant must refuse with "not part of any tech tree" vs "nobody can build it"
  2. how many nodes change owner-count under the corrected rule, and the totals
  3. whether donor_row() can hand back a row from a civ that CANNOT build the
     unit (it takes the first row in sorted civ order, whatever the status)
  4. how often one civ file lists the same node twice with different statuses
     (which decides whether node_status' "granting status wins" order matters)
"""

import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402


def main():
    tk = A.open_toolkit()
    tk._ensure()
    trees = tk._trees()

    nodes = sorted({r.get("Node ID") for t in trees.values()
                    for r in CT.unit_rows(t)})
    print("civs %d  unit nodes %d" % (len(trees), len(nodes)))

    def rows_for(nid):
        return [(c, r) for c in sorted(trees) for r in CT.unit_rows(trees[c])
                if r.get("Node ID") == nid]

    # ---- 1 / 2 ----------------------------------------------------------
    nobody, changed, hist_old, hist_new = [], 0, Counter(), Counter()
    both_ways = []
    for nid in nodes:
        old = [c for c, r in rows_for(nid)
               if r.get("Node Status") == "ResearchedCompleted"]
        new = [c for c, r in rows_for(nid)
               if r.get("Node Status") != "NotAvailable"]
        hist_old[len(old)] += 1
        hist_new[len(new)] += 1
        if len(old) != len(new):
            changed += 1
        if not new:
            nobody.append(nid)
        if old and len(old) != len(new):
            both_ways.append((nid, len(old), len(new)))
    print()
    print("nodes whose owner-count changes under the corrected rule: %d of %d"
          % (changed, len(nodes)))
    print("nodes NO civ can build (every row NotAvailable): %d %s"
          % (len(nobody), nobody[:20]))
    print("every node has >=1 residue: %s"
          % (sum(hist_new.values()) == len(nodes)))
    print("  owners=0 under old rule: %d   under new rule: %d"
          % (hist_old[0], hist_new[0]))
    print("  largest can-build set: %d" % max(hist_new))

    # nodes that differ but still have SOME owner -- the interesting middle
    print("  nodes with owners both before and after, count differs: %d"
          % len(both_ways))
    for nid, o, n in both_ways[:8]:
        nm = CT.name_string_id(trees["BRITONS"], nid)
        print("    node %-5d old %-3d new %-3d (BRITONS name id %s)"
              % (nid, o, n, nm))

    # ---- 3 --------------------------------------------------------------
    print()
    bad_donor = []
    for nid in nodes:
        cur_civ, _ = CT.donor_row(trees, nid)
        if cur_civ is None:
            continue
        st = CT.node_status(trees[cur_civ], nid)
        if st == "NotAvailable":
            good = [c for c in sorted(trees)
                    if CT.node_status(trees[c], nid) not in
                    (None, "NotAvailable")]
            bad_donor.append((nid, cur_civ, good[0] if good else None))
    print("donor_row picks a civ that CANNOT build it: %d" % len(bad_donor))
    for nid, c, g in bad_donor[:15]:
        print("    node %-5d donor=%-14s (%s)  first able=%s"
              % (nid, c, CT.node_status(trees[c], nid), g))

    # ---- 4 --------------------------------------------------------------
    dup = []
    for c, t in trees.items():
        seen = {}
        for r in CT.unit_rows(t):
            nid = r.get("Node ID")
            seen.setdefault(nid, []).append(r.get("Node Status"))
        for nid, sts in seen.items():
            if len(sts) > 1 and len(set(sts)) > 1:
                dup.append((c, nid, sts))
    print()
    print("civ files listing one node twice with different statuses: %d" % len(dup))
    for c, nid, sts in dup[:10]:
        print("    %-14s node %-5d %s" % (c, nid, sts))

    # ---- 5  the read-side gap -------------------------------------------
    print()
    gap = 0
    samples = []
    for nid in nodes:
        holders = [c for c in trees
                   if CT.node_status(trees[c], nid) not in (None, "NotAvailable")]
        d = tk.describe(nid)
        if d["civ_count"] != len(holders):
            gap += 1
            if len(samples) < 6:
                samples.append((nid, d["name"], d["civ_count"], len(holders)))
    print("read-side: describe() civ_count != can-build civs for %d of %d nodes"
          % (gap, len(nodes)))
    for nid, nm, a, b in samples:
        print("    id %-5d %-24s describe %-3d  can-build %-3d" % (nid, nm, a, b))
    return 0


if __name__ == "__main__":
    sys.exit(main())
