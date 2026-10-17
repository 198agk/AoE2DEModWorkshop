"""Name the TaskSwapGroup members by reading the unit ID straight out of the
raw bytes at the record start.

`read_bird` executes INSIDE `read_unit` (parser.py:820), so the id is not yet
available from the return value when the Bird struct is walked -- that is why my
first attempt attributed every TSG byte to the PREVIOUS unit.  The fix is to
record the unit's start offset in `read_unit` and read `ID` (i16 at start+1)
directly, since the layout is `Type u8 @+0, ID i16 @+1`.
"""
import collections
import os
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from aoe2mod.dat import parser as P  # noqa: E402

raw, how = P.load_dat(r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat")

orig_unit = P.read_unit
orig_bird = P.read_bird
cur_start = {"off": None}
found = []              # (unit_id, tsg, tsg_off, dropsite_count)
formula = collections.Counter()


def unit_spy(r, *a, **kw):
    cur_start["off"] = r.pos
    return orig_unit(r, *a, **kw)


def bird_spy(r):
    start = r.pos
    r.i16()                       # DefaultTaskID
    r.f32(); r.f32()              # SearchRadius, WorkRate
    n = r.i16()                   # drop-site COUNT (the 2 bytes my first formula missed)
    r.i16_array(n)                # DropSites
    tsg_off = r.pos
    tsg = r.u8()
    for c in (10, 12):
        if start + c + 2 * n == tsg_off:
            formula[c] += 1
    ustart = cur_start["off"]
    uid = struct.unpack_from("<h", raw, ustart + 1)[0] if ustart is not None else None
    found.append((uid, tsg, tsg_off, n))
    r.i16(); r.i16()
    r.u32(); r.u32()
    r.u8()
    tn = r.i16()
    for _ in range(tn):
        P.read_task(r)


P.read_unit = unit_spy
P.read_bird = bird_spy
try:
    P.Parser(raw).parse()
finally:
    P.read_unit = orig_unit
    P.read_bird = orig_bird

print("bird structs captured:", len(found))
print("offset formula  +10+2n -> %d   +12+2n -> %d" % (formula[10], formula[12]))

# TSG is per physical record; the same unit id repeats across 63 civs.
per_id = collections.defaultdict(set)
for uid, tsg, off, n in found:
    if uid is not None:
        per_id[uid].add(tsg)

inconsistent = {u: s for u, s in per_id.items() if len(s) > 1}
print("ids whose TSG differs between civs:", len(inconsistent))
if inconsistent:
    for u, s in list(inconsistent.items())[:10]:
        print("   id %-6d values %s" % (u, sorted(s)))

groups = collections.defaultdict(list)
for uid, s in per_id.items():
    tsg = next(iter(s))
    if tsg:
        groups[tsg].append(uid)

for k in sorted(groups):
    print()
    print("=== tsg=%d : %d distinct unit ids ===" % (k, len(groups[k])))
    print("   ", sorted(groups[k]))

print()
print("=== the decisive check against in-game ground truth ===")
print("   (user saw villager 83 -> 建筑者 after a build order; 118 is the builder)")
for probe in (83, 293, 118, 212, 56, 57, 4, 448, 206, 2714, 2715, 1810, 1891, 1892, 2333, 2334):
    vals = per_id.get(probe)
    print("   id %-6d tsg=%s" % (probe, sorted(vals) if vals else "no bird struct"))
