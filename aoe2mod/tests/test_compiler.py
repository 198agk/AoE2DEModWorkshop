# -*- coding: utf-8 -*-
"""End-to-end smoke of the product compiler using the product package only."""
import contextlib
import io
import os
import sys

# .../aoe2mod/tests/test_compiler.py -> the workspace root that holds aoe2mod
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root not in sys.path:
    sys.path.insert(0, root)

from aoe2mod.intent import compiler as C          # noqa: E402
from aoe2mod.dat import parser as P               # noqa: E402
from aoe2mod.dat import locate as L               # noqa: E402
from aoe2mod import api as A                      # noqa: E402

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

data, how = P.load_dat(BASE)
print("loaded", len(data), "bytes via", how)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
civs, civs_start, gv, tail = L.locate(data, parser=p)
print("locate: %d civs, gv=%s, tail=0x%X" % (len(civs), gv, tail))
parsed = (data, civs, civs_start, gv, tail, how)
STATS = p.stats                      # age-variant families are read from here
tk = A.open_toolkit()                # the plan() preview path, same install
BIND = C.load_schema()               # (intents, dat_bindings)


def run(label, intent, expect_ok=True):
    print("\n=== %s ===" % label)
    print("intent:", intent)
    try:
        rep = C.compile_intent(BASE, intent, parsed=parsed, stats=STATS)
    except C.IntentError as exc:
        print("IntentError:", exc)
        assert not expect_ok, "expected this intent to compile"
        return None
    v = rep["verification"]
    print("resolved   :", rep["resolved"])
    print("entity id  :", rep["entity_id"])
    print("civs edited:", rep["civs_edited"], "edits:", len(rep["edits"]))
    print("first edit :", rep["edits"][0] if rep["edits"] else None)
    print("verify ok  :", v["ok"], "| changed", v["changed_bytes"],
          "claimed", v["claimed_bytes"], "| leftover", v["leftover"],
          "| unexpected", len(v["unexpected_changes"]))
    if v["problems"]:
        for pr in v["problems"]:
            print("  PROBLEM:", pr)
    assert expect_ok, "expected this intent to fail"
    assert v["ok"], "verification failed"
    return rep


r1 = run("archer attack +2", {
    "intent": "unit.stat", "unit": "Archer",
    "stat": "displayed_attack", "delta": 2})

r2 = run("knight hp +50", {
    "intent": "unit.stat", "unit": "Knight",
    "stat": "hit_points", "delta": 50})

r3 = run("militia speed -0.1 (float)", {
    "intent": "unit.stat", "unit": "Militia",
    "stat": "movement_speed", "delta": -0.1})

r4 = run("archer LOS = 10", {
    "intent": "unit.stat", "unit": "Archer",
    "stat": "line_of_sight", "value": 10})

# --- refusals: these must be user-facing, not crashes ----------------------
run("ambiguity must be reported", {
    "intent": "unit.stat", "unit": "弓手",
    "stat": "displayed_attack", "delta": 1}, expect_ok=False)

run("overflow must be refused", {
    "intent": "unit.stat", "unit": "Archer",
    "stat": "hit_points", "delta": 40000}, expect_ok=False)

run("unknown stat must be listed", {
    "intent": "unit.stat", "unit": "Archer",
    "stat": "wingspan", "delta": 1}, expect_ok=False)

run("both delta and value must be refused", {
    "intent": "unit.stat", "unit": "Archer",
    "stat": "displayed_attack", "delta": 1, "value": 9}, expect_ok=False)

run("a unit type without an attack field", {
    "intent": "unit.stat", "unit": "河鲈",
    "stat": "displayed_attack", "delta": 1}, expect_ok=False)

run("a name shared by several buildings is ambiguous", {
    "intent": "unit.stat", "unit": "Barracks",
    "stat": "displayed_attack", "delta": 1}, expect_ok=False)

# --- civ scope -------------------------------------------------------------
r5 = run("archer attack +1, Goths only", {
    "intent": "unit.stat", "unit": "Archer",
    "stat": "displayed_attack", "delta": 1, "civs": ["Goths"]})
if r5:
    assert r5["civs_edited"] == 1, r5["civs_edited"]

# --- the other two schema intents -----------------------------------------
r6 = run("knight base attack +3 (raw class 3/4)", {
    "intent": "unit.attack_class", "unit": "Knight",
    "kind": "attack", "delta": 3})
# The label must name the field ("基础攻击"), not the armour-class id it is
# stored in: "attack cls 3" is a locator detail, and the same walker feeds the
# panel-facing armour intents.  Mirrored slots keep their "(mirror)" marker, so
# strip it before comparing.
def _bare(edit):
    return edit.where.split(" ", 2)[-1].replace(" (mirror)", "")


