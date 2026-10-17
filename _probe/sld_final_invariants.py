# -*- coding: utf-8 -*-
"""Authoritative full-tree SLD invariant pass (for the capability catalogue).

Corrected accounting: a layer whose command array is EMPTY (ncmd total cells 0)
is a legitimate blank layer, not a violation.  We separate:
   empty_cmds      : sum(skip+draw) == 0            (blank layer)
   grid_bad        : sum(skip+draw) != 0 and != main bw*bh
   size_bad        : size != base + 2*ncmd + 8*sum(draw)
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, grid_of

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

st = Counter()
bad_examples = []
lay = Counter()

for f in sorted(os.listdir(GP)):
    if not f.endswith(".sld"):
        continue
    p = os.path.join(GP, f)
    if os.path.getsize(p) == 0:
        st["zero_byte_files"] += 1
        continue
    try:
        s = read_sld(p)
    except Exception as e:
        st["walk_fail"] += 1
        if len(bad_examples) < 6:
            bad_examples.append(("WALK", f, str(e)))
        continue
    st["files_ok"] += 1
    st["frames"] += len(s.frames)
    if len(s.frames) != s.num_frames:
        st["num_frames_mismatch"] += 1
    st["fo_%d" % s.frame_offset] += 1
    for fr in s.frames:
        L = fr.layers
        for name, l in L.items():
            lay[name] += 1
        if "main" not in L:
            st["frames_without_main"] += 1
            continue
        r, mfmt, mn, mcmds = parse_rect_layer(L["main"])
        bw, bh = grid_of(r)[4], grid_of(r)[5]
        grid = bw * bh
        mspan = sum(b for _, b in mcmds)
        mcells = sum(a + b for a, b in mcmds)
        if L["main"].size != 16 + 2 * mn + 8 * mspan:
            st["main_size_bad"] += 1
            if len(bad_examples) < 8:
                bad_examples.append(("MAIN_SIZE", f, fr.index))
        if mcells == 0:
            st["main_empty"] += 1
        elif mcells != grid:
            st["main_grid_bad"] += 1
            if len(bad_examples) < 8:
                bad_examples.append(("MAIN_GRID", f, fr.index, mcells, grid))

        for nm, base_extra in (("playercolor", 8), ("damage", 8),
                               ("shadow", 16)):
            if nm not in L:
                continue
            l = L[nm]
            if base_extra == 16:
                rr, fmt, n, cmds = parse_rect_layer(l)
                span = sum(b for _, b in cmds)
                base = 16
            else:
                fmt, n, cmds, _ = _mask = None, None, None, None
                fmt, n = struct.unpack_from("<2H", l.data, 0)
                cmds = [struct.unpack_from("<2B", l.data, 4 + 2 * i)
                        for i in range(n)]
                span = sum(b for _, b in cmds)
                base = 8
            cells = sum(a + b for a, b in cmds)
            if l.size != base + 2 * n + 8 * span:
                st["%s_size_bad" % nm] += 1
            if cells == 0:
                st["%s_empty" % nm] += 1
            elif nm in ("playercolor", "damage") and cells != grid:
                st["%s_grid_bad" % nm] += 1
                if len(bad_examples) < 10:
                    bad_examples.append((nm.upper() + "_GRID", f, fr.index,
                                         cells, grid))

print("=== authoritative SLD invariants ===")
for k in sorted(st):
    print("  %-24s %10d" % (k, st[k]))
print("\n=== layers per tree ===")
for k, v in sorted(lay.items()):
    print("  %-14s %9d" % (k, v))
print("\n=== examples of residual violations ===")
for b in bad_examples:
    print("   ", b)
