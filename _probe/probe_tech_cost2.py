"""Cross-check the ResearchResourceCost Type -> resource mapping against techs
whose real in-game costs are independently known.

walk_one() in probe_tech_cost.py is an independent walk; this script pairs it
with the authoritative reader for NAMES so the two can be compared row by row.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import contextlib
import io
import json
import struct
import sys

sys.path.insert(0, _HERE_PATH(".."))
from aoe2mod.dat import parser as P          # noqa: E402

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
NAMES = _HERE_PATH("aoe2mod", "semantic", "data", "tech_names.json")

# Real AoE2 DE costs, from the game's own tech tree.  Only ones I am certain of.
KNOWN = {
    "Feudal Age":    [(0, 500)],
    "Castle Age":    [(0, 800), (3, 200)],
    "Imperial Age":  [(0, 1000), (3, 800)],
    "Crop rotation": [(0, 250), (1, 250)],
    "Heavy plow":    [(0, 125), (1, 125)],
    "Horse collar":  [(0, 75), (1, 75)],
    "Wheelbarrow":   [(0, 175), (1, 50)],
    "Hand cart":     [(0, 300), (1, 200)],
    "Loom":          [(0, 50)],
    "Coinage":       [(0, 100), (3, 100)],
    "Banking":       [(0, 200), (3, 100)],
    "Bloodlines":    [(0, 150)],
    "Town watch":    [(0, 75)],
    "Town patrol":   [(0, 300)],
    "Masonry":       [(0, 150)],
    "Architecture":  [(0, 300), (1, 200)],
}

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
    marker, ln = struct.unpack_from("<HH", b, o)
    o += 4
    name = b[o:o + ln].split(b"\x00")[0].decode("latin-1")
    o += ln
    if P.GV_C15 <= gv <= P.GV_LatestDE2:
        o += 1                                # Repeatable
    if P.GV_C31 <= gv <= P.GV_LatestDE2:
        cnt = struct.unpack_from("<h", b, o)[0]
        o += 2 + 9 * cnt
    return costs, name, o

def main():
    data, how = P.load_dat(BASE)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    gv = p.r.gv
    stages = {s[0]: (s[1], s[2]) for s in p.stage_offsets}
    tail, tend = stages["9 Techs"]
    n = struct.unpack_from("<h", data, tail)[0]

    names = json.load(open(NAMES, encoding="utf-8"))
    byid = {int(e["id"]): e for e in names} if isinstance(names, list) else None
    if byid is None:                       # tolerate {"entries": [...]}
        byid = {int(e["id"]): e for e in names.get("entries", [])}

    o = tail + 2
    rows = []
    for i in range(n):
        costs, name, o2 = walk_one(data, o, gv)
        o = o2
        e = byid.get(i, {})
        rows.append((i, name, e.get("zh"), costs))
    print("walk ended", hex(o), "== stage end", hex(tend), o == tend)

    # ---- the decisive test: do known costs land on known resource ids? ----
    print("\n=== KNOWN COSTS vs DAT (paid slots only, flag != 0) ===")
    agree = disagree = 0
    for i, name, zh, costs in rows:
        if name not in KNOWN:
            continue
        got = [(t, a) for (t, a, f) in costs if f != 0]
        want = KNOWN[name]
        ok = got == want
        agree += ok
        disagree += (not ok)
        print("  %-14s id %-4d want %-24s got %-24s %s"
              % (name, i, want, got, "OK" if ok else "MISMATCH  <--"))
    print("  agree %d / disagree %d" % (agree, disagree))

    # ---- what does each Type id accumulate? ----
    print("\n=== Type id -> total paid amount, and how many techs use it ===")
    from collections import Counter, defaultdict
    techs = Counter()
    total = defaultdict(int)
    for i, name, zh, costs in rows:
        for (t, a, f) in costs:
            if f != 0:
                techs[t] += 1
                total[t] += a
    for t in sorted(techs, key=lambda x: -techs[x]):
        print("  type %-6d used by %4d paid slots, total amount %d"
              % (t, techs[t], total[t]))

    print("\n=== oddities: non-zero Flag that is not 1, and unknown Type ids ===")
    for i, name, zh, costs in rows:
        for (t, a, f) in costs:
            if f not in (0, 1):
                print("  id %-5d %-22s type %-5d amount %-6d FLAG %d"
                      % (i, name, t, a, f))
    known_types = {0, 1, 2, 3}
    for i, name, zh, costs in rows:
        for (t, a, f) in costs:
            if t not in known_types and f == 0 and t != -1:
                print("  id %-5d %-22s unused slot holds type %d amount %d"
                      % (i, name, t, a))

    # ---- Loom specifically, since it is the one I doubted ----
    print("\n=== the techs I doubted ===")
    for i, name, zh, costs in rows:
        if name in ("Loom", "Coinage", "Banking"):
            print("  id %-5d %-10s zh %-8s %s" % (i, name, zh, costs))

main()
