# -*- coding: utf-8 -*-
"""Which mechanism actually governs per-civ unit availability?

Candidate A: a per-civ BYTE in the unit record (`Enabled` / `Disabled`, the two
             u8 fields read by `parse_dat.read_unit()` after OldPortraitPict).
Candidate B: an effect command `type 2 启用/禁用单位` on one of the civ's techs.

`probe_unit_availability.py` proved the record offsets (136,861 records, 0
icon_id mismatches) and found the record byte varies per civ for only **7** ids
(45/72/805/2148/2172/2433/2434), while 2693 ids carry the same value in all 63
civs.  That is far too few to express "the Goths get Huskarl, the Britons do
not", so the record byte is NOT the general mechanism.

This file settles what is: for every effect command of type 2, report the
owning tech, its `.civ` field, and the unit it targets -- because a type-2
command on a tech with `civ == -1` is a GLOBAL toggle, whereas one on a tech
belonging to a single civ is how that civ alone gets a unit.
"""
import collections
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                          # noqa: E402
import aoe2mod.intent.compiler as C                              # noqa: E402
from aoe2mod.dat import locate as L                              # noqa: E402


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    techs = L.locate_techs(raw, tail, gv)
    effects, _ = L.locate_effects(raw)
    civs = tk._civs
    civ_name = [c.get("name") for c in civs]

    for ti in (85, 399, 204, 1):
        t = techs[ti]
        civ = t.get("civ")
        print("tech %-4d name=%-28s civ=%-5s (%s) effect_id=%s"
              % (ti, t.get("name"), civ,
                 "GLOBAL" if (civ is None or civ < 0) else civ_name[civ],
                 t.get("effect_id")))
    print()

    # Group every type-2 command by the owning tech's civ.
    by_civ = collections.Counter()
    global_units = collections.Counter()
    civ_units = collections.defaultdict(collections.Counter)
    total = 0
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, ix=None):
            if r["type"] != 2:
                continue
            total += 1
            civ = t.get("civ")
            if civ is None or civ < 0:
                by_civ["GLOBAL"] += 1
                global_units[r["raw"][1]] += 1
            else:
                by_civ[civ_name[civ]] += 1
                civ_units[civ_name[civ]][r["raw"][1]] += 1
    print("type-2 commands: %d" % total)
    print("by owning-tech civ (top 12): %s" % by_civ.most_common(12))
    print()

    # The decisive comparison: is "does civ X have unit U" explained by a
    # type-2 command on a civ-X tech?
    print("GLOBAL toggles (civ == -1) target %d distinct units; sample: %s"
          % (len(global_units), global_units.most_common(8)))
    print()
    for name in ("Goths", "British", "Aztecs"):
        cu = civ_units.get(name) or {}
        print("%-8s civ-owned type-2 commands: %d  units=%s"
              % (name, sum(cu.values()), dict(cu.most_common(8))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
