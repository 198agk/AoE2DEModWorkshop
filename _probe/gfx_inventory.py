# -*- coding: utf-8 -*-
"""Authoritative inventory for the sprite/graphics capability catalogue."""
import os
import struct
import sys
from collections import Counter

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

ext = Counter()
size = Counter()
tot = 0
sld_x1 = sld_x2 = 0
zero = []
per_dir = Counter()
for root, dirs, files in os.walk(GAME):
    for f in files:
        e = os.path.splitext(f)[1].lower()
        ext[e] += 1
        try:
            sz = os.path.getsize(os.path.join(root, f))
        except OSError:
            continue
        if e == ".sld":
            tot += sz
            if f.endswith("_x1.sld"):
                sld_x1 += 1
            elif f.endswith("_x2.sld"):
                sld_x2 += 1
            if sz == 0:
                zero.append(os.path.relpath(os.path.join(root, f), GAME))
        per_dir[os.path.relpath(root, GAME)] += 1

print("=== extension census over the WHOLE game tree ===")
for e, c in ext.most_common(26):
    print("  %-10s %8d" % (e or "(none)", c))
print("\n  .sld total bytes :", tot)
print("  .sld  _x1 :", sld_x1, "   _x2 :", sld_x2)
print("  zero-byte .sld   :", zero)

print("\n=== drs/graphics inventory ===")
c = Counter()
n = 0
for f in os.listdir(GP):
    e = os.path.splitext(f)[1].lower()
    c[e] += 1
    n += 1
print("  files:", n)
for e, k in c.most_common(12):
    print("   %-8s %7d" % (e, k))

# prefix histogram of sld names
c2 = Counter()
for f in os.listdir(GP):
    if f.endswith(".sld"):
        c2[f.split("_")[0]] += 1
print("\n=== .sld name prefix histogram ===")
for k, v in c2.most_common(20):
    print("  %-8s %7d" % (k, v))

# palettes
PAL = os.path.join(GAME, "resources", "_common", "palettes")
if os.path.isdir(PAL):
    pc = Counter()
    magic = Counter()
    for f in os.listdir(PAL):
        e = os.path.splitext(f)[1].lower()
        pc[e] += 1
        p = os.path.join(PAL, f)
        if os.path.getsize(p) > 12:
            head = open(p, "rb").read(12)
            magic[head[:8].rstrip(b"\r\n ").decode("latin1", "replace")] += 1
    print("\n=== palettes dir ===")
    print("  ", dict(pc))
    print("  magic:", dict(magic))
