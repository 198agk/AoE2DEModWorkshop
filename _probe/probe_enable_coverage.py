# -*- coding: utf-8 -*-
"""Does a civ that CAN build a unit always own a type-2 enable for it?

This decides whether the already-shipped `unit.availability` intent is complete.
That intent copies a CivTechTrees row and touches NO `.dat` byte.  If every civ
that can build a unit also owns an "enable" command for it, then a row alone was
never demonstrated to be sufficient -- the grant would produce a row the tech
tree displays while the `.dat` still refuses to let it be built.

The comparison is per unit, civ by civ: "can build" comes from the tree layer
(:func:`civtechtrees.can_build`) and "owns an enable" comes from the `.dat`
effect commands.  A gap is not proof of a bug (the engine may honour the row
alone) but it is exactly the shape of a silent half-feature, so it must be
measured before either mechanism is called finished.

Writes nothing.
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
    civs = tk._civs
    sem = SI.index()
    trees = CT.load_trees(tk.game_root)

    idx2stem = {}
    for c in civs:
        stem = CT.civ_file_stem(c.get("name"))
        if stem in trees:
            idx2stem[c["index"]] = stem
    stem2idx = {s: i for i, s in idx2stem.items()}

    # .dat side, split by whether the command is civ-owned or global.
    own_enable = collections.defaultdict(set)
    global_enable = set()
    upgrade_pairs = set()      # (from_unit, to_unit) via type 3
    owner_of_tech = {}
    for ti, t in enumerate(techs):
        owner_of_tech[ti] = t.get("civ")
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            _ty, a, b, cc, dd = r["raw"]
            if r["type"] == 2 and b == 1:
                if t.get("civ") is None or t.get("civ") < 0:
                    global_enable.add(a)
                else:
                    own_enable[t["civ"]].add(a)
            elif r["type"] == 3 and a is not None and b is not None:
                upgrade_pairs.add((a, b))

    print("distinct units upgraded into (type 3 targets): %d" % len({b for _a, b in upgrade_pairs}))
    print()

    # For each (civ, unit the civ can build), is there an enable or an upgrade?
    gap = []
    covered_by_enable = 0
    covered_by_upgrade = 0
    covered_by_global = 0
    total = 0
    for stem, tr in sorted(trees.items()):
        idx = stem2idx.get(stem)
        for row in CT.unit_rows(tr):
            nid = row.get("Node ID")
            if nid is None or not CT.can_build(tr, nid):
                continue
            total += 1
            if idx is not None and nid in own_enable.get(idx, set()):
                covered_by_enable += 1
            elif nid in global_enable:
                covered_by_global += 1
            elif any(t == nid for _f, t in upgrade_pairs):
                covered_by_upgrade += 1
            else:
                gap.append((stem, nid, CT.node_status(tr, nid)))
    print("(civ, buildable-unit) pairs: %d" % total)
    print("  covered by a civ-owned enable:      %d" % covered_by_enable)
    print("  covered by a GLOBAL enable:         %d" % covered_by_global)
    print("  covered only by being an upgrade target: %d" % covered_by_upgrade)
    print("  NOT covered by any effect command:  %d" % len(gap))
    print()

    if gap:
        c = collections.Counter(n for _s, n, _st in gap)
        print("uncovered units, by frequency: %s"
              % [((sem.units.get(n).en if sem.units.get(n) else "?"), n, k)
                 for n, k in c.most_common(12)])
        print()
        print("samples:")
        for s, n, st in gap[:12]:
            u = sem.units.get(n)
            print("    %-14s unit %-5s %-26s status=%s"
                  % (s, n, (u.en if u else "?"), st))
    print()

    # The decisive concrete case: Hand Cannoneer.  Which of its 24 builders
    # owns a type-2 enable, and would a grant to a civ with neither mechanism
    # reach parity with them?
    print("Hand Cannoneer (unit 5):")
    for stem in CT.builders(trees, 5):
        idx = stem2idx.get(stem)
        has = (idx is not None and 5 in own_enable.get(idx, set())) or (5 in global_enable)
        print("    %-14s enable=%s" % (stem, has))
    print()

    # And the reverse: a unit granted by unit.availability would inherit the
    # donor's row.  Does the RECEIVER own no enable either?  If so, the grant
    # changes only the tree.
    _b = CT.builders(trees, 331)      # Trebuchet (Packed) style line, if present
    print("units for which NO civ owns an enable and none is global: %d"
          % len({n for _s, n, _st in gap}
                - {n for v in own_enable.values() for n in v}
                - global_enable))
    return 0


if __name__ == "__main__":
    sys.exit(main())
