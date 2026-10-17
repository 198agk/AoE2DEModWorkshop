# -*- coding: utf-8 -*-
"""SLD layer structure: find the TRUE layer byte stride and validate it.

Suspicion: my earlier probe assumed ONLY main/shadow carry a sub-rectangle and
used the full canvas for playercolor/unknown2/damage.  The contact sheet showed
main rendering correctly while the playercolor tile was garbage bands -> I was
decoding the wrong bytes.  Verify structurally:

  * frame header is 12 bytes and its LAST u16 is frame_index.
  * therefore: if I parse frame 0's layers and land exactly on a 12-byte header
    whose frame_index == 1 and whose canvas matches, my layer strides are right.

For each present layer dump: u32 size, then x1,y1,x2,y2, then the u16 fields,
then the command array, and compare computed size 16+2*ncmd+8*sum(draw) with the
declared u32.  Read-only.
"""
import os
import struct

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
u8 = lambda b, o: b[o]
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]


def dump(name):
    p = os.path.join(GP, name)
    b = open(p, "rb").read()
    sig, ver, nf, a, bb, cc = struct.unpack_from("<4s 2H 2H I", b, 0)
    print("=" * 74)
    print(name)
    print("  file header: sig=%r ver=%d num_frames=%d  u1=0x%04x u2=0x%04x u3=0x%08x  size=%d"
          % (sig, ver, nf, a, bb, cc, len(b)))
    pos = 16
    cw, ch, cx, cy, ft, unk, fi = struct.unpack_from("<2H 2h 2B H", b, pos)
    print("  frame0 header @%d: canvas=%dx%d centre=(%d,%d) frame_type=0x%02x unknown=%d idx=%d"
          % (pos, cw, ch, cx, cy, ft, unk, fi))
    pos += 12
    for bit, nm in BITS:
        if not (ft & (1 << bit)):
            continue
        start = pos
        size = u32(b, pos)
        body = pos + 4
        x1, y1, x2, y2 = struct.unpack_from("<4H", b, body)
        f8, ncmd = struct.unpack_from("<2H", b, body + 8)
        cmds = [(u8(b, body + 12 + 2 * i), u8(b, body + 13 + 2 * i)) for i in range(ncmd)]
        draws = sum(c[1] for c in cmds)
        comp = 16 + 2 * ncmd + 8 * draws
        print("    %-11s @%-8d size=%-7d rect=(%d,%d)-(%d,%d) %dx%d  f8=0x%04x ncmd=%-2d sum(draw)=%-4d comp=%-7d %s"
              % (nm, start, size, x1, y1, x2, y2, x2 - x1, y2 - y1, f8, ncmd, draws, comp,
                 "OK" if comp == size else "MISMATCH delta=%d" % (comp - size)))
        pos = start + size
    # validator: next 12 bytes must be frame 1 header
    cw1, ch1, _, _, ft1, _, fi1 = struct.unpack_from("<2H 2h 2B H", b, pos)
    print("  -> next header @%d: canvas=%dx%d frame_type=0x%02x idx=%d  %s"
          % (pos, cw1, ch1, ft1, fi1,
             "STRIDE CONFIRMED (idx==1)" if (fi1 == 1 and cw1 == cw) else "*** STRIDE WRONG ***"))
    return


for n in ("u_arc_archer_idlea_x1.sld", "u_inf_militia_idlea_x1.sld",
          "u_cav_knight_idlea_x1.sld", "u_monk_west_idlea_x1.sld"):
    dump(n)
