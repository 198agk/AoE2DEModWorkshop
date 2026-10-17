"""Why does replacing a graphics `file` string break the re-parse?

The retarget experiment wants to change `file` from the target's name to the
donor's name, which changes the record's length.  A trial run produced a file
that the UNMODIFIED parser could not finish (it died in stage 8 reading civs),
so this probe isolates the mechanism with ONE record and exact byte arithmetic
instead of reasoning about it.

Run:
  python _probe/probe_retarget_diag.py
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DAT = os.path.join(r"D:\Games\Steam\steamapps\common\AoE2DE",
                   "resources", "_common", "dat", "empires2_x2_p1.dat")


def spans(data):
    """(index, start, end, file, name) for every graphics body."""
    import aoe2mod.dat.parser as P
    cnt = struct.unpack_from("<H", data, 0x44DC0)[0]
    arr = struct.unpack_from("<%di" % cnt, data, 0x44DC2)
    r = P.Reader(data)
    r.gv = P.GV_C32
    r.pos = 0x44DC2 + 4 * cnt
    out = []
    for i, flag in enumerate(arr):
        if not flag:
            continue
        a = r.pos
        g = P.read_graphic(r)
        out.append((i, a, r.pos, g.get("file") or "", g.get("name") or ""))
    return out, r.pos


def main():
    import aoe2mod.dat.parser as P
    import aoe2mod.dat.writer as W

    data, _how = P.load_dat(DAT)
    print("shipped size %d" % len(data))

    # ---- 1. what does the raw stream actually store for one string? ------
    sp, _end = spans(data)
    # pick a record with a modern file name
    tgt = next(t for t in sp if (t[3] or "").startswith("u_arc_archer_attackA"))
    i, a, b, fname, nm = tgt
    print()
    print("1  ONE RECORD'S RAW BYTES")
    print("   gfx %d spans %d..%d (%d bytes), file=%r" % (i, a, b, b - a, fname))
    n = len(fname)
    # the file string sits after marker+len(marker,name) ... find its length prefix
    # by searching for the u16 == len(fname) within the record
    hits = []
    for p in range(a, b - 1):
        v = struct.unpack_from("<H", data, p)[0]
        if v in (n, n + 1):
            if data[p + 2:p + 2 + n] == fname.encode("latin-1"):
                hits.append((p, v))
    print("   length prefixes that match %r: %s" % (fname, [(hex(p), v) for p, v in hits]))
    if hits:
        p, v = hits[0]
        print("   stored length field = %d, actual chars = %d, extra = %d"
              % (v, n, v - n))

    # ---- 2. rewrite exactly ONE record and watch the byte delta ----------
    stats = P.Parser(data)
    stats.parse()
    stats = stats.stats
    gfx = stats["graphics"]
    src = next(g for g in gfx if g.get("id") == i)
    old = src["file"]
    new = "u_arc_longbowman_attackA_x1"
    print()
    print("2  REWRITE ONE RECORD")
    print("   %r (%d) -> %r (%d), expected delta %+d"
          % (old, len(old), new, len(new), len(new) - len(old)))
    src["file"] = new
    out, rep = W.serialize_dat(stats, raw=data, gv=P.GV_C32)
    got = len(out) - len(data)
    print("   measured delta %+d" % got)
    ok = got == len(new) - len(old)
    print("   matches the string-length difference  %s" % ("PASS" if ok else "FAIL"))

    # ---- 3. does the unmodified parser still finish? ---------------------
    print()
    print("3  RE-PARSE WITH THE UNMODIFIED PARSER")
    try:
        p2 = P.Parser(out)
        p2.parse()
        print("   finished at %d of %d bytes  %s"
              % (p2.r.pos, len(out),
                 "PASS" if p2.r.pos == len(out) else "FAIL (tail left over)"))
        rec = next(g for g in p2.stats["graphics"] if g.get("id") == i)
        print("   the record now reads %r  %s"
              % (rec.get("file"), "PASS" if rec.get("file") == new else "FAIL"))
        return 0 if ok and p2.r.pos == len(out) else 1
    except Exception as e:
        print("   FAILED: %s: %s" % (type(e).__name__, e))
        # where did it get to?
        sp2, end2 = spans(out)
        print("   the new graphics section ends at %d (shipped %d, delta %+d)"
              % (end2, _end, end2 - _end))
        print("   records: shipped %d, new %d" % (len(sp), len(sp2)))
        diff = [(x[0], x[2] - x[1], y[2] - y[1])
                for x, y in zip(sp, sp2) if x[2] - x[1] != y[2] - y[1]]
        print("   records whose byte span changed: %d %s"
              % (len(diff), diff[:5]))
        return 1


if __name__ == "__main__":
    sys.exit(main())
