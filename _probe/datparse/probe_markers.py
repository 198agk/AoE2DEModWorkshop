#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan the terrain region for 0x0A60 debug-string markers and decode each,
so record boundaries and per-record marker offsets become visible."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

data, how = P.load_dat(r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat")

start = 0x355F1A
end = 0x380000
print("scanning 0x%X .. 0x%X for 0A 60 markers" % (start, end))

hits = []
i = start
while i < end - 4:
    if data[i] == 0x60 and data[i + 1] == 0x0A:
        ln = data[i + 2] | (data[i + 3] << 8)
        if 0 < ln < 200 and i + 4 + ln <= len(data):
            s = data[i + 4:i + 4 + ln]
            if all(32 <= b < 127 for b in s):
                hits.append((i, ln, s.decode("ascii", "replace")))
                i += 4 + ln
                continue
    i += 1

print("%d markers" % len(hits))
prev = None
for off, ln, s in hits[:60]:
    d = "" if prev is None else " (+%d from prev)" % (off - prev)
    print("  0x%08X  len=%-4d %-30r%s" % (off, ln, s, d))
    prev = off
