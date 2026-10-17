# -*- coding: utf-8 -*-
"""Find the rectangle the `damage` layer indexes for the 63.75% of layers
whose command array differs from main's.

Hypothesis: the damage layer carries its OWN rect, stored somewhere in its
payload (not necessarily at offset 0).  Search the whole payload for a
4x u16 rect whose ceil4 grid == damage.span.
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, grid_of

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")


def mask_cmds(l):
    fmt, n = struct.unpack_from("<2H", l.data, 0)
    return fmt, [struct.unpack_from("<2B", l.data, 4 + 2 * i)
                 for i in range(n)]


def gs(rect):
    x1, y1, x2, y2 = rect
    if x2 <= x1 or y2 <= y1 or x2 > 4096 or y2 > 4096:
        return -1
    return ((x2 - x1 + 3) // 4) * ((y2 - y1 + 3) // 4)


FILES = [
    ("b_afri_gate_stone_e_constr_x1.sld", 2),
    ("b_afri_gate_stone_n_constr_x1.sld", 2),
    ("b_afri_mill_age2_x1.sld", 1),
    ("b_afri_gate_stone_e_constr_x2.sld", 2),
]
for fn, fi in FILES:
    p = os.path.join(GP, fn)
    if not os.path.exists(p):
        print("(missing)", fn)
        continue
    s = read_sld(p)
    fr = s.frames[fi]
    L = fr.layers
    d = L["damage"]
    m = L["main"]
    mrect, mfmt, mn, mcmds = parse_rect_layer(m)
    dfmt, dcmds = mask_cmds(d)
    n = len(dcmds)
    dspan = sum(c[1] for c in dcmds)
    print("\n=== %s f%d ===" % (fn, fi))
    print("  canvas %dx%d  main rect=%s grid=%d span=%d ncmd=%d"
          % (fr.canvas_w, fr.canvas_h, mrect, gs(mrect), sum(c[1] for c in mcmds), mn))
    print("  damage fmt=0x%04x ncmd=%d span=%d size=%d" % (dfmt, n, dspan, d.size))
    print("  damage first 40 u16: %s"
          % (struct.unpack_from("<20H", d.data, 0),))
    # search for a rect anywhere in the payload whose grid == dspan
    dd = d.data
    hits = []
    for o in range(0, min(len(dd) - 8, 4096)):
        r = struct.unpack_from("<4H", dd, o)
        if gs(r) == dspan:
            hits.append((o, r))
    print("  rect candidates with grid==dspan, offsets<4096: %d %s"
          % (len(hits), hits[:6]))
    # is the damage cmd array a subsequence/run-length-of main's?
    ms = set(c for c, _ in [(i, 0) for i in range(0)])
    print("  damage cmds[:6]=%s  main cmds[:6]=%s" % (dcmds[:6], mcmds[:6]))
    print("  identical cmds? %s" % (dcmds == mcmds))
    # compare as cell lists on main grid
    from sldlib import placed_blocks
    bw, bh = grid_of(mrect)[4], grid_of(mrect)[5]
    dcells = [c for c, _ in placed_blocks(dcmds, bw, bh)]
    mcells = [c for c, _ in placed_blocks(mcmds, bw, bh)]
    print("  dcells[:12]=%s" % dcells[:12])
    print("  mcells[:12]=%s" % mcells[:12])
    print("  dspan/ncmd=%.3f  mspan/ncmd=%.3f  bw*bh=%d"
          % (dspan / n, sum(c[1] for c in mcmds) / mn, bw * bh))
