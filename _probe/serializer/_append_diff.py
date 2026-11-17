# -*- coding: utf-8 -*-
"""_append_diff.py -- prove that out/added_tech.dat is BASE with EXACTLY two
inserted records and two patched count fields, and nothing else changed.

Method: an insertion-aware walk.  At each point, if raw[r] == new[n] the byte is
unchanged; otherwise classify the divergence as either a small PATCH (a count
field: same width, different value, both sides continue) or an INSERTION (new
bytes with no raw counterpart).  We expect exactly:
    patch  4 B @ raw 0x0036B0BE   effects 1500 -> 1501
    insert N1 B (the new Effect record)
    patch  2 B @ raw 0x058C1923   techs   1510 -> 1511
    insert N2 B (the new Tech record)
"""
import contextlib
import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "datparse"))
sys.path.insert(0, HERE)
import parse_dat
import write_dat

BASE = (GP.DAT_DIR +
        r"\empires2_x2_p1.dat")
APPENDED = os.path.join(HERE, "out", "added_tech.dat")


def main():
    raw, _ = write_dat.load_dat(BASE)
    new, _ = write_dat.load_dat(APPENDED)

    # exact insertion-aware alignment via a simple diff on the differing region
    r = n = 0
    events = []
    # common prefix
    while r < len(raw) and n < len(new) and raw[r] == new[n]:
        r += 1
        n += 1
    events.append(("common prefix", r, n))

    while r < len(raw) and n < len(new):
        if raw[r] == new[n]:
            r += 1
            n += 1
            continue
        # try patch (same width, both continue synchronised)
        if raw[r] != new[n]:
            # look ahead: find the smallest insertion length k>=1 such that
            # raw[r:] and new[n+k:] resynchronise for a long run
            best = None
            for k in range(1, 512):
                if n + k >= len(new):
                    break
                if raw[r] == new[n + k]:
                    # check a run
                    run = 0
                    while (r + run < len(raw) and n + k + run < len(new)
                           and raw[r + run] == new[n + k + run] and run < 64):
                        run += 1
                    if run >= 64:
                        best = k
                        break
            if best is not None:
                events.append(("insert", r, n, best, new[n:n + best]))
                n += best
                continue
            # else treat as a patch of 1 byte and continue
            events.append(("patch", r, n, 1, (raw[r:r + 1], new[n:n + 1])))
            r += 1
            n += 1

    # tail
    if r < len(raw) or n < len(new):
        events.append(("tail", r, n, len(raw) - r, len(new) - n))

    print("BASE      %d bytes" % len(raw))
    print("APPENDED  %d bytes" % len(new))
    print("delta     %+d" % (len(new) - len(raw)))
    print()
    print("edit script (non-'keep' events only):")
    ins_total = 0
    for e in events:
        kind = e[0]
        if kind == "common prefix":
            print("  %-14s  %d leading bytes identical" % (kind, e[1]))
        elif kind == "insert":
            _, roff, noff, k, payload = e
            ins_total += k
            print("  %-14s  raw 0x%08X / new 0x%08X  %d bytes inserted"
                  % (kind, roff, noff, k))
            print("                  payload: %s" % payload.hex())
        elif kind == "patch":
            _, roff, noff, k, (a, b) = e
            print("  %-14s  raw 0x%08X / new 0x%08X  %d B  %s -> %s"
                  % (kind, roff, noff, k, a.hex(), b.hex()))
        else:
            print("  %-14s  raw %d new %d" % (kind, e[1], e[2]))
    print()
    print("total inserted bytes: %d" % ins_total)
    patches = [e for e in events if e[0] == "patch"]
    inserts = [e for e in events if e[0] == "insert"]
    print("patch count : %d (expected 2)" % len(patches))
    print("insert count: %d (expected 2)" % len(inserts))
    ok = len(patches) == 2 and len(inserts) == 2
    if ok:
        for e in patches:
            roff, noff = e[1], e[2]
            print("  patch at raw 0x%08X -> matches a stage count field: %s"
                  % (roff, "YES" if roff in (0x0036B0BE, 0x058C1923) else "NO"))
            if roff not in (0x0036B0BE, 0x058C1923):
                ok = False
    print()
    print("EDIT SCRIPT MINIMAL: %s" % ("YES" if ok else "NO"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
