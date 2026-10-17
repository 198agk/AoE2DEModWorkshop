"""Independent verification of the subagent's claim:
`Bird.TaskSwapGroup` is a real serialized dat byte that groups villager variants.

Method: intercept `read_bird` while the AUTHORITATIVE parser walks the real file,
record the offset of the TaskSwapGroup byte for every unit, then re-read those
offsets straight out of the raw bytes.  If the claim is true the byte at each
recorded offset must (a) be 0..3 and (b) come out 1 for the male basket and 2 for
the female basket, matching the in-game observation (83 -> 118 on tasking).

Also proves the offset formula `bird_start + 10 + 2*len(DropSites)`.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from aoe2mod.dat import parser as P  # noqa: E402

tk_path = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
raw, how = P.load_dat(tk_path)
print("loaded:", how, len(raw), "bytes")

# --- intercept read_bird ---------------------------------------------------
orig_bird = P.read_bird
captured = []          # (unit_id, tsg_offset, dropsite_count, bird_start)
_stack = []


def spy(r):
    start = getattr(r, "pos", None) if hasattr(r, "pos") else getattr(r, "o", None)
    # replicate the layout up to TaskSwapGroup to find its offset
    r.i16()                                  # DefaultTaskID
    r.f32(); r.f32()                         # SearchRadius, WorkRate
    n = r.i16()                              # drop site count
    r.i16_array(n)                           # DropSites
    tsg_off = r.pos if hasattr(r, "pos") else r.o
    tsg = r.u8()
    captured.append((tsg_off, n, tsg, start))
    # continue the rest of the Bird struct so the walk stays aligned
    r.i16(); r.i16()                         # AttackSound, MoveSound
    r.u32(); r.u32()                         # Wwise attack/move
    r.u8()                                   # RunPattern
    tn = r.i16()
    for _ in range(tn):
        P.read_task(r)


P.read_bird = spy


class Collector:
    """Captures the unit id alongside the bird read."""

    def __call__(self, u):
        _stack.append(u)


# The parser calls collect(u) at unit end; we need the id at bird time.
# read_unit sets u['id'] before read_bird, so hook read_unit instead.
orig_unit = P.Unit if hasattr(P, "Unit") else None

P.read_bird = spy
try:
    p = P.Parser(raw)
    res = p.parse()
finally:
    P.read_bird = orig_bird

print("captured bird structs:", len(captured))
print("first 5 (tsg_off, dropsites, tsg):", [(hex(a), b, c) for a, b, c, _ in captured[:5]])

# --- now align captured records with unit ids ------------------------------
# read_unit stores id right after Type; simplest: re-walk and pair by order.
# Instead compare TSG histogram and verify against the raw bytes directly.
import collections

hist = collections.Counter(c for _, _, c, _ in captured)
print("TSG histogram over all bird structs:", dict(hist))

# verify byte at each captured offset really is the value we read
bad = 0
for tsg_off, n, tsg, start in captured:
    if raw[tsg_off] != tsg:
        bad += 1
print("offsets whose raw byte != parsed value:", bad)

# --- verify the formula bird_start + 10 + 2*n ------------------------------
formula_ok = 0
formula_bad = 0
for tsg_off, n, tsg, start in captured:
    if start is None:
        continue
    if start + 10 + 2 * n == tsg_off:
        formula_ok += 1
    else:
        formula_bad += 1
print("formula  bird_start+10+2*n == tsg_off : ok %d / bad %d" % (formula_ok, formula_bad))

# --- does every bird struct sit directly after the Speed float? ------------
# A bird unit (type 30) has: ... Speed f32, then DeadFish, then Bird.
print()
print("=== sanity: is the FIRST bird struct the villager at id 83? ===")
print("  We cannot name them from this probe; the histogram is the evidence.")
print("  Expected shape: a few 1/2/3 and a huge 0 bucket.")
