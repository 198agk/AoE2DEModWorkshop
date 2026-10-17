# -*- coding: utf-8 -*-
"""Two questions that must be answered before adding an availability insight.

DESIGN QUESTION 1 -- the civ-name bridge.
`civtechtrees.load_trees` keys each tree by the file's own `civ_id`, while every
other part of the product names civs the way the `.dat` does (`British`, `Mayan`,
`French`).  A lookup that joins the two must be exact for ALL 63 civs: one wrong
stem silently reports "this civ cannot have it" (or worse, edits the wrong civ's
file).  `CIV_FILE_OVERRIDES` was written from the handful of civs whose names
differ -- this measures whether it is actually complete.

DESIGN QUESTION 2 -- the scale of what a user could ask for.
"Let civ X build unit Y" is only worth a UI if the answer is interesting for many
(X, Y) pairs.  Count, over the shipped data: how many unit nodes each civ is
MISSING that at least one other civ HAS (the grantable set), and how many each
civ HAS that another civ lacks (the revocable set).  Also count the strict
per-civ totals, because "62 x 287" would be a useless worst case.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.dat import locate as L                              # noqa: E402
from aoe2mod.game import civtechtrees as CT                      # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    import aoe2mod.api as A
    tk = A.open_toolkit()
    tk._ensure()
    dat_civs = [c.get("name") for c in tk._civs]

    trees = CT.load_trees(GAME)
    print("tree keys     : %d" % len(trees))
    print("dat civ names : %d" % len(dat_civs))
    print()

    # ---- 1. does the bridge hold for every civ, both directions? ---------
    missing = []
    for name in dat_civs:
        stem = CT.civ_file_stem(name)
        if stem not in trees:
            missing.append((name, stem))
    print("dat civs whose stem is NOT a tree key: %d %s"
          % (len(missing), missing[:10]))
    extra = [k for k in trees if k not in {CT.civ_file_stem(n) for n in dat_civs}]
    print("tree keys no dat civ maps to        : %d %s" % (len(extra), extra[:10]))
    print()
    if missing:
        print("The bridge is INCOMPLETE.  Note that Gaia is expected here: it is a")
        print("dat civ with no CivTechTrees file (62 files for 63 civs).")
    print("dat civs with no file (expected: Gaia only): %s"
          % [n for n, s in missing])
    print()

    # ---- 2. scale of the grantable / revocable sets ----------------------
    unit_nodes = set()
    for t in trees.values():
        for r in CT.unit_rows(t):
            unit_nodes.add(r.get("Node ID"))
    print("distinct unit nodes across all files: %d" % len(unit_nodes))

    has_by_civ = {c: {r.get("Node ID") for r in CT.unit_rows(t)}
                  for c, t in trees.items()}
    sizes = Counter(len(v) for v in has_by_civ.values())
    print("per-civ unit-node counts: %s" % dict(sorted(sizes.items())))
    print()

    grantable = []
    revocable = []
    for civ, has in has_by_civ.items():
        others = set()
        for c2, h2 in has_by_civ.items():
            if c2 != civ:
                others |= h2
        g = others - has
        r = has - set().union(*[h for c2, h in has_by_civ.items() if c2 != civ])
        grantable.append((civ, len(g)))
        revocable.append((civ, len(r)))
    print("GRANTABLE (this civ lacks, someone has) per civ:")
    gs = [n for _c, n in grantable]
    print("   min %d  max %d  mean %.1f  total pairs %d"
          % (min(gs), max(gs), sum(gs) / len(gs), sum(gs)))
    print("   top: %s" % sorted(grantable, key=lambda x: -x[1])[:5])
    print("REVOCABLE (this civ has, someone lacks) per civ:")
    rs = [n for _c, n in revocable]
    print("   min %d  max %d  mean %.1f  total pairs %d"
          % (min(rs), max(rs), sum(rs) / len(rs), sum(rs)))
    print("   top: %s" % sorted(revocable, key=lambda x: -x[1])[:5])
    print()
    print("For contrast, the WORST-CASE pair count would be")
    print("   %d civs x %d nodes = %d, so the real numbers above are the ones"
          % (len(trees), len(unit_nodes), len(trees) * len(unit_nodes)))
    print("   a UI must be built around (most pairs are 'already has it').")
    return 0


if __name__ == "__main__":
    sys.exit(main())
