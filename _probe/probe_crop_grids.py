# -*- coding: utf-8 -*-
r"""Crop the build-grid regions from the user's four test screenshots, upscaled.

The answer to the two-game protocol is in WHICH icons the grids contain.
"""
import os
from PIL import Image

A = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_crops")
os.makedirs(OUT, exist_ok=True)

JOBS = [
    ("poles_dock", "5a",
     "5a77a828c64b351be52e2dc4d402e8b76798db6bf8f16a41e86ec13ab98ee9e6",
     (0.01, 0.50, 0.34, 0.92)),
    ("sic_upgrade", "2b",
     "2be84e564bfc25de5481338f98a153563641d463c1a8241015cfd0701ea86b01",
     (0.01, 0.42, 0.42, 0.95)),
    ("sic_build", "2d",
     "2d0a0f06566b5fc843025a23d401f421766e9251109b81dced58ef9ec4ec7589",
     (0.01, 0.42, 0.42, 0.95)),
    ("sic_tree_sw", "75",
     "75ed80858f263d9c81c3ad2755db6f584d5bd4dd385605f41e4ab29bc62ec021",
     (0.42, 0.50, 0.75, 1.00)),
]
for name, d, sha, frac in JOBS:
    p = os.path.join(A, d, sha)
    im = Image.open(p).convert("RGB")
    w, h = im.size
    box = (int(frac[0] * w), int(frac[1] * h), int(frac[2] * w), int(frac[3] * h))
    crop = im.crop(box)
    s = max(2, int(1500 / max(1, crop.size[0])))
    up = crop.resize((crop.size[0] * s, crop.size[1] * s), Image.LANCZOS)
    dst = os.path.join(OUT, "%s.png" % name)
    up.save(dst)
    print("%-12s src=%sx%s box=%s scale=%d -> %s (%s)"
          % (name, w, h, box, s, dst, up.size))
