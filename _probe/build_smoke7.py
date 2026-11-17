# -*- coding: utf-8 -*-
r"""smoke7: a `.dat`-ONLY unit grant, using the mechanism the game already uses.

## Why this route

The user's first CLEAN in-game test (m24660):

    「我再次选中你的数据模组并进入对局验证，不列颠黑暗时代兵营，没有蔷琵侦察兵，
      村民血量是1000。」

    control PASSED (villager 1000)   -> the `.dat` loaded and rendered
    test    FAILED (no Champi Scout) -> the dat-adjacent JSON availability write
                                        does NOT reach the build menu

So the `.dat` is the layer that works, and `_probe/test_dat_grant_route.py` +
`_probe/probe_makeavail_automatic.py` show the `.dat` CAN express a per-civ grant:

    effect command type 2, a=<unit>, b=1, on a tech whose `civ` is the civ
    -> 112 such techs exist in shipped data
    -> 99 of them are ABSENT from the owning civ's tree, i.e. they apply
       AUTOMATICALLY because of `tech.civ`, not because they were researched

That last number is what makes the route usable: it does not need the tree layer
that has failed to take effect.

## The artifact

    CONTROL  Villager hit_points = 1000            (proven to render)
    TEST     a NEW Effect + Tech, civ = 1 (British), containing
             command (type 2, a=2550, b=1)
             -> "make the Champi Scout available to the Britons"

Unit 2550 is already in every civilization's `.dat` unit array with a Barracks train
location, and the Britons can build a Barracks, so nothing else has to be true.
File: one `.dat`.  No JSON at all.
"""
import contextlib
import _gamepaths as GP
import hashlib
import io
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402
import aoe2mod.dat.writer as W                             # noqa: E402
from aoe2mod.mod import emitter as E                       # noqa: E402

GAME = GP.GAME
OUT = os.path.join(HERE, "out_smoke7")
TITLE = "aoe2mod Smoke7 Dat Grant"
UNIT = 2550
CIV = 1                       # British
NEW_EFFECT = "SMOKE7 make Champi Scout available to British"
NEW_TECH = "SMOKE7 British Champi Scout"

print("A  sanity: the target civ, the unit, and the precedent")
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, _tail, how = tk._parsed
names = [c["name"] for c in civs]
assert names[CIV] == "British", names[CIV]
print("     civ[%d] = %s" % (CIV, names[CIV]))
assert UNIT in [u.get("id") for u in civs[CIV]["units"]]
print("     unit %d is in the civ's own unit array" % UNIT)

print()
print("B  parse the base .dat into the writer's model")
with contextlib.redirect_stdout(io.StringIO()):
    p = P.Parser(data)
    try:
        p.parse()
    except SystemExit:
        pass
stats = p.stats
print("     effects: %d   techs: %d   civs: %d"
      % (len(stats["effects"]), len(stats["techs"]), len(stats["civs"])))

print()
print("C  append ONE Effect (type 2, a=2550, b=1) and ONE civ-owned Tech")
effect_index = len(stats["effects"])
stats["effects"].append({
    "name": NEW_EFFECT,
    # (Type=2 Enable/Disable Unit, A=unit, B=1 = enable, C=-1, D=0.0)
    "commands": [(2, UNIT, 1, -1, 0.0)],
    "_new": True,
})
stats["effect_count"] = len(stats["effects"])
stats["techs"].append({
    "civ": CIV,
    "effect_id": effect_index,
    "type": 0,
    "icon_id": -1,
    "name": NEW_TECH,
    "research_locations": [(-1, 1, 0, -1)],
    "_new": True,
})
stats["tech_count"] = len(stats["techs"])
print("     effect %d = %r" % (effect_index, NEW_EFFECT))
print("     tech   %d = %r  civ=%d effect_id=%d"
      % (len(stats["techs"]) - 1, NEW_TECH, CIV, effect_index))

