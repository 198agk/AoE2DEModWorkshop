# -*- coding: utf-8 -*-
"""Which frame_type bit combinations actually occur, and can a frame carry
main + playercolor WITHOUT the unresolved `unknown2` layer?

That question decides whether a from-scratch encoder is possible at all
without solving unknown2: main (BC1), shadow (BC4 rect) and playercolor
(BC4 mask) are all understood, unknown2 is not.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"

ft = collections.Counter()
combo = collections.Counter()
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
        ft[fr.frame_type] += 1
        combo[tuple(sorted(fr.layers))] += 1

print("files", files)
print("frame_type histogram (hex -> count):")
for k, v in sorted(ft.items(), key=lambda kv: -kv[1]):
    bits = [n for b, n in ((0, "main"), (1, "shadow"), (2, "unknown2"),
                           (3, "damage"), (4, "playercolor")) if k & (1 << b)]
    print("  0x%02x %7d  %s" % (k, v, "+".join(bits) or "(none)"))

print()
print("layer-set combos:")
for k, v in sorted(combo.items(), key=lambda kv: -kv[1])[:15]:
    print("  %7d  %s" % (v, "+".join(k) or "(none)"))
