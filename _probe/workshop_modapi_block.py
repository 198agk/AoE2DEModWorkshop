"""Dump the full mod-manager API region of the exe.

Key discovery at 0x0329D667:
  "MODS: Searching mods authenticated user. Search options: %s."  -> api/v1/Mods/FindAsUser/
  "MODS: Searching mods without authentication. Search options: %s." -> api/v1/Mods/Find/
  "MODS: List published mods." -> api/v1/Mods/My/

So the GAME uses api/v1/Mods/*, and Find/ is explicitly anonymous.

Read-only.
"""
import os
import re

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
raw = open(EXE, "rb").read()

# Big dump around the mods API block
for center, span, label in ((0x0329D667, 3000, "mods-API block"),
                            (0x0329C8D8, 1400, "mod-status / validation block")):
    a, b = max(0, center - span // 3), center + span
    print("=" * 110)
    print("%s  0x%08X..0x%08X" % (label, a, b))
    print("=" * 110)
    chunk = raw[a:b]
    for s in re.findall(rb"[\x20-\x7e]{3,}", chunk):
        print("   %s" % s.decode("ascii"))
    print()

print("=" * 110)
print("ALL api/v1 and api/v4 paths in exe")
print("=" * 110)
for m in sorted(set(re.findall(rb"api/v[0-9]/[A-Za-z0-9_/{}%\-.]{2,60}", raw))):
    print("   %s" % m.decode("ascii"))
