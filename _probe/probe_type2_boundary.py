# -*- coding: utf-8 -*-
"""Type 2's clean subset, the irregular rows, and what each would cost.

`probe_type2_shape.py` established that type 2 is NOT uniformly shaped: slot B
takes a third value (-1) and four rows use slots C/D.  That is the same situation
as the Resource Modifier family, which is implemented for the regular shape and
keeps refusing 35 irregular rows.  This probe draws that boundary precisely:

  * the CLEAN predicate, and how many rows/technologies it covers;
  * the irregular rows described one by one, so the refusal is a sentence about
    real data rather than a shrug;
  * whether any irregular row sits on a technology whose ONLY other command is
    regular (which decides whether a strict guard costs a whole technology).
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
from aoe2mod.intent import compiler as C                       # noqa: E402
from aoe2mod.semantic import index as SI                       # noqa: E402


def is_clean(r):
    """The predicate the implementation will use, stated once."""
    t, a, b, c, d = r["raw"]
    return (t == 2 and b in (0, 1) and c == -1 and d == 0.0
            and a is not None and a != -1)


def _disp(e):
    """Entity or None -> a printable name. The index is keyed by INT."""
    if e is None:
        return "?"
    return e.en or e.internal or "?"


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    effects, _ = L.locate_effects(raw)
    techs = L.locate_techs(raw, tail, gv)
    sem = SI.index()

    unit_ids = set()
    for civ in tk._civs:
        for u in civ.get("units") or ():
            unit_ids.add(u.get("id"))

    all_type2, clean, irregular = [], [], []
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["editable"] or r["type"] != 2:
                continue
            all_type2.append((ti, r))
            (clean if is_clean(r) else irregular).append((ti, r))

    print("type 2 rows: %d  clean: %d  irregular: %d"
          % (len(all_type2), len(clean), len(irregular)))
    print("technologies touched: all %d / clean %d / irregular-only %d"
          % (len({ti for ti, _r in all_type2}),
             len({ti for ti, _r in clean}),
             len({ti for ti, _r in irregular}
                 - {ti for ti, _r in clean})))
    print()

    print("clean predicate: type == 2 and slot B in {0,1} and slot C == -1 "
          "and slot D == 0 and slot A is a real unit")
    bad_a = [ (ti, r) for ti, r in clean if r["raw"][1] not in unit_ids ]
    print("  clean rows whose slot A is not a real unit id: %d" % len(bad_a))
    print("  slot B distribution in the clean set: %s"
          % collections.Counter(r["raw"][2] for _ti, r in clean).most_common())
    print()

    print("irregular rows, one per line (these keep their refusal):")
    for ti, r in sorted(irregular, key=lambda x: x[0]):
        e = sem.techs.get(ti)
        print("  tech[%-4d] %-26s raw=%s  civ=%s"
              % (ti, (_disp(e))[:26],
                 tuple(str(x) for x in r["raw"]), techs[ti].get("civ")))
    print()

    # Does a strict guard cost a whole technology?
    clean_techs = {ti for ti, _r in clean}
    irreg_techs = {ti for ti, _r in irregular}
    lost = sorted(irreg_techs - clean_techs)
    print("technologies a strict guard would leave with NO editable command: %d"
          % len(lost))
    for ti in lost[:12]:
        e = sem.techs.get(ti)
        print("    tech[%-4d] %s" % (ti, _disp(e)))
    print()

    # How many NEW technologies does the clean subset unblock?
    have = collections.Counter()
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["editable"]:
                have[ti] += 1
    new_t = {ti for ti in clean_techs if have[ti] == 0}
    vis = sum(1 for ti in new_t if (sem.techs.get(ti) and sem.techs[ti].en))
    print("technologies whose FIRST editable command would be a clean type 2: %d"
          % len(new_t))
    print("  of those, named by the semantic table (player-visible): %d" % vis)
    print()

    # Which units does the clean subset touch, and how are the two directions used?
    print("distinct units in the clean set: %d" % len({r["raw"][1] for _t, r in clean}))
    print("B=1 (enable) rows: %d   B=0 (disable) rows: %d"
          % (len([1 for _t, r in clean if r["raw"][2] == 1]),
             len([1 for _t, r in clean if r["raw"][2] == 0])))
    print("sample of B=0 rows (an existing unlock being turned OFF):")
    for ti, r in [x for x in clean if x[1]["raw"][2] == 0][:8]:
        e = sem.techs.get(ti)
        u = sem.units.get(r["raw"][1])
        print("    tech[%-4d] %-26s disables unit %-5s %s"
              % (ti, (_disp(e))[:26],
                 r["raw"][1], (_disp(u))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
