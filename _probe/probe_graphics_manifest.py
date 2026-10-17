# -*- coding: utf-8 -*-
"""`resources/_common/drs/graphics_x1.txt` / `_x2.txt` sit next to the graphics
folder.  Are they a shipped manifest of the .sld files?"""
import os

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DRS = os.path.join(GAME, "resources", "_common", "drs")
G = os.path.join(DRS, "graphics")

for name in ("graphics_x1.txt", "graphics_x2.txt"):
    p = os.path.join(DRS, name)
    raw = open(p, "rb").read()
    print("=" * 70)
    print("%s  %d B" % (name, len(raw)))
    print("=" * 70)
    print(raw.decode("latin-1"))

sld = set(f for f in os.listdir(G) if f.lower().endswith(".sld"))
other = sorted(f for f in os.listdir(G) if not f.lower().endswith(".sld"))
print("graphics/: %d .sld, %d other" % (len(sld), len(other)))
print("other files:")
for f in other[:80]:
    print("    %-50s %d B" % (f, os.path.getsize(os.path.join(G, f))))