if r6:
    _w = {_bare(e) for e in r6["edits"]}
    assert _w == {"基础攻击", "攻击力"}, _w
r7 = run("knight base melee armour +2", {
    "intent": "unit.attack_class", "unit": "Knight",
    "kind": "armour", "delta": 2})
if r7:
    _w7 = {_bare(e) for e in r7["edits"]}
    assert _w7 == {"基础护甲", "近战护甲"}, _w7
# --- the FORWARD mirror path, which the five-place walker fix missed --------
# A `mirror` dict is a TRIMMED binding: it names the raw slot but carries no
# label, so reading the label off it yields the locator's wording.  "armour
# cls 4" reached Edit.where on every displayed_melee_armour edit even after
# every walker branch used b["label"] -- because the label is not read from the
# OUTER binding on this path at all.  Sweep every displayed_* field.
import re as _re
_RAW_LABEL = _re.compile(r"(cost type\s*\d+|attack cls\s*\d+|armour cls\s*\d+|"
                         r"max_range|reload_time|hit_points|location\[)")
for _stat in ("displayed_attack", "displayed_melee_armour",
              "displayed_pierce_armour", "displayed_range",
              "displayed_reload_time"):
    _rn = run("%s +1 (forward mirror label)" % _stat, {
        "intent": "unit.stat", "unit": "Knight", "stat": _stat, "delta": 1})
    if _rn:
        for _e in _rn["edits"]:
            _lab = _e.where.split(" ", 2)[-1]
            assert not _RAW_LABEL.search(_lab), (_stat, _e.where)
        # The mirror must still be there -- a fix that simply stopped emitting
        # it would pass the leak check while breaking the sync it exists for.
        assert any("(mirror)" in _e.where for _e in _rn["edits"]), _stat

# --- the schema must be COMPLETE, so those fallbacks never fire -------------
# Every walker branch now reads b["label"] and falls back to a literal only when
# the schema entry omits one.  That fallback is a safety net, not a plan: if any
# entry it can reach lacks a label, the net becomes the normal path and the user
# reads locator vocabulary again.  Assert the schema, not the net.
_i, _b = C.load_schema()
_labeled = []
for _tname in ("unit_fields", "attack_classes", "tech_fields"):
    for _k, _v in (_b.get(_tname) or {}).items():
        if not isinstance(_v, dict) or "source" not in _v:
            continue                      # $comment and other prose keys
        _labeled.append((_tname, _k, bool(_v.get("label"))))
_unlabeled = [x for x in _labeled if not x[2]]
assert not _unlabeled, "schema bindings with no label: %s" % (_unlabeled,)
# The inline `mirror` dicts are the trimmed bindings that caused the leak, so
# each one needs a usable label from ONE of two sources: an owning schema entry
# (matched by selector) or the outer binding it hangs off.  Asserting that every
# mirror resolves to an OWNER would be over-specification: displayed_pierce_
# armour deliberately tracks class 3 first (candidates [3,4]) while the only
# armour entry is [4,3], so no entry owns that selector and the outer label
# 远程护甲 is the correct answer.  What must never happen is BOTH being absent,
# which would put locator vocabulary back in front of the user.
_mirrors = [(k, v["mirror"], v.get("label"))
            for k, v in (_b.get("unit_fields") or {}).items()
            if isinstance(v, dict) and v.get("mirror")]
assert _mirrors, "expected inline mirror links in unit_fields"
_unresolved = [(k, _m.get("source")) for k, _m, _l in _mirrors
               if not (C._label_for_mirror(_b, _m) or _l)]
assert not _unresolved, "mirrors with no label from any source: %s" % (_unresolved,)
print("schema labels: %d bindings all labelled | %d mirror links all labelled"
      % (len(_labeled), len(_mirrors)))
r8 = run("archer wood cost -5", {
    "intent": "unit.cost", "unit": "Archer",
    "resource": "wood", "delta": -5})
# Same rule as the tech cost above, on the OTHER path: each Edit carries
# "unit[4] 成本 wood", never the raw slot type.  This leaked for every unit cost
# edit because the preview sentence is built from `resolved.resource` instead of
# the walker's label, so a test that only read plan() saw nothing wrong.
if r8:
    _w8 = {_bare(e) for e in r8["edits"]}
    assert _w8 == {"成本 wood"}, _w8
r9 = run("exploding cost of a unit with no gold is refused", {
    "intent": "unit.cost", "unit": "河鲈",
    "resource": "gold", "delta": 5}, expect_ok=False)