print()
print("C1 match the shipped 'make avail' record exactly")
# `_probe/probe_smoke7_likeforlike.py` read both sides through the SAME reader and
# found two deviations from every shipped 'make avail' tech.  They are cheap to
# remove, and leaving them in would risk the in-game test failing for a reason that
# has nothing to do with the mechanism:
#     costs[].type            shipped -1   (mine defaulted to 0)
#     research_locations[].research_time  shipped 0  (mine 1, from the tuple I passed)
# The command itself already matches: (type 2, a=unit, b=1, c=-1, d=0.0).
stats["techs"][-1]["costs"] = [
    {"type": -1, "amount": 0, "flag": 0},
    {"type": -1, "amount": 0, "flag": 0},
    {"type": -1, "amount": 0, "flag": 0},
]
stats["techs"][-1]["research_locations"] = [(-1, 0, 0, -1)]
print("     costs -> three (-1, 0, 0) slots (as shipped)")
print("     research_locations -> [(-1, 0, 0, -1)] i.e. research_time 0")

print()
print("C2 the CONTROL, in the same file: villager hit points -> 1000")
# A control must ride along, or a missing Champi Scout cannot be distinguished from
# "the mod never loaded".  Measured earlier: the villager edit touches 1701 records
# = 27 unit ids x 63 civilizations (the family rule), which is exactly what the
# product's own `unit.stat` compiles to.
VILLAGER_IDS = None
_changed = 0
_seen_ids = set()
for c in stats["civs"]:
    for u in c.get("units") or []:
        if u.get("id") == 83 or u.get("name") in ("VMBAS", "VMFEM"):
            _seen_ids.add(u.get("id"))
            if u.get("hit_points") != 1000:
                u["hit_points"] = 1000
                _changed += 1
print("     records with id 83/name VMBAS|VMFEM whose hit_points were set: %d"
      % _changed)
print("     distinct ids touched: %s" % sorted(x for x in _seen_ids if x))
if _changed == 0:
    print("     !! the model does not expose villagers as id 83 -- the control would")
    print("        be missing and the test would be unreadable")
    raise SystemExit("control could not be built from the model")

print()
print("D  serialise")
# `serialize_dat` returns `(bytes, report)` -- an earlier version of this script did
# `out = serialize_dat(...)` and then measured `len(out)`, which is 2 (the tuple),
# and the re-parse below died with "read of 8 byte(s) at offset 0 would pass end of
# file (2)".  Unpack it.
out, rep = W.serialize_dat(stats, raw=data, gv=gv)
print("     raw bytes: %d (base %d, delta %+d)"
      % (len(out), len(data), len(out) - len(data)))
print("     model bytes %s (%.2f%%), opaque %s (%.2f%%), model!=raw %d group(s)"
      % (rep.get("model_bytes"), rep.get("model_pct", 0.0),
         rep.get("opaque_bytes"), rep.get("opaque_pct", 0.0),
         rep.get("model_vs_original_mismatches", -1)))

print()
print("E  re-parse the result with the UNMODIFIED parser (the real proof)")
with contextlib.redirect_stdout(io.StringIO()):
    p2 = P.Parser(out)
    try:
        p2.parse()
    except SystemExit:
        pass
ok_eof = (p2.r.pos == len(out))
print("     consumed %d of %d bytes; leftover %d; clean EOF: %s"
      % (p2.r.pos, len(out), len(out) - p2.r.pos, ok_eof))
assert ok_eof, "the written .dat must parse to exactly its own length"
e2 = p2.stats["effects"]
found = None
for e in e2:
    if e.get("name") == NEW_EFFECT:
        found = e
        break
assert found is not None, "the new effect must survive the round trip"
print("     the new effect round-trips: %s" % found["commands"])
t2 = [t for t in p2.stats["techs"] if isinstance(t, dict) and t.get("name") == NEW_TECH]
assert t2, "the new tech must survive the round trip"
print("     the new tech round-trips: civ=%s effect_id=%s"
      % (t2[0].get("civ"), t2[0].get("effect_id")))

print()
print("F  emit a mod containing ONLY this .dat")
info = E.make_info(TITLE, author="aoe2mod",
                   description="SMOKE7: dat-only grant of unit %d to the Britons "
                               "via a civ-owned type-2 effect command" % UNIT)
man = E.emit_data_mod(OUT, out, info, base_dir=GAME, overwrite=True)
print("     files:")
for root, _d, fs in os.walk(OUT):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("        %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, OUT)))
print("     dat_file_bytes=%s  changes_dat=%s"
      % (man.get("dat_file_bytes"), man.get("changes_dat")))

print()
print("SMOKE7 READY: %s" % OUT)
print("  This mod contains NO JSON -- only the .dat, the layer proven to render.")
print("  CONTROL: villager 1000.  TEST: does the Britons' Barracks offer")
print("           蔷琵侦察兵 in the Dark Age?")
