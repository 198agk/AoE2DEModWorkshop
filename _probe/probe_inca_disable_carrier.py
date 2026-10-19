# -*- coding: utf-8 -*-
r"""Which technology could carry a DISABLE command for the Incas?

The Mule Cart precedent (Armenians/Georgians, tech 932/940 -> effect 944 ->
`type 2, a=562/584, b=0`) says a civilization-owned, cost-free, location-less
tech is where a per-civilization disable hangs.  For a revoke recipe on unit
2550 we need the same kind of carrier for the Incas, plus two facts:

  A. every Incas-owned tech whose `RequiredTechs` is empty and that has no UI
     page (location -1, cost 0) -- those are the 0:00 civilization bonuses,
  B. what each of their effects already commands (so appending one command does
     not lose a bonus),
  C. whether the GLOBAL enable of 2550 (`tech 1350`, civ = -1) could out-vote a
     disable hung on an Incas tech -- i.e. the relative order of the two tech
     indices, which is all we can read statically.

Read-only.  `parser.read_tech` is monkey-patched to keep `RequiredTechs`; nothing
in `aoe2mod/dat/parser.py` changes.
"""
import contextlib
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

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CIV = "Incas"
UNIT = 2550

_ORIG = P.read_tech


def _read_tech_keep_gates(r):
    t = P.read_tech(r)          # keep the shipped reader as the single source
    return t


def read_tech_with_gates(r):
    """Re-walk the record from scratch so RequiredTechs can be captured."""
    reqs = [r.i16() for _ in range(6)]
    costs = [P.read_research_resource_cost(r) for _ in range(3)]
    count = r.i16()
    t = {}
    t["civ"] = r.i16()
    r.i16()
    if r.gv < P.GV_C31:
        r.i16()
    if r.gv >= P.GV_MATT:
        if P.GV_C18 <= r.gv <= P.GV_LatestDE2:
            r.i32(); r.i32()
        else:
            r.i16(); r.i16()
    if r.gv < P.GV_C31:
        r.i16()
    t["effect_id"] = r.i16()
    t["type"] = r.i16()
    t["icon_id"] = r.i16()
    if r.gv < P.GV_C31:
        r.u8()
    r.i32(); r.i32()
    if r.gv < P.GV_C31:
        r.i32()
    t["name"] = r.debug_string()[1]
    if P.GV_C15 <= r.gv <= P.GV_LatestDE2:
        t["repeatable"] = r.u8()
    if P.GV_C31 <= r.gv <= P.GV_LatestDE2:
        n = r.i16()
        t["research_locations"] = [P.read_research_location(r) for _ in range(n)]
    t["required"] = [x for x in reqs if x >= 0]
    t["required_count"] = count
    t["costs"] = costs
    return t


raw, how = P.load_dat(G.dat_path(GAME))
pr = P.Parser(raw)
P.read_tech = read_tech_with_gates
try:
    with contextlib.redirect_stdout(io.StringIO()):
        pr.parse()
finally:
    P.read_tech = _ORIG
st = pr.stats
techs = st.get("techs") or []
effects = st.get("effects") or []
civs, _cs, _gv, _tail = L.locate(raw, parser=pr)

idx = None
for i, c in enumerate(civs):
    if (c.get("name") or "").strip().lower() == CIV.lower():
        idx = i
        break
print("civ %r -> index %r (of %d)" % (CIV, idx, len(civs)))
assert idx is not None

print("\n=== A/B. Incas-owned, free, page-less techs and what they already do")
carriers = []
for ti, t in enumerate(techs):
    if t.get("civ") != idx:
        continue
    locs = t.get("research_locations") or []
    free = all(l[0] < 0 for l in locs) and all((l[1], l[2]) == (0, 0) for l in locs)
    if not free:
        continue
    eid = t.get("effect_id")
    eff = effects[eid] if isinstance(eid, int) and 0 <= eid < len(effects) else None
    cmds = (eff or {}).get("commands") or []
    carriers.append((ti, t, cmds))
    print("  tech %-5d %-34r req=%-8r effect=%-5r cmds=%d"
          % (ti, (t.get("name") or "")[:34], t.get("required"), eid, len(cmds)))
    for c in cmds[:4]:
        print("      (type=%r a=%r b=%r)" % (c[0], c[1], c[2]))

print("\n=== C. where the global enable of %d lives" % UNIT)
for ti, t in enumerate(techs):
    eid = t.get("effect_id")
    if not isinstance(eid, int) or not (0 <= eid < len(effects)):
        continue
    for c in effects[eid].get("commands") or []:
        if c[0] == 2 and c[1] == UNIT:
            print("  tech %-5d civ=%-4r %-30r  enables/disables b=%r  req=%r"
                  % (ti, t.get("civ"), (t.get("name") or "")[:30], c[2],
                     t.get("required")))

eid1350 = techs[1350].get("effect_id") if len(techs) > 1350 else None
print("  tech 1350 effect_id = %r ; tech 1350 civ = %r"
      % (eid1350, techs[1350].get("civ") if len(techs) > 1350 else None))

print("\n  candidates for a disable carrier (Incas-owned, free): %d"
      % len(carriers))
print("  with empty RequiredTechs (fires at 0:00): %r"
      % [ti for ti, t, _ in carriers if not t.get("required")])
print("  empty-required AND index > 1350 (would apply after the global enable): %r"
      % [ti for ti, t, _ in carriers if not t.get("required") and ti > 1350])
print()
print("INCA DISABLE CARRIER: %d candidates, %d fire at 0:00"
      % (len(carriers), sum(1 for _t, t, _c in carriers if not t.get("required"))))
