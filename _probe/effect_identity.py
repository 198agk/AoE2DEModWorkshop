"""Does the FULL command identity make a semantic selector honest?

An attribute-only selector is ambiguous in 450 of 537 techs (measured).  The
question now: if the selector is the whole identity -- operation (set/add/mul),
target (unit A or class B), attribute C, and the packed class for C in {8,9} --
does it name exactly one command?

If yes, a semantic intent is honest and we never expose an index to the user.
If exact duplicates remain, those are genuinely interchangeable only when the
value is identical too, so report them rather than guess.

Read-only, BASE only.
"""
import os, sys, io, contextlib, collections, struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"


def load(path):
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return data, p


data, p = load(BASE)
civs, civs_start, gv, tail = L.locate(data, parser=p)
techs = L.locate_techs(data, tail, gv)
effs, eff_start = L.locate_effects(data, parser=p)

SET_T, ADD_T, MUL_T = (0, 10, 20, 30, 40, 200, 203), (4, 14, 24, 34, 44, 201, 204), (5, 15, 25, 35, 45, 202, 205)


def op_of(t):
    if t in SET_T:
        return "set"
    if t in ADD_T:
        return "add"
    if t in MUL_T:
        return "mul"
    return None


def packed(c):
    """(class, value) for the attributes whose D carries a class in the high byte."""
    if c["c"] in (8, 9):
        raw = struct.unpack("<H", struct.pack("<h", int(c["d"])))[0]
        return raw >> 8, raw & 0xFF
    return None, None


def identity(c):
    cls, _val = packed(c)
    return (op_of(c["type"]), c["a"], c["b"], c["c"], cls)


print("=== 1. full-identity uniqueness inside one effect ===")
hist = collections.Counter()
dupes = []
tot = 0
for i, t in enumerate(techs):
    ei = t.get("effect_id", -1)
    if ei < 0:
        continue
    cms = [c for c in effs[ei]["commands"] if op_of(c["type"])]
    if not cms:
        continue
    tot += 1
    seen = collections.Counter(identity(c) for c in cms)
    worst = max(seen.values())
    hist[worst] += 1
    if worst > 1:
        dupes.append((i, t, seen))
print("  techs with >=1 scalar command: %d" % tot)
print("  max identical-identity count : %s" % dict(sorted(hist.items())))

print("\n=== 2. when the identity repeats, is the VALUE the same? ===")
same_val = 0
diff_val = 0
for i, t, seen in dupes:
    ei = t["effect_id"]
    cms = [c for c in effs[ei]["commands"] if op_of(c["type"])]
    per = collections.defaultdict(list)
    for c in cms:
        per[identity(c)].append(c)
    for k, lst in per.items():
        if len(lst) > 1:
            if len({x["d"] for x in lst}) == 1:
                same_val += 1
            else:
                diff_val += 1
print("  repeated identities with identical D: %d" % same_val)
print("  repeated identities with differing D: %d  <-- genuinely ambiguous" % diff_val)

print("\n=== 3. the differing-value cases, named ===")
shown = 0
for i, t, seen in dupes:
    ei = t["effect_id"]
    cms = [c for c in effs[ei]["commands"] if op_of(c["type"])]
    per = collections.defaultdict(list)
    for c in cms:
        per[identity(c)].append(c)
    for k, lst in per.items():
        if len(lst) > 1 and len({x["d"] for x in lst}) > 1:
            shown += 1
            if shown <= 6:
                print("  tech[%d] %r civ=%s effect[%d] identity=%s values=%s"
                      % (i, t["name"], t["civ"], ei, k, sorted({x["d"] for x in lst})))
print("  total: %d" % shown)

print("\n=== 4. for comparison: how unique is (op, target, attribute) without the class? ===")
hist2 = collections.Counter()
for i, t in enumerate(techs):
    ei = t.get("effect_id", -1)
    if ei < 0:
        continue
    cms = [c for c in effs[ei]["commands"] if op_of(c["type"])]
    if not cms:
        continue
    seen = collections.Counter((op_of(c["type"]), c["a"], c["b"], c["c"]) for c in cms)
    hist2[max(seen.values())] += 1
print("  max count per (op, A, B, C): %s" % dict(sorted(hist2.items())))
