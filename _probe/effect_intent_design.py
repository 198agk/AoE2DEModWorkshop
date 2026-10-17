"""Can "tech X, attribute Y" identify exactly one command?

A `tech.effect` intent is only honest if the selector the user gives maps to one
command.  If it maps to several, editing silently changes more than the user
asked for -- the same failure class as the fan-in trap, but inside one tech.

Attribute-modifier commands are the ones whose whole payload is the scalar D
(types 0/4/5 and their Team/Enemy/Neutral/Gaia/OwnMaster/Selected variants), so
they are the natural first scope.  Everything else is reported, not edited.

Read-only, BASE only.
"""
import os, sys, io, contextlib, collections, struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P

BASE = r"D:\Games\Steam\aoE2DE"  # placeholder, replaced below
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

# The scalar-D family: a command whose meaning is "apply D to attribute C".
SET_T, ADD_T, MUL_T = (0, 10, 20, 30, 40, 200, 203), (4, 14, 24, 34, 44, 201, 204), (5, 15, 25, 35, 45, 202, 205)
FAMILY = set(SET_T) | set(ADD_T) | set(MUL_T)

print("=== 1. how much of the effect corpus is the scalar family? ===")
tot = fam = 0
kinds = collections.Counter()
for e in effs:
    for c in e["commands"]:
        tot += 1
        if c["type"] in FAMILY:
            fam += 1
            kinds[("set" if c["type"] in SET_T else "add" if c["type"] in ADD_T else "mul")] += 1
print("  commands %d | in family %d (%.1f%%)" % (tot, fam, 100.0 * fam / tot))
print("  by operation: %s" % dict(kinds))

print("\n=== 2. is (tech, attribute) unique inside one effect? ===")
# Attribute means C, but C in {8,9} carries a packed class in D, so the real
# selector there is (C, class).  Track both.
by_c = collections.Counter()
by_ccls = collections.Counter()
techs_with_family = 0
for i, t in enumerate(techs):
    ei = t.get("effect_id", -1)
    if ei < 0:
        continue
    cms = [c for c in effs[ei]["commands"] if c["type"] in FAMILY]
    if not cms:
        continue
    techs_with_family += 1
    seen = collections.Counter(c["c"] for c in cms)
    seen2 = collections.Counter(
        (c["c"], (struct.unpack("<H", struct.pack("<h", int(c["d"])))[0] >> 8) if c["c"] in (8, 9) else None)
        for c in cms)
    by_c[max(seen.values())] += 1
    by_ccls[max(seen2.values())] += 1
print("  techs whose effect has >=1 scalar command: %d" % techs_with_family)
print("  max occurrences of one attribute C      : %s" % dict(sorted(by_c.items())))
print("  max occurrences of one (C, packed class): %s" % dict(sorted(by_ccls.items())))

print("\n=== 3. the ambiguous cases, named ===")
amb = 0
for i, t in enumerate(techs):
    ei = t.get("effect_id", -1)
    if ei < 0:
        continue
    cms = [c for c in effs[ei]["commands"] if c["type"] in FAMILY]
    if not cms:
        continue
    seen = collections.Counter((c["c"], (struct.unpack("<H", struct.pack("<h", int(c["d"])))[0] >> 8) if c["c"] in (8, 9) else None) for c in cms)
    worst = max(seen.values())
    if worst > 1:
        amb += 1
        if amb <= 8:
            top = seen.most_common(2)
            print("  tech[%d] %r civ=%s effect[%d]: %s"
                  % (i, t["name"], t["civ"], ei, top))
print("  techs where one (attribute, class) repeats: %d of %d" % (amb, techs_with_family))

print("\n=== 4. how often do two commands share C but differ in target? ===")
diff_target = 0
for i, t in enumerate(techs):
    ei = t.get("effect_id", -1)
    if ei < 0:
        continue
    cms = [c for c in effs[ei]["commands"] if c["type"] in FAMILY]
    per = collections.defaultdict(list)
    for c in cms:
        per[c["c"]].append(c)
    for c, lst in per.items():
        if len(lst) > 1 and len({(x["type"], x["a"], x["b"]) for x in lst}) > 1:
            diff_target += 1
            break
print("  techs where a repeated attribute has differing (type, A, B): %d" % diff_target)

print("\n=== 5. packed attack/armour decode sanity (AGE Tester rule) ===")
shown = 0
for e in effs:
    for c in e["commands"]:
        if c["c"] in (8, 9) and shown < 5:
            raw = struct.unpack("<H", struct.pack("<h", int(c["d"])))[0]
            print("  C=%d D=%-8s -> class %d, value %d"
                  % (c["c"], c["d"], raw >> 8, raw & 0xFF))
            shown += 1
