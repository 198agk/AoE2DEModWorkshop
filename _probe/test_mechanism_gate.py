# -*- coding: utf-8 -*-
"""Pin the test that decides WHICH mechanism gates buildability.

Two mechanisms could plausibly make a unit buildable for a civilization: a
`type 2` effect command in the `.dat`, and a row in `CivTechTrees/<CIV>.json`.
Both exist in the shipped data, so their coexistence proves nothing.  This file
pins the discriminating measurement so that a future round cannot quietly
describe one as the other.

The shipped-data measurements below are still true, and they still disprove the
simple readings of "type 2 gates buildability":

  * An enable is NOT necessary *as a mere presence*.  War Galley (unit 21) has
    56 builders and not one of them owns an enable command -- they have a tree
    row and nothing else.
  * An enable is NOT sufficient *as a mere presence*.  Hand Cannoneer (unit 5)
    is blocked (`NotAvailable`) for 38 civs and every one of those 38 owns an
    enable (a global one).  So owning an enable does not grant the ability.

WHAT THIS FILE GOT WRONG, AND WHEN: it used to conclude "therefore the per-civ
gate is the tech-tree row".  Two in-game runs refuted that inference, and the
distinction it missed is ORDER, not presence:

  * `dsh test v15` (2026-10-19): a mod carrying two `CivTechTrees/*.json`
    rewrites over a byte-identical `.dat`, with the engine log confirming the
    mod loaded, moved the build menu in NEITHER direction.  The tree row is
    read (the tech-tree PREVIEW screen reads it) but it does not gate the
    build menu.
  * `dsh test v7` / `v17` (2026-10-16 / 2026-10-19): a `.dat` `type 2` command
    hung on a technology the civ actually owns DOES gate it -- enable makes the
    button appear, disable removes it, and when two commands touch the same
    unit the LAST ONE TO FIRE wins (v17 hung the same disable on a 0:00 carrier
    and on a Castle-age carrier; the 0:00 one lost to the global enable, the
    Castle-age one won).

So "type 2 is not a per-civ lever" is false.  What the data below really shows
is that a `type 2` command counts only when the technology carrying it fires,
and nothing in the shipped data lets you read that off the command alone.

It also pins the boundary of the type-2 family itself, so that the irregular
rows stay refused until there is evidence for them.
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

FAILS = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(label)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    effects, _ = L.locate_effects(raw)
    techs = L.locate_techs(raw, tail, gv)
    trees = CT.load_trees(tk.game_root)

    stem2idx = {}
    for c in tk._civs:
        stem = CT.civ_file_stem(c.get("name"))
        if stem in trees:
            stem2idx[stem] = c["index"]

    own = collections.defaultdict(set)
    glob = set()
    for t in techs:
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["type"] != 2 or r["raw"][2] != 1:
                continue
            u = r["raw"][1]
            owner = t.get("civ")
            if owner is None or owner < 0:
                glob.add(u)
            else:
                own[owner].add(u)

    def owns_enable(stem, uid):
        idx = stem2idx.get(stem)
        return (idx is not None and uid in own.get(idx, set())) or uid in glob

    print("the enable command is NOT necessary for a unit to be buildable:")
    build21 = CT.builders(trees, 21)
    no_en = [s for s in build21 if not owns_enable(s, 21)]
    check(len(build21) > 50, "War Galley has many builders", len(build21))
    check(no_en == build21,
          "and not one of them owns an enable command", len(no_en))
    check(not any(CT.node_status(trees[s], 21) == "NotAvailable" for s in trees),
          "no civ lists War Galley as NotAvailable")

    print()
    print("the enable command is NOT sufficient either:")
    blocked5 = [s for s, tr in trees.items()
                if CT.node_status(tr, 5) == "NotAvailable"]
    with_en = [s for s in blocked5 if owns_enable(s, 5)]
    check(len(blocked5) > 20, "Hand Cannoneer is blocked for many civs",
          len(blocked5))
    check(with_en == blocked5,
          "and every blocked civ owns an enable anyway", len(with_en))
    check(not CT.can_build(trees[blocked5[0]], 5),
          "so owning one does not make it buildable",
          blocked5[0])

    print()
    print("=> the SHIPPED data is consistent with the tree row being the model "
          "of who may build what:")
    check(CT.can_build(trees["BRITONS"], 5) is False
          and CT.can_build(trees["TURKS"], 5) is True,
          "can_build tracks the row, not the (global) enable")
    check(len(glob) > 0, "global enables exist and span civs", len(glob))
    print("   NOTE: this is a statement about the shipped files, NOT about what")
    print("   the engine consults.  v15 showed a mod-side tree rewrite does not")
    print("   move the build menu; v7/v17 showed a `type 2` command on a tech")
    print("   the civ owns does, last-to-fire wins.  See the module docstring.")

    print()
    print("the type-2 family boundary (irregular rows stay refused):")
    rows = []
    for t in techs:
        r = C.effect_rows(effects, t, fanout=None, ix=None)
        rows.extend(x for x in r if x["type"] == 2)
    clean = [x for x in rows
             if x["raw"][2] in (0, 1) and x["raw"][3] == -1 and x["raw"][4] == 0]
    irregular = [x for x in rows if x not in clean]
    check(len(rows) == 192, "type 2 has 192 rows", len(rows))
    check(len(clean) == 165, "of which 165 are regular", len(clean))
    check(len(irregular) == 27, "and 27 are irregular", len(irregular))
    bad_b = sorted({x["raw"][2] for x in irregular})
    # The irregular group is *defined* by slot B being -1: 23 of them carry
    # nothing else unusual, and 4 of them additionally carry (C=13, D=0.85).
    # Conditioning the payload check on `raw[2] in (0,1)` would look for the
    # payload in the wrong group and always find nothing.
    check(bad_b == [-1],
          "every irregular row has the unknown slot-B value (-1)", bad_b)
    cds = sorted({(x["raw"][3], x["raw"][4]) for x in irregular
                  if x["raw"][3] != -1})
    # Slot D is a float32, so its repr is 0.8500000238418579 and not 0.85; the
    # claim being pinned is "one unexplained payload shape", not a float literal.
    check(len(cds) == 1 and cds[0][0] == 13 and 0.0 < cds[0][1] < 1.0,
          "and 4 of them carry an unexplained (C, D) payload", cds)
    check(len([x for x in irregular if x["raw"][3] != -1]) == 4,
          "exactly four rows carry that payload",
          len([x for x in irregular if x["raw"][3] != -1]))
    check(all(x in ("", None) or isinstance(x["raw"][1], int) for x in clean),
          "every regular row names a unit in slot A")

    print()
    if FAILS:
        print("MECHANISM GATE: FAILED -> %s" % FAILS)
        return 1
    print("MECHANISM GATE: in the SHIPPED data the tree row is what models "
          "buildability; a `type 2` command is neither necessary nor "
          "sufficient BY ITS MERE PRESENCE.")
    print("MECHANISM GATE (corrected 2026-10-19): that is not the whole gate. "
          "A `type 2` command on a technology the civ owns DOES move the build "
          "menu, and the last one to fire wins -- v7 (enable), v17 (disable). "
          "A mod-side tree rewrite does not (v15).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
