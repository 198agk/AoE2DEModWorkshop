# -*- coding: utf-8 -*-
"""Is `unknown2` derivable from the main layer?

Two observations from the first probe:
  * in one file the first ~20 bytes of unknown2 are IDENTICAL across frames;
  * size - main_span looked like a constant (131-40 = 91, 129-38 = 91, 127-36 = 91).

This probe tests both on many files:
  (a) is `size(unknown2) - main_span` constant within a file?
  (b) is the head prefix constant within a file?
  (c) across files, does `size - span` cluster on a few values?
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, parse_mask_layer

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"

delta_hist = collections.Counter()
prefix_const = 0
prefix_varied = 0
extra = collections.Counter()
examples = []
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
    heads = set()
    deltas = set()
    for fr in s.frames:
        u = fr.layers.get("unknown2")
        m = fr.layers.get("main")
        if u is None:
            continue
        heads.add(bytes(u.data[:16]))
        if m is None:
            continue
        rect, fmt, ncmd, cmds = parse_rect_layer(m)
        span = sum(d for _s, d in cmds)
        deltas.add(len(u.data) - span)
        delta_hist[len(u.data) - span] += 1
        # does the tail carry 8-byte blocks like other layers?
        extra[(len(u.data) - span) % 8] += 1
    if len(heads) == 1:
        prefix_const += 1
    elif heads:
        prefix_varied += 1
        if len(examples) < 5:
            examples.append((f, sorted(len(h) for h in heads)))

print("files", files)
print("(a) files whose unknown2 head prefix is CONSTANT across frames :", prefix_const)
print("    files where it VARIES                                       :", prefix_varied)
for e in examples:
    print("      varied:", e)
print()
print("(c) size(unknown2) - main_span, most common values:")
for k, v in sorted(delta_hist.items(), key=lambda kv: -kv[1])[:12]:
    print("   delta=%-6d %d" % (k, v))
print()
print("(b) (size - span) mod 8 ->", dict(extra))
