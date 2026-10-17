"""Map the exact extents of the exe's villager task-variant tables.

Two 4-byte i32 arrays were found containing the whole villager family with the
male/female pairs ADJACENT:
    0x032B1DD0  [118,212, 259,214, 83,293, 122,216, 123,218, 124,220, ...]
    0x03232E30  [259,214, 122,216, 56,57, 123,218, 118,212, ...]
Adjacency is the shape a swap table takes, and adjacency is what a heuristic
would have to GUESS.  This probe walks outwards from each seed to find the real
table bounds, then dumps what surrounds them.
"""
import struct

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
VILL = {56, 57, 83, 118, 120, 122, 123, 124, 156, 212, 214, 216, 218, 220, 222,
        259, 293, 354, 579, 581, 590, 592, 1810, 1891, 1892, 2333, 2334,
        2714, 2715}

data = open(EXE, "rb").read()


def i32(off):
    return struct.unpack_from("<i", data, off)[0]


def walk(seed):
    """Expand a run of 'plausible' i32 as far as it goes."""
    lo = seed
    while lo - 4 >= 0 and (i32(lo - 4) in VILL or 0 <= i32(lo - 4) <= 3000):
        lo -= 4
    hi = seed
    while hi + 4 < len(data) and (i32(hi + 4) in VILL or 0 <= i32(hi + 4) <= 3000):
        hi += 4
    return lo, hi


for seed in (0x032B1DD0, 0x03232E30):
    lo, hi = walk(seed)
    vals = [i32(o) for o in range(lo, hi + 4, 4)]
    print("=== seed 0x%08X ===" % seed)
    print("   extent 0x%08X .. 0x%08X  (%d i32)" % (lo, hi, len(vals)))
    # every OTHER value should be a villager id if it is a pair table
    odd = [v for i, v in enumerate(vals) if i % 2 == 0 and v not in VILL]
    even = [v for i, v in enumerate(vals) if i % 2 == 1 and v not in VILL]
    print("   malformed at even idx:", odd)
    print("   malformed at odd  idx:", even)
    pairs = [(vals[i], vals[i + 1]) for i in range(0, len(vals) - 1, 2)]
    print("   as PAIRS:", pairs)
    print("   all pairs are (male,female) villager variants:",
          all(a in VILL and b in VILL for a, b in pairs))
    print()
    print("   32 bytes BEFORE:")
    print("     ", data[lo - 32:lo].hex(" ", 1))
    print("   48 bytes AFTER:")
    print("     ", data[hi + 4:hi + 52].hex(" ", 1))
    print()

# how many distinct villager ids appear in the union of both tables?
print("=== coverage ===")
seen = set()
for seed in (0x032B1DD0, 0x03232E30):
    lo, hi = walk(seed)
    for o in range(lo, hi + 4, 4):
        v = i32(o)
        if v in VILL:
            seen.add(v)
print("   villager ids in tables:", sorted(seen))
print("   MISSING from tables   :", sorted(VILL - seen))
