# -*- coding: utf-8 -*-
"""Solve the `damage` layer layout arithmetically.

The damage overlay must cover the SAME block grid as main, so
    sum(draw) == main.span  (known exactly).
Therefore, if the layout is  <cmd_start bytes of header> | ncmd*(u8,u8) | blocks
    size == cmd_start + 2*ncmd + 8*span
so   cmd_start + 2*ncmd == size - 8*span
which pins both unknowns.  Test cmd_start over a range and see which value
makes ncmd a positive integer AND the commands sum to exactly `span`.

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
vote = collections.Counter()
samples = []
n_damage = 0
ctt = collections.Counter()


def main_span(b, q, size):
    rect = struct.unpack_from("<4H", b, q + 4)
    fmt, ncmd = struct.unpack_from("<2H", b, q + 12)
    cmds = [(b[q + 16 + 2 * i], b[q + 17 + 2 * i]) for i in range(ncmd)]
    return sum(s + d for s, d in cmds), rect, ncmd


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
        if "damage" not in lay or "main" not in lay:
            continue
        n_damage += 1
        span, mrect, mncmd = main_span(b, *lay["main"])
        dq, dsize = lay["damage"]
        need = dsize - 8 * span
        for cs in range(4, 40, 2):
            rem = need - cs
            if rem <= 0 or rem % 2:
                continue
            ncmd = rem // 2
            if ncmd <= 0 or cs + 2 * ncmd > dsize:
                continue
            cmds = [(b[dq + cs + 2 * i], b[dq + cs + 2 * i + 1]) for i in range(ncmd)]
            s = sum(x + y for x, y in cmds)
            if s == span:
                vote[cs] += 1
                if len(samples) < 10:
                    samples.append((fn, idx, dsize, span, cs, ncmd, mrect,
                                    b[dq:dq + min(dsize, 32)].hex(" ")))
                break
        else:
            ctt["no_cs_fits"] += 1

print("damage layers with a main layer:", n_damage)
print("votes for cmd_start (bytes where cmds begin):", vote.most_common())
print("could not fit any cmd_start:", ctt["no_cs_fits"])
print()
for s in samples:
    print("fn=%s idx=%d dsize=%d main_span=%d cmd_start=%d ncmd=%d rect=%s" % s[:7])
    print("    %s" % s[7])
