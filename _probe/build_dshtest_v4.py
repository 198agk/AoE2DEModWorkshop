# -*- coding: utf-8 -*-
r"""dsh test v4: BOTH halves at once -- the `.dat` enable AND the tree/panel row.

## The unified hypothesis, from four measurements

    smoke6 / clean 2026-10-15 : tree row + panel entry, NO .dat enable   -> FAIL
    dsh test v1               : .dat effect enable,   NO tree row        -> FAIL
    dsh test v3               : adds .dat EnablingResearch               -> (untested)

and the census that makes it plausible:

    units gated by a CIV-OWNED `EnablingResearch`: 47
    ...whose owner's TREE also has a row for them : 46
    ...without a tree row                         :  1  (unit 36 -> Gaia, internal)

**46 of 47 have both.**  The classic unique units all do -- unit 8 British, 41 Goths,
40 Byzantine, 46 Turks, 725 Aztecs, each `ResearchedCompleted` in its owner's tree.
So the shipped way a civilization "may build" a unit looks like a link with TWO
halves, and every shipped example has both:

    .dat   the unit's `EnablingResearch` -> a civ-owned tech whose effect says
           `(type 2, a=the unit, b=1)`
    JSON   a `Node Status` row for the unit in that civ's CivTechTrees file
           (+ the panel entry that puts the button in the building)

Each half alone has now been tested in game and produced nothing.  v4 supplies both,
and keeps v3's negative control so the mechanism stays identifiable.

    EDIT 1  new effect 1500 = [(2,8,1),(2,2550,1)]; British tech 263 -> effect 1500
    EDIT 2  unit 2550's EnablingResearch = 263
    EDIT 3  villager family (27 ids) -> hit_points 1000          [CONTROL A]
    EDIT 4  unit 8's EnablingResearch -> -1                      [NEGATIVE CONTROL]
    EDIT 5  CivTechTrees/BRITONS.json: a row for 2550, ResearchedCompleted
    EDIT 6  futuravailableunits.json: the Britons Barracks gains 2550

Reading:
    A ok  B gone  C present -> the two halves are the mechanism; grants work
    A ok  B gone  C absent  -> the halves are necessary but something else is missing
    A ok  B still C present -> the .dat was what mattered; the tree is cosmetic
    A ok  B still C absent  -> neither the .dat nor the tree delivers a grant, and the
                               remaining candidate is a layer not yet identified
    A fail                  -> the mod did not load; nothing follows
"""
import contextlib
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import testmod_name as TN                                   # noqa: E402

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.families as F                           # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402
import aoe2mod.dat.writer as W                             # noqa: E402
import aoe2mod.intent.availability as AV                   # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.mod import emitter as E                       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_dshtest_v4")
TITLE = "%s v4 - Champi Scout, both halves + control" % TN.PREFIX
TECH = 263
OLD_EFFECT = 251
UNIT = 2550
LONGBOW = 8
VILLAGER = 83
HP = 1000
VERSION = 4
CIV = "British"

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, tail, how = tk._parsed
names = [c["name"] for c in civs]
assert names[1] == CIV


def enabling(pr, raw, gv_, want):
    """`EnablingResearch` of `want`, plus its byte offset."""
    stage = next(t for t in pr.stage_offsets if "TechTree" in t[0])
    r = P.Reader(raw, gv=gv_)
    r.pos = stage[1] + 7 * 4
    n_ages, n_bldg = r.u8(), r.u8()
    n_units = r.i16() if r.gv >= P.GV_C32 else r.u8()
    r.i16() if r.gv == P.GV_CCV2 else r.u8()
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
    for _ in range(n_units):
        uid = r.i32(); r.u8()
        r.i32()
        r.i32(); r.i32_array(10); r.i32_array(10); r.i32()
        k = r.u8()
        if k:
            r.i32_array(k)
        r.i32(); r.i32()
        r.i32()
        o = r.pos
        en = r.i32()
        if uid == want:
            return o, en
    raise SystemExit("unit %d has no TechTree connection" % want)


with contextlib.redirect_stdout(io.StringIO()):
    _p = P.Parser(data)
    _p.parse()
stats = _p.stats
_o2550, _v2550 = enabling(_p, data, gv, UNIT)
_o8, _v8 = enabling(_p, data, gv, LONGBOW)
print("A  state before the .dat edits")
print("     unit %-5s EnablingResearch = %-5s ; unit %-5s = %s"
      % (UNIT, _v2550, LONGBOW, _v8))
assert _v2550 == -1 and _v8 == TECH
trees = CT.load_trees(GAME)
print("     BRITONS tree row for %s: %s"
      % (UNIT, CT.row_for(trees["BRITONS"], UNIT, CT.UNIT_USE_TYPES)))
print("     BRITONS tree row for %s: %s"
      % (LONGBOW, (CT.row_for(trees["BRITONS"], LONGBOW,
                              CT.UNIT_USE_TYPES) or {}).get("Node Status")))
