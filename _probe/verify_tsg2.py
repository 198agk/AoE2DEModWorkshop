"""Confirm the TaskSwapGroup offset formula AND map real unit ids to groups.

The subagent's report says `bird_start + 10 + 2*len(DropSites)`.  My first check
showed 0/90,190 matches, so the constant is probably 12 (there is an int16 count
field BEFORE the DropSites array).  This settles it and then names the groups --
the only proof that matters is whether id 83 comes out 1 and id 293 comes out 2.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from aoe2mod.dat import parser as P  # noqa: E402

raw, how = P.load_dat(r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat")

# Capture (unit_id, tsg) by hooking BOTH read_unit (for the id) and read_bird.
records = []
cur = {"id": None}
orig_unit = P.read_unit
orig_bird = P.read_bird
off_by = {"10": 0, "12": 0}


def unit_spy(r, *a, **kw):
    # Do NOT capture the id after read_unit returns: read_bird runs in the MIDDLE
    # of read_unit, so the id is only known once ID has been read.  Grab it at
    # unit start by peeking, then let read_bird use it.
    start = r.pos
    cur["id"] = None
    u = orig_unit(r, *a, **kw)
    cur["id"] = u.get("id")
    return u


def bird_spy_fixed(r):
    """Same as bird_spy, but resolves the id by scanning back from the struct."""
    return bird_spy(r)


def bird_spy(r):
    start = r.pos
    r.i16()                       # DefaultTaskID
    r.f32(); r.f32()              # SearchRadius, WorkRate
    n = r.i16()                   # drop site COUNT (this is the 2 bytes)
    r.i16_array(n)                # DropSites
    tsg_off = r.pos
    tsg = r.u8()
    if start + 10 + 2 * n == tsg_off:
        off_by["10"] += 1
    if start + 12 + 2 * n == tsg_off:
        off_by["12"] += 1
    records.append((cur["id"], tsg, tsg_off))
    # finish the struct so the walk stays aligned
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

print("formula matches:  +10+2n -> %d   +12+2n -> %d" % (off_by["10"], off_by["12"]))
print("bird records:", len(records))

import collections
by_id = {}
for uid, tsg, off in records:
    by_id.setdefault(uid, tsg)

g = collections.defaultdict(list)
for uid, tsg in by_id.items():
    if tsg:
        g[tsg].append(uid)
for k in sorted(g):
    print()
    print("=== tsg=%d : %d distinct unit ids ===" % (k, len(g[k])))
    print("   ", sorted(g[k]))

print()
print("=== the decisive check (in-game ground truth) ===")
for probe in (83, 293, 118, 212, 56, 57, 4, 448, 206, 2714, 2715, 1810, 1891, 1892):
    print("   id %-6d tsg=%s" % (probe, by_id.get(probe)))
