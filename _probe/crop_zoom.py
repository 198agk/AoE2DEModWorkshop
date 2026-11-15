# -*- coding: utf-8 -*-
"""Crop and enlarge one region of a screenshot, so a 19px icon can be judged.

Usage:  crop_zoom.py <src.png> <x> <y> <w> <h> <scale> <out.png>
Coordinates are in the source image's own pixels.
"""
import sys

from PIL import Image

src, x, y, w, h, scale, out = sys.argv[1:8]
im = Image.open(src).crop((int(x), int(y), int(x) + int(w), int(y) + int(h)))
im = im.resize((im.width * int(scale), im.height * int(scale)),
               Image.NEAREST)
im.save(out)
print("wrote", out, im.size)
