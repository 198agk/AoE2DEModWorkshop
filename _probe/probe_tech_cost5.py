# -*- coding: utf-8 -*-
"""What ARE the 133 zero-placeholder picks?  Decides whether tech.cost writes there.

Rule under test: among slots whose Type == want, take the first with Amount != 0.
When every Type==want slot has Amount == 0 we have a choice -- write there (making
a cost appear out of nothing, or a NEGATIVE cost if the user asked for "cheaper"),
or refuse the way a missing cost is refused.  Refusing is only defensible if those
slots are not real costs, so look at exactly which techs they are.
"""
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "datparse"))
import parse_dat as P  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
NAMES = os.path.join(HERE, "semantic", "tech_names.json")


def read_costs(b, o, gv):
    """Walk one tech, returning (costs, end).  Costs are (type, amount, flag)."""
    o += 12                                    # RequiredTechs: 6 x i16
    costs = []
    for _ in range(3):
        ty, am, fl = struct.unpack_from("<hhB", b, o)
        costs.append((ty, am, fl))
        o += 5
    o += 2                                     # RequiredTechCount
    o += 2                                     # Civilization
    o += 2                                     # FullTechMode
    if gv < P.GV_C31:
        o += 2                                 # ResearchLocation
    if gv >= P.GV_MATT:
        o += 8 if P.GV_C18 <= gv <= P.GV_LatestDE2 else 4
    if gv < P.GV_C31:
        o += 2                                 # ResearchTime (scalar shape)
    o += 6                                     # EffectID, Type, IconID
    if gv < P.GV_C31:
        o += 1                                 # ButtonID
    o += 8                                     # LanguageDLLHelp, LanguageDLLTechTree
    if gv < P.GV_C31:
        o += 4                                 # HotKey
    # debug_string = u16 marker, u16 length, then the bytes.  The LENGTH is the
    # second u16 -- reading it at the marker is how this walker first drifted
    # 265,530 bytes past the end.
    n = struct.unpack_from("<H", b, o + 2)[0]
    o += 4 + n
    if P.GV_C15 <= gv <= P.GV_LatestDE2:
        o += 1                                 # Repeatable
    if P.GV_C31 <= gv <= P.GV_LatestDE2:
        nl = struct.unpack_from("<h", b, o)[0]
        o += 2 + nl * 9
    return costs, o


def main():
    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    p.parse()
    gv = P.gv_from_version_string(p.stats["file_version"])
    # The tech section start is exactly the parser's '9 Techs' stage start.
    start = end = None
    for name, s, e in p.stage_offsets:
        if name == "9 Techs":
            start, end = s, e
    assert start is not None, "no '9 Techs' stage"
    count = struct.unpack_from("<h", data, start)[0]

    names = json.load(open(NAMES, encoding="utf-8"))
    by_id = {}
    seq = names if isinstance(names, list) else names.get("techs", names)
    if isinstance(seq, list):
        for e in seq:
            by_id[e.get("id")] = e.get("zh") or e.get("en") or e.get("internal")
    elif isinstance(seq, dict):
        for k, v in seq.items():
            by_id[int(k)] = v.get("zh") or v.get("en") or v.get("internal") if isinstance(v, dict) else v

    o = start + 2
    zero_picks = collections.Counter()
    zero_examples = []
    nonzero_short = 0          # Type matches, has a nonzero slot -> writable
    absent = 0
    per_res = collections.Counter()
    for idx in range(count):
        costs, o = read_costs(data, o, gv)
        for want in (0, 1, 2, 3):
            matching = [c for c in costs if c[0] == want]
            if not matching:
                absent += 1
                continue
            nz = [c for c in matching if c[1] != 0]
            if nz:
                nonzero_short += 1
            else:
                zero_picks[(names and (by_id.get(idx) or "?")) or "?"] += 1
                per_res[want] += 1
                if len(zero_examples) < 12:
                    zero_examples.append(
                        (idx, by_id.get(idx), costs, want,
                         [c for c in matching]))
    assert o == end, "walk ended at %d, stage end %d" % (o, end)
    print("count %d  walk ended exactly at stage end  ok" % count)
    print("absent(no slot of that type) :", absent)
    print("writable (a nonzero slot)    :", nonzero_short)
    print("zero-placeholder picks       :", sum(zero_picks.values()))
    print("  by resource:", dict(per_res))
    print("  distinct techs involved:", len(zero_picks))
    print("  top techs:", zero_picks.most_common(8))
    print("examples (id, name, all 3 slots, want, matching slots):")
    for e in zero_examples:
        print("   ", e)


if __name__ == "__main__":
    main()
