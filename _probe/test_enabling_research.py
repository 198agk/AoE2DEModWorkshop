"""PIN: the `.dat` DOES name the owner of 46 unique units, via EnablingResearch.

Why this pin exists
-------------------
§15.4v concluded "the `.dat` cannot answer who can build what".  That is half
wrong, and the half that is wrong was load-bearing enough to have been repeated
in the skill file.  `aoe2mod/dat/parser.py`'s `read_unit_connection` READS
`EnablingResearch` and then DISCARDS it.  Of the 266 unit connections, 47 point
at a CIV-OWNED tech (`tech.civ != -1`), and for 46 of those 47 that owner is
EXACTLY the one civilization the shipped tree says can build the unit.

The distinction that must not be flattened again:
  * per-civ `Node Status` (`NotAvailable` / `ResearchRequired`) -> only in
    `CivTechTrees/<CIV>.json`.  Not derivable from the `.dat`.
  * THE OWNER of a unique unit -> in the `.dat`, right there in the TechTree
    section.  The dat gates the owner; the tree gates the per-civ status.

And the limit that must not be overclaimed: this covers 46 of the 159
single-civ units.  It does NOT explain Hand Cannoneer (24 can / 38 cannot; its
enabling research 85 is global), War Galley (56 builders, no enabling research
at all) or Knight (47/9, enabling 166 global).  That split is still unlocated.

Lesson recorded with the pin: before asserting "X cannot answer this", grep
every `r.i32()` in the parser for X's structure and ask which one is read and
thrown away.
"""
import contextlib
import io
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
import aoe2mod.dat.locate as L  # noqa: E402
import aoe2mod.dat.parser as P  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
from aoe2mod.semantic.index import index as sem_index  # noqa: E402

FAILED = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- %s" % detail) if (detail and not ok) else ""))
    if not ok:
        FAILED.append(label)


tk = A.open_toolkit()
tk._ensure()
data, civs, _cs, gv, _tail, _how = tk._parsed
techs = L.locate_techs(data, _tail, gv)
names = [c["name"] for c in civs]
sem = sem_index()


def uname(uid):
    e = sem.units.get(uid)
    return e.display if e else "(unnamed)"


# --- read the dat's own TechTree connections -------------------------------
_p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    try:
        _p.parse(stop_after=9)
    except SystemExit:
        pass
r = P.Reader(data, gv=gv)
r.pos = _p.stage_offsets[-1][2] + 7 * 4
n_ages, n_bldg = r.u8(), r.u8()
n_units = r.i16() if r.gv >= P.GV_C32 else r.u8()
n_res = r.i16() if r.gv == P.GV_CCV2 else r.u8()
r.i32()
for _ in range(n_ages):
    r.i32(); r.u8()
    for _ in range(3):
        k = r.u8()
        if k:
            r.i32_array(k)
    r.i32(); r.i32_array(10); r.i32_array(10)
    r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()
for _ in range(n_bldg):
    r.i32(); r.u8()
    for _ in range(3):
        k = r.u8()
        if k:
            r.i32_array(k)
    r.i32(); r.i32_array(10); r.i32_array(10)
    r.u8(); r.skip(5); r.skip(5); r.i32(); r.i32()
conn = {}
for _ in range(n_units):
    uid = r.i32(); r.u8(); r.i32()
    r.i32(); r.i32_array(10); r.i32_array(10); r.i32()
    k = r.u8()
    if k:
        r.i32_array(k)
    r.i32(); r.i32(); r.i32()
    conn[uid] = r.i32()          # EnablingResearch

# --- the shipped tree, as an independent second source ---------------------
trees = CT.load_trees(tk.game_root)
by_stem = {CT.civ_file_stem(c["name"]): c["name"] for c in civs}
truth = {}
for stem, tax in trees.items():
    dname = by_stem.get(stem)
    for row in CT.unit_rows(tax):
        uid = row.get("Node ID")
        d = truth.setdefault(uid, {"yes": set(), "no": set(), "absent": set()})
        st = row.get("Node Status")
        if st in ("ResearchedCompleted", "ResearchRequired"):
            d["yes"].add(dname)
        elif st == "NotAvailable":
            d["no"].add(dname)
        else:
            d["absent"].add(dname)