assert CT.row_for(trees["BRITONS"], UNIT, CT.UNIT_USE_TYPES) is None

print()
print("B  the .dat edits (1-4)")
stats["effects"].append({
    "name": "dsh test v4 Longbow + Champi Scout",
    "commands": [(2, LONGBOW, 1, -1, 0.0), (2, UNIT, 1, -1, 0.0)],
    "_new": True,
})
stats["effect_count"] = len(stats["effects"])
new_idx = len(stats["effects"]) - 1
stats["techs"][TECH]["effect_id"] = new_idx
F.warm({"civs": civs}, game_root=GAME)
family = sorted(F.family_of(F.build_families(civs), VILLAGER))
touched = 0
for c in stats["civs"]:
    for u in c.get("units") or []:
        if u.get("id") in family:
            if u.get("hit_points") != HP:
                touched += 1
            u["hit_points"] = HP
print("     EDIT 1  effect %d = [(2,%d,1),(2,%d,1)]; tech %d -> %d"
      % (new_idx, LONGBOW, UNIT, TECH, new_idx))
print("     EDIT 3  villager family (%d ids) -> %d ; records set: %d"
      % (len(family), HP, touched))
assert touched == len(family) * len(civs)

out, rep = W.serialize_dat(stats, raw=data, gv=gv)
with contextlib.redirect_stdout(io.StringIO()):
    _p2 = P.Parser(out)
    _p2.parse()
# offsets MUST be re-derived: adding an effect moves the tail
_o2550b, _ = enabling(_p2, out, gv, UNIT)
_o8b, _ = enabling(_p2, out, gv, LONGBOW)
patched = bytearray(out)
struct.pack_into("<i", patched, _o2550b, TECH)      # EDIT 2
struct.pack_into("<i", patched, _o8b, -1)           # EDIT 4
patched = bytes(patched)
_d = [i for i in range(len(out)) if out[i] != patched[i]]
print("     EDIT 2+4  %d bytes patched (offsets moved %d->%d, %d->%d)"
      % (len(_d), _o2550, _o2550b, _o8, _o8b))
assert len(_d) == 8

print()
print("C  the JSON edits (5-6), through the PRODUCT's own availability path")
trees2 = CT.load_trees(GAME)
orig = __import__("json").loads(__import__("json").dumps(trees2["BRITONS"],
                                                         ensure_ascii=False))
orig.pop("path", None)
proposal = dict(trees2)
import json as _json                                          # noqa: E402
proposal["BRITONS"] = _json.loads(_json.dumps(trees2["BRITONS"],
                                              ensure_ascii=False))
rep5 = AV.apply(proposal, "BRITONS", UNIT, "grant")
files, rel = AV.emit_files(proposal, "BRITONS")
print("     EDIT 5  %s : %s" % (rel, rep5.get("mode", "?")))
row = CT.row_for(proposal["BRITONS"], UNIT, CT.UNIT_USE_TYPES)
print("     the new tree row: %s"
      % {k: row.get(k) for k in ("Node ID", "Name", "Node Status", "Age ID",
                                 "Building ID")})
panel_rep, panel_files = tk._panel_availability("BRITONS", UNIT, "grant",
                                                CT.UNIT_USE_TYPES, proposal)
print("     EDIT 6  panel: %s" % {k: panel_rep.get(k) for k in
                                  ("mode", "ok", "donor", "before_entries",
                                   "after_entries")})
files.update(panel_files)

print()
print("D  emit: one mod carrying the patched .dat AND the JSON overrides")
info = E.make_info(
    TITLE, author="dsh",
    description=TN.description_for(
        VERSION,
        "BOTH halves: .dat (effect on tech 263 + unit 2550 EnablingResearch=263) AND "
        "the tree row + panel entry; villager family HP 1000; unit 8's "
        "EnablingResearch cleared as the negative control",
        "Britons' Barracks, Dark Age",
        extra_lines=[
            "CONTROL A: a villager given a task STAYS at 1000 hp",
            "CONTROL B (negative): Castle Age, British Castle -> if the Longbowman is"
            " GONE, EnablingResearch is load-bearing",
            "TEST C: Barracks, Dark Age -> Champi Scout?",
        ]))
man = E.emit_data_mod(OUT, patched, info, base_dir=GAME, overwrite=True,
                      json_files=files or None)
for root, _dd, fs in os.walk(OUT):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("     %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, OUT)))
print("     changes_dat=%s  json_overrides=%s"
      % (man.get("changes_dat"), man.get("json_overrides")))
print("     dat_is_carrier=%s" % man.get("dat_is_carrier"))

print()
print("DSH TEST V4 READY: %s" % OUT)
print("  Title: %s" % TITLE)
print("  CONTROL A : villager + task -> stays at 1000 hp")
print("  CONTROL B : CASTLE AGE, British CASTLE -> Longbowman present or GONE?")
print("  TEST C    : DARK AGE, British BARRACKS -> Champi Scout?")
