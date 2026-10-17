# -*- coding: utf-8 -*-
"""Which rows in CivTechTrees are TECH rows, and can anything read them?

The unit side is fully wired: unit_rows() filters `Use Type: Unit`, and
can_build/builders answer "who can train it".  The corpus also carries thousands
of rows whose `Use Type` is `Tech` -- those are what make a tech available to a
civ, which is the OTHER half of "what can this civilization do".

Before designing anything, measure:
  1. which keys/groups the tech rows live in;
  2. whether they are reachable through the current reader API;
  3. whether a known tech (Loom, Hand Cart, ...) can be located and whether its
     owner set matches what a player knows;
  4. whether the same Node ID space collision hits the tech side.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                     # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    trees = CT.load_trees(GAME)
    print("trees: %d" % len(trees))

    # 1. what keys exist, and what lives in each
    keys = Counter()
    use_of_key = {}
    for civ, t in trees.items():
        for k, v in t.items():
            if k == "path" or not isinstance(v, list):
                continue
            keys[k] += 1
            for e in v:
                if isinstance(e, dict):
                    use_of_key.setdefault(k, Counter())[e.get("Use Type")] += 1
    print("\nlist-valued keys per civ:")
    for k, n in sorted(keys.items()):
        print("  %-24s in %d civs   use types %s"
              % (k, n, dict(use_of_key.get(k, {}))))

    # 2. reachable through the current API?
    print("\nthrough the CURRENT reader API:")
    print("  rows_of()     -> %d rows"
          % sum(len(CT.rows_of(t)) for t in trees.values()))
    print("  unit_rows()   -> %d rows"
          % sum(len(CT.unit_rows(t)) for t in trees.values()))
    all_rows = sum(len([e for v in t.values() if isinstance(v, list)
                        for e in v if isinstance(e, dict)]) for t in trees.values())
    print("  every row     -> %d rows" % all_rows)
    print("  => tech rows are %s through unit_rows()"
          % ("REACHABLE" if all_rows == sum(len(CT.unit_rows(t)) for t in trees.values())
             else "NOT reachable"))

    # 3. the tech use-type rows
    tech_rows = [(civ, e) for civ, t in trees.items()
                 for v in t.values() if isinstance(v, list)
                 for e in v if isinstance(e, dict) and e.get("Use Type") == "Tech"]
    print("\nrows with Use Type == 'Tech': %d  across %d civs"
          % (len(tech_rows), len({c for c, _ in tech_rows})))
    print("  their Node Type histogram: %s"
          % dict(Counter(e.get("Node Type") for _, e in tech_rows)))
    print("  their Node Status histogram: %s"
          % dict(Counter(e.get("Node Status") for _, e in tech_rows)))
    uniq = sorted({e.get("Node ID") for _, e in tech_rows})
    print("  distinct Node IDs: %d   range %s..%s"
          % (len(uniq), uniq[0], uniq[-1]))

    # 4. a known tech, looked up the way the unit side does it
    print("\nknown techs by Node ID:")
    for nid, want in ((22, "Loom (all civs)"), (8, "?"), (10, "?")):
        owners = sorted(c for c in trees
                        if CT.node_status(trees[c], nid) == "ResearchedCompleted")
        print("  id %-5d %-22s haves=%d" % (nid, want, len(owners)))

    # 5. the collision: does an id that is a UNIT somewhere appear as Tech too?
    unit_ids = {e.get("Node ID") for t in trees.values() for e in CT.unit_rows(t)}
    tech_ids = {e.get("Node ID") for _, e in tech_rows}
    both = sorted(unit_ids & tech_ids)
    print("\nids present as BOTH a unit row and a tech row: %d" % len(both))
    print("  sample %s" % both[:12])
    if both:
        nid = both[0]
        where = [(c, CT.node_status(trees[c], nid),
                  [e.get("Use Type") for e in CT.rows_of(trees[c])
                   if e.get("Node ID") == nid])
                 for c in sorted(trees)][:4]
        print("  id %d per civ (civ, unit-reading, all use types): %s" % (nid, where))

    # 6. does the tech row carry the same field set?
    print("\ntech row key sets:")
    for ks, n in Counter(tuple(sorted(e)) for _, e in tech_rows).most_common(4):
        print("  n=%-6d %s" % (n, list(ks)))
    print("\nunit row key sets (for comparison, top 2):")
    for ks, n in Counter(tuple(sorted(e)) for t in trees.values()
                         for e in CT.unit_rows(t)).most_common(2):
        print("  n=%-6d %s" % (n, list(ks)))


if __name__ == "__main__":
    sys.exit(main())
