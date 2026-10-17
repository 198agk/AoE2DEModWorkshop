"""Before adding `tech.cost`, check whether "the gold cost of this tech" is
ever ambiguous -- i.e. does any tech carry two PAID slots of the same type?

If it can, the compiler must report the ambiguity rather than silently edit the
first one; if it cannot, selection by resource type is safe and total.

Self-contained on purpose: importing probe_tech_cost2 would run its main().
"""
import contextlib
import io
import struct
import sys
from collections import Counter

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
from aoe2mod.dat import parser as P          # noqa: E402


def walk_one(b, o, gv):
    """(costs, internal_name, next_offset) mirroring Research.cpp exactly."""
    o += 12                                   # RequiredTechs i16 x6
    costs = []
    for _ in range(3):
        costs.append(struct.unpack_from("<hhB", b, o))
        o += 5
    o += 2                                    # RequiredTechCount
    o += 2                                    # Civ
    o += 2                                    # FullTechMode
    if gv < P.GV_C31:
        o += 2                                # ResearchLocation
    if gv >= P.GV_MATT:
        o += 8 if P.GV_C18 <= gv <= P.GV_LatestDE2 else 4
    if gv < P.GV_C31:
        o += 2                                # ResearchTime
    o += 6                                    # EffectID, Type, IconID
    if gv < P.GV_C31:
        o += 1                                # ButtonID
    o += 8                                    # LanguageDLLHelp, TechTree
    if gv < P.GV_C31:
        o += 4                                # HotKey
    o += 4                                    # debug-string marker + length
    ln = struct.unpack_from("<H", b, o - 2)[0]
    o += ln
    name = b[o - ln:o].split(b"\x00")[0].decode("latin-1")
    if P.GV_C15 <= gv <= P.GV_LatestDE2:
        o += 1                                # Repeatable
    if P.GV_C31 <= gv <= P.GV_LatestDE2:
        cnt = struct.unpack_from("<h", b, o)[0]
        o += 2 + 9 * cnt
    return costs, name, o


def main():
    base = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
    data, how = P.load_dat(base)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    gv = p.r.gv
    stages = {s[0]: (s[1], s[2]) for s in p.stage_offsets}
    tail, tend = stages["9 Techs"]
    n = struct.unpack_from("<h", data, tail)[0]

    o = tail + 2
    dup_paid = []
    dup_any = []
    paid_types = Counter()
    odd = []
    zero_paid = 0
    for i in range(n):
        costs, name, o2 = walk_one(data, o, gv)
        o = o2
        paid = [(t, a) for (t, a, f) in costs if f != 0]
        cnt = Counter(t for (t, a) in paid)
        if any(c > 1 for c in cnt.values()):
            dup_paid.append((i, name, costs))
        cnt_any = Counter(t for (t, a, f) in costs if t != -1)
        if any(c > 1 for c in cnt_any.values()):
            dup_any.append((i, name, cnt_any, costs))
        for t, a in paid:
            paid_types[t] += 1
        for (t, a, f) in costs:
            if f == 0 and t >= 0 and a != 0:
                odd.append((i, name, t, a, f))
            if f != 0 and a == 0:
                zero_paid += 1

    print("techs:", n, "| walk ended", hex(o), "== stage end", hex(tend), o == tend)
    print("paid types histogram:", dict(paid_types))
    print()
    print("techs with TWO PAID slots of the same type:", len(dup_paid))
    for i, name, c in dup_paid[:10]:
        print("   id %d %r %s" % (i, name, c))
    print()
    print("techs with two slots of same type (incl. unpaid):", len(dup_any))
    for i, name, cnt, costs in dup_any[:10]:
        print("   id %d %r %s %s" % (i, name, dict(cnt), costs))
    print()
    print("slots with flag==0 but type>=0 and amount!=0 (needed-not-paid):", len(odd))
    for r in odd[:10]:
        print("   ", r)
    print("paid slots (flag!=0) whose amount is 0:", zero_paid)


main()
