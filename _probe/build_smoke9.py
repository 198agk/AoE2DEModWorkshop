# -*- coding: utf-8 -*-
r"""smoke9: smoke8 with BOTH of its errors fixed.

## What smoke8 got wrong (user m25056: 「没有蔷琵侦察兵，村民血量 1000失效，靶场没有长弓兵，
长弓兵不是在城堡的吗」)

**Error 1 -- control A was hand-rolled and therefore wrong.**
I set `hit_points` on **unit id 83 alone**.  The engine re-points a villager to another
record in the same FAMILY when you give it a task -- the user found this in the very
first test (「一操作村民去做别的，就恢复25了」).  Measured, the family of 83 is 27 ids:

    56, 57, 83, 118, 120, 122, 123, 124, 156, 212, 214, 216, 218, 220, 222,
    259, 293, 354, 579, 581, 590, 592, 1810, 1891, 1892, 2333, 2334

and the PRODUCT's `unit.stat` compiles to exactly those 27 x 63 = **1,701 edits**.
So control A has to go through `aoe2mod.dat.families`, not through id 83.

**Error 2 -- control B pointed at the wrong building AND the wrong age.**
I told the user to look at the British **Archery Range**.  Measured:

    British unit 8 (Longbowman)  train_locations: [{'unit_id': 82}]   # 82 = Castle
    building 82 = Castle, Age ID 3 (Castle Age)

The Longbowman is a **Castle** unit in the **Castle Age**.  A Dark-Age Archery Range
could never show it, so that control was unreadable from the start.  My mistake.

## smoke9

    EDIT 1  new effect 1500 = [(2, 8, 1), (2, 2550, 1)]
            tech 263's effect_id: 251 -> 1500        (unchanged from smoke8)
    EDIT 2  hit_points = 1000 for the WHOLE family of unit 83, every civ
            (the product's own rule, so the edit count must be 1,701)

    CONTROL A  villagers stay at 1000 even after you give them a task
    CONTROL B  CASTLE AGE, British CASTLE -> the 长弓兵 is still there
    TEST       DARK AGE, British BARRACKS -> 蔷琵侦察兵?
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.families as F                           # noqa: E402
import aoe2mod.dat.locate as L                             # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402
import aoe2mod.dat.writer as W                             # noqa: E402
from aoe2mod.mod import emitter as E                       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_smoke9")
TITLE = "aoe2mod Smoke9 Dat Grant"
TECH = 263
OLD_EFFECT = 251
UNIT = 2550
LONGBOW = 8
VILLAGER = 83
HP = 1000

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, tail, how = tk._parsed
names = [c["name"] for c in civs]

print("A  what the product's own villager rule spans")
F.warm({"civs": civs}, game_root=GAME)
fams = F.build_families(civs)
family = sorted(F.family_of(fams, VILLAGER))
print("     family_of(%d) = %d ids: %s" % (VILLAGER, len(family), family))
plan = tk.plan({"intent": "unit.stat", "unit": "Villager",
                "stat": "hit_points", "value": HP})
print("     the product's plan for 「村民 生命值 =1000」: edit_count=%s"
      % plan.get("edit_count"))
check_expected = len(family) * len(civs)
print("     family x civs = %d x %d = %d  (product said %s)"
      % (len(family), len(civs), check_expected, plan.get("edit_count")))
assert plan.get("edit_count") == check_expected, \
    "the family rule and the product must agree, or one of them moved"

print()
print("B  parse and edit")
with contextlib.redirect_stdout(io.StringIO()):
    p = P.Parser(data)
    try:
        p.parse()
    except SystemExit:
        pass
stats = p.stats

# --- EDIT 2: the control, through the FAMILY (not id 83 alone) --------------
touched = 0
for c in stats["civs"]:
    for u in c.get("units") or []:
        if u.get("id") in family:
            if u.get("hit_points") != HP:
                touched += 1
            u["hit_points"] = HP
print("     villager-family records set to %d: %d" % (HP, touched))
assert touched == check_expected, "touched %d, expected %d" % (touched, check_expected)

# --- EDIT 1: the grant, via a new effect + repointing tech 263 --------------
stats["effects"].append({
    "name": "SMOKE9 Longbow + Champi Scout",
    "commands": [(2, LONGBOW, 1, -1, 0.0), (2, UNIT, 1, -1, 0.0)],
    "_new": True,
})
stats["effect_count"] = len(stats["effects"])
new_idx = len(stats["effects"]) - 1
stats["techs"][TECH]["effect_id"] = new_idx
print("     effect %d appended; tech %d effect_id: %d -> %d"
      % (new_idx, TECH, OLD_EFFECT, new_idx))

print()
print("C  serialise + re-parse")
out, rep = W.serialize_dat(stats, raw=data, gv=gv)
print("     raw %d (base %d, delta %+d); model!=raw %s group(s)"
      % (len(out), len(data), len(out) - len(data),
         rep.get("model_vs_original_mismatches")))
with contextlib.redirect_stdout(io.StringIO()):
    p2 = P.Parser(out)
    p2.parse()
print("     consumed %d of %d; clean EOF: %s"
      % (p2.r.pos, len(out), p2.r.pos == len(out)))
assert p2.r.pos == len(out)

print()
print("D  verify from the ARTIFACT, and prove the control matches the product")
_c2, _cs2, _gv2, tail2 = L.locate(out, parser=p2)
_c = p2.stats["civs"]
# control A
_v = sorted({u.get("hit_points") for ci in _c for u in (ci.get("units") or [])
             if u.get("id") in family})
print("     hit_points across the whole villager family: %s" % _v)
assert _v == [HP], _v
# how many records changed, vs the product's own changed-id set
_braw, _ = P.load_dat(os.path.join(GAME, "resources", "_common", "dat",
                                   "empires2_x2_p1.dat"))
with contextlib.redirect_stdout(io.StringIO()):
    _pb = P.Parser(_braw)
    _pb.parse()
_base_hp = {}
for ci in _pb.stats["civs"]:
    for u in (ci.get("units") or []):
        _base_hp.setdefault(ci["name"], {})[u["id"]] = u.get("hit_points")
changed_ids = set()
for ci in _c:
    for u in (ci.get("units") or []):
        if _base_hp.get(ci["name"], {}).get(u["id"]) != u.get("hit_points"):
            changed_ids.add(u["id"])
print("     ids whose hit_points changed: %d -> %s"
      % (len(changed_ids), sorted(changed_ids)))
assert changed_ids == set(family), \
    "changed ids %s != family %s" % (sorted(changed_ids), family)
print("     ==> the control now matches the product's family rule exactly")
# control B + test
techs2 = L.locate_techs(out, tail2, _gv2)
e_new = next(r for r in L.locate_effects(out)[0]
             if r.get("index") == techs2[TECH].get("effect_id"))
print("     tech %d -> effect %s : %s"
      % (TECH, techs2[TECH].get("effect_id"),
         [(c.get("type"), c.get("a"), c.get("b")) for c in e_new["commands"]]))
assert sorted(c.get("a") for c in e_new["commands"]) == sorted([LONGBOW, UNIT])

print()
print("E  emit")
info = E.make_info(TITLE, author="aoe2mod",
                   description="SMOKE9: dat-only grant + villager-family control "
                               "(%d ids) + Longbow control" % len(family))
man = E.emit_data_mod(OUT, out, info, base_dir=GAME, overwrite=True)
for root, _d, fs in os.walk(OUT):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("     %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, OUT)))

print()
print("SMOKE9 READY: %s" % OUT)
print("  CONTROL A : give a villager a task -- it must STAY at 1000 hit points")
print("  CONTROL B : CASTLE AGE, British CASTLE -> 长弓兵 still offered")
print("  TEST      : DARK AGE, British BARRACKS -> 蔷琵侦察兵?")
