# -*- coding: utf-8 -*-
r"""Where could a per-civilization DISABLE for the Incas hang without losing to
the global enable?

The Mule Cart precedent (Armenians/Georgians, tech 932/940 -> effect 944 ->
`type 2, a=562/584, b=0`) proves the SHAPE of a per-civ disable exists in the
shipped data.  It does NOT prove the ordering: 562 (Lumber Camp) is never
enabled by any command, the game simply starts with it on, so a disable has
nothing to out-vote.

Unit 2550 is different.  It is switched on globally:

    tech 1350  'Champi Scout (Make avail)'   civ = -1   RequiredTechs = [104]

So a disable hung on an Incas tech only wins if the engine applies effects in
an order that puts that tech after 1350.  Two things are knowable statically
and this file measures them:

  A. what tech 104 is (the gate in front of the enable), and
  B. every Incas-owned, cost-free, page-less tech with its index and
     RequiredTechs -- specifically whether any of them fires at the SAME age
     as (or later than) the enable while sitting at a HIGHER index.

Read-only.  `parser.read_tech` is monkey-patched here to keep `RequiredTechs`;
`aoe2mod/dat/parser.py` is untouched.
"""
import contextlib
import _gamepaths as GP
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from aoe2mod.dat import parser as P                        # noqa: E402
from aoe2mod.dat import locate as L                        # noqa: E402
from aoe2mod.game import locations as G                    # noqa: E402

GAME = GP.GAME
CIV = "Incas"
UNIT = 2550
ENABLE_TECH = 1350

fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("  :: " + str(detail) if detail else ""))
    if not ok:
        fails.append(name)


# ---------------------------------------------------------------- A. read it
raw, how = P.load_dat(G.dat_path(GAME))
print("dat : %d raw bytes (%s)" % (len(raw), how))

# Keep RequiredTechs: `read_tech` reads and discards the six i16 gates, so the
# only way to see them without changing the shipped parser is to re-walk the
# record here from its start offset.
_TECH_STARTS = []

_orig_read_tech = P.read_tech


def read_tech_with_gates(r):
    start = r.pos
    _TECH_STARTS.append(start)
    reqs = [r.i16() for _ in range(6)]
    costs = [P.read_research_resource_cost(r) for _ in range(3)]
    req_count = r.i16()
    t = {}
    t["civ"] = r.i16()
    r.i16()                                            # FullTechMode
    if r.gv < P.GV_C31:
        r.i16()                                        # ResearchLocation
    if r.gv >= P.GV_MATT:
        r.i32()
        r.i32()
    else:
        r.i16()
        r.i16()
    if r.gv < P.GV_C31:
        r.i16()                                        # ResearchTime
    t["effect_id"] = r.i16()
    t["type"] = r.i16()
    t["icon_id"] = r.i16()
    if r.gv < P.GV_C31:
        r.u8()                                         # ButtonID
    r.i32()
    r.i32()
    if r.gv < P.GV_C31:
        r.i32()                                        # HotKey
    t["name"] = r.debug_string()[1]
    if P.GV_C15 <= r.gv <= P.GV_LatestDE2:
        r.u8()                                         # Repeatable
    if P.GV_C31 <= r.gv <= P.GV_LatestDE2:
        n = r.i16()
        t["research_locations"] = [P.read_research_location(r) for _ in range(n)]
    t["required_techs"] = [q for q in reqs if q >= 0]
    t["required_count"] = req_count
    t["costs"] = costs
    return t


P.read_tech = read_tech_with_gates
pr = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    pr.parse()
P.read_tech = _orig_read_tech

st = pr.stats
techs = st.get("techs") or []
civs, _cs, _gv, _tail = L.locate(raw, parser=pr)
check("parser reaches the last byte", pr.r.pos == len(raw), "%d of %d" % (pr.r.pos, len(raw)))
print("techs: %d   civs: %d" % (len(techs), len(civs)))

inca_ix = next(i for i, c in enumerate(civs) if c.get("name") == CIV)
print("civ %r -> index %d" % (CIV, inca_ix))

# ---------------------------------------------------------------- B. tech 104
t104 = techs[104]
print()
print("=== A. the gate in front of the global enable")
print("  tech 104 %r civ=%r required=%r effects=%r"
      % (t104.get("name"), t104.get("civ"),
         (t104.get("required_techs") or []), t104.get("effect_id")))
print("  tech %d %r civ=%r required=%r effects=%r"
      % (ENABLE_TECH, techs[ENABLE_TECH].get("name"), techs[ENABLE_TECH].get("civ"),
         (techs[ENABLE_TECH].get("required_techs") or []),
         techs[ENABLE_TECH].get("effect_id")))
check("the global enable is global (civ = -1)",
      techs[ENABLE_TECH].get("civ") == -1, techs[ENABLE_TECH].get("civ"))
check("the global enable waits for tech 104",
      104 in (techs[ENABLE_TECH].get("required_techs") or []),
      techs[ENABLE_TECH].get("required_techs"))

# ---------------------------------------------------------------- C. carriers
print()
print("=== B. Incas-owned, free, page-less techs (the carriers that exist)")
rows = []
for ti, t in enumerate(techs):
    if t.get("civ") != inca_ix:
        continue
    locs = t.get("research_locations") or []
    free = all(l[0] < 0 and (l[1], l[2]) == (0, 0) for l in locs) if locs else True
    if not free:
        continue
    rows.append((ti, t.get("name") or "", t.get("required_techs") or [],
                 t.get("effect_id")))
print("  %d carriers" % len(rows))
for ti, name, req, eff in rows:
    eff_cmds = len((st["effects"][eff].get("commands") or [])) if isinstance(eff, int) and 0 <= eff < len(st["effects"]) else -1
    print("  tech %-5d %-34r req=%-18r effect=%-5r cmds=%d"
          % (ti, name[:34], req, eff, eff_cmds))

print()
print("=== C. which carriers could out-vote the enable")
# Three grades of carrier, strongest first:
#   same-age-plus-higher-index  -- fires in the same age as the enable and sits
#                                  after it, so an index-ordered engine applies
#                                  it second
#   same-age                    -- fires in the same age but before it by index
#   dark-age (required == [])   -- fires at 0:00, BEFORE the enable
strong = [r for r in rows if 104 in r[2] and r[0] > ENABLE_TECH]
same = [r for r in rows if 104 in r[2] and r[0] < ENABLE_TECH]
dark = [r for r in rows if not r[2]]
print("  fires with the enable AND sits after it (index > %d) : %r"
      % (ENABLE_TECH, [r[0] for r in strong]))
print("  fires with the enable but sits before it             : %r"
      % ([r[0] for r in same],))
print("  fires at 0:00, before the enable                     : %r"
      % ([r[0] for r in dark],))
print()
print("INCA LATE CARRIER: %d carriers, %d after the enable at the same age"
      % (len(rows), len(strong)))
if fails:
    for f in fails:
        print("  - " + f)
sys.exit(1 if fails else 0)
