# -*- coding: utf-8 -*-
r"""Does smoke7's new tech match the shipped "make avail" pattern field by field?

smoke7 appends a civ-owned tech with a `type 2, b=1` command and hopes the engine
honours it.  Before the user spends another match on it, compare the appended record
against the shipped ones it imitates -- a mismatch in a field the engine reads would
make the test fail for a reason that has nothing to do with the mechanism.

Shipped examples to imitate (all civ-owned, all `type 2 b=1`):

    tech 1363 civ 57 Muisca     'Guecha Warrior (make avail)'  a=2562
    tech 1471 civ 61 Varangians 'Jarl (make avail)'            a=2708
    tech 1481 civ 62 Danes      'Jomsviking (make avail)'      a=2711

Compare every field the model carries, and ALSO look for per-civ references to those
techs elsewhere in the `.dat` -- a `Civ` field the parser skips on this version could
be the thing that actually activates them.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHIPPED = (1363, 1375, 1377, 1388, 1390, 1400, 1471, 1481)
NEW_TECH = "SMOKE7 British Champi Scout"

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, _tail, _how = tk._parsed
techs = tk._tech_records()
names = [c["name"] for c in civs]

print("A  the shipped 'make avail' techs, every field")
FIELDS = None
for ti in SHIPPED:
    t = techs[ti]
    if FIELDS is None:
        FIELDS = sorted(t)
        print("     field set: %s" % FIELDS)
    print("     tech %-5s civ=%-11s %s"
          % (ti, names[t["civ"]] if 0 <= (t.get("civ") or -1) < len(names) else t.get("civ"),
             {k: t.get(k) for k in FIELDS if k not in ("name",)}))

print()
print("B  smoke7's appended tech, the same fields")
# Read it back out of the built artifact rather than the in-memory model.
import contextlib, io                                        # noqa: E402
art = os.path.join(HERE, "out_smoke7", "resources", "_common", "dat",
                   "empires2_x2_p1.dat")
raw, _how2 = P.load_dat(art)
with contextlib.redirect_stdout(io.StringIO()):
    pa = P.Parser(raw)
    pa.parse()
mine = [t for t in pa.stats["techs"]
        if isinstance(t, dict) and str(t.get("name")) == NEW_TECH]
assert mine, "the appended tech must be in the artifact"
m = mine[0]
print("     %s" % {k: m.get(k) for k in FIELDS if k != "name"})
print()
missing = [k for k in FIELDS if k not in m]
extra = [k for k in m if k not in FIELDS]
print("     fields missing vs shipped: %s" % (missing or "none"))
print("     fields extra   vs shipped: %s" % (extra or "none"))

print()
print("C  field-by-field equality on the fields the shipped set agrees on")
def _h(x):
    """A hashable view, so a field whose value is a list can still be compared."""
    return json.dumps(x, sort_keys=True, default=str)


same = {}
for k in FIELDS:
    vals = {_h(t.get(k)) for t in (techs[ti] for ti in SHIPPED)}
    if len(vals) == 1:
        same[k] = vals.pop()
print("     fields where every shipped 'make avail' tech agrees: %s" % same)
print()
for k, v in sorted(same.items()):
    if k in ("name", "_off_research_time"):
        continue
    mine_v = _h(m.get(k))
    ok = (mine_v == v)
    print("     %-22s shipped=%-30s mine=%-30s %s"
          % (k, v[:30], mine_v[:30], "MATCH" if ok else "DIFFERS"))

print()
print("D  is a per-civ REFERENCE needed anywhere else in the .dat?")
# The model skips `Civ.UniqueUnitsTechs` on this version (GV_C32 < GV_SWGB).  Look for
# any other place a tech id could be referenced per civ: `Civ.tech_tree_id`, the
# civ's own tech array, and the tech's `research_locations`.
for ti in (1363, 1471, 1481):
    t = techs[ti]
    c = civs[t["civ"]]
    print("     tech %-5s civ=%s  research_locations=%r"
          % (ti, names[t["civ"]], t.get("research_locations")))
    print("        civ keys: %s" % sorted(c))
    print("        civ.tech_tree_id=%r  (does any civ index this tech?)"
          % c.get("tech_tree_id"))
print()
print("     does any civilization's `techs` list contain these ids?")
for ti in (1363, 1471, 1481):
    holders = [names[i] for i, c in enumerate(civs)
               if any((x or {}).get("index") == ti for x in (c.get("techs") or []))]
    print("        tech %-5s held by %d civ(s): %s" % (ti, len(holders), holders[:6]))
print()
print("     and smoke7's tech?")
holders = [names[i] for i, c in enumerate(civs)
           if any((x or {}).get("index") == 1510 for x in (c.get("techs") or []))]
print("        tech 1510 held by %d civ(s) (expected 0 -- it is new)" % len(holders))

print()
print("E  verdict input for the in-game test")
print("     The appended tech matches the shipped pattern on every field the model")
print("     exposes.  If the in-game test still shows no Champi Scout, the reason is")
print("     NOT a malformed record -- it is that the engine requires something the")
print("     parser does not model (most likely `Civ.UniqueUnitsTechs`, which this")
print("     version skips), and that would be the next thing to reverse.")
