# -*- coding: utf-8 -*-
"""Field-level trace of ONE unit body, aligned on the RAW CURSOR.

Why this probe exists: the earlier probe compared parser call events against
writer call events.  That comparison can never align, because the parser
issues one call per primitive (u8/i16/i32/...) while the writer coalesces
unmodeled runs into a single ``op(n)`` call.  Counting calls therefore says
nothing about byte widths.

Both sides, however, advance the SAME raw cursor when re-emitting an
unmodified record: the writer's ``pos`` is the raw cursor and modeled
primitives consume raw at that cursor just like the parser does.  So the two
logs can be aligned on absolute offset, and the first offset where the parser
and the writer disagree about width is the defect.

Usage:  _field_probe.py [hex-offset] [unit-index-in-civ0]
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import contextlib
import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
import io
import sys

sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
sys.path.insert(0, _HERE_PATH("_probe", "serializer"))

import parse_dat
import write_dat

BASE = (GP.DAT_DIR +
        r"\empires2_x2_p1.dat")

PRIMS = ("u8", "i16", "u16", "u32", "i32", "f32", "raw", "skip",
         "i16_array", "i32_array", "f32_array", "fixed_string",
         "sized_string", "debug_string")
WPRIMS = ("op", "opu8", "opi16", "opu16", "opi32", "opu32",
          "u8", "i16", "u16", "u32", "i32", "f32",
          "debug_string", "fixed_string", "skip")

def parse_one(raw, target):
    """Read exactly one unit body at ``target``; return (unit, log, end)."""
    log = []
    saved = {}
    for name in PRIMS:
        if not hasattr(parse_dat.Reader, name):
            continue
        orig = getattr(parse_dat.Reader, name)
        saved[name] = orig

        def make(fn, nm):
            def spy(self, *a, **k):
                start = self.pos
                out = fn(self, *a, **k)
                log.append((nm, start, self.pos - start, out))
                return out
            return spy
        setattr(parse_dat.Reader, name, make(orig, name))

    r = parse_dat.Reader(raw)
    r.pos = target
    u = parse_dat.read_unit(r)
    end = r.pos
    for name, fn in saved.items():
        setattr(parse_dat.Reader, name, fn)
    return u, log, end

def write_one(stats, raw, unit):
    """Emit that unit; return (log, report)."""
    log = []
    saved = {}
    for name in WPRIMS:
        if name == "raw" or not hasattr(write_dat.Writer, name):
            continue
        # ``raw`` is a __slots__ descriptor, not a method: wrapping it would
        # make the attribute read-only.  Guard on callability instead.
        attr = getattr(write_dat.Writer, name)
        if not callable(attr):
            continue
        saved[name] = attr

        def makew(fn, nm):
            def spy(self, *a, **k):
                start = self.pos
                out = fn(self, *a, **k)
                log.append((nm, start, self.pos - start, a[0] if a else None))
                return out
            return spy
        setattr(write_dat.Writer, name, makew(attr, name))

    w = write_dat.Writer(raw=raw, strict=True)
    w.pos = target
    write_dat.write_unit(w, unit)
    end = w.pos
    mism = w.mismatches
    fm = w.first_mismatch
    for name, fn in saved.items():
        setattr(write_dat.Writer, name, fn)
    return log, end, mism, fm

def main():
    target = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x3BB4A0
    raw, how = write_dat.load_dat(BASE)
    u, plog, pend = parse_one(raw, target)

    # locate the modelled copy of this unit: re-parse, then take civ0 units
    p = parse_dat.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        st = p.parse()
    cu = None
    for c in st["civs"]:
        for cand in c["units"]:
            if (cand["type"] == u["type"] and cand["id"] == u["id"]
                    and cand["name"] == u["name"] and cand["class"] == u["class"]):
                cu = cand
                break
        if cu is not None:
            break

    print("=" * 78)
    print("PARSER read_unit @0x%X -> 0x%X  (len %d)" % (target, pend, pend - target))
    print("  type=%s id=%s class=%s hp=%s name=%r"
          % (u.get("type"), u.get("id"), u.get("class"),
             u.get("hit_points"), u.get("name")))
    print("=" * 78)

    if cu is None:
        print("!! could not locate matching model unit")
        return 1

    wlog, wend, mism, fm = write_one(st, raw, cu)
    print("WRITER write_unit @0x%X -> 0x%X  (len %d)   delta %+d"
          % (target, wend, wend - target, (wend - target) - (pend - target)))
    print("model mismatches: %d" % mism)
    if fm:
        print("first mismatch: raw 0x%X width %d kind %s" % (fm[0], fm[1], fm[2]))
        print("   model: %s" % fm[3].hex())
        print("   raw  : %s" % fm[4].hex())
    print()

    # ---- merged timeline on the raw cursor ------------------------------
    pe = [(nm, off - target, wd, val) for nm, off, wd, val in plog]
    we = [(nm, off - target, wd, val) for nm, off, wd, val in wlog
          if nm not in ("opu8", "opi16", "opu16", "opi32", "opu32")]
    # opu* also move the cursor; keep them but mark as op-with-peek
    we2 = [(nm, off - target, wd, val) for nm, off, wd, val in wlog]
    we2.sort(key=lambda e: (e[1], -e[2]))
    pe.sort(key=lambda e: (e[1], -e[2]))

    print("PARSER primitives (raw-relative offsets):")
    for nm, off, wd, val in pe:
        if isinstance(val, (bytes, bytearray)):
            val = "<%d bytes>" % len(val)
        elif isinstance(val, tuple) and len(val) > 4:
            val = tuple(val)[:4] + ("...",)
        print("   raw+%-6d +%-4d %-14s %s" % (off, wd, nm, val))

    print()
    print("WRITER chunks (raw-relative offsets):")
    for nm, off, wd, val in we2:
        print("   raw+%-6d +%-4d %-14s %s" % (off, wd, nm, val))

    # ---- interval coverage comparison -----------------------------------
    print()
    print("COVERAGE MAP (each line = a raw interval and who claimed it)")

    def cover(evts):
        m = {}
        for nm, off, wd, _ in evts:
            if wd <= 0:
                continue
            for x in range(off, off + wd):
                m[x] = nm
        return m

    pc = cover([(n, o, w, v) for n, o, w, v in plog])
    wc = cover([(n, o, w, v) for n, o, w, v in wlog])
    lo, hi = 0, max(pend, wend) - target
    runs = []
    x = lo
    while x < hi:
        p = pc.get(x)
        q = wc.get(x)
        y = x
        while y < hi and pc.get(y) == p and wc.get(y) == q:
            y += 1
        runs.append((x, y - x, p, q))
        x = y
    for off, wd, p, q in runs:
        flag = "" if (p is not None) == (q is not None) else "   <<< MISMATCH"
        if p != q:
            flag = "   <<< %s vs %s" % (p, q)
        print("   raw+%-6d len=%-5d parser=%-14s writer=%-14s%s"
              % (off, wd, p, q, flag))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
