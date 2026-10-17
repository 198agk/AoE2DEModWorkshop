"""DECISIVE: the dat's civ-owned `EnablingResearch` as the per-civ buildability gate.

The dat ships ONE global TechTree.  Its 266 UnitConnections have an
`EnablingResearch` field, read and discarded by `parser.py:read_unit_connection`.
Of the 73 units that set it, 47 name a research whose `tech.civ` is NOT -1 --
i.e. a CIV-OWNED tech.

Spot check: unit 8 (Longbowman) -> EnablingResearch 263 -> `techs[263].civ == 1`
== British.  British is the one civilization that can build Longbowmen.  That is
exactly the shape of a per-civ gate, sitting in the .dat, per the user's
correction (m19924).

THE TEST: for every unit whose dat enabling research is civ-owned, is the owning
civilization EXACTLY the set of civilizations the shipped tree says can build it?
If yes, the dat is the authority and the gate is identified.
If no, the dat names only the OWNER (as with unique units) while the shipped tree
carries the full per-civ answer, and both are needed.
"""
import io
import os
import sys
import contextlib
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
import aoe2mod.dat.locate as L  # noqa: E402
import aoe2mod.dat.parser as P  # noqa: E402
import aoe2mod.intent.compiler as C  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
from aoe2mod.semantic.index import index as sem_index  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data, civs, _cs, gv, _tail, _how = tk._parsed
techs = L.locate_techs(data, _tail, gv)
names = [c["name"] for c in civs]
effects, _ = L.locate_effects(data)
sem = sem_index()


def tname(ti):
    e = sem.techs.get(ti)
    return e.display if e else "(unnamed)"


def uname(uid):
    e = sem.units.get(uid)
    return e.display if e else "(unnamed)"


# --- dat TechTree connections ---------------------------------------------
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
    uid = r.i32(); r.u8(); upper = r.i32()
    r.i32(); r.i32_array(10); r.i32_array(10); r.i32()
    k = r.u8()
    if k:
        r.i32_array(k)
    r.i32(); req = r.i32(); r.i32(); enab = r.i32()
    conn[uid] = {"upper": upper, "required": req, "enabling": enab}

# --- ground truth from the shipped tree ------------------------------------
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
print("1. every civ-owned EnablingResearch, against the shipped tree")
print("=" * 78)
print("  %-5s %-26s %-6s %-22s %-6s %-6s %-5s %s"
      % ("unit", "unit name", "enab", "tech name", "owner", "can", "cannot",
         "verdict"))
exact = 0
rows = 0
detail = []
for uid in sorted(conn):
    en = conn[uid]["enabling"]
    if en is None or en < 0 or en >= len(techs):
        continue
    owner = techs[en].get("civ", -1)
    if owner == -1:
        continue
    rows += 1
    d = truth.get(uid, {"yes": set(), "no": set(), "absent": set()})
    ownname = names[owner]
    ok = "EXACT" if (d["yes"] == {ownname} and len(d["yes"]) == 1) else "differs"
    if ok == "EXACT":
        exact += 1
    detail.append((uid, names[owner], len(d["yes"]), len(d["no"]),
                   len(d["absent"]), ok))
    print("  %-5d %-26s %-6d %-22s %-6s %-6d %-6d %-5d %s"
          % (uid, uname(uid)[:26], en, tname(en)[:22], names[owner],
             len(d["yes"]), len(d["no"]), len(d["absent"]), ok))

print()
print("  civ-owned enabling researches scored : %d" % rows)
print("  ...whose owner is the ONLY civ the tree says can build it : %d" % exact)
print("  ...where the tree says others can too                      : %d"
      % (rows - exact))

print()
print("=" * 78)
print("2. the units that matter: does the dat split them?")
print("=" * 78)
for uid, label in ((5, "Hand Cannoneer"), (21, "War Galley"), (38, "Knight"),
                   (8, "Longbowman"), (41, "Huskarl")):
    d = truth.get(uid, {"yes": set(), "no": set(), "absent": set()})
    en = conn.get(uid, {}).get("enabling", -1)
    owner = techs[en].get("civ", -1) if 0 <= en < len(techs) else -1
    print("  %-16s can=%-3d cannot=%-3d absent=%-3d enabling=%-5s owner=%s"
          % (label, len(d["yes"]), len(d["no"]), len(d["absent"]),
             en if en >= 0 else "none",
             names[owner] if owner != -1 else "(global)"))

print()
print("=" * 78)
print("3. how many units does the dat's tree gate per-civ AT ALL?")
print("=" * 78)
glob = sum(1 for u in conn if conn[u]["enabling"] >= 0
           and techs[conn[u]["enabling"]].get("civ", -1) == -1)
civ_owned = sum(1 for u in conn if conn[u]["enabling"] >= 0
                and techs[conn[u]["enabling"]].get("civ", -1) != -1)
print("  unit connections total        : %d" % len(conn))
print("  enabling research global      : %d" % glob)
print("  enabling research civ-owned   : %d" % civ_owned)
print("  no enabling research          : %d" % (len(conn) - glob - civ_owned))
multi = [(u, len(truth.get(u, {}).get("yes", set()))) for u in conn
         if truth.get(u, {}).get("yes")]
spread = Counter(n for _u, n in multi)
print("  distribution of 'how many civs can build it' over those units:")
for k in sorted(spread)[:14]:
    print("     %-3d civs: %d units" % (k, spread[k]))
print("  units buildable by exactly ONE civ : %d"
      % sum(1 for _u, n in multi if n == 1))
print("  ...of those, does the dat name that civ via enabling research?")
single = [(u, n) for u, n in multi if n == 1]
named = 0
for u, _n in single:
    en = conn.get(u, {}).get("enabling", -1)
    if en is not None and en >= 0 and techs[en].get("civ", -1) != -1:
        named += 1
print("     %d of %d" % (named, len(single)))