run("an unknown resource is refused", {
    "intent": "unit.cost", "unit": "Archer",
    "resource": "bananas", "delta": 5}, expect_ok=False)

# --- the tech path: a GLOBAL record, one per tech id, never per civ --------
rt = run("loom research time +25 (tech, addressed by NAME)", {
    "intent": "tech.research_time", "tech": "Loom", "delta": 25})
assert rt is not None
assert rt["civs_edited"] == 0, rt["civs_edited"]     # a tech has no per-civ copies
# The label names the field ("研究时间[0]"), not the locator's raw key: this
# walker feeds Edit.where straight into the UI's change list.
assert all("研究时间" in e.where for e in rt["edits"]), rt["edits"][0].where
assert not any("location[" in e.where for e in rt["edits"]), rt["edits"][0].where

# 14 techs carry more than one research location and EVERY copy must move, or
# the game sees two different research times for the same technology.
rmulti = run("crop rotation research time +10 (two research locations)", {
    "intent": "tech.research_time", "tech": 12, "delta": 10})
assert rmulti is not None and rmulti["edit_count"] == 2, rmulti["edit_count"]

run("an unknown tech name must list candidates, not traceback", {
    "intent": "tech.research_time", "tech": "no such tech", "delta": 5},
    expect_ok=False)
run("an out-of-range tech index is refused", {
    "intent": "tech.research_time", "tech": 999999, "delta": 5},
    expect_ok=False)
run("tech overflow must be refused too", {
    "intent": "tech.research_time", "tech": "Loom", "delta": 40000},
    expect_ok=False)

# an integer tech id must resolve -- api.search() hands out numbers
rt2 = run("loom research time set to 7 (tech, addressed by ID)", {
    "intent": "tech.research_time", "tech": 22, "value": 7})
assert rt2 is not None and rt2["entity_id"] == 22, rt2["entity_id"]

# --- tech costs: 3 fixed slots, selected by TYPE and not by position --------
# Loom costs 50 GOLD, and the gold lives in slot 0 -- so a selector that trusts
# slot order writes to the wrong number.  The locator records all three.
rc = run("loom gold cost -20 (tech, the value is NOT in the first slot)", {
    "intent": "tech.cost", "tech": "Loom", "resource": "gold", "delta": -20})
assert rc is not None, "tech.cost must compile"
assert rc["civs_edited"] == 0, rc["civs_edited"]      # global record, no civ copies
_e = rc["edits"][0]
assert (_e.before, _e.after) == (50, 30), (_e.before, _e.after)
assert _e.where.startswith("tech[22] 成本 gold"), _e.where
# The label must name the resource, never the raw slot type id: "cost type 3"
# tells a player nothing about the gold they are about to spend.
assert "cost type" not in _e.where, _e.where
assert "type 3" not in _e.where, _e.where
assert (rc.get("verification") or {}).get("leftover") == 0

# Crop rotation is 250 food + 250 wood: editing wood must leave food alone.
rc2 = run("crop rotation wood cost +50 (two-resource tech)", {
    "intent": "tech.cost", "tech": 12, "resource": "wood", "delta": 50})
assert rc2 is not None and rc2["edits"][0].before == 250, rc2["edits"][0].before

run("a resource the tech does not cost is reported, not skipped", {
    "intent": "tech.cost", "tech": "Loom", "resource": "stone", "delta": 10},
    expect_ok=False)

# --- NEGATIVE costs are not discounts --------------------------------------
# -75 fits in an i16 and passed the overflow check, so it used to be written as
# if it were a cheaper unit.  The engine reads a cost as a requirement.
run("a tech cost cannot go negative", {
    "intent": "tech.cost", "tech": "Loom", "resource": "gold", "value": -10},
    expect_ok=False)
run("a unit cost cannot go negative either", {
    "intent": "unit.cost", "unit": "Archer", "resource": "wood", "delta": -100},
    expect_ok=False)
rneg = run("but a discount that stays positive is still fine", {
    "intent": "unit.cost", "unit": "Archer", "resource": "wood", "delta": -5})
assert rneg is not None and rneg["edits"][0].after == 20, rneg["edits"][0].after

# --- DISPLAYED vs RAW: the panel number and the damage number --------------
# AoE2 stores several unit properties TWICE: once as the number the unit panel
# renders (DisplayedAttack / DisplayedMeleeArmour / DisplayedPierceArmour) and
# once as the number the damage maths reads (the attacks[]/armors[] entry for
# class 3 or 4).  Editing only one produces a record the game never ships: the
# panel would show 10 while the arrow still hits for 4.  Both directions must
# move both numbers.
_ma = run("archer displayed_attack +6 (mirrors the raw class-3 entry)", {
    "intent": "unit.stat", "unit": "Archer", "stat": "displayed_attack", "delta": 6})
