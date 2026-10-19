# -*- coding: utf-8 -*-
"""probe_train_locations.py -- what IS the shape of train_locations?

probe_icon_produced_rule.py assumed each entry is a dict with a "unit" key (or a
4-tuple with the unit in slot 3) and got `units trained by something: 0`, i.e. it
read nothing at all.  Before building any rule on "is this trainable", print the
raw value for producers we know train things (Barracks 12, Castle 82, TC 71,
Archery Range 87).
"""
from __future__ import print_function

import codecs
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

WANT = [12, 82, 71, 87, 101, 45, 50, 83]


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)

    for i in WANT:
        u = by_id.get(i) or {}
        print("\nunit %s  name=%r  type=%r" % (i, u.get("name"), u.get("type")))
        tl = u.get("train_locations")
        print("  type of train_locations: %s" % type(tl).__name__)
        if isinstance(tl, (list, tuple)):
            print("  len=%d" % len(tl))
            for e in list(tl)[:8]:
                print("    %r  (%s)" % (e, type(e).__name__))
        else:
            print("  raw=%r" % (tl,))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
