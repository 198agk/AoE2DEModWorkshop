"""Settle the selection rule for `tech.cost` before writing any compiler code.

Two questions:
  Q1  Are the 112 techs whose 3 slots all share one Type real "costs"?
      (They are all (0,0,0) placeholder slots on 'New Research' records, or
      type -1 sentinels with a stray amount -- i.e. zeroed memory, not a cost.)
  Q2  Does `unit.cost`'s rule (edit EVERY slot whose type matches) ever fire
      twice on a unit, and would it be wrong if it did?

Rule under test for tech: among slots whose Type == wanted, take the first with
Amount != 0; if all are 0, take the first.  Verify it against known costs.
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

def walk_tech(b, o, gv):
    o += 12
    costs = []
    for _ in range(3):
        costs.append(struct.unpack_from("<hhB", b, o))
        o += 5
    o += 6                                    # count, civ, fulltech
    if gv < P.GV_C31:
        o += 2
    if gv >= P.GV_MATT:
        o += 8 if P.GV_C18 <= gv <= P.GV_LatestDE2 else 4
    if gv < P.GV_C31:
        o += 2
    o += 6                                    # effect, type, icon
    if gv < P.GV_C31:
        o += 1
    o += 8
    if gv < P.GV_C31:
        o += 4
    o += 4
    ln = struct.unpack_from("<H", b, o - 2)[0]
    name = b[o:o + ln].split(b"\x00")[0].decode("latin-1")
    o += ln
    if P.GV_C15 <= gv <= P.GV_LatestDE2:
        o += 1
    if P.GV_C31 <= gv <= P.GV_LatestDE2:
        cnt = struct.unpack_from("<h", b, o)[0]
        o += 2 + 9 * cnt
    return costs, name, o

KNOWN = {
    12:  [(0, 250), (1, 250)],
    13:  [(0, 125), (1, 125)],
    14:  [(0, 75), (1, 75)],
    22:  [(3, 50)],
    103: [(0, 1000), (3, 800)],
    102: [(0, 800), (3, 200)],
    50:  [(1, 175), (0, 150)],
    51:  [(1, 200), (0, 300)],
}

def main():
    base = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
    data, _ = P.load_dat(base)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    gv = p.r.gv
    st = {s[0]: (s[1], s[2]) for s in p.stage_offsets}
    tail, tend = st["9 Techs"]
    n = struct.unpack_from("<h", data, tail)[0]

    rows = []
    o = tail + 2
    for i in range(n):
        c, name, o2 = walk_tech(data, o, gv)
        o = o2
        rows.append((i, name, c))
    print("techs", n, "| walk end", hex(o), o == tend)

    def pick(costs, want):
        """The rule under test.  Returns (index, slot) or None."""
        hits = [k for k, (t, a, f) in enumerate(costs) if t == want]
        if not hits:
            return None
        for k in hits:
            if costs[k][1] != 0:
                return k, costs[k]
        return hits[0], costs[hits[0]]

    # ---- Q1: what are the duplicate-type techs really? ----
    print("\n=== Q1: duplicate-Type techs, by whether ANY slot is nonzero ===")
    allzero = 0
    stray = []
    for i, name, c in rows:
        cnt = Counter(t for (t, a, f) in c)
        dups = [t for t, k in cnt.items() if k > 1]
        if not dups:
            continue
        if all(a == 0 for (t, a, f) in c):
            allzero += 1
        else:
            stray.append((i, name, c))
    print("  duplicate-Type techs whose EVERY amount is 0:", allzero)
    print("  duplicate-Type techs with any nonzero amount:", len(stray))
    for i, name, c in stray:
        print("     id %-5d %-28r %s" % (i, name, c))

    # ---- verify the rule against known real costs ----
    print("\n=== the rule vs known real costs ===")
    ok = bad = 0
    for i, want in KNOWN.items():
        name, c = rows[i][1], rows[i][2]
        got = []
        for (t, a) in want:
            r = pick(c, t)
            got.append((t, r[1][1] if r else None))
        good = got == want
        ok += good
        bad += (not good)
        print("  id %-4d %-14s want %-24s got %-24s %s"
              % (i, name, want, got, "OK" if good else "MISMATCH"))
    print("  ok %d / mismatch %d" % (ok, bad))

    # ---- how often is the picked slot a zero-amount placeholder? ----
    print("\n=== how the rule lands across all techs ===")
    stat = Counter()
    for i, name, c in rows:
        for want in (0, 1, 2, 3):
            r = pick(c, want)
            if r is None:
                stat["absent"] += 1
            elif r[1][1] == 0:
                stat["picked a zero placeholder"] += 1
            elif r[1][2] == 0:
                stat["picked nonzero but flag==0"] += 1
            else:
                stat["picked a real paid cost"] += 1
    for k, v in stat.most_common():
        print("   %-32s %d" % (k, v))

    # ---- Q2: does the unit path ever double-fire? ----
    print("\n=== Q2: units with two cost slots of the same real Type ===")
    with open(base, "rb") as fh:
        pass
    from aoe2mod.dat import locate as L
    civs, cs, gvv, ttail = L.locate(data, parser=p)
    units = {}
    for c in civs:
        for u in c["units"]:
            units.setdefault(u["id"], u)
    dup_units = []
    for uid, u in sorted(units.items()):
        cnt = Counter(x["type"] for x in (u.get("costs") or []))
        for t, k in cnt.items():
            if k > 1 and t >= 0:
                dup_units.append((uid, t, k, [(x["type"], x["amount"], x["flag"])
                                              for x in u["costs"]]))
    print("  distinct units:", len(units))
    print("  units with two slots of the same real resource type:",
          len(dup_units))
    for r in dup_units[:10]:
        print("     ", r)

main()
