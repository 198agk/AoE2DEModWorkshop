# -*- coding: utf-8 -*-
"""The `damage` layer (frame_type bit 3) does NOT use the main layout:
   main/shadow  size == 16 + 2*ncmd + 8*sum(draw)   [100% verified]
   damage       size == 16 + 2*ncmd + 8*sum(draw)   [33,517 / 66,620 FAIL]
Collect damage layer sizes and the first bytes to find its real layout.
Read-only.
"""
import os
import struct
import collections

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
ceil4 = lambda x: x + ((4 - x % 4) % 4)

sizes = collections.Counter()
samples = []
resid = collections.Counter()
n = 0


def walk(b, fo):
    p = fo
    while p < len(b):
        cw, ch, cx, cy, ft, un, idx = struct.unpack_from("<2H 2h 2B H", b, p)
        q = p + 12
        out = []
        for bit, nm in [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"),
                        (4, "playercolor")]:
            if not (ft & (1 << bit)):
                continue
            size = struct.unpack_from("<I", b, q)[0]
            out.append((nm, q, size))
            q = q + ceil4(size)
        yield idx, ft, out
        p = q


files = sorted(f for f in os.listdir(GP) if f.lower().endswith(".sld"))
for fn in files:
    b = open(os.path.join(GP, fn), "rb").read()
    if not b:
        continue
    _, _, _, _, fo, _ = struct.unpack_from("<4s 2H 2H H", b, 0)
    ts = False
    for idx, ft, layers in walk(b, fo):
        for nm, q, size in layers:
            if nm != "damage":
                continue
            ts = True
            n += 1
            sizes[size] += 1
            rect = struct.unpack_from("<4H", b, q + 4)
            fmt, ncmd = struct.unpack_from("<2H", b, q + 12)
            base = 16 + 2 * ncmd
            rem = size - base
            resid[rem % 8] += 1
            if len(samples) < 20:
                samples.append((fn, idx, size, rect, fmt, ncmd, rem,
                                b[q:q + min(size, 40)].hex(" ")))

print("damage layers found:", n)
print("size histogram (top 20):", sizes.most_common(20))
print("(size - 16 - 2*ncmd) % 8 histogram:", dict(resid))
print()
for s in samples:
    print("fn=%s idx=%d size=%d rect=%s fmt=0x%04x ncmd=%d rem=%d" % s[:7])
    print("    %s" % s[7])
