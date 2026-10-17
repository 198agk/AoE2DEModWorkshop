# -*- coding: utf-8 -*-
"""What IS the `unknown2` layer?  It is mandatory for every frame that
carries `main` (0 exceptions in 4,737,215 frames), so a from-scratch encoder
cannot dodge it.

Test the size hypothesis against the main layer:
    unknown2 size == 16 + 2*ncmd + 8*sum(draw)   (a rect layer, like main)
    unknown2 size ==  8 + 2*ncmd + 8*sum(draw)   (a mask layer, sharing main's grid)
    unknown2 size == 8 * sum(draw) + const
and dump a few bodies to see whether they parse as rect or mask.
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, parse_mask_layer

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"

rel = collections.Counter()
samples = []
files = 0
for f in sorted(os.listdir(GP)):
    if not f.endswith(".sld"):
        continue
    p = os.path.join(GP, f)
    if os.path.getsize(p) == 0:
        continue
    try:
        s = read_sld(p)
    except Exception:
        continue
    files += 1
    for fr in s.frames:
        u = fr.layers.get("unknown2")
        m = fr.layers.get("main")
        if u is None:
            continue
        if m is None:
            rel[("no-main", len(u.data))] += 1
            continue
        rect, fmt, ncmd, cmds = parse_rect_layer(m)
        span = sum(d for _s, d in cmds)
        rel[(len(u.data) - (16 + 2 * ncmd + 8 * span), fmt)] += 1
        if len(samples) < 4 and span > 20:
            samples.append((f, fr.index, rect, fmt, ncmd, span, len(u.data),
                            u.data[:64]))
    if files >= 60:
        break

print("files scanned", files)
print("unknown2 size minus a MAIN-shaped formula (delta, main fmt) histogram:")
for k, v in sorted(rel.items(), key=lambda kv: -kv[1])[:10]:
    print("  delta=%-6s fmt=0x%04x  %d" % (k[0], k[1], v))

print()
for f, ix, rect, fmt, ncmd, span, usz, head in samples:
    print("%s f%d rect=%s fmt=0x%04x ncmd=%d span=%d unknown2=%dB"
          % (f, ix, rect, fmt, ncmd, span, usz))
    print("   head %s" % head.hex())
    # try both shapes
    try:
        r, uf, un, uc = parse_rect_layer_safe = (None,)
    except Exception:
        pass
    print("   as mask: fmt=%s ncmd=%s sum=%s"
          % (struct.unpack_from("<H", head, 0)[0],
             struct.unpack_from("<H", head, 2)[0],
             sum(head[4 + 2 * i] + head[5 + 2 * i]
                 for i in range(struct.unpack_from("<H", head, 2)[0]))))
