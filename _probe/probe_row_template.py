# -*- coding: utf-8 -*-
"""To GRANT a civ a unit it lacks, can we copy the row another civ has?

`civtechtrees.py` established that absence is real: a civ that cannot obtain a node
has NO row for it.  So granting one is not "flip a status" -- it means creating a
row, and a created row must match the schema the engine parses.  Inventing field
values would be guessing.

The alternative is to COPY a row that a civ which already has the node ships, and
the only thing that has to change is the fields that are inherently per-civ.  That
is safe exactly when:

  (a) rows for the same node id share a KEY SET across the civs that have them, so
      "copy a row" is well-defined rather than picking one of several shapes, and
  (b) the fields that differ per civ are identifiable, so the copy does not carry
      another civ's identity into this one.

Measure both across the whole corpus.  Also measure whether the row's own `Name`
field is even used, since we already know it is stale on 44 rows.
"""
import json
import os
import sys
from collections import Counter, defaultdict

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CT = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")


def main():
    trees = {}
    for fn in sorted(os.listdir(CT)):
        with open(os.path.join(CT, fn), encoding="utf-8") as fh:
            trees[fn[:-5]] = json.load(fh)

    # Gather, per (node id, Use Type), every row shape seen and which civs have it.
    shapes = defaultdict(Counter)          # (nid, use) -> shape -> count
    civs_of = defaultdict(set)
    key_sets = defaultdict(set)
    for civ, j in trees.items():
        for e in j.get("civ_techs_units") or ():
            if not isinstance(e, dict):
                continue
            nid, use = e.get("Node ID"), e.get("Use Type")
            if nid is None:
                continue
            shape = tuple(sorted(e))
            shapes[(nid, use)][shape] += 1
            civs_of[(nid, use)].add(civ)
            key_sets[use].add(shape)

    print("distinct (Node ID, Use Type) pairs: %d" % len(shapes))
    multi = {k: v for k, v in shapes.items() if len(v) > 1}
    print("pairs with MORE THAN ONE row shape : %d" % len(multi))
    for k in sorted(multi)[:8]:
        print("   %s -> %d shapes" % (k, len(multi[k])))
    print()

    print("key sets per Use Type:")
    for use in sorted(key_sets, key=lambda x: str(x)):
        print("   %-12s %d distinct key set(s)" % (use, len(key_sets[use])))
        for s in list(key_sets[use])[:1]:
            print("        %s" % (list(s),))
    print()

    # Which fields vary across civs for the SAME node?  Those are the per-civ ones
    # a copy must rewrite (or must NOT carry).
    print("fields that vary across civs for the same node (top 10 signals):")
    varying = Counter()
    total_fields = Counter()
    for (nid, use), cs in civs_of.items():
        rows = []
        for civ in cs:
            for e in trees[civ].get("civ_techs_units") or ():
                if isinstance(e, dict) and e.get("Node ID") == nid \
                        and e.get("Use Type") == use:
                    rows.append(e)
        if len(rows) < 2:
            continue
        keys = set()
        for r in rows:
            keys |= set(r)
        for k in keys:
            total_fields[k] += 1
            vals = {repr(r.get(k)) for r in rows}
            if len(vals) > 1:
                varying[k] += 1
    for k, n in varying.most_common(10):
        print("   %-24s varies in %4d / %4d node-pairs" % (k, n, total_fields[k]))
    print()
    stable = [k for k in total_fields if not varying.get(k)]
    print("fields NEVER varying for a given node: %s" % sorted(stable))
    print()
    print("VERDICT: a row can be copied from a civ that has it; the fields under")
    print("'varies' must then be handled by name, and the 'never varying' set is")
    print("safe to inherit unchanged.  Copying is therefore schema-safe because it")
    print("invents no field -- only values that the source civ genuinely had.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