assert _ma is not None and _ma["edit_count"] == 126, _ma["edit_count"]
_disp = {e.off for e in _ma["edits"] if "(mirror)" not in e.where}
_mir = {e.off for e in _ma["edits"] if "(mirror)" in e.where}
assert len(_disp) == 63 and len(_mir) == 63, (len(_disp), len(_mir))
print("mirror: %d displayed + %d raw slots" % (len(_disp), len(_mir)))

# The mirror must carry the DELTA, never copy the displayed value.  20 of the
# 779 comparable units deliberately store two different numbers (id 1113 shows
# 8 and hits for 6); copying would erase that offset.
_dv = run("a divergent record keeps its offset (id 1113, disp 8 / raw 6)", {
    "intent": "unit.stat", "unit": 1113, "stat": "displayed_attack", "delta": 2})
assert _dv is not None, "the divergent unit must still compile"
_pairs = {(e.before, e.after) for e in _dv["edits"]}
assert (8, 10) in _pairs, sorted(_pairs)[:6]      # the panel number
assert (6, 8) in _pairs, sorted(_pairs)[:6]       # the damage number, +2 not +6

# The REVERSE direction: editing the raw entry has to move the panel number.
_ar = run("archer class-3 attack +2 (mirrors displayed_attack)", {
    "intent": "unit.attack_class", "unit": "Archer", "class_id": 3,
    "kind": "attack", "delta": 2})
assert _ar is not None and _ar["edit_count"] == 126, _ar["edit_count"]

# Armour routing is class-dependent: raw class 4 is the MELEE panel number and
# raw class 3 the PIERCE one, so each must find its own displayed field.  Assert
# on the resolved OFFSETS rather than on label text, so the check survives any
# future wording change.
_mil = None
for _c in civs:
    for _u in _c["units"]:
        if _u["id"] == 74:
            _mil = _u
            break
    if _mil is not None:
        break
assert _mil is not None, "Militia id 74 must exist"
for _cls, _field, _other in ((4, "displayed_melee_armour", "displayed_pierce_armour"),
                             (3, "displayed_pierce_armour", "displayed_melee_armour")):
    _am = run("militia armour class %d +1 -> %s" % (_cls, _field), {
        "intent": "unit.attack_class", "unit": "Militia", "class_id": _cls,
        "kind": "armour", "delta": 1})
    assert _am is not None and _am["edit_count"] == 126, _am["edit_count"]
    _exp = {o for o, _, _, _ in
            C._primary_targets_for_unit(_mil, BIND[1]["unit_fields"][_field])}
    _other_exp = {o for o, _, _, _ in
                  C._primary_targets_for_unit(_mil, BIND[1]["unit_fields"][_other])}
    _got = {e.off for e in _am["edits"]}
    assert _exp and _exp <= _got, (_cls, _field, _exp, sorted(_got)[:6])
    assert not (_other_exp & _got), "class %d also moved %s" % (_cls, _other)
    print("armour cls %d -> %s at %s" % (_cls, _field, sorted(_exp)))

# ...and plan() must agree with the build on the mirrored count, or the preview
# understates the change by half.
for _intent in ({"intent": "unit.stat", "unit": "Archer",
                 "stat": "displayed_attack", "delta": 6},
                {"intent": "unit.attack_class", "unit": "Archer", "class_id": 3,
                 "kind": "attack", "delta": 6}):
    _pl = tk.plan(dict(_intent))
    _bx = C.compile_intent(BASE, dict(_intent), parsed=parsed, stats=STATS)
    assert _pl["edit_count"] == _bx["edit_count"], (_pl["edit_count"],
                                                    _bx["edit_count"])
    assert _pl.get("mirror_count") == 63, _pl.get("mirror_count")

# --- RANGE and RELOAD: the first float32 fields, and the last two mirrors ---
# Same double-storage as attack and armour, but these are float32, so the whole
# intent can carry a fraction.  reload_time is SECONDS BETWEEN ATTACKS: a
# SMALLER number is a faster unit, so "attacks faster" is a NEGATIVE delta and
# the sign guard must not mistake it for an illegal value.
_rng = run("archer range +1 (float32, mirrors the panel range)", {
    "intent": "unit.stat", "unit": "Archer", "stat": "max_range", "delta": 1})
