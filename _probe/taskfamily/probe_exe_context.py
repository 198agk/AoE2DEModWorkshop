# -*- coding: utf-8 -*-
"""Inspect the exact context of every exe numeric hit from probe_exe_tables.py,
so each can be believed or dismissed as coincidence."""
import struct, sys

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
b = open(EXE, "rb").read()

HITS = [
    ("u16 [118,83]", 0x31D7CF8), ("u16 [118,83]", 0x31D8E00),
    ("u16 [118,83]", 0x31DA6A0), ("u16 [118,83]", 0x31DBFE0),
    ("u16 [118,83]", 0x33BFA30), ("u16 [118,83]", 0x33BFA6C),
    ("u32 [118,212]", 0x3232E50),
    ("u32 [118,212]", 0x32B1DD0), ("u32 [83,293]", 0x32B1DE0),
    ("u16 [56,57]", 0x326E298), ("u16 [56,57]", 0x32705B2),
    ("u16 [56,57]", 0x327312A), ("u16 [56,57]", 0x33CC7B8),
    ("u16 [56,57]", 0x3402BE0), ("u16 [56,57]", 0x3463AEA),
    ("u16 [57,56]", 0x326E648), ("u16 [57,56]", 0x326E648),
]

print("=== context around each numeric hit ===")
for label, off in HITS:
    lo = max(0, off - 32)
    hi = min(len(b), off + 40)
    print("\n%s @0x%X" % (label, off))
    print("  bytes : %s" % b[lo:hi].hex(" "))
    # try u16 view and see whether the neighborhood looks like a table of ids
    vals16 = [struct.unpack_from("<H", b, lo + 2 * k)[0] for k in range((hi - lo) // 2)]
    vals32 = [struct.unpack_from("<I", b, lo + 4 * k)[0] for k in range((hi - lo) // 4)]
    print("  u16   : %s" % vals16)
    print("  u32   : %s" % vals32)
    # printable ASCII run?
    asc = "".join(chr(c) if 32 <= c < 127 else "." for c in b[lo:hi])
    print("  ascii : %s" % asc)

# --- does any hit sit inside a plausible id table?  Walk forward from the hit
# and ask how many consecutive u16s are < 3000 (a unit-id-ish range).
print("\n=== forward u16 run length (values < 3000) from each hit ===")
for label, off in HITS:
    run = 0
    while off + 2 * run + 2 <= len(b):
        v = struct.unpack_from("<H", b, off + 2 * run)[0]
        if v < 3000:
            run += 1
        else:
            break
        if run > 200:
            break
    seq = [struct.unpack_from("<H", b, off + 2 * k)[0] for k in range(min(run, 24))]
    print("  %-14s @0x%X run=%-4d first24=%s" % (label, off, run, seq))
print("\nDONE")
