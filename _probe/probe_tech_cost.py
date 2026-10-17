"""Probe the three ResearchResourceCost triples of every tech, using an
independent reader (NOT locate.Orec) so the numbers are a real cross-check.

Research.cpp:61  serializeSub<ResearchResourceCost>(ResourceCosts, 3)
ResourceUsage.h:56-61  Type(i16) Amount(i16) Flag(u8)  -- 5 bytes each, x3 = 15
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import contextlib
import io
import struct
import sys
from collections import Counter

sys.path.insert(0, _HERE_PATH(".."))
from aoe2mod.dat import parser as P          # noqa: E402

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"

def advance_rest(b, o, gv):
    """Skip everything after ResourceCosts up to the next tech, per Research.cpp.

    Returns the new offset.  Mirrors the authoritative read_tech exactly but
    with plain offsets, so it is an independent walk.
    """
    o += 12                                   # RequiredTechs i16 x6
    o += 15                                   # 3 x ResearchResourceCost
    o += 2                                    # RequiredTechCount
    o += 2                                    # Civ
    o += 2                                    # FullTechMode
    if gv < P.GV_C31:
        o += 2                                # ResearchLocation
    if gv >= P.GV_MATT:
        o += 8 if P.GV_C18 <= gv <= P.GV_LatestDE2 else 4
    if gv < P.GV_C31:
        o += 4                                # ResearchTime i16 + EffectID i16
    else:
        o += 4                                # EffectID i16 + Type i16
    o += 2                                    # (IconID) / (Type tail)
    # Recompute precisely instead of guessing: caller passes the offset of
    # EffectID; see walk() below for the explicit version.
    raise AssertionError("unused")

def walk_one(b, o, gv):
    """Return (costs, next_offset) mirroring Research.cpp field by field."""
    costs = []
    o += 12                                   # RequiredTechs
    for _ in range(3):
        t, a, f = struct.unpack_from("<hhB", b, o)
        costs.append((t, a, f))
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
    # serializeDebugString: u16 marker, u16 len, len bytes
    o += 4
    n = struct.unpack_from("<H", b, o - 2)[0]
    o += n
    if P.GV_C15 <= gv <= P.GV_LatestDE2:
        o += 1                                # Repeatable
    if P.GV_C31 <= gv <= P.GV_LatestDE2:
        cnt = struct.unpack_from("<h", b, o)[0]
        o += 2 + 9 * cnt                      # ResearchLocation array (9 B each)
    return costs, o

def main():
    data, how = P.load_dat(BASE)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    gv = p.r.gv
    # stage_offsets entries are 3-tuples (name, start, end) -- take the EXACT
    # '9 Techs' entry.  Matching on "Tech" also hits '10 Tail+TechTree', whose
    # start is the *end* of the tech section, and reading a count there yields
    # a small nonsense number that then drifts off the end of the file.
    stages = {s[0]: (s[1], s[2]) for s in p.stage_offsets}
    tail, techs_end = stages["9 Techs"]
    print("'9 Techs' start %s end %s | gv %d"
          % (hex(tail), hex(techs_end), gv))
    n = struct.unpack_from("<h", data, tail)[0]
    print("tech count:", n)

    o = tail + 2
    trio = Counter()
    flags = Counter()
    types = Counter()
    examples = {}
    bad = []
    for i in range(n):
        costs, o2 = walk_one(data, o, gv)
        if o2 <= o:
            bad.append(i)
        o = o2
        trio[tuple(c[0] for c in costs)] += 1
        for (t, a, f) in costs:
            flags[f] += 1
            types[t] += 1
        if i in (0, 1, 2, 4, 12, 22, 101, 102, 103, 104):
            examples[i] = costs

    print("\nwalk ended at", hex(o), "| raw len", hex(len(data)),
          "| remaining", len(data) - o)
    print("bad offsets:", bad[:10], "count", len(bad))
    print("\ndistinct (t0,t1,t2) triples:", len(trio))
    for k, v in trio.most_common(14):
        print("   ", k, v)
    print("\nAmount==0 count:", sum(1 for _ in ()) or "")
    print("Flag histogram:", dict(flags))
    print("Type histogram (top):", types.most_common(10))
    print("\nexamples (type, amount, flag):")
    for i, c in sorted(examples.items()):
        print("  tech %4d" % i, c)

main()
