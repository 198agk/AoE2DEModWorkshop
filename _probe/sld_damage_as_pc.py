# -*- coding: utf-8 -*-
"""Does `damage` use the SAME layout as playercolor?
    damage: u16 fmt | u16 ncmd | ncmd*(u8 skip,u8 draw) | blocks
            size == 8 + 2*ncmd + 8*sum(draw),  sum(draw) == main.span
Read-only.
"""
import os
import struct
import collections

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
ceil4 = lambda x: x + ((4 - x % 4) % 4)
BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]

files = sorted(f for f in os.listdir(GP) if f.lower().endswith(".sld"))
stat = collections.Counter()
bad = []
n = 0


def main_span_and_cmds(b, q, size):
    fmt, ncmd = struct.unpack_from("<2H", b, q + 12)
    cmds = [(b[q + 16 + 2 * i], b[q + 17 + 2 * i]) for i in range(ncmd)]
    return sum(s + d for s, d in cmds), ncmd


for fn in files:
    b = open(os.path.join(GP, fn), "rb").read()
    if not b:
        continue
    _, _, _, _, fo, _ = struct.unpack_from("<4s 2H 2H H", b, 0)
    p = fo
    while p < len(b):
        cw, ch, cx, cy, ft, un, idx = struct.unpack_from("<2H 2h 2B H", b, p)
        q = p + 12
        lay = {}
        for bit, nm in BITS:
            if not (ft & (1 << bit)):
                continue
            size = struct.unpack_from("<I", b, q)[0]
            lay[nm] = (q, size)
            q += ceil4(size)
        p = q
        d = lay.get("damage")
        m = lay.get("main") or lay.get("shadow")
        if not d or not m:
            continue
        n += 1
        span, _ = main_span_and_cmds(b, *m)
        dq, dsize = d
        if dsize < 8:
            stat["too_small"] += 1
            continue
        fmt, ncmd = struct.unpack_from("<2H", b, dq + 4)
        avail = dsize - 8
        if 2 * ncmd > avail:
            stat["ncmd_overflow"] += 1
            continue
        cmds = [(b[dq + 8 + 2 * i], b[dq + 9 + 2 * i]) for i in range(ncmd)]
        s = sum(x + y for x, y in cmds)
        comp = 8 + 2 * ncmd + 8 * s
        stat["comp_eq_size"] += (comp == dsize)
        stat["comp_ne_size"] += (comp != dsize)
        stat["span_eq_main"] += (s == span)
        stat["span_ne_main"] += (s != span)
        stat["both_ok"] += (comp == dsize and s == span)
        if not (comp == dsize and s == span) and len(bad) < 12:
            bad.append((fn, idx, dsize, comp, span, s, ncmd, fmt))

print("damage layers examined:", n)
for k in sorted(stat):
    print("   %-16s %d" % (k, stat[k]))
print()
print("failures / mismatches:")
for e in bad:
    print("   fn=%s idx=%d dsize=%d comp=%d main_span=%d dspan=%d ncmd=%d fmt=0x%04x" % e)
