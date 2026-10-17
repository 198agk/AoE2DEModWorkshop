# -*- coding: utf-8 -*-
"""Sanity-check the tech name field and locate the Age technologies."""
import contextlib
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mod.dat import parser as P
from aoe2mod.dat import locate as L

BASE = os.path.join(r"D:\Games\Steam\steamapps\common\AoE2DE",
                    "resources", "_common", "dat", "empires2_x2_p1.dat")
data, how = P.load_dat(BASE)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
civs, civs_start, gv, tail = L.locate(data, parser=p)
n = struct.unpack_from("<h", data, tail)[0]
print("gv=%d tail=0x%X count=%d" % (gv, tail, n))

# The parser stage for techs also records the tech records it walked; use its
# own reader so this is independent of my probe walk.
r = L.Orec(data, tail + 2, gv=gv)
names = []
for i in range(n):
    t = P.read_tech(r)
    names.append(t["name"])
print("walked to 0x%X  leftover %d" % (r.o, len(data) - r.o))
print()
print("--- techs whose name contains 'Age' ---")
for i, nm in enumerate(names):
    if nm and "Age" in nm:
        print("  id %-5d %r" % (i, nm))
print()
print("--- ids 100..105 raw ---")
for i in range(100, 106):
    print("  id %-5d %r" % (i, names[i]))
print()
print("total techs: %d, named: %d, empty: %d"
      % (len(names), sum(1 for x in names if x), sum(1 for x in names if not x)))
# how many share a name (name is not a unique key)
from collections import Counter
c = Counter(x for x in names if x)
print("distinct names: %d ; most duplicated: %s" % (len(c), c.most_common(4)))