print("=" * 78)
print("A. the field exists and splits the unit connections")
print("=" * 78)
check(len(conn) == 266, "the dat's TechTree carries 266 unit connections",
      "got %d" % len(conn))
glob = sum(1 for u in conn if conn[u] >= 0
           and techs[conn[u]].get("civ", -1) == -1)
owned = sum(1 for u in conn if conn[u] >= 0
            and techs[conn[u]].get("civ", -1) != -1)
none = len(conn) - glob - owned
check(owned == 47, "47 enabling researches are CIV-OWNED", "got %d" % owned)
check(glob == 26, "26 are global", "got %d" % glob)
check(none == 193, "193 units set no enabling research at all",
      "got %d" % none)

print()
print("=" * 78)
print("B. the decisive score: owner vs the shipped tree")
print("=" * 78)
exact = 0
scored = 0
anomalies = []
for uid in sorted(conn):
    en = conn[uid]
    if en < 0 or en >= len(techs):
        continue
    owner = techs[en].get("civ", -1)
    if owner == -1:
        continue
    scored += 1
    d = truth.get(uid, {"yes": set(), "no": set(), "absent": set()})
    own = names[owner]
    if d["yes"] == {own}:
        exact += 1
    else:
        anomalies.append((uid, own, len(d["yes"]), len(d["no"])))
check(scored == 47, "47 civ-owned records were scored", "got %d" % scored)
check(exact == 46, "46 of them name EXACTLY the sole builder",
      "got %d; anomalies=%r" % (exact, anomalies[:4]))
check(len(anomalies) == 1, "exactly one exception, and it is unit 36",
      "got %r" % (anomalies,))
check(anomalies and anomalies[0][0] == 36,
      "the exception is unit 36 (Bombard Cannon) whose owner reads Gaia",
      "got %r" % (anomalies[:1],))

# Five named spot checks, so the claim is anchored to units a reader knows.
for uid, civ, tech_id in ((8, "British", 263), (41, "Goths", 270),
                          (725, "Aztecs", 431), (755, "Huns", 1),
                          (291, "Japanese", 262)):
    en = conn.get(uid)
    check(en == tech_id and names[techs[en].get("civ", -1)] == civ,
          "unit %d (%s) -> tech %s -> %s" % (uid, uname(uid), tech_id, civ),
          "got enab=%r owner=%r" % (en,
                                    names[techs[en].get("civ", -1)] if en is not None else None))

print()
print("=" * 78)
print("C. the limit: it covers 46 of 159, and NOT the contested units")
print("=" * 78)
single = [u for u in conn if len(truth.get(u, {}).get("yes", set())) == 1]
named = sum(1 for u in single if conn[u] >= 0
            and techs[conn[u]].get("civ", -1) != -1)
check(len(single) == 159, "159 units are buildable by exactly one civ",
      "got %d" % len(single))
check(named == 46, "the dat names 46 of those 159", "got %d" % named)

for uid, label, exp_can, exp_cannot, is_civ_owned in (
        (5, "Hand Cannoneer", 24, 38, False),
        (21, "War Galley", 56, 0, False),
        (38, "Knight", 47, 9, False)):
    d = truth[uid]
    en = conn.get(uid, -1)
    own = techs[en].get("civ", -1) if 0 <= en < len(techs) else -1
    check(len(d["yes"]) == exp_can and len(d["no"]) == exp_cannot,
          "%s still splits %d can / %d cannot in the tree"
          % (label, exp_can, exp_cannot),
          "got %d / %d" % (len(d["yes"]), len(d["no"])))
    check((own != -1) == is_civ_owned,
          "%s is NOT resolved by a civ-owned enabling research" % label,
          "owner=%r" % (names[own] if own != -1 else "(global)",))

print()
print("ENABLING-RESEARCH PIN: the dat gates the OWNER of 46 unique units; the "
      "tree gates the per-civ status.")
print("NOT PROVEN: where the Hand Cannoneer / War Galley / Knight split lives "
      "-- still unlocated in the dat.")
sys.exit(1 if FAILED else 0)
