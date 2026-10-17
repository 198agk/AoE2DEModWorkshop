# -*- coding: utf-8 -*-
"""Which of the two mechanisms GATES buildability?  A discriminating test.

`unit.availability` writes only CivTechTrees; a `type 2` effect command is the
other candidate mechanism.  Both exist in the shipped data, so "both are present"
proves nothing about which one is *necessary*.

The data offers a clean discriminator.  Take a unit that some civs can build and
others cannot (Hand Cannoneer, unit 5: 24 builders, 38 civs whose row reads
`NotAvailable`).  Then:

  * if the 38 BLOCKED civs own no enable command, the enable is necessary and a
    tree row alone is not sufficient -> `unit.availability` is half a feature;
  * if the 38 blocked civs DO own an enable, then owning an enable is not
    sufficient (they have it and still cannot build), so whatever differs between
    them and the 24 builders is what actually gates it.

Only one of those can be true, and both are actionable.  Writes nothing.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                        # noqa: E402
from aoe2mod.dat import locate as L                            # noqa: E402
from aoe2mod.game import civtechtrees as CT                    # noqa: E402
from aoe2mod.intent import compiler as C                       # noqa: E402
from aoe2mod.semantic import index as SI                       # noqa: E402


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    effects, _ = L.locate_effects(raw)
    techs = L.locate_techs(raw, tail, gv)
    trees = CT.load_trees(tk.game_root)
    sem = SI.index()

    stem2idx = {}
    for c in tk._civs:
        stem = CT.civ_file_stem(c.get("name"))
        if stem in trees:
            stem2idx[stem] = c["index"]

    # (civ index) -> {unit ids enabled}; globals separately
    own = collections.defaultdict(set)
    glob = set()
    enable_tech_of = {}          # (civ idx, unit) -> tech index
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["type"] != 2 or r["raw"][2] != 1:
                continue
            u = r["raw"][1]
            owner = t.get("civ")
            if owner is None or owner < 0:
                glob.add(u)
            else:
                own[owner].add(u)
                enable_tech_of[(owner, u)] = ti

    for NODE, label in ((5, "Hand Cannoneer"), (41, "Huskarl"), (21, "War Galley")):
        build = CT.builders(trees, NODE)
        blocked = [s for s, tr in trees.items()
                   if CT.node_status(tr, NODE) == "NotAvailable"]
        absent = [s for s, tr in trees.items()
                  if CT.node_status(tr, NODE) is None]
        print("=" * 72)
        print("unit %d (%s): %d builders, %d blocked(NotAvailable), %d absent"
              % (NODE, label, len(build), len(blocked), len(absent)))
        print("  builders owning an enable:      %d / %d"
              % (len([s for s in build
                      if NODE in own.get(stem2idx.get(s), set()) or NODE in glob]),
                 len(build)))
        print("  BLOCKED civs owning an enable:  %d / %d"
              % (len([s for s in blocked
                      if NODE in own.get(stem2idx.get(s), set()) or NODE in glob]),
                 len(blocked)))
        print("  ABSENT civs owning an enable:   %d / %d"
              % (len([s for s in absent
                      if NODE in own.get(stem2idx.get(s), set()) or NODE in glob]),
                 len(absent)))
        # Is the enable civ-owned or global, for the blocked ones?
        ob = len([s for s in blocked if NODE in own.get(stem2idx.get(s), set())])
        gb = len([s for s in blocked if NODE in glob])
        print("    of those, civ-owned: %d   global: %d" % (ob, gb))
        if blocked:
            ex = blocked[:5]
            for s in ex:
                u = sem.units.get(NODE)
                ti = enable_tech_of.get((stem2idx.get(s), NODE))
                print("    blocked sample %-14s enable_tech=%s" % (s, ti))
        print()

    # The general form: over ALL (civ, unit) pairs, cross-tabulate
    # "can this civ build it" against "does it own an enable".
    tab = collections.Counter()
    for stem, tr in trees.items():
        idx = stem2idx.get(stem)
        for row in CT.unit_rows(tr):
            nid = row.get("Node ID")
            if nid is None:
                continue
            can = CT.can_build(tr, nid)
            status = CT.node_status(tr, nid)
            has = (idx is not None and nid in own.get(idx, set())) or (nid in glob)
            key = ("can_build" if can else "cannot",
                   "yes" if status == "NotAvailable" else "no")
            tab[(key[0], key[1], "enable" if has else "no_enable")] += 1
    print("=" * 72)
    print("cross-tabulation over every (civ, unit row):")
    for k in sorted(tab, key=lambda x: (-tab[x], x)):
        print("  can_build=%-8s listed_NotAvailable=%-3s enable=%-9s : %d"
              % (k[0], k[1], k[2], tab[k]))
    print()
    print("THE DECIDING CELL: civs that CANNOT build it but the row is not")
    print("NotAvailable (i.e. absent-from-build-set yet non-blocking):")
    for k in sorted(tab):
        if k[0] == "cannot" and k[1] == "no":
            print("   %s -> %d" % (k, tab[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
