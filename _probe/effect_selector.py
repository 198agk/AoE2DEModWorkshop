"""Which selector identifies exactly one command?

Candidates, from loosest to tightest:
  S1 (C)                      -- measured: ambiguous in 450/537 techs
  S2 (op-family, A, B, C)     -- measured: ambiguous in many
  S3 (op-family, A, B, C, packed class)   -- 510/537 unique
  S4 (full Type, A, B, C, packed class)   -- tighter: Type also encodes the
                                             scope (base/team/enemy/neutral/
                                             gaia/own-master/selected)

The intent should use the TIGHTEST selector that is still natural to state,
and refuse with a candidate list when even that repeats.  This measures how
often each refuses, so the refusal rate is a known number rather than a
surprise at runtime.

Read-only, BASE only.
"""
import os, sys, io, contextlib, collections, struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"

SET_T = (0, 10, 20, 30, 40, 200, 203)
ADD_T = (4, 14, 24, 34, 44, 201, 204)
MUL_T = (5, 15, 25, 35, 45, 202, 205)


def op_of(t):
    return "set" if t in SET_T else "add" if t in ADD_T else "mul" if t in MUL_T else None


def cls_of(c):
    if c["c"] in (8, 9):
        return struct.unpack("<H", struct.pack("<h", int(c["d"])))[0] >> 8
    return None


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

SELECTORS = {
    "S2 (op,A,B,C)": lambda c: (op_of(c["type"]), c["a"], c["b"], c["c"]),
    "S3 (op,A,B,C,cls)": lambda c: (op_of(c["type"]), c["a"], c["b"], c["c"], cls_of(c)),
    "S4 (type,A,B,C,cls)": lambda c: (c["type"], c["a"], c["b"], c["c"], cls_of(c)),
}

for name, sel in SELECTORS.items():
    hist = collections.Counter()
    ambiguous = 0
    total = 0
    for i, t in enumerate(techs):
        ei = t.get("effect_id", -1)
        if ei < 0:
            continue
        cms = [c for c in effs[ei]["commands"] if op_of(c["type"])]
        if not cms:
            continue
        total += 1
        seen = collections.Counter(sel(c) for c in cms)
        worst = max(seen.values())
        hist[worst] += 1
        if worst > 1:
            ambiguous += 1
    print("%-22s techs %d | unique %d (%.1f%%) | ambiguous %d (%.1f%%) | hist %s"
          % (name, total, total - ambiguous, 100.0 * (total - ambiguous) / total,
             ambiguous, 100.0 * ambiguous / total, dict(sorted(hist.items()))))

print("\n=== S4 ambiguous cases: how many are the same value (harmless)? ===")
same = diff = 0
for i, t in enumerate(techs):
    ei = t.get("effect_id", -1)
    if ei < 0:
        continue
    cms = [c for c in effs[ei]["commands"] if op_of(c["type"])]
    if not cms:
        continue
    per = collections.defaultdict(list)
    for c in cms:
        per[SELECTORS["S4 (type,A,B,C,cls)"](c)].append(c)
    for k, lst in per.items():
        if len(lst) > 1:
            if len({x["d"] for x in lst}) == 1:
                same += 1
            else:
                diff += 1
print("  repeated S4 with identical D: %d" % same)
print("  repeated S4 with differing D: %d  <-- must refuse" % diff)

print("\n=== how many techs would be UNREACHABLE because they end up ambiguous? ===")
blocked = 0
for i, t in enumerate(techs):
    ei = t.get("effect_id", -1)
    if ei < 0:
        continue
    cms = [c for c in effs[ei]["commands"] if op_of(c["type"])]
    if not cms:
        continue
    per = collections.defaultdict(list)
    for c in cms:
        per[SELECTORS["S4 (type,A,B,C,cls)"](c)].append(c)
    if any(len(l) > 1 and len({x["d"] for x in l}) > 1 for l in per.values()):
        blocked += 1
print("  techs with at least one truly ambiguous selector: %d" % blocked)
