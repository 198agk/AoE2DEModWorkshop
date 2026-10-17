# -*- coding: utf-8 -*-
r"""Crop the building-panel regions out of the user's test screenshots.

The four screenshots answer the two-game protocol, but the answer is in the button
grids, which are small.  Crop and upscale them so the icons can actually be
identified.
"""
import os
import sys

from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_crops")
os.makedirs(OUT, exist_ok=True)
A = r"C:\Users\26913\.dsh\attachments\v1\objects"
SRC = {
    "poles_dock": os.path.join(A, "5a",
        "5a77a828c64b351be52e2dc4d402e8b76798db6bf8f16a41e86ec13ab98ee9e6"),
    "sic_tree": os.path.join(A, "75",
        "75ed80858f263d9c81c3ad2755db6f584d5bd4dd385605f41e4ab29bc62ec021"),
    "sic_upgrade": os.path.join(A, "2b",
        "2be84e564bfc25de5481338f98a153563641d463c1a8241015cfd0701ea86b01"),
    "sic_build": os.path.join(A, "2d",
        "2d0a0f06566b5fc843025a23d401f421766e9251109b81dced58ef9ec4ec7589"),
}
for k, p in SRC.items():
    if not os.path.exists(p):
        print("MISSING %s -> %s" % (k, p))
        sys.exit(1)
    im = Image.open(p)
    print("%-12s %s  %s" % (k, p[-12:], im.size))

# The build grid sits at the bottom-left of the in-game screenshots.
# Crop the left half of the bottom third, then upscale.
for k, box_frac in (("poles_dock", (0.00, 0.48, 0.42, 1.00)),
                    ("sic_upgrade", (0.00, 0.42, 0.40, 1.00)),
                    ("sic_build", (0.00, 0.42, 0.40, 1.00))):
    im = Image.open(SRC[k]).convert("RGB")
    w, h = im.size
    box = (int(box_frac[0] * w), int(box_frac[1] * h),
           int(box_frac[2] * w), int(box_frac[3] * h))
    crop = im.crop(box)
    scale = max(2, int(1400 / max(1, crop.size[0])))
    crop = crop.resize((crop.size[0] * scale, crop.size[1] * scale),
                       Image.LANCZOS)
    dst = os.path.join(OUT, "%s.png" % k)
    crop.save(dst)
    print("wrote %-12s %s  (crop %s x%d)" % (k, dst, box, scale))
