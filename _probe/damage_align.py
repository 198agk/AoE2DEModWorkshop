# -*- coding: utf-8 -*-
"""Structural alignment test for the `damage` layer.

damage uses the MASK header layout (8 + 2*ncmd + 8*span) and its data is a
BC4 mask (rendering it as BC1 colour gives garbage; rendering it as a red
overlay reproduces the building silhouette exactly).

Open question: on which grid are its blocks placed, given dspan != main.span
in 63% of layers?

Test 1: is damage's command run-list byte-identical to main's?
Test 2: placed on MAIN's grid, do the cells damage marks coincide with cells
        main actually draws?  (subset property)
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, grid_of, placed_blocks

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")


def mask_cmds(l):
    fmt, n = struct.unpack_from("<2H", l.data, 0)
    return fmt, [struct.unpack_from("<2B", l.data, 4 + 2 * i)
                 for i in range(n)]


ident = 0
differ = 0
tot = 0
subset_ok = 0
subset_bad = 0
bad_ex = []
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
        tot += 1
        rect, mfmt, mn, mcmds = parse_rect_layer(L["main"])
        x1, y1, rw, rh, bw, bh = grid_of(rect)
        dfmt, dcmds = mask_cmds(L["damage"])
        if dcmds == mcmds:
            ident += 1
        else:
            differ += 1
        mcells = set(c for c, _ in placed_blocks(mcmds, bw, bh))
        dcells = set(c for c, _ in placed_blocks(dcmds, bw, bh))
        if dcells <= mcells:
            subset_ok += 1
        else:
            subset_bad += 1
            if len(bad_ex) < 5:
                bad_ex.append((f, fr.index, len(dcells - mcells),
                               len(dcells), len(mcells), dfmt, len(dcmds)))

print("frames with damage+main          : %d" % tot)
print("damage cmds == main cmds         : %d  (%.2f%%)"
      % (ident, 100.0 * ident / tot))
print("damage cmds != main cmds         : %d" % differ)
print("damage cells SUBSET of main cells: %d  (%.2f%%)"
      % (subset_ok, 100.0 * subset_ok / tot))
print("damage cells NOT subset          : %d" % subset_bad)
for e in bad_ex:
    print("   ", e)

# for the identical-cmds set, does the mask look like a coherent overlay?
print("\n=== BC4 mask value distribution on identical-cmd layers ===")
val = Counter()
n = 0
for f in sorted(os.listdir(GP))[:4000]:
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
        rect, mfmt, mn, mcmds = parse_rect_layer(L["main"])
        dfmt, dcmds = mask_cmds(L["damage"])
        if dcmds != mcmds:
            continue
        d = L["damage"]
        nn = len(dcmds)
        blocks = [d.data[4 + 2 * nn + 8 * i: 4 + 2 * nn + 8 * i + 8]
                  for i in range((d.size - 8 - 2 * nn) // 8)]
        for b in blocks:
            val[b[0]] += 1
        n += len(blocks)
print("sampled blocks: %d ; top first-byte values: %s"
      % (n, val.most_common(10)))
