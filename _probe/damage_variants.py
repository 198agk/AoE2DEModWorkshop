# -*- coding: utf-8 -*-
"""The damage layer has TWO variants distinguished by its fmt word:
  0x0100 -> span == main.span, renders correctly as a BC4 mask over main
  0x0180 -> different grid

For a run-list, the grid size is sum(skip+draw), not sum(draw)=span.
Check whether sum(skip+draw) equals a plausible cell count for a rect
related to main's rect / canvas.
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, grid_of

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")


def mask(l):
    fmt, n = struct.unpack_from("<2H", l.data, 0)
    cmds = [struct.unpack_from("<2B", l.data, 4 + 2 * i) for i in range(n)]
    return fmt, cmds, sum(c[1] for c in cmds), sum(c[0] + c[1] for c in cmds)


FILES = [
    ("b_afri_archery_range_age2_x1.sld", 0),
    ("b_afri_gate_stone_e_constr_x1.sld", 2),
    ("b_afri_gate_stone_n_constr_x1.sld", 2),
    ("b_afri_mill_age2_x1.sld", 1),
    ("b_afri_gate_stone_e_constr_x2.sld", 2),
    ("b_west_castle_age3_x1.sld", 0),
]
for fn, fi in FILES:
    p = os.path.join(GP, fn)
    if not os.path.exists(p):
        continue
    s = read_sld(p)
    fr = s.frames[fi]
    L = fr.layers
    if "damage" not in L:
        continue
    dfmt, dcmds, dspan, dcells = mask(L["damage"])
    r, mfmt, mn, mcmds = parse_rect_layer(L["main"])
    x1, y1, w, h, bw, bh = grid_of(r)
    mcells = sum(c[0] + c[1] for c in mcmds)
    print("\n%s f%d canvas=%dx%d" % (fn, fi, fr.canvas_w, fr.canvas_h))
    print("   main  rect=%s grid %dx%d = %d (sum skip+draw %d) span %d"
          % (r, bw, bh, bw * bh, mcells, sum(c[1] for c in mcmds)))
    print("   dmg   fmt=0x%04x span=%-6d sum(skip+draw)=%-6d"
          % (dfmt, dspan, dcells))
    cw, ch = fr.canvas_w, fr.canvas_h
    for name, v in [("bw*bh main", bw * bh),
                    ("ceil(cw/4)*ceil(ch/4)", ((cw + 3) // 4) * ((ch + 3) // 4)),
                    ("ceil(cw/8)*ceil(ch/8)", ((cw + 7) // 8) * ((ch + 7) // 8)),
                    ("ceil(cw/2)*ceil(ch/2)", ((cw + 1) // 2) * ((ch + 1) // 2)),
                    ("cw*ch", cw * ch)]:
        print("      vs %-24s %-8d  %s" % (name, v,
              "== sum(skip+draw)" if v == dcells else ""))

# bulk: for fmt 0x0180, does sum(skip+draw) match main's grid?
print("\n=== bulk: fmt vs relations ===")
c = Counter()
n = 0
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
        if not isinstance(L, dict) or "damage" not in L or "main" not in L:
            continue
        n += 1
        dfmt, dcmds, dspan, dcells = mask(L["damage"])
        r, mfmt, mn, mcmds = parse_rect_layer(L["main"])
        x1, y1, w, h, bw, bh = grid_of(r)
        tag = "0x%04x" % dfmt
        c[tag] += 1
        if dspan == sum(cc[1] for cc in mcmds):
            c[tag + " span==main.span"] += 1
        if dcmds == mcmds:
            c[tag + " cmds==main"] += 1
        if dcells == bw * bh:
            c[tag + " cells==main grid"] += 1
        if dcells == ((fr.canvas_w + 3) // 4) * ((fr.canvas_h + 3) // 4):
            c[tag + " cells==canvas/4"] += 1
for k, v in sorted(c.items()):
    print("  %-34s %7d" % (k, v))
print("total", n)
