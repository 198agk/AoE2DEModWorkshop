"""Exercise the RandomMaps MapInfo body -- the catalogue's "largest untested path".

No dataset on this machine has count > 0 (probe_random_maps.py: all five are
empty, 8 bytes = u32 count + i32 ptr).  So the per-map reader/writer have never
run against real data, and we cannot validate them by round-tripping a .dat.

We can still validate them against something better than real data: the field
widths in the game's own shipped genieutils source
(_probe/source/genieutils/src/dat/RandomMap.cpp), which is ground truth.

Method
  1. Build a canonical RandomMaps block from the C++ record layouts.
  2. read_random_maps() it and assert the reader consumes EXACTLY the block.
  3. write_random_maps() the resulting model and assert the bytes match.
Step 2 is what catches a reader that under-consumes; step 3 catches a writer
whose opaque runs have the wrong width.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import parse_dat as P

# Field layouts transcribed from RandomMap.cpp serializeObject().
# MapLand  lines 151-168 : i32 u32 i32 i32 | u8 u8 i16 | i32 i32 | u8 u8 i16 | i32 i32 i32
MAPLAND_LAYOUT = [("<i", 1), ("<I", 1), ("<i", 1), ("<i", 1),
                  ("<B", 2), ("<h", 1),
                  ("<i", 2),
                  ("<B", 2), ("<h", 1),
                  ("<i", 3)]
# MapTerrain lines 187-195 : 6 x i32
MAPTERRAIN_LAYOUT = [("<i", 6)]
# MapUnit  lines 214-229 : i32 i32 | u8 u8 i16 | i32 x8
MAPUNIT_LAYOUT = [("<i", 2), ("<B", 2), ("<h", 1), ("<i", 8)]
# MapElevation lines 248-256 : 6 x i32
MAPELEV_LAYOUT = [("<i", 6)]


def size_of(layout):
    return sum(struct.calcsize(f) * n for f, n in layout)


def emit(layout, seed):
    """Deterministic bytes that always fit each field's width."""
    out = b""
    v = seed
    for fmt, n in layout:
        w = struct.calcsize(fmt)
        for _ in range(n):
            if w == 1:
                val = v & 0xFF
            elif w == 2:
                val = v & 0x7FFF
            else:
                val = v & 0x7FFFFFFF
            out += struct.pack(fmt, val)
            v = (v * 1103515245 + 12345) & 0x7FFFFFFF   # keep it varied
        v += 1
    return out


MAPLAND_SIZE = size_of(MAPLAND_LAYOUT)
MAPTERRAIN_SIZE = size_of(MAPTERRAIN_LAYOUT)
MAPUNIT_SIZE = size_of(MAPUNIT_LAYOUT)
MAPELEV_SIZE = size_of(MAPELEV_LAYOUT)

print("=== authoritative record sizes (from RandomMap.cpp) ===")
print("  MapLand      %d B   (parse_dat comment claims 47 B)" % MAPLAND_SIZE)
print("  MapTerrain   %d B" % MAPTERRAIN_SIZE)
print("  MapUnit      %d B" % MAPUNIT_SIZE)
print("  MapElevation %d B" % MAPELEV_SIZE)
print()

# ---- compare against what our reader/writer actually consume --------------
print("=== what our code actually consumes ===")


class Countreader(object):
    """Minimal reader that just counts bytes consumed."""

    def __init__(self, b, base=0):
        self.b = b
        self.o = base
        self.gv = P.GV_C32

    def _t(self, fmt):
        n = struct.calcsize(fmt)
        v = struct.unpack_from(fmt, self.b, self.o)[0]
        self.o += n
        return v

    def i32(self):
        return self._t("<i")

    def u32(self):
        return self._t("<I")

    def u8(self):
        return self._t("<B")

    def i16(self):
        return self._t("<h")

    def i32_array(self, n):
        return [self.i32() for _ in range(n)]


