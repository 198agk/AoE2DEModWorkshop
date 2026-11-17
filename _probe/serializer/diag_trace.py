# -*- coding: utf-8 -*-
"""Show the emission trace leading into the first model-vs-raw divergence.

`Writer(first_mismatch)` keeps the last 24 trace entries, but only when
trace=True.  The byte before the divergence is what tells us which write_* call
emitted the wrong width -- far more useful than re-reading the code.
"""
import os
import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
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
    p = parse_dat.Parser(bytearray(raw))
    stats = p.parse()

    # trace=True records (out_pos, kind, n, cur) for every emission.
    data, rep = write_dat.serialize_dat.__wrapped__(stats, raw=raw, strict=True,
                                                    gv=None) \
        if hasattr(write_dat.serialize_dat, "__wrapped__") else (None, None)

    # serialize_dat does not expose trace, so drive the Writer directly.
    w = write_dat.Writer(raw, strict=True, trace=True, gv=stats["game_version"])
    # Re-run the body by calling serialize_dat with a traced writer: simplest is
    # to monkeypatch Writer construction.
    import types
    orig_writer = write_dat.Writer

    class TracedWriter(orig_writer):
        __slots__ = ()

    created = {}

    def factory(*a, **k):
        k["trace"] = True
        inst = orig_writer(*a, **k)
        created["w"] = inst
        return inst

    write_dat.Writer = factory
    try:
        out, rep = write_dat.serialize_dat(stats, raw=raw, strict=True)
    finally:
        write_dat.Writer = orig_writer

    tw = created["w"]
    print("out size      : %d  delta %+d" % (len(out), len(out) - len(raw)))
    print("raw consumed  : %d / %d" % (rep["raw_consumed"], rep["raw_size"]))
    print("mismatches    : %d" % rep["model_vs_original_mismatches"])

    fm = rep["first_model_mismatch"]
    if fm:
        rpos, n, kind, b, seg, cur, log = fm
        print("\nfirst mismatch: raw 0x%08X n=%d kind=%s cur=%s" % (rpos, n, kind, cur))
        print("   wrote %s" % b.hex())
        print("   raw   %s" % seg.hex())
        print("\n-- emission trace leading in (last 24) --")
        for (opos, k, nn, c) in log:
            print("   out 0x%08X  %-7s n=%-4d %s" % (opos, k, nn, c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