assert _rng is not None and _rng["edit_count"] == 126, _rng["edit_count"]
_rdisp = {e.off for e in _rng["edits"] if "(mirror)" not in e.where}
_rmir = {e.off for e in _rng["edits"] if "(mirror)" in e.where}
assert len(_rdisp) == 63 and len(_rmir) == 63, (len(_rdisp), len(_rmir))
assert all(e.kind == "float" for e in _rng["edits"]), "range is float32"
print("range mirror: %d engine + %d panel slots" % (len(_rdisp), len(_rmir)))

# A fractional delta must survive the round trip intact: 4.0 -> 4.5, not 4.
_rf = run("archer range +0.5 (a fraction, not a rounded int)", {
    "intent": "unit.stat", "unit": "Archer", "stat": "max_range", "delta": 0.5})
assert _rf is not None, "a fractional delta is legal on a float field"
assert {e.after for e in _rf["edits"]} == {4.5}, sorted({e.after for e in _rf["edits"]})

# Faster attacks are a DECREASE.  2.0 -> 1.5 must compile.
_rl = run("archer reload -0.5 (a faster unit is a SMALLER number)", {
    "intent": "unit.stat", "unit": "Archer", "stat": "reload_time", "delta": -0.5})
assert _rl is not None and _rl["edit_count"] == 126, _rl["edit_count"]
assert {e.after for e in _rl["edits"]} == {1.5}, sorted({e.after for e in _rl["edits"]})

# ...but a reload that would go negative is not "even faster", it is a broken
# record the engine will read as garbage.  The schema's `non_negative` flag is
# what decides this, and it has to apply to float32 exactly as it does to i16.
run("range cannot go negative", {
    "intent": "unit.stat", "unit": "Archer", "stat": "max_range", "delta": -100},
    expect_ok=False)
run("reload cannot go negative", {
    "intent": "unit.stat", "unit": "Archer", "stat": "reload_time", "value": -1},
    expect_ok=False)

# A zero range is NOT illegal -- every melee unit in the game has one (1039
# records in BASE), so a guard that rejected zero would break the infantry.
_rz = run("archer range set to 0 (legal, and every melee unit stores one)", {
    "intent": "unit.stat", "unit": "Archer", "stat": "max_range", "value": 0})
assert _rz is not None and {e.after for e in _rz["edits"]} == {0}, "zero range is legal"

# The user-facing wording must come from the schema, never from the locator's
# key: "步弓手 max_range +1" is what a player would see without the label.
for _stat, _label in (("max_range", "射程"), ("reload_time", "装填时间"),
                      ("hit_points", "生命值"), ("displayed_attack", "攻击力"),
                      ("min_range", "最小射程"), ("accuracy", "命中率"),
                      ("garrison_capacity", "驻扎容量")):
    _d = tk.plan({"intent": "unit.stat", "unit": "Archer",
                  "stat": _stat, "delta": 1})["description"]
    assert _label in _d, (_stat, _d)
    assert _stat not in _d, "the raw stat key leaked into %r" % _d
    print("  reads:", _d)

# min_range and accuracy are BOTH float-or-int fields on the same type50 block
# and neither existed until this round.  Guard the two properties that made them
# worth binding: min_range refuses a negative (it is a distance), accuracy does
# NOT (the format stores a plain i16 and clamping would invent a rule).
_mn = run("trebuchet min_range -> 2.0 (a real dead zone, fraction allowed)", {
    "intent": "unit.stat", "unit": 42, "stat": "min_range", "value": 2.0})
assert _mn is not None and {e.after for e in _mn["edits"]} == {2.0}, "min_range write"
# expect_ok=False: `run()` asserts success by default, so a refusal has to be
# declared or the helper itself reports the failure.
_mnneg = run("negative min_range must be refused", {
    "intent": "unit.stat", "unit": 42, "stat": "min_range", "value": -1.0},
    expect_ok=False)
assert _mnneg is None, "a negative minimum range was accepted"
print("  min_range negative is refused by the schema's non_negative flag")

_ac = run("archer accuracy 80 -> 65 (a whole percent, no sign guard)", {
    "intent": "unit.stat", "unit": 4, "stat": "accuracy", "value": 65})
assert _ac is not None and {e.after for e in _ac["edits"]} == {65}, "accuracy write"
# 80 -> 65 and not 80 -> 80: writing back the value that is already there would
# claim 63 edits while changing zero bytes, so it would pass while proving
# nothing about the write path.
assert {e.before for e in _ac["edits"]} == {80}, "the archer baseline moved"
print("  accuracy and min_range are both writable on a combatant")

