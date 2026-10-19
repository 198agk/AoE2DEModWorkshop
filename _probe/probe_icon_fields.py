# -*- coding: utf-8 -*-
"""probe_icon_fields.py -- how many icon-ish fields does a unit record carry?

The section question ("Units[28] is a trebuchet, Buildings[28] is a Town Center,
and BOTH unit 71 the TC and unit 42 the Trebuchet say icon_id=28") cannot be
settled by type or by name if one number has to serve both.  So first check
whether the record carries more than one icon field -- an older build-menu icon
next to a current one would explain the collision.

Prints every key of a few records, and any key whose value differs between the
TC and the Trebuchet.
"""
from __future__ import print_function

import codecs
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

WANT = [12, 71, 42, 83, 4, 682, 446, 263]


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

    keys = sorted(by_id.get(12) or {})
    print("unit record has %d keys:" % len(keys))
    print("  %s" % keys)

    iconish = [k for k in keys if "icon" in k.lower() or "dll" in k.lower()
               or "graphic" in k.lower() or "name" in k.lower()]
    print("\nicon / name / graphic fields: %s" % iconish)

    print("\nvalues for the interesting records:")
    hdr = ["id"] + iconish
    print("  " + "  ".join("%-22s" % h for h in hdr))
    for i in WANT:
        u = by_id.get(i) or {}
        row = ["%-22s" % i]
        for k in iconish:
            row.append("%-22s" % repr(u.get(k))[:22])
        print("  " + "  ".join(row))

    # how many icon-carrying fields are non-zero across the whole set?
    for k in iconish:
        vals = set()
        for u in by_id.values():
            # `_dll_names` is a set, so a bare `vals.add(u.get(k))` raised
            # TypeError: unhashable type: 'set' -- the probe crashed after it had
            # already printed everything above, which looks like a clean finish.
            v = u.get(k)
            vals.add(v if isinstance(v, (str, int, float, type(None))) else repr(v))
            if len(vals) > 8:
                break
        print("\n%-24s distinct(sample)=%r" % (k, sorted(vals, key=str)[:8]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
