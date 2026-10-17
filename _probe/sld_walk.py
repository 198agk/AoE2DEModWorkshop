# -*- coding: utf-8 -*-
"""Validate the ALIGNED layer walk (u32 size + 4-byte pad between layers).

Hypothesis from frame 0 of u_arc_archer_idlea_x1.sld:
  header @16 (12 B); main @28 size 412 -> 440; shadow @440 size 574 -> 1014
  pad 2 -> 1016; unknown2 size 178 -> 1194 pad 2 -> 1196;
  playercolor size 106 -> 1302 pad 2 -> 1304 = frame 1 header.  (412+574+178+106+6 = 1276)
The walk therefore uses ONLY declared u32 sizes + 4-byte alignment.

Strong validation: walk 200 consecutive frames and require frame_index to
increment 0,1,2,... for EVERY frame.  If that holds the walk is right.
Also dump full raw bytes of an ft==0x01 (main only) frame to learn the minimal
layer layout.  Read-only.
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


def walk_frames(b, start=16, limit=None):
    """Yield (off, canvas, ft, idx, [(name, size, off)])."""
    off = start
    n = 0
    while off + 12 <= len(b):
        cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", b, off)
        if cw == 0 or ch == 0 or cw > 4096 or ch > 4096:
            return
        p = off + 12
        layers = []
        ok = True
        for bit, nm in BITS:
            if not (ft & (1 << bit)):
                continue
            if p + 4 > len(b):
                ok = False
                break
            sz = u32(b, p)
            if sz < 4 or p + sz > len(b):
                ok = False
                break
            layers.append((nm, sz, p))
            p = PAD(p + sz)
        yield off, (cw, ch), ft, fi, layers, p, ok
        if p <= off:
            return
        off = p
        n += 1
        if limit and n >= limit:
            return


name = "u_arc_archer_idlea_x1.sld"
b = open(os.path.join(GP, name), "rb").read()
print("=" * 78)
print("V1  aligned walk over 300 frames of %s (file %d B)" % (name, len(b)))
prev = -1
bad = []
count = 0
szs = {nm: Counter() for _, nm in BITS}
for off, (cw, ch), ft, fi, layers, endp, ok in walk_frames(b, 16, 300):
    if not ok or fi != prev + 1:
        bad.append((count, off, fi, prev, ok, ft))
        if len(bad) > 6:
            break
    for nm, sz, _ in layers:
        szs[nm][sz] += 1
    prev = fi
    count += 1
print("   frames walked: %d ; first idx=%d ; last idx=%d ; discontinuities=%d"
      % (count, 0, prev, len(bad)))
for r in bad[:6]:
    print("      BAD", r)
print("   layer size histograms (top 6):")
for nm, c in szs.items():
    if c:
        print("      %-11s n=%-5d top=%s" % (nm, sum(c.values()), c.most_common(6)))

print()
print("=" * 78)
print("V2  minimal frame: find an .sld whose frame_type == 0x01 (main only) and dump it")
found = None
for fn in sorted(os.listdir(GP))[:4000]:
    if not fn.endswith(".sld"):
        continue
    p = os.path.join(GP, fn)
    if os.path.getsize(p) < 200:
        continue
    bb = open(p, "rb").read(4096)
    if bb[:4] != b"SLDX":
        continue
    ft = bb[16 + 8]
    if ft == 0x01:
        found = (fn, p, bb)
        break
if not found:
    print("   none in first 4000 files")
else:
    fn, p, bb = found
    full = open(p, "rb").read()
    print("   file: %s  size=%d" % (fn, len(full)))
    cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", full, 16)
    print("   frame0: canvas=%dx%d centre=(%d,%d) ft=0x%02x idx=%d" % (cw, ch, cx, cy, ft, fi))
    sz = u32(full, 28)
    print("   main layer declared size = %d" % sz)
    print("   bytes 28..28+%d:" % sz)
    for i in range(28, 28 + min(sz, 200), 16):
        chunk = full[i:i + 16]
        print("      %5d  %s  |%s|" % (i, " ".join("%02x" % c for c in chunk),
                                       "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)))
    # minimal layout candidate: u32 size, 4xu16 rect, u16 a, u16 ncmd, cmds
    x1, y1, x2, y2 = struct.unpack_from("<4H", full, 32)
    a1, ncmd = struct.unpack_from("<2H", full, 40)
    cmds = [(full[44 + 2 * i], full[45 + 2 * i]) for i in range(ncmd)]
    draws = sum(c[1] for c in cmds)
    comp = 16 + 2 * ncmd + 8 * draws
    print("   candidate: rect=(%d,%d)-(%d,%d) %dx%d  a1=0x%04x ncmd=%d draws=%d comp=%d %s"
          % (x1, y1, x2, y2, x2 - x1, y2 - y1, a1, ncmd, draws, comp,
             "MATCH" if comp == sz else "mismatch delta=%d" % (comp - sz)))
    print("   after main: next frame?")
    nxt = PAD(28 + sz)
    print("      padded next = %d ; u32 there = %d" % (nxt, u32(full, nxt)))
