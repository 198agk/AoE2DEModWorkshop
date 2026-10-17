# -*- coding: utf-8 -*-
"""Find the simplest frame layouts to settle the SLD layer payload format.

Validated already: frame walk = 12-byte frame header then, per layer present in
frame_type, u32 size + payload, each layer padded to 4-byte alignment.  300
consecutive frames of u_arc_archer_idlea_x1 slot agree (idx 0..299, no breaks).

main/shadow payload = u32 size | 4xu16 rect | u16 a | u16 ncmd | ncmd*(u8,u8) | blocks,
where size == 16 + 2*ncmd + 8*sum(draw).  Trailing layers (unknown2/playercolor) do
NOT fit that.

Plan: histogram frame_type across all .sld; then fully hexdump files whose
frame_type has the FEWEST bits set (ideally a single layer) so the payload can be
read unambiguously.  Read-only.
"""
import os
import struct
from collections import Counter

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]
PAD = lambda x: x + ((4 - x % 4) % 4)

ft_hist = Counter()
first_by_ft = {}
files = [f for f in os.listdir(GP) if f.endswith(".sld")]
print("sld files:", len(files))
for fn in files:
    p = os.path.join(GP, fn)
    try:
        if os.path.getsize(p) < 28:
            continue
        with open(p, "rb") as fh:
            h = fh.read(28)
    except Exception:
        continue
    if h[:4] != b"SLDX":
        continue
    ft = h[16 + 8]
    ft_hist[ft] += 1
    if ft not in first_by_ft:
        first_by_ft[ft] = fn

print("\nframe_type histogram (bit0 main, bit1 shadow, bit2 unknown2, bit3 damage, bit4 playercolor):")
for ft, n in sorted(ft_hist.items(), key=lambda kv: -kv[1]):
    names = [nm for bit, nm in BITS if ft & (1 << bit)]
    print("   0x%02x  n=%-6d  layers=%s" % (ft, n, names or ["NONE"]))

print("\n--- dump the file with the FEWEST layers set ---")
order = sorted(first_by_ft.items(), key=lambda kv: bin(kv[0]).count("1"))
for ft, fn in order[:3]:
    p = os.path.join(GP, fn)
    b = open(p, "rb").read()
    print("\n=== ft=0x%02x file=%s size=%d" % (ft, fn, len(b)))
    cw, ch, cx, cy, ftv, un, fi = struct.unpack_from("<2H 2h 2B H", b, 16)
    print("    frame0 canvas=%dx%d centre=(%d,%d) ft=0x%02x idx=%d" % (cw, ch, cx, cy, ftv, fi))
    p2 = 28
    for bit, nm in BITS:
        if not (ftv & (1 << bit)):
            continue
        sz = u32(b, p2)
        print("    %-11s @%-6d size=%-7d  payload[0:48]=%s"
              % (nm, p2, sz, b[p2 + 4:p2 + 4 + min(sz, 48)].hex(" ")))
        p2 = PAD(p2 + sz)
    print("    walk end =", p2, " PAD(p2)==p2 ->", p2 % 4 == 0)
    # is there a following frame header?
    if p2 + 12 <= len(b):
        cw2, ch2, cx2, cy2, ft2, un2, fi2 = struct.unpack_from("<2H 2h 2B H", b, p2)
        print("    next header @%d canvas=%dx%d ft=0x%02x idx=%d" % (p2, cw2, ch2, ft2, fi2))
    print("    first 160 bytes of file:")
    for i in range(0, min(160, len(b)), 16):
        chunk = b[i:i + 16]
        print("       %5d  %s  |%s|" % (i, " ".join("%02x" % c for c in chunk),
                                        "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)))
