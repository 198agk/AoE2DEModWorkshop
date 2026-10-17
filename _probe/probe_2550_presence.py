# -*- coding: utf-8 -*-
r"""Does the British civilization even HAVE a unit-2550 object in the shipped .dat?

Everything v5/v6 did assumed it does.  If it does not, then enabling unit 2550
for the British enables nothing, and the only thing that ever made the button
appear was the extra command hung on tech 263 -- which is Castle-triggered.

The check is deliberately blunt: print the keys of a parsed unit object, then
look for 2550 by every plausible accessor instead of one.
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import aoe2mod.dat.parser as P                                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
UNIT = 2550


def load(path):
    raw, _how = P.load_dat(path)
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    return raw, pr.stats


def main():
    raw, st = load(DAT)
    civs = st["civs"]
    print("civs: %d" % len(civs))

    for ci in (1, 21):
        civ = civs[ci]
        print()
        print("=" * 74)
        print("civ[%d] name=%r" % (ci, civ.get("name")))
        print("  civ keys: %s" % sorted(civ.keys()))
        units = civ.get("units")
        print("  units type=%s len=%s" % (type(units).__name__,
                                          len(units) if units is not None else None))
        if not units:
            continue
        uid0 = units[0]
        print("  units[0] type=%s" % type(uid0).__name__)
        if isinstance(uid0, dict):
            print("  units[0] keys: %s" % sorted(uid0.keys()))
            print("  units[0] id=%r name=%r" % (uid0.get("id"), uid0.get("name")))
        # search by every plausible key
        hits = []
        for u in units:
            if not isinstance(u, dict):
                continue
            if u.get("id") == UNIT or u.get("ID") == UNIT:
                hits.append(u)
        print("  units with id == %d: %d" % (UNIT, len(hits)))
        for u in hits:
            print("     keys: %s" % sorted(u.keys()))
            for k in sorted(u.keys()):
                if k.startswith("_"):
                    continue
                print("     %-24s %r" % (k, u[k]))
        ids = set()
        for u in units:
            if isinstance(u, dict):
                ids.add(u.get("id"))
        print("  min id=%s max id=%s" % (min(ids), max(ids)))
        print("  %d in ids: %s" % (UNIT, UNIT in ids))
        ids_sorted = sorted(i for i in ids if isinstance(i, int))
        print("  ids near 2550: %s" % [i for i in ids_sorted if 2540 <= i <= 2560])


if __name__ == "__main__":
    main()
