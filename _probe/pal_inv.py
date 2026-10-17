# -*- coding: utf-8 -*-
import os
from collections import Counter

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PAL = os.path.join(GAME, "resources", "_common", "palettes")

c = Counter()
magic = Counter()
sub = []
for root, dirs, files in os.walk(PAL):
    for f in files:
        e = os.path.splitext(f)[1].lower()
        c[e] += 1
        p = os.path.join(root, f)
        try:
            head = open(p, "rb").read(10)
        except Exception:
            continue
        magic[head[:8].rstrip(b"\r\n ").decode("latin1", "replace")] += 1
    for d in dirs:
        sub.append(os.path.relpath(os.path.join(root, d), PAL))
print("palettes ext:", dict(c))
print("palettes magic:", dict(magic))
print("subdirs:", sub)

GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
n = sum(1 for f in os.listdir(GP) if f.endswith(".sld"))
tot = 0
where = Counter()
for root, dirs, files in os.walk(GAME):
    for f in files:
        if f.endswith(".sld"):
            tot += 1
            where[os.path.relpath(root, GAME)] += 1
print("drs/graphics sld:", n, " whole tree sld:", tot, " elsewhere:", tot - n)
for k, v in where.most_common(8):
    print("   %-58s %6d" % (k, v))
