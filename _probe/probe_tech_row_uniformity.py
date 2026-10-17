# -*- coding: utf-8 -*-
"""Is a TECH row the same row in every civ that lists it?

For the UNIT space the answer was "mostly yes, but 43 of 287 nodes have rows that
differ across civs" -- and that mattered, because `grant` copies the donor's row
and inherits its presentation fields (Name String ID, Picture Index, ...).

The tech space has a sharper stake: a tech row carries `Prerequisite IDs`,
`Prerequisite Types`, `Building ID` and `Age ID`.  If those differ between the
civ that has the tech and the civ that does not, then "grant this tech to that
civ" is not one edit -- it silently also decides what the tech requires and where
it is researched.  Measure that before writing any of it.

Also measures the SIZE of each operation, the way the unit side was measured
(GRANTABLE / REVOCABLE per civ), because that is what the UI has to be designed
around -- 62 x 238 = 14,756 pairs is not the number that matters.
"""
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                      # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
TU = CT.TECH_USE_TYPES
# Fields a grant copies and that a user would notice.
INHERITED = ("Name", "Name String ID", "Picture Index", "Help String ID",
             "Building ID", "Age ID", "Link ID", "Trigger Tech ID",
             "Prerequisite IDs", "Prerequisite Types", "Node Type")


def sig(row):
    """What the row MEANS, ignoring its status (which is the thing being edited)."""
    return json.dumps({k: row.get(k) for k in INHERITED}, sort_keys=True,
                      ensure_ascii=False)


def main():
    trees = CT.load_trees(GAME)
    names = json.load(open(os.path.join(ROOT, "aoe2mod", "semantic", "data",
                                        "tech_names.json"), encoding="utf-8"))

    # ---- 1. are the rows uniform across civs? ------------------------------
    by_id = defaultdict(dict)          # node_id -> {civ: row}
    for civ, t in trees.items():
        for e in CT.tech_rows(t):
            by_id[e.get("Node ID")][civ] = e

    distinct = {}
    for nid, rows in by_id.items():
        distinct[nid] = len({sig(r) for r in rows.values()})
    hist = Counter(distinct.values())
    print("tech node ids: %d" % len(by_id))
    print("distinct signatures per node (ignoring status): %s"
          % dict(sorted(hist.items())))
    multi = [nid for nid, n in distinct.items() if n > 1]
    print("nodes whose row is NOT the same everywhere: %d %s"
          % (len(multi), sorted(multi)[:20]))
    print("nodes whose rows share one signature: %d of %d"
          % (len(by_id) - len(multi), len(by_id)))

    # which fields actually differ, on those nodes?
    fld = Counter()
    for nid in multi:
        rows = list(by_id[nid].values())
        for k in INHERITED:
            if len({json.dumps(r.get(k), sort_keys=True) for r in rows}) > 1:
                fld[k] += 1
    print("fields that differ on those nodes: %s" % dict(fld))

    # show a few, with names, so this is checkable by eye
    print("\nthe differing nodes that a player would recognise:")
    shown = 0
    for nid in sorted(multi):
        nm = (names.get(str(nid)) or {}).get("en")
        if not nm:
            continue
        rows = by_id[nid]
        print("   id=%-5d %-26s civs=%-3d %s"
              % (nid, nm, len(rows),
                 {k: sorted({json.dumps(r.get(k), ensure_ascii=False)
                             for r in rows.values()})[:3] for k in INHERITED
                  if len({json.dumps(r.get(k), sort_keys=True)
                          for r in rows.values()}) > 1}))
        shown += 1
        if shown >= 8:
            break

    # ---- 2. how big is each operation? -------------------------------------
    all_ids = sorted(by_id)
    grantable = revocable = settable = 0
    per_civ = []
    for civ, t in trees.items():
        mine = {e.get("Node ID"): e for e in CT.tech_rows(t)}
        g = r = s = 0
        for nid in all_ids:
            st = (mine.get(nid) or {}).get("Node Status")
            if st is None:
                # absent: a grant can add it, IF some other civ can offer it
                if CT.builders(trees, nid, TU):
                    g += 1
            elif st == "NotAvailable":
                if CT.builders(trees, nid, TU):
                    s += 1
                else:
                    pass
            else:
                r += 1        # revocable (the civ has it in its tree)
        per_civ.append((civ, g, s, r))
        grantable += g
        settable += s
        revocable += r
    gs = [g for _, g, _, _ in per_civ]
    ss = [s for _, _, s, _ in per_civ]
    rs = [r for _, _, _, r in per_civ]
    print("\nper civ: absent-and-grantable min %d max %d mean %.1f"
          % (min(gs), max(gs), sum(gs) / len(gs)))
    print("per civ: NotAvailable-and-fixable min %d max %d mean %.1f"
          % (min(ss), max(ss), sum(ss) / len(ss)))
    print("per civ: in-tree (revocable) min %d max %d mean %.1f"
          % (min(rs), max(rs), sum(rs) / len(rs)))
    print("totals: pairs %d = grantable %d + status-fix %d + revocable %d"
          % (grantable + settable + revocable, grantable, settable, revocable))
    print("worst case 62 x %d = %d" % (len(all_ids), 62 * len(all_ids)))

    # ---- 3. is the set_status path real on the tech side? ------------------
    na_rows = [(c, e.get("Node ID")) for c, t in trees.items()
               for e in CT.tech_rows(t) if e.get("Node Status") == "NotAvailable"]
    fixable = [(c, n) for c, n in na_rows if CT.builders(trees, n, TU)]
    print("\nNotAvailable tech rows: %d, of which another civ offers it: %d"
          % (len(na_rows), len(fixable)))
    print("sample fixable: %s" % fixable[:6])

    # ---- 4. max builders, and the extremes --------------------------------
    bc = sorted(((len(CT.builders(trees, n, TU)), n) for n in all_ids),
                reverse=True)
    print("\nmost-offered techs: %s"
          % [(n, nm, (names.get(str(n)) or {}).get("en"))
             for n, nm in [(n, c) for c, n in bc[:5]]])
    print("least-offered (still >=1): %s"
          % [(n, (names.get(str(n)) or {}).get("en"))
             for c, n in bc if c == 1][:8])
    print("techs NOBODY offers: %s"
          % [n for c, n in bc if c == 0])

    print("\n(no assertions: this is a measurement, not a contract)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
