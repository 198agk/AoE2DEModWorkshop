# -*- coding: utf-8 -*-
r"""dsh test v2: add the missing half of the link.

## What v1 established (user m25302)

    A  villagers stay at 1000 even with a task   -> PASS
    B  Castle Age, British Castle -> Longbowman  -> PASS
    C  Dark Age, British Barracks -> Champi Scout-> FAIL

B is the informative one: v1 re-pointed British `tech 263` from effect 251 to a NEW
effect 1500 = `[(2,8,1),(2,2550,1)]`, and the Longbowman still appears.  So the engine
READS and FOLLOWS that effect.  It simply did not act on the appended second command.

## The measured difference between the unit that works and the one that does not

    unit 8    Longbowman     EnablingResearch = 263 (a British tech) + tree row
    unit 2550 Champi Scout   EnablingResearch = -1                 + no tree row

A shipped unit's enable looks like a LINK with two halves:

    1. the unit's `TechTree.UnitConnection.EnablingResearch` names a tech
    2. that tech's effect contains `(type 2, a=that unit, b=1)`

For unit 8 both halves are present and consistent.  v1 only ever supplied half 2 for
unit 2550, which is why nothing happened.

## v2 supplies both

    EDIT 1  effect 1500 = [(2,8,1),(2,2550,1)]; British tech 263 -> effect 1500
            (carried over from v1, where B proved it is read)
    EDIT 2  NEW: patch unit 2550's `EnablingResearch` from -1 to 263
            (an in-place 4-byte patch at offset 93237962 in the BASE stream; the
             offset is derived per-build, never hard-coded)
    EDIT 3  CONTROL A: the whole villager family (27 ids) -> hit_points 1000
    CONTROL B: Castle Age, British Castle -> Longbowman must still be offered

Reading:
    A ok, B ok, C ok    -> the two halves are the mechanism; grants are now possible
    A ok, B ok, C fail  -> `EnablingResearch` is not the missing half either, and the
                          JSON tree layer must be involved after all
    A fail              -> the mod did not load; nothing follows
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
from aoe2mod.mod import emitter as E                       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_dshtest_v2")
TITLE = "%s v2 - Champi Scout for Britons (both halves)" % TN.PREFIX
TECH = 263              # British 'Longbow (make avail)'
OLD_EFFECT = 251
UNIT = 2550
LONGBOW = 8
VILLAGER = 83
HP = 1000
VERSION = 2

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, tail, how = tk._parsed
names = [c["name"] for c in civs]
assert names[1] == "British"


def enabling_offset(raw, gv_, want_unit):
    """Byte offset of `want_unit`'s EnablingResearch i32 in `raw`."""
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
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
        enab = r.i32()
        if uid == want_unit:
            return o, enab
    raise SystemExit("unit %d has no TechTree connection" % want_unit)


print("A  the two halves, measured before the edit")
_o, _before = enabling_offset(data, gv, UNIT)
print("     unit %d EnablingResearch = %d  (at offset %d)" % (UNIT, _before, _o))
assert _before == -1, "expected -1, got %s" % _before
print("     tech %d = %r  civ=%d  effect was %d"
      % (TECH, tk._tech_records()[TECH].get("name"),
         tk._tech_records()[TECH].get("civ"), OLD_EFFECT))

print()
print("B  parse, then apply the three edits")
with contextlib.redirect_stdout(io.StringIO()):
    p = P.Parser(data)
    try:
        p.parse()
    except SystemExit:
        pass
stats = p.stats

# EDIT 1 -- the effect half (carried from v1)
stats["effects"].append({
    "name": "dsh test v2 Longbow + Champi Scout",
    "commands": [(2, LONGBOW, 1, -1, 0.0), (2, UNIT, 1, -1, 0.0)],
    "_new": True,
})
stats["effect_count"] = len(stats["effects"])
new_idx = len(stats["effects"]) - 1
stats["techs"][TECH]["effect_id"] = new_idx
print("     EDIT 1  effect %d = [(2,%d,1),(2,%d,1)]; tech %d -> effect %d"
      % (new_idx, LONGBOW, UNIT, TECH, new_idx))

