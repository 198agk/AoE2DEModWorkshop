# -*- coding: utf-8 -*-
r"""dsh test v3: v2 PLUS a negative control that predicts the answer in the same run.

## What v1 taught (user m25302: A pass, B pass, C fail)

B is the informative one: v1 re-pointed British `tech 263` to a NEW effect
`[(2,8,1),(2,2550,1)]` and the **Longbowman survived**.  So the engine reads that
effect and follows its FIRST command.  It did nothing with the appended second one.

## The two mechanisms, and why v2 alone cannot separate them

    1  the effect command `(type 2, a=unit, b=1)` on a civ-owned tech
    2  the unit's own `EnablingResearch` naming that tech

For unit 8 both are present, so v1/v2 cannot tell which one the engine obeyed.
v2 supplies BOTH for unit 2550 -- but if C still fails, that only rules out "both
together are enough"; it does not say which link is load-bearing, and it leaves open
that the TREE ROW is required (which the clean 2026-10-15 test suggested does not work
through a mod anyway).

## v3 adds a negative control that resolves it

    EDIT 4  CLEAR unit 8's `EnablingResearch` (-1)

The Longbowman then keeps its effect command (`tech 263 -> effect -> (2,8,1)`) but
loses its unit-side link.  Reading it against the other two observations:

    Longbowman DISAPPEARS  -> `EnablingResearch` IS load-bearing, so v2's second half
                              is the right field, and C should pass
    Longbowman STAYS       -> the effect command alone is enough for unit 8, which
                              contradicts v1's C failure... UNLESS unit 8 has a path
                              2550 lacks.  The one measured difference left is the
                              TREE ROW: unit 8 has one in the British tree, 2550 does
                              not.  That would make the JSON tree layer load-bearing
                              after all.

Either way the run is decisive, and it costs the user nothing extra: same match, same
three observations, one added line in the reading.
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
OUT = os.path.join(HERE, "out_dshtest_v3")
TITLE = "%s v3 - Champi Scout + EnablingResearch control" % TN.PREFIX
TECH = 263
OLD_EFFECT = 251
UNIT = 2550
LONGBOW = 8
VILLAGER = 83
HP = 1000
VERSION = 3

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, tail, how = tk._parsed
names = [c["name"] for c in civs]
assert names[1] == "British"


def enabling(pr, raw, gv_, want):
    """The `EnablingResearch` of `want`, and its byte offset."""
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
    raise SystemExit("unit %d has no connection" % want)


with contextlib.redirect_stdout(io.StringIO()):
    _p = P.Parser(data)
    _p.parse()

print("A  the fields we are going to touch, before any edit")
_o2550, _v2550 = enabling(_p, data, gv, UNIT)
_o8, _v8 = enabling(_p, data, gv, LONGBOW)
print("     unit %-5s EnablingResearch = %-6s (offset %d)" % (UNIT, _v2550, _o2550))
print("     unit %-5s EnablingResearch = %-6s (offset %d)" % (LONGBOW, _v8, _o8))
assert _v2550 == -1 and _v8 == TECH
print("     tech %d = %r civ=%d"
      % (TECH, tk._tech_records()[TECH].get("name"),
         tk._tech_records()[TECH].get("civ")))

print()
print("B  the model edits (effect + villager family)")
stats = _p.stats
stats["effects"].append({
    "name": "dsh test v3 Longbow + Champi Scout",
    "commands": [(2, LONGBOW, 1, -1, 0.0), (2, UNIT, 1, -1, 0.0)],
    "_new": True,
})
stats["effect_count"] = len(stats["effects"])
new_idx = len(stats["effects"]) - 1
stats["techs"][TECH]["effect_id"] = new_idx
print("     EDIT 1  effect %d = [(2,%d,1),(2,%d,1)]; tech %d -> effect %d"
      % (new_idx, LONGBOW, UNIT, TECH, new_idx))
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
assert touched == len(family) * len(civs)

print()
print("C  serialise, then the two in-place byte patches")
out, rep = W.serialize_dat(stats, raw=data, gv=gv)
print("     after model edits: %d bytes (base %d, delta %+d)"
      % (len(out), len(data), len(out) - len(data)))
with contextlib.redirect_stdout(io.StringIO()):
    _p2 = P.Parser(out)
    _p2.parse()
# Offsets MUST be re-derived on the serialised stream -- adding an effect moves the
# tail, so a base-stream offset would silently patch the wrong bytes.
_o2550b, _v2550b = enabling(_p2, out, gv, UNIT)
_o8b, _v8b = enabling(_p2, out, gv, LONGBOW)
print("     offsets moved: unit %d %d -> %d ; unit %d %d -> %d"
      % (UNIT, _o2550, _o2550b, LONGBOW, _o8, _o8b))
patched = bytearray(out)
struct.pack_into("<i", patched, _o2550b, TECH)      # EDIT 2: give 2550 a link
struct.pack_into("<i", patched, _o8b, -1)           # EDIT 4: clear unit 8's link
patched = bytes(patched)
_diff = [i for i in range(len(out)) if out[i] != patched[i]]
print("     EDIT 2+4 bytes changed: %d at %s" % (len(_diff), _diff))
assert len(_diff) == 8, "expected 2 x 4 bytes, got %d: %s" % (len(_diff), _diff)

print()
print("D  re-parse the FINAL artifact and confirm every edit")
with contextlib.redirect_stdout(io.StringIO()):
    _p3 = P.Parser(patched)
    _p3.parse()
print("     consumed %d of %d; clean EOF: %s"
      % (_p3.r.pos, len(patched), _p3.r.pos == len(patched)))
assert _p3.r.pos == len(patched)
_, _n2550 = enabling(_p3, patched, gv, UNIT)
_, _n8 = enabling(_p3, patched, gv, LONGBOW)
print("     unit %d EnablingResearch: %s -> %s" % (UNIT, _v2550, _n2550))
print("     unit %d EnablingResearch: %s -> %s  (negative control)"
      % (LONGBOW, _v8, _n8))
assert _n2550 == TECH and _n8 == -1
_hp = sorted({u.get("hit_points") for c in _p3.stats["civs"]
              for u in (c.get("units") or []) if u.get("id") in family})
print("     villager family hit_points: %s" % _hp)
assert _hp == [HP]
print("     tech %d effect %s commands %s"
      % (TECH, _p3.stats["techs"][TECH]["effect_id"],
         _p3.stats["effects"][new_idx]["commands"]))

print()
print("E  emit")
info = E.make_info(
    TITLE, author="dsh",
    description=TN.description_for(
        VERSION,
        "villager HP 1000 (all %d family ids) + Champi Scout for Britons via BOTH "
        "halves; unit 8's EnablingResearch CLEARED as a control" % len(family),
        "Britons' Barracks, Dark Age",
        extra_lines=[
            "CONTROL A: a villager given a task STAYS at 1000 hp",
            "CONTROL B (negative): Castle Age, British Castle -> if the Longbowman"
            " is GONE, EnablingResearch is load-bearing",
            "TEST C: Barracks, Dark Age -> Champi Scout?",
        ]))
man = E.emit_data_mod(OUT, patched, info, base_dir=GAME, overwrite=True)
for root, _d, fs in os.walk(OUT):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("     %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, OUT)))

print()
print("DSH TEST V3 READY: %s" % OUT)
print("  Title: %s" % TITLE)
print("  CONTROL A : villager + task -> stays at 1000 hp")
print("  CONTROL B : CASTLE AGE, British CASTLE -> Longbowman present or GONE?")
print("  TEST C    : DARK AGE, British BARRACKS -> Champi Scout?")
print()
print("  READING (B is the mechanism probe):")
print("    B GONE + C present -> EnablingResearch is the gate and both halves grant")
print("    B GONE + C absent  -> EnablingResearch is the gate but the effect half is")
print("                          not how a grant is delivered")
print("    B PRESENT + C present -> the effect command alone suffices (v1's C failure")
print("                          then means something else distinguished 2550)")
print("    B PRESENT + C absent  -> the effect command is not enough AND")
print("                          EnablingResearch is not read: the TREE ROW is the")
print("                          remaining candidate")
