# -*- coding: utf-8 -*-
"""Diagnostic: run the writer against BASE and report every model-vs-raw
mismatch together with the enclosing writer function name.

The round-trip verifier only prints the FIRST mismatch; when a record layout is
wrong the first mismatch is often a side effect, and the real culprit is the
function that appears most often.  This dumps them all so the fix is chosen from
evidence rather than from re-reading the code.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(PROBE, "datparse"))

import parse_dat
import write_dat

BASE = (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
        r"\empires2_x2_p1.dat")


def main():
    raw, how = parse_dat.load_dat(BASE)
    print("raw size      : %d  (%s)" % (len(raw), how))

    p = parse_dat.Parser(bytearray(raw))
    stats = p.parse()
    print("parsed        : final %d  leftover %d" % (p.r.pos, len(raw) - p.r.pos))

    out, rep = write_dat.serialize_dat(stats, raw=raw, strict=True)

    print("out size      : %d   delta %+d" % (len(out), len(out) - len(raw)))
    print("raw consumed  : %d / %d" % (rep.get("raw_consumed"), rep.get("raw_size")))
    print("mismatches    : %s" % rep.get("model_vs_original_mismatches"))

    fm = rep.get("first_model_mismatch")
    if fm:
        rpos, n, kind, b, seg, cur, log = fm
        print("first mismatch: raw 0x%08X n=%d kind=%s cur=%s" % (rpos, n, kind, cur))
        print("   wrote %s" % b.hex())
        print("   raw   %s" % seg.hex())

    ml = rep.get("model_mismatches") or []
    print("captured      : %d" % len(ml))
    by_cur = collections.Counter(x[5] for x in ml)
    print("\n-- mismatch context histogram (top 25) --")
    for cur, n in by_cur.most_common(25):
        print("  %6d  %s" % (n, cur))

    print("\n-- first 12 mismatches --")
    for (rpos, n, kind, b, seg, cur) in ml[:12]:
        print("  raw 0x%08X n=%d kind=%s cur=%s" % (rpos, n, kind, cur))
        print("     wrote %s" % b.hex())
        print("     raw   %s" % seg.hex())

    # first divergence between the whole output and the whole raw stream
    lim = min(len(out), len(raw))
    first = None
    for i in range(lim):
        if out[i] != raw[i]:
            first = i
            break
    print("\nfirst whole-stream diff: %s" % (("0x%08X" % first) if first is not None else "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
