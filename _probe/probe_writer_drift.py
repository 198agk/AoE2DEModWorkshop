"""Isolate the mechanism: does changing a model string's LENGTH desync the raw cursor?

The writer keeps two cursors: `pos` (output) and `rpos` (input).  `_emit`
advances BOTH by the emitted length.  That is exactly right when every model
field has the same width as the raw field it replaces -- which is true for every
in-place patch this project has ever done -- and it is silently wrong the moment
a field changes width, because `rpos` then points into the middle of the next
raw field and every later `op()` reads shifted bytes.

This probe measures the drift instead of arguing about it.

Run:
  python _probe/probe_writer_drift.py
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DAT = os.path.join(r"D:\Games\Steam\steamapps\common\AoE2DE",
                   "resources", "_common", "dat", "empires2_x2_p1.dat")


def main():
    import aoe2mod.dat.parser as P
    import aoe2mod.dat.writer as W

    data, _how = P.load_dat(DAT)
    p = P.Parser(data)
    p.parse()
    stats = p.stats

    print()
    print("A  NO EDIT AT ALL (the control)")
    out0, rep0 = W.serialize_dat(stats, raw=data, gv=P.GV_C32)
    print("   identical to the shipped stream: %s" % (out0 == data))
    print("   model-vs-raw mismatches: %s" % (rep0.get("model_vs_original_mismatches"),))

    # One record whose file string we lengthen by 4 characters.
    gfx = stats["graphics"]
    src = next(g for g in gfx if g.get("id") == 627)
    old, new = src["file"], src["file"][:-3] + "xyz_x1"
    print()
    print("B  ONE STRING LENGTHENED BY %+d BYTES" % (len(new) - len(old)))
    print("   %r -> %r" % (old, new))
    src["file"] = new
    out1, rep1 = W.serialize_dat(stats, raw=data, gv=P.GV_C32)
    print("   output delta %+d (a correct writer would emit exactly %+d)"
          % (len(out1) - len(out0), len(new) - len(old)))
    print("   mismatches reported: %s" % (rep1.get("model_vs_original_mismatches"),))
    fm = rep1.get("first_model_mismatch")
    if fm:
        print("   first mismatch at raw offset %d, width %d, %s" % (fm[0], fm[1], fm[2]))
        print("     wrote %r" % (fm[3],))
        print("     raw   %r" % (fm[4],))

    # Where does the output first diverge from a pure shift?
    print()
    print("C  IS THE OUTPUT " + "THE SHIPPED STREAM WITH 4 EXTRA BYTES INSERTED?")
    n = 0
    while n < min(len(out0), len(out1)) and out0[n] == out1[n]:
        n += 1
    print("   common prefix %d bytes" % n)
    shift = len(new) - len(old)
    tail_ok = out1[n + shift:] == out0[n:]
    print("   the rest is the shipped stream shifted by %+d: %s" % (shift, tail_ok))
    if not tail_ok:
        m = 0
        lim = min(len(out1) - n - shift, len(out0) - n)
        while m < lim and out1[n + shift + m] == out0[n + m]:
            m += 1
        print("   ...only for the first %d bytes after the insert" % m)

    print()
    print("D  WHERE THE RAW CURSOR ENDS UP")
    print("   output size %d, raw consumed %s of %d"
          % (len(out1), rep1.get("raw_consumed"), rep1.get("raw_size")))
    print("   (a correct writer consumes the raw stream exactly once;")
    print("    a drift shows up as raw_consumed != raw_size)")

    print()
    if rep1.get("model_vs_original_mismatches"):
        print("VERDICT: the writer's two cursors assume equal widths.  A length-")
        print("changing edit is NOT supported today: it desyncs rpos and the")
        print("output stops being the input with an insertion.")
        return 1
    print("VERDICT: length-changing edits already work; the retarget failure has")
    print("some other cause.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
