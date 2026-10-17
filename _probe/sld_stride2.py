# -*- coding: utf-8 -*-
"""What is actually at offset 1014 in u_arc_archer_idlea_x1.sld, and where does
frame 1 really begin?

main+shadow parse cleanly with the rect+command header (sizes verified by
16+2*ncmd+8*sum(draw)).  The next layer does NOT.  Determine the real layout by:
  D1  hexdump the bytes right after shadow
  D2  brute-force locate frame 1's 12-byte header (canvas 200x200, idx==1) and
      report the delta from 1014 -> that delta is the true size of the trailing
      layers combined
  D3  repeat for several frames to see if the trailing-size is constant, which
      would indicate raw fixed-size blocks (no command array)
Read-only.
"""
import os
import struct

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
u8 = lambda b, o: b[o]
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]


def hexd(b, o, n=96):
    s = []
    for i in range(0, n, 16):
        chunk = b[o + i:o + i + 16]
        s.append("    +%04d  %s  |%s|" % (i, " ".join("%02x" % c for c in chunk),
                                         "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)))
    return "\n".join(s)


def parse_f0(b):
    cw, ch, cx, cy, ft, unk, fi = struct.unpack_from("<2H 2h 2B H", b, 16)
    pos = 28
    out = {}
    for bit, nm in BITS:
        if not (ft & (1 << bit)):
            continue
        size = u32(b, pos)
        body = pos + 4
        x1, y1, x2, y2 = struct.unpack_from("<4H", b, body)
        f8, ncmd = struct.unpack_from("<2H", b, body + 8)
        cmds = [(u8(b, body + 12 + 2 * i), u8(b, body + 13 + 2 * i)) for i in range(ncmd)]
        comp = 16 + 2 * ncmd + 8 * sum(c[1] for c in cmds)
        out[nm] = dict(pos=pos, size=size, rect=(x1, y1, x2, y2), ncmd=ncmd,
                       draws=sum(c[1] for c in cmds), comp=comp)
        if comp != size:
            break
        pos = pos + size
    return cw, ch, ft, out, pos


name = "u_arc_archer_idlea_x1.sld"
b = open(os.path.join(GP, name), "rb").read()
cw, ch, ft, out, pos = parse_f0(b)
print("%s  canvas=%dx%d ft=0x%02x" % (name, cw, ch, ft))
for nm, d in out.items():
    print("   %-11s @%-7d size=%-7d rect=%s ncmd=%-3d draws=%-5d comp=%-7d %s"
          % (nm, d["pos"], d["size"], d["rect"], d["ncmd"], d["draws"], d["comp"],
             "OK" if d["comp"] == d["size"] else "MISMATCH"))
print("\nD1  bytes after the last cleanly parsed layer (@%d):" % pos)
print(hexd(b, pos))

print("\nD2  locate frame 1 header (canvas=%dx%d, idx==1) by scanning forward:" % (cw, ch))
hits = []
for o in range(pos, min(len(b) - 12, pos + 60000)):
    try:
        c1, h1, _, _, f1, _, i1 = struct.unpack_from("<2H 2h 2B H", b, o)
    except Exception:
        break
    if c1 == cw and h1 == ch and i1 == 1:
        hits.append((o, f1))
print("   candidates (offset, frame_type):", hits[:8])
if hits:
    delta = hits[0][0] - pos
    print("   => trailing bytes after shadow = %d ; next frame_type=0x%02x" % (delta, hits[0][1]))
    print("   => shadow rect comp was %d, so trailing = %d" % (out["shadow"]["comp"], delta))

print("\nD3  does the trailing size stay constant across frames?")
# walk several frames using the discovered trailing size
if hits:
    trail = hits[0][0] - pos
    off = 16
    sizes = []
    for k in range(6):
        cwk, chk, _, _, ftk, _, fik = struct.unpack_from("<2H 2h 2B H", b, off)
        p = off + 12
        tot = 0
        for bit, nm in BITS:
            if not (ftk & (1 << bit)):
                continue
            sz = u32(b, p)
            body = p + 4
            f8, ncmd = struct.unpack_from("<2H", b, body + 8)
            cmds = [(u8(b, body + 12 + 2 * i), u8(b, body + 13 + 2 * i)) for i in range(ncmd)]
            comp = 16 + 2 * ncmd + 8 * sum(c[1] for c in cmds)
            if comp == sz:
                p += sz
            else:
                p += sz  # unknown layer: trust declared size
            tot += sz
        sizes.append((k, fik, ftk, tot))
        off = off + 12 + tot
    for k, fik, ftk, tot in sizes:
        print("   frame %-2d idx=%-3d ft=0x%02x  total layer bytes=%d" % (k, fik, ftk, tot))
    print("   (if totals vary, sizes are content-dependent; if the declared-size walk")
    print("    keeps idx incrementing, trusting declared sizes is the correct parser.)")
