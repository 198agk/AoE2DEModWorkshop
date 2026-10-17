"""Is there a villager task-variant table baked into the exe as NUMBERS?

The in-game test proved the engine swaps villager id 83 for a task variant
record (idle -> 村展 2500, build order -> 建筑者 25).  Strings were a dead end
(`VMBLD` etc. are absent from the exe), so the remaining possibility is a
numeric table.

This scans the exe for contiguous int16 / int32 little-endian runs drawn from
the known villager id set, and separately for the gender PAIRS, which is the
shape a swap table would take.
"""
import os
import struct

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"

# villager-family unit ids (from dat), including the two class-61 repairers
VILL = {56, 57, 83, 118, 120, 122, 123, 124, 156, 212, 214, 216, 218, 220, 222,
        259, 293, 354, 579, 581, 590, 592, 1810, 1891, 1892, 2333, 2334,
        2714, 2715}

# gender pairs (male, female)
PAIRS = [(83, 293), (118, 212), (156, 222), (120, 354), (122, 216),
         (123, 218), (124, 220), (579, 581), (259, 214), (592, 590),
         (56, 57), (1892, 1891), (2333, 2334), (2714, 2715)]

data = open(EXE, "rb").read()
print("exe bytes:", len(data))

for width, fmt in ((2, "<h"), (4, "<i")):
    print()
    print("=== %d-byte little-endian runs of villager ids ===" % width)
    hits = []
    best = 0
    for off in range(0, len(data) - width * 3, 2):
        run = 0
        while off + (run + 1) * width <= len(data):
            v = struct.unpack_from(fmt, data, off + run * width)[0]
            if v in VILL:
                run += 1
            else:
                break
        if run >= 3:
            vals = [struct.unpack_from(fmt, data, off + i * width)[0] for i in range(run)]
            hits.append((off, vals))
            best = max(best, run)
    print("runs of >=3: %d   longest run: %d" % (len(hits), best))
    for off, vals in sorted(hits, key=lambda h: -len(h[1]))[:12]:
        print("   0x%08X  len %-2d  %s" % (off, len(vals), vals))

print()
print("=== gender pairs present as adjacent i16 ===")
found = []
for m, f in PAIRS:
    b = struct.pack("<hh", m, f)
    n = data.count(b)
    if n:
        found.append((m, f, n, [hex(i) for i in _find_all(data, b)[:4]] if False else n))
    else:
        found.append((m, f, 0, None))
for m, f, n, _ in found:
    print("   (%4d,%4d)  occurrences: %d" % (m, f, n))

print()
print("=== the whole family as one contiguous block? ===")
for order in (sorted(VILL),):
    blob = b"".join(struct.pack("<h", v) for v in order)
    print("   sorted i16 block present:", data.count(blob))