# garrison_capacity is the ONLY unsigned field in the schema, and it is the one
# that proves the `signed` flag is read at all.  Before it, every write path
# hard-coded signed=True: correct only because all six int fields happened to be
# signed.  Writing 200 into one signed byte raises OverflowError, so this case
# fails loudly rather than silently if the flag stops being honoured.
_gc = run("barracks garrison_capacity 10 -> 200 (a uint8, the only unsigned field)", {
    "intent": "unit.stat", "unit": 12, "stat": "garrison_capacity", "value": 200})
assert _gc is not None, "garrison_capacity write"
# The Edit has to carry the signedness forward, or the emitter would pack it
# differently from the compiler and the byte on disk would disagree with the
# value the compiler reported.
assert all(e.signed is False for e in _gc["edits"]), "an Edit lost its signedness"
assert {e.before for e in _gc["edits"]} == {10}, "the barracks baseline moved"
assert {e.after for e in _gc["edits"]} == {200}, "garrison_capacity after"
# The byte really landed: 200 is 0xC8, packed through the same apply_edits the
# product emitter uses -- not a second copy of the packing rule.
_gcbytes = C.apply_edits(data, _gc["edits"])
assert {_gcbytes[e.off] for e in _gc["edits"]} == {200}, "the unsigned byte on disk"
assert {data[e.off] for e in _gc["edits"]} == {10}, "the base stream was mutated"
print("  %d records, all unsigned, 10 -> 200 (byte on disk 0x%02X)"
      % (len(_gc["edits"]), _gcbytes[_gc["edits"][0].off]))

# 256 does not fit a byte, and the refusal must say WHICH byte rather than
# reusing the 16-bit wording that every other field gets.
_gcbig = run("garrison_capacity 256 must be refused by the 8-bit unsigned bound", {
    "intent": "unit.stat", "unit": 12, "stat": "garrison_capacity", "value": 256},
    expect_ok=False)
assert _gcbig is None, "a 256-byte garrison was accepted"
print("  the 8-bit unsigned bound is enforced, not the 16-bit one")

# --- VARIANTS: one visible object is several records ------------------------#
# Two distinct mechanisms, one rule.
#
# (a) AGE VARIANTS.  "Barracks" is four .dat records (12 Dark, 498 Feudal,
#     132 Castle, 20 Imperial) and the engine REPLACES the whole record when
#     the player advances an age (effect command type 3).  Editing only id 12
#     produced a mod that worked in Dark Age and silently stopped applying at
#     Feudal.
# (b) TASK-SWAP VARIANTS.  "Villager (Male)" (83) is repointed at Builder (118),
#     Lumberjack (123), Farmer (259) ... the moment the player assigns a job.
#     Editing only id 83 produced a villager that showed 2500/2500 while idle
#     and 25/25 as soon as it was sent to build -- verified in-game.
#
# Every variant must move in both cases.
rb = run("barracks hp +100 (a building with 4 age variants)", {
    "intent": "unit.stat", "unit": 12, "stat": "hit_points", "delta": 100})
assert rb is not None, "the barracks edit must compile"
assert rb["edit_count"] == 252, rb["edit_count"]           # 63 civs x 4 ages
_offsets = {e.off for e in rb["edits"]}
assert len(_offsets) == 252, "two ages wrote the same byte"
print("barracks: %d edits across the 4 age records" % rb["edit_count"])

# The family must be reported, not silently applied: the user is entitled to
# know that "make the barracks tougher" touches four records.
bp = tk.plan({"intent": "unit.stat", "unit": 12, "stat": "hit_points", "delta": 100})
assert sorted(bp.get("variants") or []) == [20, 132, 498], bp.get("variants")
assert bp["edit_count"] == 252, bp["edit_count"]
assert bp.get("unit_ids") == [12, 20, 132, 498], bp.get("unit_ids")
# An age family carries no task-swap group at all, so the key is ABSENT rather
# than 0 -- "this is not a job basket" and "this basket is group 0" are
# different statements and the UI must not have to guess which it got.
assert not bp.get("task_swap_groups"), bp.get("task_swap_groups")
hbp = tk.plan({"intent": "unit.stat", "unit": 70, "stat": "hit_points",
               "delta": 100})
assert sorted(hbp.get("variants") or []) == [191, 192, 463, 464, 465], \
    hbp.get("variants")
assert hbp["edit_count"] == 378, hbp["edit_count"]        # 63 civs x 6 ages

# ...and a lone unit must NOT be dragged into some family.
ra = run("archer hp +5 (no age variants)", {
    "intent": "unit.stat", "unit": "Archer", "stat": "hit_points", "delta": 5})
assert ra is not None and ra["edit_count"] == 63, ra["edit_count"]
ap = tk.plan({"intent": "unit.stat", "unit": "Archer", "stat": "hit_points",
              "delta": 5})