for name, fn, expect in (("read_map_land", P.read_map_land, MAPLAND_SIZE),
                         ("read_map_terrain", P.read_map_terrain, MAPTERRAIN_SIZE),
                         ("read_map_unit", P.read_map_unit, MAPUNIT_SIZE),
                         ("read_map_elevation", P.read_map_elevation, MAPELEV_SIZE)):
    r = Countreader(b"\x00" * 4096)
    fn(r)
    tag = "OK" if r.o == expect else "*** MISMATCH ***"
    print("  %-20s consumes %2d B   authoritative %2d B   %s"
          % (name, r.o, expect, tag))

# writer side: sum the w.op() widths each helper emits
_SER = os.path.normpath(os.path.join(HERE, "..", "serializer"))
if _SER not in sys.path:
    sys.path.insert(0, _SER)
import write_dat as W


class Countwriter(object):
    """Minimal writer that just counts bytes emitted."""

    def __init__(self):
        self.o = 0

    def op(self, n):
        self.o += n


for name, fn, expect in (("_write_map_land", W._write_map_land, MAPLAND_SIZE),
                         ("_write_map_terrain", W._write_map_terrain, MAPTERRAIN_SIZE),
                         ("_write_map_unit", W._write_map_unit, MAPUNIT_SIZE),
                         ("_write_map_elevation", W._write_map_elevation, MAPELEV_SIZE)):
    w = Countwriter()
    fn(w)
    tag = "OK" if w.o == expect else "*** MISMATCH ***"
    print("  %-20s emits     %2d B   authoritative %2d B   %s"
          % (name, w.o, expect, tag))

print()

n_land, n_terr, n_unit, n_elev = 2, 3, 4, 5


def synth(COUNT, n_land, n_terr, n_unit, n_elev):
    """Build a RandomMaps block per RandomMap.cpp.

    Each MapInfo owns its own ``io_all_`` (RandomMap.h:147, non-static), starting
    False.  serializeSub<MapInfo> runs TWICE over the vector (RandomMap.cpp:62-63),
    so pass 0 writes only headers + counts and pass 1 writes the bodies.
    """
    blk = struct.pack("<I", COUNT) + struct.pack("<i", 0)     # count, ptr
    for _pass in range(2):
        for mi in range(COUNT):
            io_all = (_pass == 1)
            if not io_all:
                blk += struct.pack("<i", 900 + mi)             # MapID
            blk += struct.pack("<i", 0x11111111) * 9           # 9 x i32 header
            for cnt, layout, sd in ((n_land, MAPLAND_LAYOUT, 100),
                                    (n_terr, MAPTERRAIN_LAYOUT, 200),
                                    (n_unit, MAPUNIT_LAYOUT, 300),
                                    (n_elev, MAPELEV_LAYOUT, 400)):
                blk += struct.pack("<I", cnt) + struct.pack("<i", 0)
                if io_all:
                    for k in range(cnt):
                        blk += emit(layout, sd + k * 17 + mi * 5)
    return blk


for COUNT in (1, 2, 3):
    print()
    print("=== end-to-end: synthetic block with count = %d ===" % COUNT)
    blk = synth(COUNT, 2, 3, 4, 5)
    print("  synthetic block: %d bytes" % len(blk))

    # --- step 1: can the READER consume it exactly? ------------------------
    r = Countreader(blk)
    model = P.read_random_maps(r)
    consumed = r.o
    ok = consumed == len(blk)
    print("  read_random_maps consumed %d / %d bytes   -> %s"
          % (consumed, len(blk), "EXACT" if ok else "*** UNDER/OVER-RUN ***"))

    # --- step 2: does the WRITER reproduce it, given the parsed model? -----
    if not ok:
        print("  writer test skipped: reader does not consume the block exactly")
        continue
    w = W.Writer(raw=blk, strict=True, gv=P.GV_C32)
    W.write_random_maps(w, model)
    out = bytes(w.out)
    same = out == blk
    print("  write_random_maps emitted %d / %d bytes   -> %s"
          % (len(out), len(blk), "BYTE-EXACT" if same else "*** DIFFERS ***"))
    if not same:
        for i in range(min(len(out), len(blk))):
            if out[i] != blk[i]:
                print("      first diff at %d: wrote %02x expected %02x"
                      % (i, out[i], blk[i]))
                break
