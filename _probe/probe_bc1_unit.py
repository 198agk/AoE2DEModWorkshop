# -*- coding: utf-8 -*-
"""Unit-test the BC1 encoder against the decoder, one block at a time."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import bc1_palette, _idx_bits
from probe_sld_encode import encode_bc1_block

cases = {
    "solid red": [(230, 30, 30, 255)] * 16,
    "solid blue": [(30, 30, 230, 255)] * 16,
    "half/half": [(230, 30, 30, 255)] * 8 + [(30, 30, 230, 255)] * 8,
    "all transparent": [(0, 0, 0, 0)] * 16,
    "half transparent": [(230, 30, 30, 255)] * 8 + [(0, 0, 0, 0)] * 8,
    "gradient": [((i * 16) % 256, (i * 8) % 256, (i * 4) % 256, 255)
                 for i in range(16)],
}

worst = 0
for name, px in cases.items():
    blk = encode_bc1_block(px)
    pal = bc1_palette(blk)
    bits = _idx_bits(blk)
    err = 0
    for i in range(16):
        q = pal[bits[i]]
        s = px[i]
        if s[3] == 0:
            if q[3] != 0:
                err = max(err, 255)
            continue
        if q[3] == 0:
            err = max(err, 255)
            continue
        err = max(err, max(abs(q[c] - s[c]) for c in range(3)))
    worst = max(worst, err)
    print("%-18s endpoints=%04x/%04x  max channel error %d"
          % (name, blk[0] | blk[1] << 8, blk[2] | blk[3] << 8, err))
print("worst", worst)
