import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump raw hex around the terrain records to find the correct record phase."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

data, how = P.load_dat(GP.DAT)
print("size %d (%s)" % (len(data), how))

def hexdump(off, n):
    for i in range(0, n, 16):
        chunk = data[off + i: off + i + 16]
        hx = " ".join("%02X" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("  0x%08X  %-47s  %s" % (off + i, hx, asc))

print("\n--- bytes at 0x355F1A (terrain 0 claimed start) ---")
hexdump(0x355F1A, 64)

print("\n--- bytes at 0x3560C7 (claimed end of terrain 0 / start of terrain 1) ---")
hexdump(0x3560C7, 96)

print("\n--- bytes at 0x35608C (0x3560C7 - 0x3B) ---")
hexdump(0x35608C, 96)

# Manual: parse terrain 0 piecewise, printing every field, to see where 'Grass' sits
r = P.Reader(data)
r.pos = 0x355F1A
print("\n--- piecewise parse of terrain 0 ---")
print("Enabled=%d Random=%d" % (r.u8(), r.u8()))
print("IsWater=%d HideInEditor=%d StringID=%d" % (r.u8(), r.u8(), r.i32()))
print("Name=%r (marker=0x%04X)" % (None, r.u16()))
ln = r.u16(); nm = r.raw(ln); print("  Name len=%d bytes=%r" % (ln, nm))
m2 = r.u16(); ln2 = r.u16(); nm2 = r.raw(ln2)
print("Name2 marker=0x%04X len=%d bytes=%r" % (m2, ln2, nm2))
print("SLP=%d ShapePtr=%d SoundID=%d" % (r.i32(), r.i32(), r.i32()))
print("WwiseSoundID=%d WwiseSoundStopID=%d" % (r.u32(), r.u32()))
print("BlendPriority=%d BlendType=%d" % (r.i32(), r.i32()))
m3 = r.u16(); ln3 = r.u16(); nm3 = r.raw(ln3)
print("OverlayMaskName marker=0x%04X len=%d bytes=%r" % (m3, ln3, nm3))
print("Colors=%s CliffColors=%s Passable=%d Impassable=%d" %
      (r.raw(3), r.raw(2), r.u8(), r.u8()))
print("IsAnimated=%d AnimationFrames=%d Pause=%d" % (r.u8(), r.i16(), r.i16()))
print("Interval=%r PauseBetweenLoops=%r" % (r.f32(), r.f32()))
print("Frame=%d DrawFrame=%d AnimateLast=%r" % (r.i16(), r.i16(), r.f32()))
print("FrameChanged=%d Drawn=%d" % (r.u8(), r.u8()))
r.skip(19 * 6); print("ElevationGraphics skipped, pos=0x%X" % r.pos)
print("TerrainToDraw=%d TerrainDimensions=(%d,%d)" % (r.i16(), r.i16(), r.i16()))
r.skip(30 * 2); print("MaskedDensity skipped, pos=0x%X" % r.pos)
r.skip(30 * 2); print("TerrainUnitID skipped, pos=0x%X" % r.pos)
r.skip(30 * 2); print("TerrainUnitDensity skipped, pos=0x%X" % r.pos)
r.skip(30); print("TerrainUnitCentering skipped, pos=0x%X" % r.pos)
print("NumberOfTerrainUnitsUsed=%d" % r.i16())
print("END pos=0x%X" % r.pos)
