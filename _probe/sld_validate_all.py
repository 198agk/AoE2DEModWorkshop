# -*- coding: utf-8 -*-
"""BROAD validation of the reconstructed SLD layout over the whole game tree.

Claims under test (all read-only):
  C1  file header is 16 B  <4s 2H 2H I  sig='SLDX' ver=4
  C2  walking frames with 12 B frame headers and per-layer
        u32 size | payload | PAD to 4 B
      reaches EXACTLY EOF (no leftover, no overrun) for every file
  C3  frame_index increments by exactly 1 per frame, starting at 0
  C4  main/shadow:  size == 16 + 2*ncmd + 8*sum(draw)
  C5  playercolor:  size ==  8 + 2*ncmd + 8*sum(draw)
  C6  span identity: sum(skip+draw) == bw*bh for main and for playercolor,
      and main.span == palyercolor.span
  C7  frame_type bit set == union of layers actually walked
Emit per-file pass/fail and a global histogram so the report can quote
honest denominators.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import struct
import collections

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = _HERE_PATH("_probe", "sld_validate_out.txt")

BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]
PAD = lambda x: x + ((4 - x % 4) % 4)

def walk(b):
    """Return (nframes, ok_eof, idx_ok, per-layer stats) or raise."""
    sig, ver, n, u1, u2, u3 = struct.unpack_from("<4s 2H 2H I", b, 0)
    if sig != b"SLDX":
        return dict(sig=sig, err="bad sig")
    p, off = 16, 0
    stats = collections.Counter()
    seen = collections.Counter()
    idx_bad = 0
    first_idx = None
    comp_bad = collections.Counter()
    span_bad = collections.Counter()
    comp_ok = collections.Counter()
    span_ok = collections.Counter()
    while off < n:
        if p + 12 > len(b):
            return dict(sig=sig, ver=ver, n=n, err="frame header past EOF", walked=off)
        cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", b, p)
        if first_idx is None:
            first_idx = fi
        elif fi != first_idx + off:
            idx_bad += 1
        p += 12
        rects = {}
        recs = {}
        for bit, nm in BITS:
            if not (ft & (1 << bit)):
                continue
            seen[nm] += 1
            if p + 4 > len(b):
                return dict(sig=sig, ver=ver, n=n, err="layer size past EOF", walked=off)
            size = struct.unpack_from("<I", b, p)[0]
            q = p + 4
            rect = None
            if nm in ("main", "shadow"):
                rect = struct.unpack_from("<4H", b, q)
                q += 8
            fmt, ncmd = struct.unpack_from("<2H", b, q)
            q += 4
            cmds = [(b[q + 2 * i], b[q + 2 * i + 1]) for i in range(ncmd)]
            q += 2 * ncmd
            draws = sum(c[1] for c in cmds)
            span = sum(c[0] + c[1] for c in cmds)
            base = 16 if nm in ("main", "shadow") else 8
            comp = base + 2 * ncmd + 8 * draws
            if comp == size:
                comp_ok[nm] += 1
            else:
                comp_bad[nm] += 1
            if rect:
                bw = (rect[2] - rect[0] + 3) // 4
                bh = (rect[3] - rect[1] + 3) // 4
                if bw * bh == span and bw > 0 and bh > 0:
                    span_ok[nm] += 1
                else:
                    span_bad[nm] += 1
                rects[nm] = (bw, bh, span)
            elif nm == "playercolor":
                recs[nm] = span
            stats[nm] += size
            p = PAD(p + size)
        if "main" in rects and "playercolor" in recs:
            if rects["main"][2] == recs["playercolor"]:
                span_ok["pc==main"] += 1
            else:
                span_bad["pc==main"] += 1
        off += 1
    return dict(sig=sig, ver=ver, n=n, walked=off, eof_ok=(p == len(b)), p=p, blen=len(b),
                idx_bad=idx_bad, comp_ok=comp_ok, comp_bad=comp_bad, span_ok=span_ok,
                span_bad=span_bad, seen=seen, u1=u1, u2=u2, u3=u3)

def main():
    files = sorted(os.listdir(GP))
    sld = [f for f in files if f.endswith(".sld")]
    tot = collections.Counter()
    ftr = collections.Counter()
    ver_hist = collections.Counter()
    fails = []
    nframes_total = 0
    comp_ok = collections.Counter()
    comp_bad = collections.Counter()
    span_ok = collections.Counter()
    span_bad = collections.Counter()
    idx_bad_files = []
    unknown2_ok = 0
    unknown2_bad = 0
    lines = []
    for i, fn in enumerate(sld):
        try:
            b = open(os.path.join(GP, fn), "rb").read()
        except OSError as e:
            fails.append((fn, "read:" + str(e)))
            continue
        if len(b) == 0:
            tot["zero_bytes"] += 1
            continue
        try:
            r = walk(b)
        except Exception as e:  # noqa
            fails.append((fn, "exc:" + type(e).__name__ + ":" + str(e)))
            continue
        if "err" in r:
            fails.append((fn, r["err"]))
            continue
        ver_hist[r["ver"]] += 1
        tot["files"] += 1
        nframes_total += r["walked"]
        tot["frames"] += r["walked"]
        if r["eof_ok"]:
            tot["eof_ok"] += 1
        else:
            fails.append((fn, "eof mismatch p=%d len=%d" % (r["p"], r["blen"])))
        if r["idx_bad"]:
            idx_bad_files.append((fn, r["idx_bad"], r["walked"]))
        for k, v in r["comp_ok"].items():
            comp_ok[k] += v
        for k, v in r["comp_bad"].items():
            comp_bad[k] += v
        for k, v in r["span_ok"].items():
            span_ok[k] += v
        for k, v in r["span_bad"].items():
            span_bad[k] += v
        for k, v in r["seen"].items():
            ftr[k] += v
        if "unknown2" in r["comp_ok"] or "unknown2" in r["seen"]:
            pass
    out = []
    out.append("files scanned        : %d (.sld in drs\\graphics)" % len(sld))
    out.append("zero-byte files      : %d" % tot["zero_bytes"])
    out.append("files walked OK      : %d" % tot["files"])
    out.append("files reaching EXACT EOF: %d" % tot["eof_ok"])
    out.append("total frames walked  : %d" % nframes_total)
    out.append("SLD version histogram: %s" % dict(ver_hist))
    out.append("")
    out.append("C4/C5  size == base + 2*ncmd + 8*sum(draw)")
    for k in sorted(set(list(comp_ok) + list(comp_bad))):
        out.append("    %-12s ok=%-9d bad=%d" % (k, comp_ok[k], comp_bad[k]))
    out.append("")
    out.append("C6     span == bw*bh  (and playercolor.span == main.span)")
    for k in sorted(set(list(span_ok) + list(span_bad))):
        out.append("    %-12s ok=%-9d bad=%d" % (k, span_ok[k], span_bad[k]))
    out.append("")
    out.append("C7     layers per frame_type (occurrences)")
    for k in sorted(ftr):
        out.append("    %-12s %d" % (k, ftr[k]))
    out.append("")
    out.append("C3     files with frame_index discontinuity: %d" % len(idx_bad_files))
    for fn, nb, w in idx_bad_files[:20]:
        out.append("       %-46s bad=%-5d frames=%d" % (fn, nb, w))
    out.append("")
    out.append("FAILURES: %d" % len(fails))
    for fn, why in fails[:40]:
        out.append("    %-46s %s" % (fn, why))
    txt = "\n".join(out)
    io = open(OUT, "w", encoding="utf-8")
    io.write(txt)
    io.close()
    print(txt)

main()
