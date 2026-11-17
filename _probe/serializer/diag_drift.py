# -*- coding: utf-8 -*-
"""Locate the first writer function whose emitted width stops matching the raw
stream.

Every `write_*` function is wrapped so we can watch `w.pos - w.rpos` (output
offset minus raw cursor).  For a byte-exact writer that drift is 0 at all times;
the first function that moves it is the one whose layout is wrong -- which is a
measurement, not a guess about which edit broke things.
"""
import collections
import _gamepaths as GP
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(PROBE, "datparse"))

import parse_dat
import write_dat

BASE = (GP.DAT_DIR +
        r"\empires2_x2_p1.dat")


def main():
    raw, how = parse_dat.load_dat(BASE)
    print("raw size      : %d" % len(raw))

    p = parse_dat.Parser(bytearray(raw))
    stats = p.parse()
    print("parsed        : final %d  leftover %d"
          % (p.r.pos, len(raw) - p.r.pos))

    events = []            # (seq, name, d0, d1, cur)
    counts = collections.Counter()
    totals = collections.Counter()

    def wrap(name, fn):
        def wrapper(w, *a, **k):
            if not isinstance(w, write_dat.Writer):
                return fn(w, *a, **k)
            d0 = w.pos - w.rpos
            r = fn(w, *a, **k)
            d1 = w.pos - w.rpos
            if d1 != d0:
                counts[name] += 1
                totals[name] += (d1 - d0)
                if len(events) < 40:
                    events.append((len(events), name, d0, d1, w.cur))
            return r
        wrapper.__name__ = name
        return wrapper

    for name in sorted(list(vars(write_dat))):
        if not name.startswith("write_") or name == "write_dat_file":
            continue
        obj = getattr(write_dat, name)
        if callable(obj):
            setattr(write_dat, name, wrap(name, obj))

    out, rep = write_dat.serialize_dat(stats, raw=raw, strict=True)
    print("out size      : %d   delta %+d" % (len(out), len(out) - len(raw)))
    print("mismatches    : %s" % rep.get("mismatches"))

    print("\n-- drift total per function (bytes of accumulated drift) --")
    for name, tot in totals.most_common(20):
        print("  %+10d  x%-8d %s" % (tot, counts[name], name))

    print("\n-- first 40 drift events, in call order --")
    for (seq, name, d0, d1, cur) in events:
        print("  #%-3d %-28s drift %+d -> %+d   (%s)" % (seq, name, d0, d1, cur))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