# EDIT 3 -- control A, through the product's family rule
F.warm({"civs": civs}, game_root=GAME)
family = sorted(F.family_of(F.build_families(civs), VILLAGER))
touched = 0
for c in stats["civs"]:
    for u in c.get("units") or []:
        if u.get("id") in family:
            if u.get("hit_points") != HP:
                touched += 1
            u["hit_points"] = HP
print("     EDIT 3  villager family (%d ids) -> %d ; records set: %d"
      % (len(family), HP, touched))
assert touched == len(family) * len(civs), \
    "expected %d touched, got %d" % (len(family) * len(civs), touched)

print()
print("C  serialise, then apply EDIT 2 as an in-place byte patch")
out, rep = W.serialize_dat(stats, raw=data, gv=gv)
print("     after edits 1+3: %d bytes (base %d, delta %+d)"
      % (len(out), len(data), len(out) - len(data)))
# The TechTree lives in the same stage as the tail, so it may have MOVED relative to
# the base stream.  Re-derive the offset on the SERIALISED bytes, never reuse the
# base offset.
_o2, _v2 = enabling_offset(out, gv, UNIT)
print("     unit %d EnablingResearch at offset %d in the edited stream (was %d)"
      % (UNIT, _o2, _v2))
patched = bytearray(out)
struct.pack_into("<i", patched, _o2, TECH)
patched = bytes(patched)
_diffs = sum(1 for i in range(len(out)) if out[i] != patched[i])
print("     EDIT 2  patched EnablingResearch %d -> %d ; bytes changed: %d"
      % (_v2, TECH, _diffs))
assert _diffs == 4, "the patch must touch exactly 4 bytes, got %d" % _diffs

print()
print("D  re-parse the FINAL artifact with the unmodified parser")
with contextlib.redirect_stdout(io.StringIO()):
    p3 = P.Parser(patched)
    p3.parse()
print("     consumed %d of %d; clean EOF: %s"
      % (p3.r.pos, len(patched), p3.r.pos == len(patched)))
assert p3.r.pos == len(patched)
_o3, _v3 = enabling_offset(patched, gv, UNIT)
print("     unit %d EnablingResearch now = %d" % (UNIT, _v3))
assert _v3 == TECH
# controls
_hp = sorted({u.get("hit_points") for c in p3.stats["civs"]
              for u in (c.get("units") or []) if u.get("id") in family})
print("     villager family hit_points: %s" % _hp)
assert _hp == [HP]
_t = p3.stats["techs"][TECH]
print("     tech %d effect_id now = %s ; effect commands = %s"
      % (TECH, _t.get("effect_id"),
         p3.stats["effects"][new_idx]["commands"]))
assert _t.get("effect_id") == new_idx
# unit 8 must be untouched
_o8, _v8 = enabling_offset(patched, gv, LONGBOW)
print("     control B input: unit %d EnablingResearch = %d (unchanged)" % (LONGBOW, _v8))
assert _v8 == TECH

print()
print("E  emit")
info = E.make_info(
    TITLE, author="dsh",
    description=TN.description_for(
        VERSION,
        "villager HP 1000 (all %d family ids) + Champi Scout for Britons: effect on "
        "tech 263 AND unit 2550's EnablingResearch -> 263" % len(family),
        "Britons' Barracks, Dark Age",
        extra_lines=[
            "CONTROL A: give a villager a task, it must STAY at 1000 hp",
            "CONTROL B: Castle Age, British Castle -> Longbowman still offered",
            "v1 lacked the EnablingResearch half; v2 supplies both halves",
        ]))
man = E.emit_data_mod(OUT, patched, info, base_dir=GAME, overwrite=True)
for root, _d, fs in os.walk(OUT):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("     %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, OUT)))
print("     changes_dat=%s" % man.get("changes_dat"))

print()
print("DSH TEST V2 READY: %s" % OUT)
print("  Title: %s" % TITLE)
print("  CONTROL A : villager given a task stays at 1000 hp")
print("  CONTROL B : CASTLE AGE, British CASTLE -> 长弓兵 still offered")
print("  TEST      : DARK AGE, British BARRACKS -> 蔷琵侦察兵?")
