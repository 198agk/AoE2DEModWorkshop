# -*- coding: utf-8 -*-
"""Is a `Use Type: Tech` row's `Node ID` the .dat tech index?

The unit side answered YES for its own namespace (probe_node_id_vs_unit_id.py:
0 unit-use node ids are missing from the .dat).  The tech side must be measured
separately, and the first attempt to read it failed for an instructive reason:
`CT.node_status()` filters to `Use Type: Unit`, so asking it about Loom returned
"nobody has Loom" -- a WRONG answer, not an error.

Measurement:
  1. build the tech-row index by hand (Use Type == Tech);
  2. resolve each distinct Node ID through the .dat tech array and compare the
     row's own `Name` / `Name String ID` against the .dat record;
  3. do the same for a few techs every player knows (Loom, Hand Cart, ...).
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                          # noqa: E402
from aoe2mod.dat import locate as L                              # noqa: E402
from aoe2mod.game import civtechtrees as CT                      # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def tech_rows(tree):
    """Rows whose Use Type is Tech -- deliberately separate from unit_rows()."""
    out = []
    for v in tree.values():
        if isinstance(v, list):
            for e in v:
                if isinstance(e, dict) and e.get("Use Type") == "Tech":
                    out.append(e)
    return out


def main():
    tk = A.open_toolkit()
    tk._ensure()
    tail, gv = tk._parsed[4], tk._parsed[3]
    techs = L.locate_techs(tk._raw, tail, gv)
    print("dat techs: %d" % len(techs))
    names_path = os.path.join(ROOT, "aoe2mod", "semantic", "data",
                              "tech_names.json")
    with open(names_path, encoding="utf-8") as fh:
        names = json.load(fh)
    trees = CT.load_trees(GAME)

    rows = [(c, e) for c, t in trees.items() for e in tech_rows(t)]
    print("tech rows: %d over %d civs" % (len(rows), len({c for c, _ in rows})))
    ids = sorted({e.get("Node ID") for _, e in rows})
    print("distinct tech node ids: %d  range %d..%d" % (len(ids), ids[0], ids[-1]))

    # 1. is every tech node id a .dat tech index?
    missing = [i for i in ids if not (0 <= i < len(techs))]
    print("\ntech node ids outside the .dat tech array: %d  %s"
          % (len(missing), missing[:10]))

    # 2. does the row's Name / Name String ID match the .dat record's?
    #    tech_names.json carries the id and the internal name, both derived from
    #    the tech array by the same parser the product uses.
    agree = disagree = unk = 0
    samples = []
    for c, e in rows:
        i = e.get("Node ID")
        if not (0 <= i < len(techs)):
            continue
        rec = names.get(str(i)) or {}
        want = e.get("Name String ID")
        got = rec.get("name_string_id")
        if want is None or got is None:
            unk += 1
        elif want == got:
            agree += 1
        else:
            disagree += 1
            if len(samples) < 10:
                samples.append((c, i, e.get("Name"), want, got))
    print("row Name String ID == tech_names[%s].name_string_id: agree %d / disagree %d / unknown %d"
          % ("id", agree, disagree, unk))
    for s in samples:
        print("   %-12s id=%-5d row Name=%-28r row nsid=%s dat nsid=%s" % s)

    # 2b. internal name agreement (the .dat's debug_string)
    nm = di = 0
    nmsample = []
    for c, e in rows:
        i = e.get("Node ID")
        if not (0 <= i < len(techs)):
            continue
        rec = names.get(str(i)) or {}
        a = (e.get("Name") or "").strip()
        b = (rec.get("internal") or "").strip()
        if not a or not b:
            continue
        if a.lower() == b.lower():
            nm += 1
        else:
            di += 1
            if len(nmsample) < 8:
                nmsample.append((i, a, b))
    print("row Name == tech internal name: agree %d / differ %d" % (nm, di))
    for s in nmsample:
        print("   id=%-5d row=%-30r dat=%r" % s)

    # 3. techs every player knows, by name, using the row's own Name field
    print("\nknown techs, located as Tech rows (name from the row itself):")
    for want in ("Loom", "Hand Cart", "Town Watch", "Wheelbarrow", "Horse Collar"):
        hits = [(c, e.get("Node ID"), e.get("Node Status")) for c, e in rows
                if (e.get("Name") or "").strip() == want]
        nid = sorted({h[1] for h in hits})
        st = Counter(h[2] for h in hits)
        print("  %-14s rows=%-4d ids=%s  %s" % (want, len(hits), nid, dict(st)))

    # 4. the collision, measured on the TECH side: for each id that is also a
    #    unit row id, what does the same id mean as a tech row?
    unit_only = {e.get("Node ID") for t in trees.values() for e in CT.unit_rows(t)}
    both = sorted(set(ids) & unit_only)
    print("\nids that are BOTH a unit row and a tech row: %d  %s" % (len(both), both[:14]))
    for nid in both[:4]:
        as_tech = {(e.get("Name"), techs[nid].get("LanguageDLLName"))
                   for _, e in rows if e.get("Node ID") == nid}
        print("  id %-4d as tech: %s   as .dat tech: id=%d name=%r"
              % (nid, list(as_tech)[:2], nid, techs[nid].get("name")))

    # 5. how many ids does a civ have as ResearchedCompleted, tech side?
    per_civ = Counter()
    for c, t in trees.items():
        per_civ[c] = sum(1 for e in tech_rows(t)
                         if e.get("Node Status") == "ResearchedCompleted")
    vals = sorted(per_civ.values())
    print("\ntech rows per civ that read ResearchedCompleted: min %d max %d"
          % (vals[0], vals[-1]))
    status = Counter(e.get("Node Status") for _, e in rows)
    print("tech row status histogram: %s" % dict(status))


if __name__ == "__main__":
    sys.exit(main())
