# -*- coding: utf-8 -*-
"""What colours are actually IN the archer's main layer?

Needed so the recolour demo targets a colour that really exists.
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, grid_of, rect_blocks, decode_bc1_plane

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

name = "u_arc_archer_idlea_x1.sld"
s = read_sld(os.path.join(GP, name))
fr = s.frames[0]
m = fr.layers["main"]
rect, fmt, n, cmds = parse_rect_layer(m)
x1, y1, rw, rh, bw, bh = grid_of(rect)
plane, PW, PH = decode_bc1_plane(rect_blocks(m, n), bw, bh, cmds)
print("rect=%s grid=%dx%d fmt=0x%04x ncmd=%d" % (rect, bw, bh, fmt, n))
c = Counter()
for i in range(PW * PH):
    r, g, b, a = plane[i * 4:i * 4 + 4]
    if a:
        c[(r, g, b)] += 1
print("distinct opaque colours:", len(c))
for (r, g, b), k in c.most_common(20):
    print("   rgb(%3d,%3d,%3d)  x%-5d  %s" % (r, g, b, k,
          "BLUE-ISH" if b - r > 30 and b - g > 20 else
          "RED-ISH" if r - g > 30 and r - b > 20 else ""))

# also: what does the playercolor mask cover?
import struct as st
if "playercolor" in fr.layers:
    pc = fr.layers["playercolor"]
    pfmt, pn = st.unpack_from("<2H", pc.data, 0)
    print("\nplayercolor fmt=0x%04x ncmd=%d size=%d" % (pfmt, pn, pc.size))
