# -*- coding: utf-8 -*-
"""The 1,322 round-trip diffs all start at offset 25.  Hypothesis: I write a
literal 0 for the frame-header `unknown` byte and never kept the original.
Check the distribution of that byte across the tree."""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, ceil4, BITS

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

c = Counter()
per_file = Counter()
files_with_nz = 0
for f in sorted(os.listdir(GP)):
    if not f.endswith(".sld"):
        continue
    p = os.path.join(GP, f)
    if os.path.getsize(p) == 0:
        continue
    b = open(p, "rb").read()
    fo = struct.unpack_from("<H", b, 10)[0]   # 5th field: sig(4) ver(2) nf(2) u1(2) fo(2) magic(2)
    q = fo
    nz = 0
    first = None
    while q < len(b):
        cw, ch, cx, cy, ft, un, idx = struct.unpack_from("<2H 2h 2B H", b, q)
        c["unknown=%d" % un] += 1
        if un:
            nz += 1
            if first is None:
                first = (f, fo, idx, un, ft)
        # advance
        q += 12
        for bit, nm in BITS:
            if not (ft & (1 << bit)):
                continue
            size = struct.unpack_from("<I", b, q)[0]
            q += ceil4(size)
    per_file[nz] += 1
    if nz:
        files_with_nz += 1
        if files_with_nz <= 8:
            print("   non-zero file:", first)

print("=== frame-header `unknown` byte distribution (all frames) ===")
for k, v in c.most_common(12):
    print("  %-16s %9d" % (k, v))
print("\n=== per-file count of frames with unknown != 0 ===")
for k, v in sorted(per_file.items())[:12]:
    print("  nz=%d -> %d files" % (k, v))
print("  files with at least one non-zero unknown:", files_with_nz)
