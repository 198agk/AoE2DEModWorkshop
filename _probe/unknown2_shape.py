# -*- coding: utf-8 -*-
"""unknown2 structure probe + empty-frame rule confirmation.

Facts already established:
  unknown2 payload starts with u16 tag == 5 for 810,344 / 810,344 layers
  (the next u16 is 0 -> the 4 leading bytes read as u32 == 5).
  The tail is NOT block-structured (size parity varies, (%4)/(%8) uniform).

Q_a: is the 4-byte lead really u32==5, or u16 tag + u16 count?
Q_b: what is the strictly-increasing u16 sequence after it?
Q_c: do the 761 span==0 frames coincide exactly with sum(skip+draw)==0?
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, grid_of, parse_mask_layer

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

# ---------------- Q_c: empty frames ----------------
zero_span = 0
zero_span_cells0 = 0
zero_span_cellsnz = 0
nz_span_bad = 0
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
    for fr in s.frames:
        L = fr.layers
        if not isinstance(L, dict) or "main" not in L:
            continue
        r, mfmt, mn, mcmds = parse_rect_layer(L["main"])
        x1, y1, w, h, bw, bh = grid_of(r)
        cells = sum(a + b for a, b in mcmds)
        span = sum(b for a, b in mcmds)
        if span == 0:
            zero_span += 1
            if cells == 0:
                zero_span_cells0 += 1
            else:
                zero_span_cellsnz += 1
                if zero_span_cellsnz <= 5:
                    print("   span0/cells!=0:", f, fr.index, "cells", cells,
                          "grid", bw * bh, "ncmd", mn,
                          "rect", r, "ft", hex(fr.frame_type))
        elif cells != bw * bh:
            nz_span_bad += 1
            if nz_span_bad <= 8:
                print("   span!=0 & cells!=grid:", f, fr.index, "span", span,
                      "cells", cells, "grid", bw * bh, "ft", hex(fr.frame_type))
print("=== Q_c: empty-frame rule ===")
print("  main frames with sum(draw)==0        :", zero_span)
print("     .. of which sum(skip+draw)==0     :", zero_span_cells0)
print("     .. of which sum(skip+draw)!=0     :", zero_span_cellsnz)
print("  main frames sum(draw)!=0 & cells!=grid:", nz_span_bad)

# ---------------- Q_a/Q_b: unknown2 ----------------
print("\n=== Q_a/Q_b: unknown2 ===")
c = Counter()
lens = Counter()
tails = Counter()
shown = 0
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
    for fr in s.frames:
        L = fr.layers
        if not isinstance(L, dict) or "main" not in L or "unknown2" not in L:
            continue
        u = L["unknown2"]
        d = u.data
        c["layers"] += 1
        c["u16[0]==5"] += 1 if struct.unpack_from("<H", d, 0)[0] == 5 else 0
        c["u16[1]==0"] += 1 if struct.unpack_from("<H", d, 2)[0] == 0 else 0
        c["u32[0]==5"] += 1 if struct.unpack_from("<I", d, 0)[0] == 5 else 0
        # count leading strictly-increasing u16 run starting at offset 4
        run = 0
        prev = -1
        while 4 + 2 * (run + 1) <= len(d):
            v = struct.unpack_from("<H", d, 4 + 2 * run)[0]
            if v > prev:
                prev = v
                run += 1
            else:
                break
        lens[run] += 1
        if d:
            tails[d[-2:].hex()] += 1
        if shown < 8:
            print("   %s f%d size=%d run=%d" % (f, fr.index, u.size, run))
            print("      head:", d[:64].hex(" "))
            print("      tail:", d[-32:].hex(" "))
            shown += 1
for k, v in sorted(c.items()):
    print("  %-16s %9d" % (k, v))
print("  increasing-run length histogram (top 12):",
      lens.most_common(12))
print("  last-2-bytes histogram (top 8):", tails.most_common(8))
