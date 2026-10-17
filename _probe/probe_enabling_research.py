"""DECISIVE: is the dat's own TechTree `EnablingResearch` the per-civ gate?

The dat ships one global TechTree whose 266 UnitConnections carry
`EnablingResearch` ("Makes available.  Used by units, which need a research to be
available") and `RequiredResearch` ("Upgrades unit").  Both are currently read and
discarded by `parser.py:read_unit_connection`.

Hand Cannoneer (unit 5) has EnablingResearch = 85.  We already know from the
shipped CivTechTrees JSON that 24 civilizations may build it and 38 are told
NotAvailable.  So the question is sharp and answerable:

  For each unit with an EnablingResearch, is the tech it names CIV-OWNED
  (`tech.civ != -1`)?  If yes, that tech is the per-civ gate -- only the civ that
  owns it can ever reach the unit.

This is the test the whole availability line of work has been missing: it uses the
dat, per the user's correction (m19924), not the JSON.

Cross-checks against facts already pinned:
  * 24 can build unit 5 / 38 cannot.
  * the dat's tree must be consistent with the type-2 Enable layer, which called
    Hand Cannoneer GLOBALLY enabled -- if EnablingResearch=85 is also global, then
    the dat genuinely does not express the 24/38 split and the split comes from
    somewhere else again.
"""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
import aoe2mod.dat.locate as L  # noqa: E402
import aoe2mod.dat.parser as P  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data, civs, _cs, gv, _tail, _how = tk._parsed
techs = L.locate_techs(data, _tail, gv)
names = [c["name"] for c in civs]

# --- walk the dat's own TechTree, keeping what the parser throws away -------
_p = P.Parser(data)
import io as _io
import contextlib as _ctx
with _ctx.redirect_stdout(_io.StringIO()):
    try:
        _p.parse(stop_after=9)
    except SystemExit:
        pass
_tech_end = _p.stage_offsets[-1][2]

r = P.Reader(data, gv=gv)
r.pos = _tech_end + 7 * 4
n_ages = r.u8()
n_bldg = r.u8()
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
    uid = r.i32()
    r.u8()
    upper = r.i32()
    r.i32(); r.i32_array(10); r.i32_array(10)
    r.i32()
    k = r.u8()
    if k:
        r.i32_array(k)
    r.i32()
    req = r.i32()
    r.i32()
    enab = r.i32()
    conn[uid] = {"upper": upper, "required": req, "enabling": enab}

print("dat TechTree: %d unit connections" % len(conn))

# --- how many name an enabling/required research, and who owns that tech? ---
enab_civ = Counter()
req_civ = Counter()
enab_rows = []
for uid, c in sorted(conn.items()):
    for field, counter, store in (("enabling", enab_civ, enab_rows),
                                  ("required", req_civ, None)):
        tid = c[field]
        if tid is None or tid < 0:
            continue
        owner = techs[tid].get("civ") if 0 <= tid < len(techs) else "OOR"
        counter[("global" if owner == -1 else "civ-owned")] += 1
        if store is not None:
            store.append((uid, tid, owner))

print("EnablingResearch present on %d units  -> %s"
      % (len(enab_rows), enab_civ.most_common()))
print("  (of those, civ-owned: %s)"
      % [(u, t, o) for u, t, o in enab_rows if o != -1][:12])
tot_req = sum(req_civ.values())
print("RequiredResearch present on %d units  -> %s"
      % (tot_req, req_civ.most_common()))

print()
print("=" * 72)
print("Hand Cannoneer: everything the dat says about unit 5")
print("=" * 72)
c5 = conn.get(5)
print("  dat TechTree connection : %s" % c5)
if c5 and c5["enabling"] >= 0:
    t = techs[c5["enabling"]]
    print("  enabling tech %d: civ=%s name=%r effect_id=%s"
          % (c5["enabling"], t.get("civ"), t.get("name"), t.get("effect_id")))
    rows = L.locate_effects(data)[0]
    import aoe2mod.intent.compiler as C
    for row in C.effect_rows(rows, t, fanout=None, ix=None):
        print("      effect: type=%s raw=%s" % (row["type"], row["raw"]))
print("  and every dat command that names unit 5:")
rows_all = L.locate_effects(data)[0]
hits = []
for ti, t in enumerate(techs):
    for row in C.effect_rows(rows_all, t, fanout=None, ix=None):
        if row["type"] == 2 and row["raw"][1] == 5:
            hits.append((ti, names[t["civ"]] if 0 <= t["civ"] < 63 else "GLOBAL",
                         row["raw"]))
for h in hits:
    print("      tech %-5d civ=%-12s raw=%s" % h)

print()
print("=" * 72)
print("does the dat's EnablingResearch split the 24/38?")
print("=" * 72)
trees = CT.load_trees(tk.game_root)
by_stem = {CT.civ_file_stem(c["name"]): c["name"] for c in civs}

# The trees already tell us the per-civ answer; use it as ground truth.
truth = {}
for stem, tax in trees.items():
    dname = by_stem.get(stem)
    for row in CT.unit_rows(tax):
        uid = row.get("Node ID")
        st = row.get("Node Status")
        d = truth.setdefault(uid, {"yes": set(), "no": set()})
        if st == "ResearchedCompleted" or st == "ResearchRequired":
            d["yes"].add(dname)
        elif st == "NotAvailable":
            d["no"].add(dname)

rows = []
for uid, c in sorted(conn.items()):
    en = c["enabling"]
    if en is None or en < 0:
        continue
    owner = techs[en].get("civ", -1)
    d = truth.get(uid)
    if not d or not d["yes"] or not d["no"]:
        continue
    ownname = names[owner] if 0 <= owner < 63 else None
    rows.append((uid, en, owner, ownname, len(d["yes"]), len(d["no"]),
                 (ownname in d["yes"]) if ownname else None))

print("  units with BOTH a dat enabling research AND a 24/38-style split: %d"
      % len(rows))
print("  %-6s %-8s %-12s %-8s %-8s %s" % ("unit", "enab", "owner", "can", "cannot",
                                          "owner can build?"))
for uid, en, owner, ownname, nyes, nno, ok in rows[:30]:
    print("  %-6d %-8d %-12s %-8d %-8d %s"
          % (uid, en, ownname if ownname else "(global)", nyes, nno,
             "(n/a global)" if ok is None else ok))

nonglobal = [x for x in rows if x[2] != -1]
print()
print("  enabling researches that are civ-owned: %d of %d"
      % (len(nonglobal), len(rows)))
if nonglobal:
    good = sum(1 for x in nonglobal if x[6])
    print("  ...where the owning civ is one the tree says CAN build it: %d/%d"
          % (good, len(nonglobal)))
