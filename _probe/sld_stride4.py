# -*- coding: utf-8 -*-
"""Where exactly do frame 0's trailing layers sit?

main  @28   size=412  -> 440
shadow@440  size=574  -> 1014
frame1 appears to start at 1304, leaving 290 bytes for 2 more layers (ft=0x17
has bits 0,1,2,4 set).

Relax the search: for every s in [1014,1304), report s where s + u32(s) == 1304
(declared-size chain lands exactly on frame 1).  Also hexdump the whole region so
the structure can be read by eye.  Read-only.
"""
import os
import struct

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]

b = open(os.path.join(GP, "u_arc_archer_idlea_x1.sld"), "rb").read()
print("file size", len(b))

print("\n--- declared-size chain candidates ending exactly at 1304 ---")
found = []
for s in range(1014, 1304):
    sz = u32(b, s)
    if 16 <= sz <= 1304 and s + sz == 1304:
        found.append((s, sz))
for s, sz in found:
    print("   s=%-5d size=%-6d  bytes=%s" % (s, sz, b[s:s + 20].hex(" ")))

print("\n--- frame1 candidate headers near 1300 ---")
for o in range(1296, 1316):
    cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", b, o)
    print("   @%-5d %dx%d centre=(%d,%d) ft=0x%02x unk=%d idx=%d" % (o, cw, ch, cx, cy, ft, un, fi))

print("\n--- hexdump 1000..1320 ---")
for i in range(1000, 1320, 16):
    chunk = b[i:i + 16]
    print("   %5d  %s  |%s|" % (i, " ".join("%02x" % c for c in chunk),
                                "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)))

print("\n--- interpret as u16 grid from 1014 ---")
for base in (1014, 1016):
    print("   base=%d:" % base)
    vals = [u16(b, base + 2 * i) for i in range(16)]
    print("      ", " ".join("%5d" % v for v in vals))
    print("       as hex:", " ".join("%04x" % v for v in vals))

print("\n--- parse a frame AT 1304 and check its layer chain with declared sizes ---")
def walk_frames(off, n=5):
    for k in range(n):
        cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", b, off)
        p = off + 12
        got = []
        err = None
        for bit, nm in ((0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")):
            if not (ft & (1 << bit)):
                continue
            if p + 16 > len(b):
                err = "eof@%d" % p
                break
            sz = u32(b, p)
            x1, y1, x2, y2 = struct.unpack_from("<4H", b, p + 4)
            f8, ncmd = struct.unpack_from("<2H", b, p + 12)
            cmds = [(b[p + 16 + 2 * i], b[p + 17 + 2 * i]) for i in range(ncmd)] if p + 16 + 2 * ncmd <= len(b) else []
            draws = sum(c[1] for c in cmds)
            comp = 16 + 2 * ncmd + 8 * draws
            got.append((nm, p, sz, (x1, y1, x2, y2), ncmd, draws, comp, comp == sz))
            p += sz
        print("   frame k=%d @%d canvas=%dx%d ft=0x%02x idx=%d err=%s end=%d" % (k, off, cw, ch, ft, fi, err, p))
        for g in got:
            print("       %-11s @%-6d sz=%-7d rect=%-22s ncmd=%-3d draws=%-5d comp=%-7d %s"
                  % (g[0], g[1], g[2], str(g[3]), g[4], g[5], g[6], "exact" if g[7] else "APPROX"))
        if err:
            return
        off = p

walk_frames(1304, 3)
