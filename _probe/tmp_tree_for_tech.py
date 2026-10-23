# -*- coding: utf-8 -*-
"""Can a NEW technology get a row in the tech tree?

`_plan_new_tech` warns the player that it cannot:

    它不会出现在科技树里：科技树的 Node ID 与单位共用一套整数，编号 1510
    在科技树里已经是单位「City Gate NE (Rubble)」，所以这项科技只有 .dat
    那一半（能被研究，但科技树面板上没有它）

That sentence contradicts `aoe2mod/game/civtechtrees.py`, which spends 22 lines
of comment (``UNIT_USE_TYPES`` / ``TECH_USE_TYPES``) proving the opposite: a
Node ID is a UNIT id in a Unit row and a TECH id in a Tech row, and rows live in
the same list separated only by ``Use Type``.  If that is true, a Tech row with
Node ID 1510 does NOT collide with the Unit row 1510, and the tree half is
reachable.

This file measures which of the two statements is true.  It writes nothing.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT          # noqa: E402
from aoe2mod.game import locations as G             # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
FAILS = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name + ((" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(name)


def main():
    trees = CT.load_trees(GAME)
    print("trees: %d" % len(trees))

    # A. what a Tech row looks like -- the donor's row is the template
    print("\n=== A. a shipped technology has a tree row, and it says Use Type Tech")
    # The tree files are keyed by the FILE stem, which is the engine's own
    # spelling ("BRITONS", not the .dat's "British").  Asking for the wrong one
    # returns None and every measurement below would be about nothing.
    brit = trees.get("BRITONS")
    check("BRITONS is a key in the tree set", brit is not None)
    looms = CT.tech_rows(brit)
    ids = sorted(int(r.get("Node ID")) for r in looms if r.get("Node ID") is not None)
    check("BRITISH has tech rows at all", bool(ids), "0 rows")
    check("its largest tech node id stays inside the 1510-record array",
          ids and max(ids) < 1510, "max=%r" % (ids[-1] if ids else None))
    row22 = CT.row_for(brit, 22, use_types=CT.TECH_USE_TYPES)
    check("Loom (tech 22) has a row", row22 is not None)
    if row22 is not None:
        print("  row 22: %s" % json.dumps(row22, ensure_ascii=False, sort_keys=True)[:300])
        check("and its Use Type is Tech", row22.get("Use Type") == "Tech",
              repr(row22.get("Use Type")))

    # B. is node id 1510 free IN THE TECH SPACE?
    print("\n=== B. node id 1510 in the TECH space, in every civ")
    per_civ = {}
    unit_space = {}
    for name, tree in trees.items():
        t = CT.row_for(tree, 1510, use_types=CT.TECH_USE_TYPES)
        u = CT.row_for(tree, 1510, use_types=CT.UNIT_USE_TYPES)
        per_civ[name] = t
        unit_space[name] = u
    taken = [n for n, r in per_civ.items() if r is not None]
    taken_u = [n for n, r in unit_space.items() if r is not None]
    print("  tech rows with node 1510 : %d of %d civs" % (len(taken), len(trees)))
    print("  unit rows with node 1510 : %d of %d civs" % (len(taken_u), len(trees)))
    check("no civilization has a TECH row at node 1510", not taken,
          str(taken[:5]))
    check("but the UNIT space does hold 1510 -- which is the collision the "
          "warning claims", bool(taken_u), str(taken_u[:5]))
    if taken_u:
        r = unit_space[taken_u[0]]
        print("  the unit row everyone shares: %s" % json.dumps(
            r, ensure_ascii=False, sort_keys=True)[:240])

    # C. every id a new tech can take, checked in both spaces
    print("\n=== C. the full array end, per space")
    worst = []
    for nid in range(1510, 1516):
        t_hits = sum(1 for tree in trees.values()
                     if CT.row_for(tree, nid, use_types=CT.TECH_USE_TYPES))
        u_hits = sum(1 for tree in trees.values()
                     if CT.row_for(tree, nid, use_types=CT.UNIT_USE_TYPES))
        worst.append((nid, t_hits, u_hits))
        print("  node %d : tech rows %d, unit rows %d" % (nid, t_hits, u_hits))
    check("every id from the array end is free in the tech space",
          all(t == 0 for _n, t, _u in worst), str(worst))

    # D. the writer can append a Tech row without disturbing the file
    print("\n=== D. grant() with the tech use-type writes a Tech row")
    buf = io.StringIO()
    row, warns = CT.grant(brit, 1510, row22, use_types=CT.TECH_USE_TYPES)
    check("a row came back", row is not None)
    check("with Node ID 1510", row.get("Node ID") == 1510, repr(row.get("Node ID")))
    check("and Use Type Tech", row.get("Use Type") == "Tech",
          repr(row.get("Use Type")))
    check("and it carries the donor's name string id",
          row.get("Name String ID") == row22.get("Name String ID"),
          "%r vs %r" % (row.get("Name String ID"), row22.get("Name String ID")))
    check("the tech-node collision is NOT one of the warnings",
          not any("1510" in w and "单位" in w for w in warns), str(warns))
    print("  warnings: %s" % ("; ".join(warns)[:300] or "(none)"))
    check("the civ keeps its own 22 row untouched",
          CT.row_for(brit, 22, use_types=CT.TECH_USE_TYPES) is row22)

    # E. so the sentence the player reads today is false
    print("\n=== E. what the product says now")
    sys.path.insert(0, ROOT)
    from aoe2mod import api as A
    tk = A.open_toolkit(GAME)
    plan = tk.plan({"intent": "tech.create", "donor": 22, "name": "快速采集"})
    warns = [str(w) for w in (plan.get("warnings") or ())]
    tree_warn = [w for w in warns if "科技树" in w]
    print("  tree warning: %s" % (tree_warn or "(none)"))
    check("the product warns it will not be in the tree", bool(tree_warn))
    check("and the reason it gives is a UNIT-space collision",
          bool(tree_warn) and "单位" in tree_warn[0], str(tree_warn))

    if FAILS:
        print("\nTREE FOR TECH: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("\nTREE FOR TECH: A TECH ROW AT 1510 COLLIDES WITH NOTHING -- "
          "THE TECH SPACE IS EMPTY PAST 1509")
    return 0


if __name__ == "__main__":
    sys.exit(main())
