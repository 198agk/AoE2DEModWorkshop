"""Systematic sweep: does every read_X / _write_X pair agree on width?

The RandomMaps bug was found by accident (a segment that is empty in all real
datasets). This script looks for the whole *class*: for each section, run the
authoritative reader and the writer against the same control input and compare
consumed vs emitted bytes.

Both sides are driven with zeroed buffers and a tall buffer so width-only
disagreements show up. Functions that branch on *values* will diverge on zeros
without being buggy, so treat hits as a screening list, not verdicts.

Usage: python sweep_read_write_widths.py [--gv GV_C32|GV_C21]
Read-only.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.normpath(os.path.join(HERE, "..", "serializer"))):
    if p not in sys.path:
        sys.path.insert(0, p)

import parse_dat as P
import write_dat as W

GVNAME = "GV_C32"
for i, a in enumerate(sys.argv):
    if a == "--gv" and i + 1 < len(sys.argv):
        GVNAME = sys.argv[i + 1]
GV = getattr(P, GVNAME)

BIG = 1 << 20


class Countreader(object):
    def __init__(self, b, base=0):
        self.b = b
        self.o = base
        self.gv = GV

    def _t(self, fmt):
        n = struct.calcsize(fmt)
        v = struct.unpack_from(fmt, self.b, self.o)[0]
        self.o += n
        return v

    def i8(self):
        return self._t("<b")

    def u8(self):
        return self._t("<B")

    def i16(self):
        return self._t("<h")

    def u16(self):
        return self._t("<H")

    def i32(self):
        return self._t("<i")

    def u32(self):
        return self._t("<I")

    def f32(self):
        return self._t("<f")

    def i32_array(self, n):
        return [self.i32() for _ in range(n)]

    def u16_array(self, n):
        return [self.u16() for _ in range(n)]

    def i16_array(self, n):
        return [self.i16() for _ in range(n)]

    def u8_array(self, n):
        return [self.u8() for _ in range(n)]

    def f32_array(self, n):
        return [self.f32() for _ in range(n)]

    def skip(self, n):
        # verbatim padding read by several sections (BuildingsPerZone / AGES / ...)
        self.o += n
        return None

    def raw(self, n):
        s = self.b[self.o:self.o + n]
        self.o += n
        return s

    def debug_string(self):
        # layout: u16 marker, u16 length, bytes  (parse_dat.Reader.debug_string)
        self._t("<H")
        n = self._t("<H")
        s = self.b[self.o:self.o + n]
        self.o += n
        z = s.find(b"\x00")
        if z >= 0:
            s = s[:z]
        return (0, s.decode("latin-1", "replace"))


class Countwriter(object):
    def __init__(self):
        self.o = 0
        self.gv = GV

    def op(self, n):
        self.o += max(0, n)

    def opu8(self):
        self.o += 1
        return 0

    def opi16(self):
        self.o += 2
        return 0

    def opu16(self):
        self.o += 2
        return 0

    def opi32(self):
        self.o += 4
        return 0

    def opu32(self):
        self.o += 4
        return 0

    def _n(self, n):
        self.o += n

    def u8(self, v):
        self._n(1)

    def i8(self, v):
        self._n(1)

    def u16(self, v):
        self._n(2)

    def i16(self, v):
        self._n(2)

    def u32(self, v):
        self._n(4)

    def i32(self, v):
        self._n(4)

    def f32(self, v):
        self._n(4)

    def debug_string(self, s):
        # u16 marker + u16 exact byte count + bytes  (write_dat.Writer.debug_string)
        b = (s or "").encode("latin-1")
        self._n(2 + 2 + len(b))

    def new_record(self):
        return _Noop()

    def mark(self, name):
        pass


class _Noop(object):
    def __enter__(self):
        return None

    def __exit__(self, *a):
        return False


# ---- pair up by name -------------------------------------------------------
# Writers use two conventions: write_X (most) and _write_map_X (RandomMaps).
pairs = []
missing = []
for rn in sorted(n for n in dir(P) if n.startswith("read_")):
    suffix = rn[len("read_"):]
    for cand in ("write_" + suffix, "_write_" + suffix):
        if hasattr(W, cand):
            pairs.append((rn, cand))
            break
    else:
        missing.append(rn)

print("=" * 100)
print("read_X / _write_X width sweep   (gv=%s, %s, control input = zeros)"
      % (GVNAME, GV))
print("=" * 100)

same = 0
diff = []
err = []
# A few readers take extra scalar context that the writer does not: supply a
# fixed neutral value so the width comparison is still apples-to-apples.
# read_terrain_restriction is sized by DatFile's TerrainsUsed1 (134 in VER 8.9);
# the writer derives its width from the model's own list lengths, so any
# consistent value works here.
EXTRA_ARGS = {
    "read_terrain_restriction": (134,),
}

for rn, wn in pairs:
    rf = getattr(P, rn)
    wf = getattr(W, wn)
    try:
        r = Countreader(b"\x00" * BIG)
        rv = rf(r, *EXTRA_ARGS.get(rn, ()))
        rb = r.o
    except Exception as e:
        err.append((rn, "%s: %s" % (type(e).__name__, e)))
        continue
    try:
        w = Countwriter()
        wf(w, rv)
        wb = w.o
    except TypeError:
        # writer expects the model; try passing the reader's return directly
        try:
            w = Countwriter()
            wf(w)
            wb = w.o
        except Exception as e:
            err.append((wn, "%s: %s" % (type(e).__name__, e)))
            continue
    except Exception as e:
        err.append((wn, "%s: %s" % (type(e).__name__, e)))
        continue

    if rb == wb:
        same += 1
        print("  %-34s read=%-7d write=%-7d  OK" % (rn, rb, wb))
    else:
        diff.append((rn, wn, rb, wb))
        print("  %-34s read=%-7d write=%-7d  *** DIFF %+d ***"
              % (rn, rb, wb, wb - rb))

print()
print("=" * 100)
print("pairs=%d  agree=%d  differ=%d  error=%d" % (len(pairs), same, len(diff), len(err)))
print("=" * 100)
if diff:
    print("DIFFERENCES (screening list -- verify each against the C++ source):")
    for rn, wn, rb, wb in diff:
        print("  %-34s %s  read=%d write=%d  delta=%+d" % (rn, wn, rb, wb, wb - rb))
if err:
    print("ERRORS (usually signature mismatch, not a width bug):")
    for n, e in err:
        print("  %-34s %s" % (n, e))
