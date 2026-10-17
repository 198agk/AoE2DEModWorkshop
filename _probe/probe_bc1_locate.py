# -*- coding: utf-8 -*-
"""Locate the block whose round trip is wrong."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import (read_sld, parse_rect_layer, grid_of, rect_blocks,
                    decode_bc1_plane, placed_blocks)
from probe_sld_encode import replace_main, encode_bc1_block

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
p = os.path.join(GP, "a_herd_sheep_idleA_x1.sld")
s = read_sld(p)
m = s.frames[0].layers["main"]
rect, fmt, ncmd, cmds = parse_rect_layer(m)
x1, y1, rw, rh, bw, bh = grid_of(rect)
W, H = bw * 4, bh * 4
print("rect", rect, "grid", bw, bh, "W,H", W, H, "ncmd", ncmd,
      "sum(draw)", sum(d for _s, d in cmds))

img = bytearray(W * H * 4)
for y in range(H):
    for x in range(W):
        o = (y * W + x) * 4
        img[o:o + 4] = bytes((230, 30, 30, 255) if (x // 4 + y // 4) % 2 == 0
                             else (30, 30, 230, 255))

placed = placed_blocks(cmds, bw, bh)
print("cells drawn", len(placed), "of", bw * bh)

# encode each block, decode it immediately, report the worst
worst = (-1, None)
for cell, drawn in placed:
    gx, gy = (cell % bw) * 4, (cell // bw) * 4
    px = []
    for i in range(16):
        x, y = gx + (i % 4), gy + (i // 4)
        o = (y * W + x) * 4
        px.append(tuple(img[o:o + 4]))
    blk = encode_bc1_block(px)
    from sldlib import bc1_palette, _idx_bits
    pal = bc1_palette(blk)
    bits = _idx_bits(blk)
    err = max(max(abs(pal[bits[i]][c] - px[i][c]) for c in range(3))
              for i in range(16))
    if err > worst[0]:
        worst = (err, (cell, gx, gy, px[0], blk.hex(), pal, bits[:4]))
print("worst per-block error", worst[0], worst[1][:3] if worst[1] else None)
if worst[0] > 10:
    cell, gx, gy, p0, hx, pal, bits = worst[1]
    print("  sample pixel", p0, "block", hx)
    print("  palette", pal)
    print("  bits", bits)
