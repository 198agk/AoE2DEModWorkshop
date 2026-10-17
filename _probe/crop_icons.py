"""Crop the mod manager's enable-icon column so the checkbox state is legible."""
import os
import sys

from PIL import Image

SRC = r"D:\Software\DeepSeek Harness\工作区2\_smoke\now01.png"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_smoke\now01_icons.png"

im = Image.open(SRC).convert("RGB")
print("source size:", im.size)

# Rows 1..8 of the installed-mod list.
box = (505, 615, 705, 1245)
crop = im.crop(box)
crop = crop.resize((crop.width * 3, crop.height * 3), Image.NEAREST)
crop.save(OUT)
print("saved", OUT, crop.size)
