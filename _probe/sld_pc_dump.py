# -*- coding: utf-8 -*-
"""Dump the raw playercolor layer payload so its exact layout can be read off.

Archer pc: size=106.  Two candidate readings both fit the size:
   with rect (like main):  16 + 2*ncmd + 8*draws  -> ncmd=5, draws=10
   without rect:            8 + 2*ncmd + 8*draws  -> ncmd=5, draws=11
Dump the bytes; whichever gives a rect inside the 200x200 canvas, with a block
grid matching the draw count, is right.
"""
import os
import struct

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]
PAD = lambda x: x + ((4 - x % 4) % 4)


def dump(fn):
    b = open(os.path.join(GP, fn), "rb").read()
    cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", b, 16)
    print("=" * 76)
    print("%s  canvas=%dx%d ft=0x%02x" % (fn, cw, ch, ft))
    p = 28
    for bit, nm in BITS:
        if not (ft & (1 << bit)):
            continue
        size = u32(b, p)
        print("\n  -- %s @%d size=%d" % (nm, p, size))
        raw = b[p + 4:p + 4 + min(size - 4, 120)]
        for i in range(0, len(raw), 16):
            print("       +%-3d  %s" % (i, " ".join("%02x" % c for c in raw[i:i + 16])))
        # candidate A: rect first
        x1, y1, x2, y2 = struct.unpack_from("<4H", b, p + 4)
        fA, nA = struct.unpack_from("<2H", b, p + 12)
        q = p + 16
        cA = [(b[q + 2 * i], b[q + 2 * i + 1]) for i in range(nA)]
        dA = sum(c[1] for c in cA)
        compA = 16 + 2 * nA + 8 * dA
        print("     A(rect): rect=(%d,%d)-(%d,%d) %dx%d fmt=0x%04x ncmd=%d draws=%d comp=%d %s"
              % (x1, y1, x2, y2, x2 - x1, y2 - y1, fA, nA, dA, compA,
                 "MATCH" if compA == size else "no"))
        # candidate B: no rect
        fB, nB = struct.unpack_from("<2H", b, p + 4)
        q = p + 8
        if q + 2 * nB <= len(b):
            cB = [(b[q + 2 * i], b[q + 2 * i + 1]) for i in range(nB)]
            dB = sum(c[1] for c in cB)
            compB = 8 + 2 * nB + 8 * dB
            print("     B(norect): fmt=0x%04x ncmd=%d draws=%d comp=%d %s   cmds=%s"
                  % (fB, nB, dB, compB, "MATCH" if compB == size else "no", cB[:12]))
        p = PAD(p + size)


for fn in ("u_arc_archer_idlea_x1.sld", "u_inf_militia_idlea_x1.sld"):
    dump(fn)