assert not ap.get("variants"), ap.get("variants")

# (b) THE TASK-SWAP BASKETS, BOTH OF THEM.  "Villager" is 27 records across all
# 63 civs, and the engine swaps the live object between them twice over: the
# TaskSwapGroup (1 = male jobs, 2 = female jobs) when the player retasks him, and
# the declared sex swap in objreplacement.json (83 <-> 293, chance 50) when the
# unit is created.  Writing only id 83 is the bug the in-game test found; writing
# only TaskSwapGroup 1 is the same bug one level down, because a villager that
# spawns female is record 293.
_vp = tk.plan({"intent": "unit.stat", "unit": 83, "stat": "hit_points",
               "delta": 100})
assert _vp["task_swap_groups"] == [1, 2], _vp.get("task_swap_groups")
assert _vp["edit_count"] == 1701, _vp["edit_count"]        # 63 civs x 27 records
assert sorted(_vp.get("unit_ids") or []) == [
    56, 57, 83, 118, 120, 122, 123, 124, 156, 212, 214, 216, 218, 220, 222, 259,
    293, 354, 579, 581, 590, 592, 1810, 1891, 1892, 2333, 2334], _vp.get("unit_ids")
# ...and every one of those records must really move.
_vb = run("villager hp +100 covers every job AND both sexes", {
    "intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 100})
assert _vb is not None and _vb["edit_count"] == 1701, _vb["edit_count"]
print("male villager: %d edits across the 27 task-swap records" % _vb["edit_count"])

# Naming either sex reaches the same family: the user typed "Villager" or
# "Villager (Female)" and must not get different mods for it.
_vf = tk.plan({"intent": "unit.stat", "unit": 293, "stat": "hit_points",
               "delta": 100})
assert _vf["edit_count"] == 1701, _vf["edit_count"]
assert sorted(_vf.get("unit_ids") or []) == sorted(_vp.get("unit_ids") or []), \
    "both sexes must resolve to the same family"
_vfb = run("villager (female) writes the same 27 records", {
    "intent": "unit.stat", "unit": 293, "stat": "hit_points", "delta": 100})
assert _vfb is not None and _vfb["edit_count"] == 1701, _vfb["edit_count"]

# `linkedUnits.json` offers `206 VMDL` as a villager.  Its TaskSwapGroup is 0 --
# it is a corpse, not a job -- and no declared swap names it, so the official
# list must be filtered rather than trusted, and a lone record must stay lone.
assert not tk.plan({"intent": "unit.stat", "unit": 206, "stat": "hit_points",
                    "delta": 100}).get("variants")

# The other declared rows, each verified at the record level rather than by
# family size: a Town Center edit must reach the packed one, or razing a TC to
# pack it (or unpacking it) silently restores the unmodded stats.
assert tk.plan({"intent": "unit.stat", "unit": 109, "stat": "hit_points",
                "delta": 100}).get("unit_ids") == [71, 109, 141, 142, 444]
assert tk.plan({"intent": "unit.stat", "unit": 45, "stat": "hit_points",
                "delta": 100}).get("unit_ids") == [45, 47, 51, 133, 2141, 2142,
                                                   2143, 2172]
assert tk.plan({"intent": "unit.stat", "unit": 68, "stat": "hit_points",
                "delta": 100}).get("unit_ids") == [68, 129, 130, 131, 2556, 2558,
                                                   2560]
assert tk.plan({"intent": "unit.stat", "unit": 562, "stat": "hit_points",
                "delta": 100}).get("unit_ids") == [562, 563, 564, 565, 584, 585,
                                                   586, 587, 1808]
# 562/584/68/45 are the rows whose declared swap carries a technology gate
# (`technology` + `technology_state`), while 109 carries `required_attribute` +
# `excluded_computer_players` instead.  The gate does NOT shrink the family, and
# this asserts that on purpose: the engine decides at runtime whether the swap
# applies, so an edit that skipped a gated target would be a mod that works until
# someone researches the prerequisite.

# A plan must not promise edits the build then refuses: a Barracks stores no
# base attack, so this is 0 edits, not 252.
abp = tk.plan({"intent": "unit.attack_class", "unit": 12, "delta": 1})
assert abp["edit_count"] == 0, abp["edit_count"]
run("a building has no base attack, and building it is refused", {
    "intent": "unit.attack_class", "unit": 12, "delta": 1}, expect_ok=False)

# --- PLAN MUST REFUSE WHAT BUILD REFUSES ------------------------------------
# A preview that only counts records is not a preview.  "Archer costs 100 less
# wood" is 63 records and an impossible number, and the user has to learn that
# from the plan, not from an exception after they press the button.  Every case
# below is checked on BOTH paths: if plan and build ever disagree, one of these
# assertions fails instead of the user being surprised.
def both_refuse(label, intent):
    """plan() and the compiler must reach the same verdict, both ways."""
    try:
        tk.plan(intent)
        planned = None
    except C.IntentError as exc:
        planned = str(exc)
    try:
        C.compile_intent(BASE, intent, parsed=parsed, stats=STATS)
        built = None
    except C.IntentError as exc:
        built = str(exc)
    assert planned is not None, "%s: plan accepted what must be refused" % label
    assert built is not None, "%s: build accepted what must be refused" % label
    print("  both refuse %-42s %s" % (label, planned))
    return planned

both_refuse("unit cost going negative", {
    "intent": "unit.cost", "unit": "Archer", "resource": "wood", "delta": -100})
both_refuse("unit cost written as -1", {
    "intent": "unit.cost", "unit": "Archer", "resource": "wood", "value": -1})
both_refuse("tech cost going negative", {
    "intent": "tech.cost", "tech": "Loom", "resource": "gold", "delta": -100})
both_refuse("tech research time going negative", {
    "intent": "tech.research_time", "tech": "Loom", "value": -1})
both_refuse("tech research time overflowing i16", {
    "intent": "tech.research_time", "tech": "Loom", "value": 40000})

# ...but a field that has no non-negative constraint is still allowed to go
# negative: hit points are a signed range, and refusing this would be wrong.
_hpm = tk.plan({"intent": "unit.stat", "unit": "Archer",
                "stat": "hit_points", "value": -5})
assert _hpm["edit_count"] == 63, _hpm["edit_count"]
print("  plan allows a negative hit_points (no non_negative binding): 63 edits")

# A discount that stays positive must survive on both paths.
_disc = tk.plan({"intent": "unit.cost", "unit": "Archer",
                 "resource": "wood", "delta": -5})
assert _disc["edit_count"] == 63, _disc["edit_count"]
print("  plan allows wood -5 (25 -> 20): 63 edits")

# --- write a real mod dat -------------------------------------------------
os.makedirs(OUT, exist_ok=True)
p5 = os.path.join(OUT, "archer_attack_plus2.dat")
rep = C.compile_intent(BASE, {
    "intent": "unit.stat", "unit": "Archer",
    "stat": "displayed_attack", "delta": 2}, out_path=p5, parsed=parsed)
print("\nwrote", rep["out_path"], rep["out_bytes"], "B compressed,",
      rep["patched_bytes"], "B raw")

# the written file must round-trip through the game's own inflate path
back, how2 = P.load_dat(p5)
print("reload:", len(back), "bytes via", how2, "| identical:",
      back == data)
p2 = P.Parser(back)
with contextlib.redirect_stdout(io.StringIO()):
    p2.parse()
print("reparse final offset", p2.r.pos, "of", len(back),
      "| leftover", len(back) - p2.r.pos)
assert p2.r.pos == len(back)

civs2, _, gv2, _ = L.locate(back, parser=p2)
after = sorted({u["type50"]["displayed_attack"]
                for _, _, u in L.find_units(civs2, 4)})
print("archer displayed_attack values after:", after)
assert after == [6], after

# The MIRROR: the number the damage maths reads has to move too, or the panel
# would show 6 while the arrow still hits for 4.  This is the whole point of the
# `mirror` binding, so assert on the raw entry, not just the displayed one.
raw_after = sorted({a["amount"] for _, _, u in L.find_units(civs2, 4)
                    for a in (u["type50"]["attacks"] or []) if a["class"] == 3})
print("archer raw class-3 attack after:", raw_after)
assert raw_after == [6], raw_after

hp_after = sorted({u["hit_points"] for _, _, u in L.find_units(civs2, 4)})
print("archer hit_points values after:", hp_after)
assert hp_after == [30], hp_after

# byte discipline: compare raw streams.
diff = [i for i in range(len(data)) if data[i] != back[i]]
print("changed bytes in raw stream:", len(diff))
# 4 -> 6 only moves the low byte, so 126 of the 252 claimed bytes actually
# differ (63 records x 2 slots, displayed + raw class 3).  That gap is exactly
# why verify() reports claimed and changed separately.
assert len(diff) == 126, len(diff)
claimed = set()
for e in rep["edits"]:
    claimed.update(range(e.off, e.off + e.width))
assert set(diff) <= claimed, "a changed byte is outside every claimed edit"
print("every changed byte lies inside a claimed edit offset: True")

print("\nALL COMPILER SMOKE CHECKS PASSED")
