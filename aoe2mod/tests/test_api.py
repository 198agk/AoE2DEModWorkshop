# -*- coding: utf-8 -*-
"""The façade a UI actually calls: sentence in, installable mod out."""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root not in sys.path:
    sys.path.insert(0, root)

from aoe2mod import api                      # noqa: E402
from aoe2mod.dat import locate as _L         # noqa: E402
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.game import locations as G      # noqa: E402
from aoe2mod.intent import compiler as C     # noqa: E402
from aoe2mod.mod import emitter as E         # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# 1. locate the install without being told
# The explicit path is what a caller passes when they know it; the no-argument
# form is what a real user hits, and it must find the game on its own.  That
# form was BROKEN until Steam discovery was added: this machine's game lives
# under ...\Games\Steam\steamapps\, a depth no fixed layout list would guess.
auto = G.find_game_root()
print("auto-found:", auto)
game = G.find_game_root(explicit=os.environ.get("AOE2MOD_GAME_ROOT") or auto)
assert os.path.normcase(auto) == os.path.normcase(game), (auto, game)
print("game root :", game)
print("dat       :", G.dat_path(game))
tk = api.open_toolkit(game)
print("version   :", tk.version, "| civs:", len(tk.civ_names))
print("first civs:", tk.civ_names[:5])

# 2. search is a first-class verb -- ambiguity is information, not an error
print("\nsearch '弓手'   :", [(h["id"], h["name"]) for h in tk.search("弓手")])
print("search 'Archer':", [(h["id"], h["name"]) for h in tk.search("Archer")])
print("search 'nonsense':", tk.search("zzz-no-such-thing"))

# 3. describe one entity
d = tk.describe(4)
print("\nunit 4:", d["name"], "| en:", d["en"], "| records:", d["record_count"],
      "across", d["civ_count"], "civs")
print("  stats:", json.dumps(d["stats"], ensure_ascii=False))

k = tk.describe(38)
print("unit 38:", k["name"], "| hp", k["stats"]["hit_points"],
      "speed", round(k["stats"]["movement_speed"], 3),
      "costs", k["stats"]["costs"])

# 4. plan without writing anything
plan = tk.plan({"intent": "unit.stat", "unit": "Archer",
                "stat": "displayed_attack", "delta": 2})
print("\nplan:", plan["description"], "->", plan["civ_count"], "civs,",
      plan["edit_count"], "records")

# 5. build the mod
mod_dir = os.path.join(OUT, "ArcherAttackPlus2_via_api")
if os.path.isdir(mod_dir):
    shutil.rmtree(mod_dir)
man = tk.build({"intent": "unit.stat", "unit": "Archer",
                "stat": "displayed_attack", "delta": 2},
               mod_dir, author="aoe2mod",
               description="弓手攻击力 +2（全文明）",
               overwrite=True)
print("\nmod:", man["mod_dir"])
print("  dat raw", man["dat_raw_bytes"], "B -> file", man["dat_file_bytes"], "B")
print("  reloaded with the game's own path:", man["reloaded_with"])
print("  reparse leftover:", man["reparse_leftover"], "| ok:", man["reparse_ok"])
print("  verification ok:", man["verification"]["ok"],
      "| changed", man["verification"]["changed_bytes"])
for f in man["files"]:
    print("   %-52s %10d B" % (f["rel"], f["bytes"]))

assert man["reparse_ok"] and man["verification"]["ok"]
assert os.path.exists(os.path.join(mod_dir, "info.json"))

# 6. the schema is data, not code -- a UI can render the form from it
sch = tk.schema()
print("\nintent kinds:", sorted(sch["intents"]["intents"]))
print("unit stats  :", sch["intents"]["intents"]["unit.stat"]["fields"]["stat"]["options"])
print("binds to    :", sch["bindings"]["binds_to_dat_version"])

# 6b. a TECH is global: one record for the whole game, not one per civ.  A
#     plan that reports 63 civilizations here would be inventing them.
tplan = tk.plan({"intent": "tech.research_time", "tech": "Loom", "delta": 25})
print("\ntech plan:", tplan["description"], "| kind:", tplan["kind"],
      "| locations:", tplan["locations"], "| edits:", tplan["edit_count"])
assert tplan["kind"] == "tech"
assert tplan["civ_count"] == 0 and tplan["civs"] == []
assert tplan["edit_count"] == tplan["locations"] > 0
# resolve a tech by its integer id too -- search() hands out numbers, so a UI
# echoing one back must not fall into the substring branch and come up empty.
assert tk.plan({"intent": "tech.research_time", "tech": 22,
                "delta": 1})["entity_id"] == 22
assert [h["id"] for h in tk.search(22, kind="tech")] == [22]

# A C31+ tech stores its time once per research LOCATION; the plan must warn
# before the user agrees, not after.
tplan2 = tk.plan({"intent": "tech.research_time", "tech": 12, "delta": 10})
print("multi-location tech plan:", tplan2["description"],
      "| locations:", tplan2["locations"], "ids", tplan2["location_ids"])
assert tplan2["locations"] == len(tplan2["location_ids"]) == tplan2["edit_count"]
d12 = tk.describe(12, "tech")
print("describe tech 12:", d12["name"], d12["stats"])
assert d12["civ_count"] == 0

# 6d. tech COSTS.  A tech always stores exactly 3 cost slots; Loom's gold sits
#     in a slot that is not the first, so a preview that guesses position would
#     promise one number and the build would move another.
cplan = tk.plan({"intent": "tech.cost", "tech": "Loom",
                 "resource": "gold", "delta": -20})
print("tech cost plan:", cplan["description"], "| kind:", cplan["kind"],
      "| edits:", cplan["edit_count"], "| slot:", cplan.get("cost_slot"),
      "| current:", cplan.get("value"))
assert cplan["kind"] == "tech"
assert cplan["civ_count"] == 0 and cplan["civs"] == []
assert cplan["edit_count"] == 1
assert cplan["cost_slot"] == 3, cplan["cost_slot"]     # gold, and NOT slot 0
assert cplan["value"] == 50, cplan["value"]
# a resource the tech does not cost must preview as zero edits, not as a
# pretend-success that the compiler would then refuse.
cmiss = tk.plan({"intent": "tech.cost", "tech": "Loom",
                 "resource": "stone", "delta": 10})
assert cmiss["edit_count"] == 0, cmiss["edit_count"]
# describe must expose readable costs and hide the -1 sentinel slots
d22 = tk.describe(22, "tech")
print("describe tech 22 costs:", d22["stats"]["costs"])
assert any(c["resource"] == "gold" and c["amount"] == 50
           for c in d22["stats"]["costs"]), d22["stats"]["costs"]
assert all(not c["resource"].startswith("type -")
           for c in d22["stats"]["costs"]), d22["stats"]["costs"]

# 6c. the user-facing sentence must never leak a Python None, and it must never
#     leak a raw field key either: "步弓手 max_range +1" tells a player nothing,
#     because `max_range` is the locator's key and `射程` is the word they use.
for it in ({"intent": "tech.research_time", "tech": "Loom", "delta": 25},
           {"intent": "tech.cost", "tech": "Loom", "resource": "gold", "delta": -20},
           {"intent": "unit.stat", "unit": "Archer", "stat": "hit_points", "delta": 5},
           {"intent": "unit.stat", "unit": "Archer", "stat": "max_range", "delta": 1},
           {"intent": "unit.stat", "unit": "Archer", "stat": "reload_time", "delta": -0.5},
           {"intent": "unit.stat", "unit": "Archer", "stat": "displayed_range", "delta": 1}):
    desc = tk.plan(it)["description"]
    assert "None" not in desc, desc
    if it["intent"] == "unit.stat":
        assert it["stat"] not in desc, "raw stat key leaked into %r" % desc
    print("  reads:", desc)

# 7. bad input stays user-facing prose -- INCLUDING illegal values, which the
# preview must refuse for the same reason the build would.  A plan that says
# "63 edits" and then raises after the button is pressed is worse than useless.
for bad in ({"intent": "unit.stat", "unit": "弓手", "stat": "displayed_attack", "delta": 1},
            {"intent": "unit.stat", "unit": "Archer", "stat": "nope", "delta": 1},
            {"intent": "no.such.intent", "unit": "Archer", "delta": 1},
            {"intent": "unit.cost", "unit": "Archer", "resource": "wood", "delta": -100},
            {"intent": "unit.cost", "unit": "Archer", "resource": "wood", "value": -1},
            {"intent": "unit.cost", "unit": "Archer", "resource": "population", "value": -1},
            {"intent": "tech.cost", "tech": "Loom", "resource": "gold", "delta": -100},
            {"intent": "tech.research_time", "tech": "Loom", "value": -1},
            {"intent": "tech.research_time", "tech": "Loom", "value": 40000},
            # float32 fields are non-negative too, and going negative there makes
            # exactly as broken a record as a negative cost does.
            {"intent": "unit.stat", "unit": "Archer", "stat": "max_range", "delta": -100},
            {"intent": "unit.stat", "unit": "Archer", "stat": "reload_time", "delta": -5}):
    try:
        tk.plan(bad)
        raise AssertionError("should have been refused: %r" % bad)
    except C.IntentError as exc:
        print("refused:", exc)
        # The negative-value message must not enumerate which fields it covers:
        # it was "Cost and time cannot be negative" until range/reload were
        # routed through the same guard, at which point it named costs while
        # refusing a negative 射程.  A field list in user-facing prose goes
        # stale the moment a field is added.  (The prose is Chinese now, so the
        # marker is 「负数」 -- what is pinned is the CLAIM, not the language.)
        if "负数" in str(exc):
            assert "Cost and time" not in str(exc) and "成本和时间" not in str(exc), \
                "refusal prose enumerates its own cases: %s" % exc

# The same guard, checked by the field it now also covers: refusing a negative
# range must not talk about costs at all.
try:
    tk.plan({"intent": "unit.stat", "unit": "Archer",
             "stat": "max_range", "delta": -100})
    raise AssertionError("negative range should have been refused")
except C.IntentError as _e:
    assert "成本" not in str(_e) and "Cost" not in str(_e), str(_e)
    assert "负数" in str(_e), str(_e)
    print("negative range refusal is field-neutral:", _e)

# A value with no non_negative binding is still allowed to go negative: hit
# points are a signed range, and refusing them would be its own bug.  This is
# the control that keeps the sign guard from over-reaching.
_hpneg = tk.plan({"intent": "unit.stat", "unit": "Archer",
                  "stat": "hit_points", "value": -5})
assert _hpneg["edit_count"] == 63, _hpneg["edit_count"]
print("allowed (signed field):", _hpneg["description"], "| edits", _hpneg["edit_count"])

# A building's age variants carry DIFFERENT baselines (Barracks hp is
# 1200/1500/1800/2100), so an extreme delta must be caught on every age and not
# only on the record the name resolved to.
for delta in (30000, 30600):
    _ok = tk.plan({"intent": "unit.stat", "unit": 12,
                   "stat": "hit_points", "delta": delta})
    assert _ok["edit_count"] == 252, (delta, _ok["edit_count"])
    print("allowed (fits every age): hp +%d -> %d edits" % (delta, _ok["edit_count"]))
try:
    tk.plan({"intent": "unit.stat", "unit": 12, "stat": "hit_points", "delta": 30700})
    raise AssertionError("an overflowing age variant should have been refused")
except C.IntentError as exc:
    print("refused (overflows the Imperial record):", exc)

# 8. describe() must cover exactly what an edit can reach.
# Binding a field in dat_bindings.json is not enough if describe() still hands
# out a hand-written list: the four range/reload fields were declared, bound and
# writable while describe() reported seven stats and hid them.  So the invariant
# is a BICONDITIONAL, not "describe is not empty": a field is reported precisely
# when plan() accepts an edit of it on that same record.
import aoe2mod.intent.compiler as _C  # noqa: E402
from aoe2mod.game import civtechtrees as _CT  # noqa: E402
from aoe2mod.game import buildpanel as _BP_MODULE  # noqa: E402
_declared = list(_C.load_schema()[0]["intents"]["unit.stat"]["fields"]["stat"]["options"])
_disc = 0
for _uid in (4, 38, 83, 12, 70, 82, 10, 87, 125, 448, 546, 209, 2418, 35, 2556, 20):
    _rep = {k for k in tk.describe(_uid)["stats"] if k != "costs"}
    for _st in _declared:
        # Reachability is `edit_count > 0`, not "plan() raised".  An unreachable
        # field is reported as 0 edits plus prose ("this unit has no range to
        # change"); reading the exception would call every field reachable and
        # the assertion would pass while testing nothing.
        _n = tk.plan({"intent": "unit.stat", "unit": _uid, "stat": _st,
                      "delta": 1})["edit_count"]
        _reach = _n > 0
        if (_st in _rep) != _reach:
            _disc += 1
            print("  DESCRIBE/DESCRIBE MISMATCH unit %s %s: reported=%s reachable=%s"
                  % (_uid, _st, _st in _rep, _reach))
assert _disc == 0, "%d describe()/compile() disagreements" % _disc
assert all(k in tk.describe(4)["stats"] for k in _declared), \
    "describe() must report every declared stat"
print("\nall %d declared stats are reported by describe(), and only when reachable"
      % len(_declared))

# A field the record cannot carry is OMITTED, never reported as a zero or a
# None -- "this unit has no range" and "this unit has range 0" are different
# statements and only the record can tell them apart.
for _uid in (4, 38, 83, 12, 70, 82, 10, 87, 125, 448, 546, 209, 2418, 35, 2556, 20):
    _s = tk.describe(_uid)["stats"]
    _nones = sorted(k for k, v in _s.items() if v is None)
    assert not _nones, "unit %s reported None for %s" % (_uid, _nones)
print("no describe() field is ever None: absent fields are omitted, not zeroed")

# 8b. the same biconditional, for COSTS.  A cost list is not a filtered copy of
# the stored slots: it must be the projection of the very function the compiler
# uses to pick a slot.  Tech 20/1210/1211/1270 were writable but hidden (119
# slots fell into the fallback onto a wholly empty (t,0,0) slot), and 10 slots
# were shown that no intent could name.  Being wrong in either direction is a
# silent lie, so both are asserted here.
#
# Reachability is read from `edit_count`, NOT from whether plan() raised: an
# unreachable cost is reported as 0 edits plus user-facing prose ("骑士 has no
# 成本 wood to change"), which is the same contract the stat path uses.
_RES = list(_C.load_schema()[0]["intents"]["tech.cost"]["fields"]["resource"]["options"])
_RES_U = list(_C.load_schema()[0]["intents"]["unit.cost"]["fields"]["resource"]["options"])
_costdisc = 0
for _tid in (22, 12, 103, 102, 20, 1270, 1210, 1211, 0, 699, 1195, 101, 104, 39, 67):
    _d = tk.describe(_tid, "tech")
    _rep = {c["resource"] for c in _d["stats"].get("costs", [])}
    for _res in _RES:
        _n = tk.plan({"intent": "tech.cost", "tech": _tid, "resource": _res,
                      "delta": 1})["edit_count"]
        if (_res in _rep) != (_n > 0):
            _costdisc += 1
            print("  COST MISMATCH tech %s %s: reported=%s reachable=%s"
                  % (_tid, _res, _res in _rep, _n > 0))
    # An unnamed cost is reported under `unmapped_costs`, never as a resource
    # name -- so nothing in the reachable list may be a raw type id.
    for _c in _d["stats"].get("costs", []):
        assert not _c["resource"].startswith("type"), \
            "tech %s leaked a raw slot type into the cost list: %r" % (_tid, _c)
for _uid in (4, 83, 38, 1259, 2162, 2443, 12, 70, 82):
    _d = tk.describe(_uid)
    _rep = {c["resource"] for c in _d["stats"].get("costs", [])}
    for _res in _RES_U:
        _n = tk.plan({"intent": "unit.cost", "unit": _uid, "resource": _res,
                      "delta": 1})["edit_count"]
        if (_res in _rep) != (_n > 0):
            _costdisc += 1
            print("  COST MISMATCH unit %s %s: reported=%s reachable=%s"
                  % (_uid, _res, _res in _rep, _n > 0))
assert _costdisc == 0, "%d cost describe()/compile() disagreements" % _costdisc
print("every reported cost is exactly one an edit can reach, and no raw slot "
      "type leaks into the list")

# 8b-2. An unnamed cost type must be NAMED, and must stay a bare number when the
# game itself does not name it.  Both halves matter: the name comes from the
# game's own resource-name block
# (resources/<locale>/strings/key-value/key-value-strings-utf8.txt at string id
# 15000 + type), so inventing one would be a lie, and leaving a name off would
# put "type 7" back in front of the user.  The raw `type` must survive either
# way, because the name is an ADDITION and not a replacement -- a caller that
# needs the id cannot be made to parse it back out of prose.
#
# This table used to come from AGE's AGE3NamesV0007.ini, which named 271 slots
# and could not name 501/506/508/513/514 at all -- so those five rendered as bare
# numbers and this test asserted they must.  The game's own block names 328
# slots including all five, so the assertion is now the opposite: every type the
# shipped dat actually charges MUST have a name.  What still stays nameless is
# any slot the game reserves as "Unused Resource NNN".
_labels = _C.load_resource_labels()
assert _labels, "the resource name table did not load"
_NAMED_EVERYWHERE = (0, 1, 2, 3, 4, 7, 214, 215, 501, 506, 508, 513, 514)
_absent = [t for t in _NAMED_EVERYWHERE if not _labels.get(t)]
assert not _absent, (
    "the game names every resource type the shipped data charges; these have no "
    "name and would render as bare numbers: %s" % _absent)
# And the game's own reservations must NOT be shipped as names: slot 34 is
# "Unused Resource 034" and AGE's "Faith" is not the engine's vocabulary.
assert 34 not in _labels and 194 not in _labels, (
    "slots the game reserves as 'Unused Resource' must stay numbers, not take "
    "AGE's private wording")
_t7 = tk.describe(699, "tech")["stats"].get("unmapped_costs") or []
assert _t7 and _t7[0].get("name") == _labels[7], \
    "tech 699's relic cost must report a name, got %r" % (_t7,)
assert _t7[0]["type"] == 7, "the raw type must survive alongside the name"
# 506 was the id that used to prove "unnamed"; it is named now, so it proves the
# switch took effect end to end (table -> cost_report -> describe).
_t506 = tk.describe(1195, "tech")["stats"].get("unmapped_costs") or []
assert _t506 and _t506[0].get("name") == _labels[506], \
    "type 506 is named by the game now and must report that name: %r" % (_t506,)
assert _t506[0]["type"] == 506, "the raw type must survive alongside the name"
_u_cuman = tk.describe(1259)["stats"].get("unmapped_costs") or []
assert {e.get("name") for e in _u_cuman} == {_labels[214], _labels[215]}, \
    "unit 1259's mercenary costs must report the game's names: %r" % (_u_cuman,)
# And nothing in any list may be an empty string -- a name of "" would read as a
# resource with no name rather than as an unnamed id.
for _e in _t7 + _t506 + _u_cuman:
    assert _e.get("name", "x") != "", "an empty name was reported: %r" % (_e,)
print("unnamed cost types carry the game's own name (%s) and every type the "
      "shipped data charges is now named"
      % ", ".join("%s=%s" % (k, _labels[k])
                  for k in (7, 214, 215, 501, 506, 508, 513, 514)))

# 8c. the schema declares `signed`, and the write path must READ it.
# `signed` sat in dat_bindings.json from the beginning and no code ever read it:
# every write path packed with signed=True hard-coded.  That was harmless only
# because all six declared int fields happened to be signed -- so binding the
# first unsigned field (garrison_capacity, a uint8) would have raised
# OverflowError the moment a value above 127 was written.  A flag that is
# declared and never read is the same defect as `non_negative` being swallowed
# by a float early-return, so it is asserted by OBSERVING the byte on disk.
_BIND = _C.load_schema()[1]
_UNSIGNED = sorted(n for n, f in _BIND["unit_fields"].items()
                   if f.get("signed") is False)
assert _UNSIGNED == ["garrison_capacity"], _UNSIGNED
print("\nthe schema's only unsigned field is %s" % _UNSIGNED[0])

# The flag is load-bearing, not decorative: packing 200 into one signed byte
# fails outright, which is exactly what every write path used to do.
try:
    (200).to_bytes(1, "little", signed=True)
    raise AssertionError("a signed byte held 200 -- the test proves nothing")
except OverflowError:
    print("packing 200 as a signed byte raises OverflowError (the flag matters)")

# READ: a uint8 read as signed would report 200 as -56.
assert tk.describe(12)["stats"]["garrison_capacity"] == 10, "Barracks garrison"
assert tk.describe(82)["stats"]["garrison_capacity"] == 20, "Castle garrison"
assert tk.describe(71)["stats"]["garrison_capacity"] == 15, "Town Center garrison"
assert tk.describe(35)["stats"]["garrison_capacity"] == 6, "BTRAM garrison"
assert tk.describe(4)["stats"]["garrison_capacity"] == 0, "Archer garrison"
print("read back: Barracks 10 | Castle 20 | Town Center 15 | BTRAM 6 | Archer 0")

# WRITE: 200 must land on disk as 0xC8, and the Edit must SAY it is unsigned so
# the emitter packs it the same way the compiler did.
_rep = _C.compile_intent(tk.dat_path,
                         {"intent": "unit.stat", "unit": 12,
                          "stat": "garrison_capacity", "value": 200},
                         parsed=tk._parsed, stats=tk._stats)
_e0 = _rep["edits"][0]
assert _e0.signed is False, "the unsigned field produced a signed Edit"
assert _e0.before == 10 and _e0.after == 200, (_e0.before, _e0.after)
_patched = _C.apply_edits(tk._raw, _rep["edits"])
assert _patched[_e0.off] == 200, _patched[_e0.off]
assert tk._raw[_e0.off] == 10, "the base stream was mutated"
print("wrote 200 over 10 -> byte on disk is 0x%02X (unsigned)" % _patched[_e0.off])

# BOUNDS: the byte range is 0..255, and the refusal names that range and that
# signedness.  A hard-coded "16-bit" message would be a second, contradictory
# statement of the same field's limits.
try:
    tk.plan({"intent": "unit.stat", "unit": 12,
             "stat": "garrison_capacity", "value": 256})
    raise AssertionError("a 256-byte garrison should have been refused")
except C.IntentError as _e:
    # The width and the signedness are what must be in the sentence (the prose is
    # Chinese now, so the markers are too).  A hard-coded "16 位" would be a
    # second, contradictory statement of the same field's limits.
    assert "8 位" in str(_e) and "无符号" in str(_e), _e
    assert "0..255" in str(_e), _e
    assert "16 位" not in str(_e), _e
    print("256 refused by range:", _e)
try:
    tk.plan({"intent": "unit.stat", "unit": 12,
             "stat": "garrison_capacity", "delta": -100})
    raise AssertionError("a negative garrison should have been refused")
except C.IntentError as _e:
    assert "负数" in str(_e), _e
    print("negative refused:", _e)

# The byte-width field is reported/reachable under the same biconditional as
# every other stat, so it is not a second-class field bolted on.
_bidisc = 0
for _uid in (12, 82, 71, 35, 4, 45, 33, 70, 83, 125):
    _d = tk.describe(_uid)["stats"]
    _n = tk.plan({"intent": "unit.stat", "unit": _uid,
                  "stat": "garrison_capacity", "delta": 1})["edit_count"]
    if ("garrison_capacity" in _d) != (_n > 0):
        _bidisc += 1
        print("  GARRISON MISMATCH unit %s: reported=%s reachable=%s"
              % (_uid, "garrison_capacity" in _d, _n > 0))
assert _bidisc == 0, "%d garrison describe()/compile() disagreements" % _bidisc
print("a byte-wide field obeys the same describe/reach biconditional")

# 8d-0. The Resource Modifier family (command types 1 and 6) is a SECOND kind of
# editable command, and it is not an attribute modifier at all: its operation
# lives in slot B (0 = set, 1 = add) and its slot C is a TIMES-RESOURCE, so a
# row's `attribute` means a resource id on those rows.  It was refused wholesale
# until this round, which is why the assertions below are worth having: the
# failure mode is a whole family of real commands the UI lists and cannot write
# (236 + 117 commands over BASE, and 142 techs with nothing else editable).
#
# Every shipped starting-resource grant is in this family -- that is how a civ
# gets its opening bank, and the civ Resources array is all zeroes, so this path
# is the ONLY way to change it.
print("\nthe Resource Modifier family is editable, and it is not an attribute:")
_ops_seen = {}
for _t in range(len(tk._stats["techs"])):
    for _row in tk.effects(_t)["rows"]:
        if _row["resource"] and _row["editable"]:
            _ops_seen.setdefault(_row["operation"], (_t, _row))
assert set(_ops_seen) == {"add", "set", "multiply"}, sorted(_ops_seen)

# Slot C is a times-resource on these rows, so `attribute`/`attribute_label`
# must stay empty -- a resource id of 8 or 9 would otherwise be read as the
# packed armour/attack attribute and the number would be decoded as a garbage
# pair.  This is the trap the `resource` flag exists to close.
for _op, (_t, _row) in _ops_seen.items():
    assert _row["attribute_label"] is None, (_op, _row["attribute_label"])
    assert _row["target_kind"] == "resource", (_op, _row["target_kind"])
    # NOT "the game names every resource the data charges" -- it does not: six
    # visible rows still fall back.  The invariant is that the FALLBACK is
    # Chinese, because it lands inside a sentence a player reads.  Asserting
    # `not startswith("Resource ")` would pass no matter what the fallback said,
    # so it would be a test that cannot fail.
    assert _row["target_label"], (_op, "a resource row with no label at all")
    assert not re.search(r"[A-Za-z]{2,}", _row["target_label"]), \
        (_op, _row["target_label"])

# The preview sentence has to describe the OPERATION, because the three
# operations need three different sentences: a multiply row's number is a
# factor (a "+0.05" would read as adding half a unit of something), and a set
# row would render as a cryptic "=4" next to a bare resource name.
_t, _row = _ops_seen["add"]
_p = tk.plan({"intent": "tech.effect", "tech": _t, "command": _row["index"],
              "delta": 500})
assert _row["target_label"] in _p["description"], _p["description"]
# The fallback for an id the game does not name is now 资源 NN, so this cannot
# assert "the number never appears".  What it CAN assert is that the English
# fallback spelling is gone from the sentence -- a regression guard on the one
# thing that was wrong (this string is printed inside a player-facing sentence).
assert not re.search(r"Resource \d", _p["description"]), _p["description"]
_t, _row = _ops_seen["set"]
_p = tk.plan({"intent": "tech.effect", "tech": _t, "command": _row["index"],
              "value": 4})
assert "设为" in _p["description"], _p["description"]
_t, _row = _ops_seen["multiply"]
_p = tk.plan({"intent": "tech.effect", "tech": _t, "command": _row["index"],
              "delta": 0.05})
assert "×" in _p["description"], _p["description"]
print("  add/set/multiply all render (e.g. %s)" % _p["description"])

# A civ's opening bank is reachable through the family, end to end: tech 223 is
# the Persians' free C-Bonus, and its command 0 adds 50 food at the start.
_grants = [(_t, r) for _t in (223, 224, 225, 226, 227, 228, 1394)
           for r in tk.effects(_t)["rows"]
           if r["resource"] and r["editable"] and r["target"] in (91, 92, 93, 94)]
assert len(_grants) == 12, len(_grants)
assert all(k == "add" for _t, r in _grants for k in [r["operation"]]), \
    "every starting-resource grant is an 'add', never a 'set' or a factor"
print("  %d starting-resource grants are writable (a civ's opening bank)"
      % len(_grants))

# And the two shapes the engine uses for something else must stay REFUSED: a
# times-resource row multiplies by another resource's CURRENT value, so "add
# 175" is not the edit it looks like, and an unrecognised slot B cannot be
# guessed into one of the two operations.
_ref = {"times": 0, "badb": 0}
for _t in range(len(tk._stats["techs"])):
    for _row in tk.effects(_t)["rows"]:
        if _row["resource"] and not _row["editable"]:
            # Keyed on reason_code, not on the sentence: the sentence is written
            # for a player and is Chinese now, so matching English prose here
            # would turn both counts into zero the moment it was reworded --
            # which is what happened when the refusals were translated.
            if _row.get("reason_code") == "times_resource":
                _ref["times"] += 1
            elif _row.get("reason_code") == "slot_b_unreadable":
                _ref["badb"] += 1
assert _ref["times"] == 17, _ref
assert _ref["badb"] == 8, _ref
print("  17 times-resource and 8 unreadable-B commands stay refused with a reason")

# 8d-3. A refusal SENTENCE must not print an internal number where the vendored
# vocabulary already has a name.  "command type 3 does not carry an attribute"
# reached the user even though `effect_command_types.json` calls type 3
# "升级单位" and the same row dict already carried that label.  This is the fifth
# time this project leaked a raw key into user-facing text (cost types,
# attack/armour classes, train/research locations, unit field labels), so it is
# asserted at the whole-population level: walk EVERY refused command of every
# tech and require that none of them mentions a bare type number.
print("\nno refusal sentence prints a raw command type number:")
_bare = []
_named = 0
for _t in range(len(tk._stats["techs"])):
    for _row in tk.effects(_t)["rows"]:
        _why = _row.get("reason") or ""
        if _row["editable"] or _row.get("reason_code") != "no_attribute_slot":
            continue
        _named += 1
        if re.search(r"type\s*\d", _why) or _row["type_label"] == "Type %d" % _row["type"]:
            _bare.append((_t, _row["type"], _why))
assert not _bare, _bare[:3]
assert _named, "the no_attribute_slot refusal disappeared; this walks nothing"
print("  every one of the %d such refusals names its command instead" % _named)

# 8d. tech.effect -- the effect vocabulary and the shared-record warning.
#
# The attribute and class names come from the vendored tables, and those tables
# are GENERATED by walking AGE's own version branches.  A regression here is
# invisible in the bytes and only shows up as a wrong word on screen, which is
# why it needs an assertion rather than a code review.
print("\nthe effect vocabulary is the AoE2:DE branch, not another engine's:")
_rows22 = tk.effects("Loom")["rows"]
assert _rows22[0]["attribute_label"] == "生命值", _rows22[0]["attribute_label"]
assert _rows22[1]["packed_class_label"] == "平民", _rows22[1]["packed_class_label"]
assert "Wood" not in json.dumps(_rows22, ensure_ascii=False), \
    "a Star Wars/AoE1 resource name leaked in (the branch bug)"
print("  Loom: %s / %s (attr=%s class=%s)"
      % (_rows22[0]["attribute_label"], _rows22[0]["type_label"],
         _rows22[0]["attribute"], _rows22[1]["packed_class"]))
_e104 = [t for t in range(len(tk._stats["techs"]))
         if any(r["attribute"] == 104 for r in (tk.effects(t)["rows"] or []))]
if _e104:
    _r = [r for r in tk.effects(_e104[0])["rows"] if r["attribute"] == 104][0]
    assert _r["attribute_label"] == "木材成本", _r["attribute_label"]
    print("  attribute 104 reads '%s' (was 'Carbon Costs' from the SWGB branch)"
          % _r["attribute_label"])

# A tech's effect is a SHARED record: editing it changes every tech that points
# at it.  The preview must say so, and the count must be real.
_shared = None
for _t in range(len(tk._stats["techs"])):
    _ee = tk.effects(_t)
    if _ee["rows"] and _ee["rows"][0]["fan_in"] > 1:
        _shared = (_t, _ee)
        break
assert _shared, "no shared effect found (this dataset is supposed to have 37)"
_st, _see = _shared
_sr = _see["rows"][0]
# `fan_in` is how many techs reference the effect and `shared_with` lists them,
# INCLUDING the tech being edited -- so the two agree exactly.  The number a
# preview shows as "also changes N others" is fan_in - 1.
assert _sr["fan_in"] == len(_sr["shared_with"]), \
    (_sr["fan_in"], len(_sr["shared_with"]))
assert _st in [s["index"] for s in _sr["shared_with"]], \
    "the tech being edited must appear in its own share list"
print("  tech[%d] shares effect[%s] with %d other techs -- the preview must say so"
      % (_st, _see["effect_id"], _sr["fan_in"] - 1))

# The preview/build biconditional, stated the way it actually is: a command with
# no addressable/named value is reported read-only and refused, and one with an
# address is reported editable and accepts a legal change.  NOTE `editable` is
# about ADDRESSABILITY (the walk marked a value offset and the attribute has a
# name), not about a particular amount: 22 shipped commands already sit at the
# packed maximum of 255, so "+1" is refused for them by the RANGE check while
# "-1" is accepted.  Testing only +1 would have called those three a defect.
# "Reachable" is edit_count > 0 for a plan -- never "did plan() raise", which is
# how the cost version of this bug hid.
_bad = 0
_swept = 0
for _t in range(0, len(tk._stats["techs"]), 37):
    _ee = tk.effects(_t)
    _swept += 1
    for _row in _ee["rows"]:
        _ok = False
        for _d in (-1, 1):
            try:
                if tk.plan({"intent": "tech.effect", "tech": _t,
                            "command": _row["index"], "delta": _d})["edit_count"] > 0:
                    _ok = True
                    break
            except C.IntentError:
                pass
        if _ok != _row["editable"]:
            _bad += 1
            print("  EFFECT MISMATCH tech %d cmd %d: row says %s, plan says %s"
                  % (_t, _row["index"], _row["editable"], _ok))
assert _bad == 0, "%d effect describe()/plan() disagreements" % _bad
print("  every effect row's editable flag matches what plan() does (%d techs swept)"
      % _swept)

# A packed attribute hides a class in the high byte of D.  Writing the value
# alone would silently retarget the command at class 0, so the class byte has to
# survive -- and this is checked against the real byte stream, not the helper.
assert _C.decode_effect_value(8, 1025.0) == (1, 4), _C.decode_effect_value(8, 1025.0)
assert _C.encode_effect_value(8, 1025.0, 3) == 1027.0
assert _C.decode_effect_value(8, 1027.0) == (3, 4)
assert _C.decode_effect_value(9, float(0x03C8)) == (200, 3), "low byte is unsigned"
print("  a packed value keeps its class byte (1->3 with class 4 stays class 4)")

# 8e. A request is several sentences, not one.  Two separate builds are two
# complete .dat replacements and the engine loads only the highest-priority one,
# so the lower one's edit is simply absent from the file that loads
# (`_probe/probe_multi_intent.py`: two builds both changed the SAME 1701 villager
# bytes).  The bundle path exists so one request becomes one mod, and the tests
# that matter are the two the single-intent path cannot express:
#   * the fold ACCUMULATES -- "hp +5 then hp +7" is +12, which is only true
#     because each step reads `before` from the accumulated buffer.  Reading the
#     original would give 32: a plausible number with an edit silently missing.
#   * it is ALL-OR-NOTHING, and a refusal names WHICH sentence failed.
_PB_INTENTS = [
    {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 5},
    {"intent": "tech.cost", "tech": 22, "resource": "gold", "delta": -10},
    {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 7},
]
_pb = tk.plan_bundle(_PB_INTENTS)
assert len(_pb["plans"]) == 3, _pb["plans"]
assert _pb["edit_count"] == sum(_pb["per_intent_edits"]), _pb
assert _pb["verification"]["ok"], _pb["verification"]["problems"]
assert _pb["civs_edited"] == 63, _pb["civs_edited"]
# Two of the three sentences write the same villager field, so the fold MUST
# report overlaps rather than printing a total that hides one of them.
assert _pb["overlap_count"] > 0, "the fold lost track of its own overlaps"
assert _pb["per_intent_edits"][0] == _pb["per_intent_edits"][2] == 1701, _pb
print("\na bundle folds several sentences into one mod:")
print("", " / ".join(str(d) for d in _pb["descriptions"]))
print("  %d edits from %s sentences, %d civs, %d offsets written twice"
      % (_pb["edit_count"], len(_pb["plans"]), _pb["civs_edited"],
         _pb["overlap_count"]))

# The accumulate-don't-overwrite property, checked on VALUES rather than counts.
_HP0 = tk.describe(83)["stats"]["hit_points"]
_pb_schema, _pb_bindings = _C.load_schema()
_pb_patched, _pb_edits, _pb_per = _C.compile_bundle(
    tk._raw, tk._civs,
    [_C.resolve(i, _pb_schema, bindings=_pb_bindings) for i in _PB_INTENTS],
    _pb_bindings, _pb_schema,
    tail=tk._parsed[4], gv=tk._parsed[3], stats=tk._stats, game_root=tk.game_root)
_pb_p = P.Parser(_pb_patched)
with contextlib.redirect_stdout(io.StringIO()):
    _pb_p.parse()
_pb_civs = _L.locate(_pb_patched, parser=_pb_p)[0]
_HP1 = [u["hit_points"] for c in _pb_civs for u in c["units"] if u["id"] == 83][0]
assert _HP1 == _HP0 + 12, "expected %s+12=%s, got %s (the overwrite bug gives %s)" % (
    _HP0, _HP0 + 12, _HP1, _HP0 + 7)
print("  而且 生命值 %s -> %s (+5 then +7 accumulates, not last-writer-wins)"
      % (_HP0, _HP1))

# ALL-OR-NOTHING.  A building's unit type stores no raw attack list, so
# `unit.attack_class` on a Barracks is the sentence that cannot be written --
# while `unit.stat displayed_attack` on the same building IS legal (it stores a
# displayed_attack of 0).  Choosing the wrong one of those two would make this
# test pass while testing nothing.
try:
    tk.plan_bundle([{"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 5},
                    {"intent": "unit.attack_class", "unit": 12, "kind": "attack",
                     "delta": 3}])
    raise AssertionError("a bundle with an impossible sentence planned anyway")
except _C.IntentError as _exc:
    _msg = str(_exc)
    # Which sentence failed is the fact; the surrounding words are the product's
    # Chinese now (was "sentence 2: ...").  `test_prose_language` owns the wording.
    assert "第 2 句" in _msg, _msg
    print("  one impossible sentence refuses the whole bundle, naming it: %s" % _msg)

# Sentences that fail while RESOLVING are all collected, so the user fixes every
# bad sentence in one pass instead of rediscovering the next one each time.
#
# This assertion caught a real preview/build divergence when it was first
# written: `plan_bundle` resolved one sentence at a time via a list
# comprehension, so it named the first offender while `build_bundle` named both.
# Both now call `C.resolve_bundle`, and the identical-message check below is what
# keeps a second implementation from growing back.
_BAD_BUNDLE = [{"intent": "unit.stat", "unit": 99999, "stat": "hit_points", "delta": 3},
               {"intent": "tech.cost", "tech": 99999, "resource": "gold", "delta": -3}]
try:
    tk.plan_bundle(_BAD_BUNDLE)
    raise AssertionError("a bundle of only-bad sentences planned anyway")
except _C.IntentError as _exc:
    _msg = str(_exc)
    assert "第 1 句" in _msg and "第 2 句" in _msg, _msg
    print("  every unresolvable sentence is reported together: %s" % _msg)

# The preview and the write must say the SAME thing about the same bad bundle --
# a user who is told about one problem and then, on build, about two, has been
# lied to by the preview.
try:
    tk.build_bundle(_BAD_BUNDLE, os.path.join(tempfile.gettempdir(), "aoe2mod bad bundle"),
                    title="bad", author="test")
    raise AssertionError("a bundle of only-bad sentences built anyway")
except _C.IntentError as _exc:
    assert str(_exc) == _msg, "preview said %r, build said %r" % (_msg, str(_exc))
    print("  the preview and the build refuse it with the same words")

# An empty bundle is a no-op that would emit a mod changing nothing.
try:
    tk.build_bundle([], os.path.join(tempfile.gettempdir(), "aoe2mod empty bundle"),
                    title="empty", author="test")
    raise AssertionError("an empty bundle was accepted")
except _C.IntentError as _exc:
    # The refusal is printed on screen, so it is Chinese; asserting the English
    # phrase that used to be here would have passed only until it was translated.
    assert "这个组合里一句都没有" == str(_exc), str(_exc)
    assert not re.search(r"[A-Za-z]{2,}", str(_exc)), str(_exc)
    print("  an empty bundle is refused rather than emitting a no-op mod")

# A bundle may MIX strategies.  Their products are different FILES -- the byte
# patcher writes .dat, the JSON strategy writes CivTechTrees/<CIV>.json -- and
# one mod folder can carry both.  Before the split, the .dat fold refused the
# whole sentence list, so "villagers are tougher AND Britons can build
# Huskarls" was impossible even though each half worked alone.  The failure was
# loud, but the request was still unbuildable.
_MIX_INTENTS = [
    {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 5},
    # By id: the NAME "Huskarl" is ambiguous (41 and 759 are both 近卫军).
    {"intent": "unit.availability", "unit": 41, "civ": "British",
     "action": "grant"},
    # And one in the TECH space, which is the same machinery over a different
    # namespace.  With no tech sentence here a dropped `use_types` in
    # `_apply_availability_bundle` or `_availability_verification` would be
    # invisible: the shape of the answer is identical either way.
    {"intent": "tech.availability", "tech": 3, "civ": "Goths",
     "action": "grant"},
]
_pmb = tk.plan_bundle(_MIX_INTENTS)
assert _pmb["edit_count"] > 0, "the .dat half of a mixed bundle must carry edits"
assert len(_pmb["availability"]) == 2, _pmb["availability"]
assert [n["civ"] for n in _pmb["availability"]] == ["BRITONS", "GOTHS"], \
    _pmb["availability"]
assert _pmb["availability"][0]["node_id"] == 41, _pmb["availability"]
assert _pmb["availability"][1]["node_id"] == 3, _pmb["availability"]
assert {n["space"] for n in _pmb["availability"]} == {"Unit", "Tech"}, \
    "the two notes must be distinguishable by id space: %r" \
    % [n.get("space") for n in _pmb["availability"]]
print("  a mixed bundle previews ALL THREE ways: .dat edits %d, JSON civs %s"
      % (_pmb["edit_count"], [(n["civ"], n["space"])
                              for n in _pmb["availability"]]))

# The preview runs the WRITE path (`_apply_availability_bundle`) on a throwaway
# copy.  If that copy were shallow, planning would silently grant the unit in
# the tool's cached picture of the game -- and the next preview would say "it
# already has it".  A preview that changes the answer to the next preview is
# indistinguishable, to a user, from a preview that changed the game.
_p_again = tk.plan_bundle([_MIX_INTENTS[1]])
assert _p_again["availability"][0]["civ"] == "BRITONS", _p_again["availability"]
assert _p_again["availability"][0]["description"] == \
    _pmb["availability"][0]["description"], \
    "planning a bundle changed what planning it again says"
_p_single = tk.plan(_MIX_INTENTS[1])
assert _p_single.get("editable") is True and _p_single.get("mode") == "add_row", \
    "a bundle preview mutated the cached tech trees: %r" % _p_single
print("  and the preview leaves the cached trees untouched")

_mix_root = tempfile.mkdtemp(prefix="aoe2mod mixed ")
_mix_dir = os.path.join(_mix_root, "mixed")
_mix = tk.build_bundle(_MIX_INTENTS, _mix_dir, title="mixed", author="test")
assert _mix["mod_contains_dat"] is True, "the .dat half must be in the mod"
assert _mix["edit_count"] > 0, _mix["edit_count"]
assert _mix["json_overrides"], _mix.get("json_overrides")
# Both TREE files must be in the mod, and so must the pre-baked PANEL file: an
# availability sentence that lands only in the tree changes a document the menu
# may never consult.  Asserted by predicate rather than by count, because the
# count went stale the moment the panel half was wired in -- and a count that
# encodes today's file list would fail again the next time a layer is added.
_mix_trees_out = [r for r in _mix["json_overrides"] if "CivTechTrees/" in r]
_mix_panel_out = [r for r in _mix["json_overrides"]
                  if "futuravailableunits" in r or "paphosfutureavailableunits" in r]
assert sorted(os.path.basename(r) for r in _mix_trees_out) == ["BRITONS.json", "GOTHS.json"], \
    "both tree files must be in the mod: %s" % _mix["json_overrides"]
assert _mix_panel_out, \
    "the panel half is missing from the mod: %s" % _mix["json_overrides"]
# Both products must actually exist on disk; a manifest claiming a file it did
# not write is the same "promise vs delivery" failure the bundle exists to kill.
assert os.path.isfile(_mix["dat"]), _mix["dat"]
_mix_json = os.path.join(_mix_dir, _mix["json_overrides"][0].replace("/", os.sep))
assert os.path.isfile(_mix_json), _mix_json
for _rel in _mix["json_overrides"]:
    assert os.path.isfile(os.path.join(_mix_dir, _rel.replace("/", os.sep))), _rel
print("  and BUILDS one mod carrying both spaces: %s + %s"
      % (os.path.basename(_mix["dat"]),
         " + ".join(os.path.basename(r) for r in _mix["json_overrides"])))

# The JSON half must reach the tree when read back the way the engine reads it,
# IN THE RIGHT SPACE: the unit went to BRITONS, the tech to GOTHS.
_mix_trees = _CT.load_trees(_mix_dir)
_mix_tree = _mix_trees["BRITONS"]
assert _CT.has(_mix_tree, 41), "the granted unit is absent from the emitted tree"
assert _CT.node_status(_mix_tree, 41) == "ResearchedCompleted", _mix_tree
_mix_tech = _mix_trees["GOTHS"]
assert _CT.has(_mix_tech, 3, _CT.TECH_USE_TYPES), \
    "the granted technology is absent from the emitted tree"
# The spaces must not leak into each other.  Assert it as a PER-SPACE row delta,
# not as "does not have the other node": both chosen nodes already belong to the
# other civilization (Huskarl is GOTHS's own unit, Yeomen is BRITONS's own tech),
# so "GOTHS has unit 41" is true before the build and would prove nothing.  What
# only the cross-space routing can explain is that each file gained a row in
# exactly ONE space.
_orig = tk._trees()


def _space_rows(tree):
    return (len(_CT.unit_rows(tree)), len(_CT.tech_rows(tree)))


for _civ, _node, _ut in (("BRITONS", 41, _CT.UNIT_USE_TYPES),
                         ("GOTHS", 3, _CT.TECH_USE_TYPES)):
    _b, _a = _space_rows(_orig[_civ]), _space_rows(_mix_trees[_civ])
    _want = (_b[0] + 1, _b[1]) if _ut == _CT.UNIT_USE_TYPES else (_b[0], _b[1] + 1)
    assert _CT.has(_mix_trees[_civ], _node, _ut), \
        "%s did not get node %s in space %s" % (_civ, _node, _ut)
    assert _a == _want, \
        "%s gained a row in the wrong id space: %s -> %s (wanted %s)" \
        % (_civ, _b, _a, _want)
assert _CT.node_status(_mix_tree, 3, use_types=_CT.TECH_USE_TYPES) \
    == _CT.node_status(_orig["BRITONS"], 3, use_types=_CT.TECH_USE_TYPES), \
    "BRITONS's tech rows moved, but only a UNIT was granted to them"
print("  the emitted trees grant a UNIT to BRITONS and a TECH to GOTHS, with no "
      "leak between the spaces")

# A bundle of only REVOKE availability sentences DOES edit the .dat now -- see
# the note below the build call, which has the date and the in-game evidence.
# The paragraph that used to sit here said the opposite ("must not CHANGE any
# .dat byte") and described the mod as carrying an unmodified copy; that was
# true until `dsh test v17` (2026-10-19) and was left behind when the assertion
# was corrected, so it is rewritten rather than deleted: what stays true is WHY
# a .dat is in the mod at all (the game fails to start when a mod overrides
# `resources/_common/dat/` without `empires2_x2_p1.dat`, reported by the user in
# game twice -- `_probe/test_dat_carrier.py`).  A carrier is still the right
# answer for any JSON-only edit; it is simply no longer what a revoke emits.
#
# GRANT is the other case now, and it is the one this section got wrong.  A
# grant has a `.dat` half (the recipe the user confirmed in game, m27131), so
# `changes_dat` is True and NO carrier is involved: the file IS the edit.  The
# two blocks below are deliberately adjacent -- when `changes_dat` was hardwired
# to `bool(dat_list)` the grant reported True *for the wrong reason*, which is
# exactly how it stayed wrong.
_rev = {"intent": "unit.availability", "unit": 41, "civ": "Goths",
        "action": "revoke"}
_only = tk.build_bundle([_rev],
                        os.path.join(_mix_root, "revoke"),
                        title="revoke", author="test")
# A REVOKE has had a verified `.dat` half since 2026-10-19 (`dsh test v17`: the
# Incas lost the Champi Scout, but only from the Castle Age -- the last command to
# fire wins).  So this bundle now EDITS the .dat rather than carrying it, and the
# block that used to assert the opposite was pinning a fact that had stopped
# being true.  What it must still assert is that the edit is accounted for:
# `changes_dat`, a non-carrier `.dat`, and a count matching the recipe's edits.
assert _only["changes_dat"] is True, _only["changes_dat"]
assert _only["dat_is_carrier"] is False, _only["dat_is_carrier"]
assert _only["mod_contains_dat"] is True, _only["mod_contains_dat"]
assert _only["dat_half_edit_count"] > 0, _only["dat_half_edit_count"]
assert _only["edit_count"] == _only["dat_half_edit_count"], \
    (_only["edit_count"], _only["dat_half_edit_count"])
assert _only["dat_half"] and _only["dat_half"][0].get("ok") is True, \
    "a revoke must report the `.dat` work it did (or why it refused): %r" \
    % (_only["dat_half"],)
assert _only["verification"]["ok"] is True, _only["verification"]
assert [f for f in os.listdir(os.path.join(_mix_root, "revoke", "resources",
                                           "_common", "dat"))
        if f.endswith(".dat")], "a revoke bundle shipped NO .dat"
print("  a revoke-only bundle edits the .dat, counts the edit, and verifies")

# ...and the GRANT-only bundle is the one that must ship real `.dat` bytes.
#
# This is the defect `_probe/probe_bundle_dat_half.py` measured: the bundle path
# ran the tree and panel halves, emitted a `.dat` byte-identical to the base, and
# reported `changes_dat: True` only because an unrelated sentence had set it.  A
# user got a mod with two thirds of the grant and a manifest describing all of it.
_gr = {"intent": "unit.availability", "unit": 2550, "civ": "British",
       "action": "grant"}
_gr_root = os.path.join(_mix_root, "grant only")
_grp = tk.plan_bundle([_gr])
assert _grp["changes_dat"] is True, _grp["changes_dat"]
assert _grp["dat_is_carrier"] is False, _grp["dat_is_carrier"]
assert _grp["dat_half_edit_count"] == 2, _grp["dat_half_edit_count"]
assert _grp["dat_half_refusals"] == [], _grp["dat_half_refusals"]
_grb = tk.build_bundle([_gr], _gr_root, title="grant only", author="test")
assert _grb["edit_count"] == _grp["edit_count"] == 2, \
    "preview %r vs build %r" % (_grp["edit_count"], _grb["edit_count"])
assert _grb["dat_half_edit_count"] == 2, _grb["dat_half_edit_count"]
_gr_raw, _ = P.load_dat(_grb["dat"])
_gr_base, _ = P.load_dat(os.path.join(
    tk.game_root, "resources", "_common", "dat", "empires2_x2_p1.dat"))
assert len(_gr_raw) > len(_gr_base), \
    "a grant-only bundle shipped a .dat that is not actually edited (an effect " \
    "must have been appended): %d vs %d" % (len(_gr_raw), len(_gr_base))
_grp2 = P.Parser(_gr_raw)
with contextlib.redirect_stdout(io.StringIO()):
    _grp2.parse()
assert _grp2.r.pos == len(_gr_raw), "the shipped .dat does not reparse cleanly"
assert _grp2.stats["techs"][383]["effect_id"] == len(_grp2.stats["effects"]) - 1, \
    "the anchor technology was not re-pointed at the appended effect"
print("  a grant-only bundle WRITES the .dat half (%d edit(s), +%d bytes) and "
      "previews exactly what it ships"
      % (_grb["dat_half_edit_count"], len(_gr_raw) - len(_gr_base)))

# BOTH at once, into ONE panel file.
#
# This is the second defect in this area, found by building `dsh test v9`.  Each
# `_panel_availability` call started from the SHIPPED 1.3 MB text, so both
# returned a complete file and the caller's `files.update()` let the later one
# overwrite the earlier one.  "Grant the Champi Scout to the British AND revoke
# it from the Incas" shipped only the revoke while the manifest described both.
#
# The two sentences must therefore CHAIN: the second starts from the first's
# text.  A test that exercises only one of them cannot see this.
from aoe2mod.game import buildpanel as _BP
_both_root = os.path.join(_mix_root, "both panel edits")
_both = [
    {"intent": "unit.availability", "unit": 2550, "civ": "British",
     "action": "grant"},
    {"intent": "unit.availability", "unit": 2550, "civ": "Incas",
     "action": "revoke"},
]
_bman = tk.build_bundle(_both, _both_root, title="both panel edits",
                        author="test")
_bp = json.load(open(os.path.join(
    _both_root, "resources", "_common", "dat", "futuravailableunits.json"),
    "r", encoding="utf-8"))

def _panel_listings(panel_obj, civ_name, unit_id):
    key = _BP.civ_key_for(panel_obj, civ_name)
    out = []
    for _blk in _BP.buildings(panel_obj, key):
        for _e in _BP.entries(panel_obj, key, _blk.get("ID"), _BP.UNITS_KEY):
            if int(_e.get("ID", -1)) == unit_id:
                out.append(_blk.get("ID"))
    return out

assert _panel_listings(_bp, "British", 2550) == [12], \
    "the GRANT was lost when a later sentence edited the same panel file: %r" \
    % (_panel_listings(_bp, "British", 2550),)
assert _panel_listings(_bp, "Incas", 2550) == [], \
    "the REVOKE was lost: %r" % (_panel_listings(_bp, "Incas", 2550),)
_shipped_panel, _shipped_obj = __import__(
    "aoe2mod.game.buildpanel", fromlist=["x"]).load_panel(os.path.join(
        tk.game_root, "resources", "_common", "dat",
        "futuravailableunits.json"))
assert _panel_listings(_shipped_obj, "Incas", 2550) == [12], \
    "the shipped file is supposed to list this for the Incas, or the revoke " \
    "half of this test proves nothing"
print("  two sentences editing ONE panel file both survive "
      "(grant -> British, revoke -> Incas)")

# ...and the same panel file must still verify as surgical for BOTH.
for _n in _bman.get("availability", {}).get("civs", []) or []:
    _v = _n.get("verification") if isinstance(_n, dict) else None
    if _v:
        assert _v.get("ok") is True, _v
print("  and each per-civ panel verification still passes")
shutil.rmtree(_mix_root, ignore_errors=True)

# 8f. describe() must answer "who can build this" WITHOUT planning an edit.
# The write side could already grant/revoke, but a unit detail panel needs the
# answer before the user decides anything.  `civ_count` is NOT that answer: it
# counts .dat RECORDS, and every unit has 63 of them whether or not anybody can
# build it (Huskarl: civ_count 63, builders 1).
_d41 = tk.describe(41)
_av = _d41.get("availability")
assert _av is not None, "describe() reports no availability for Huskarl"
assert _av["holders"] == ["GOTHS"], _av
assert _av["builders"] == ["GOTHS"], _av
assert len(_av["absent_from"]) == 61, len(_av["absent_from"])
assert _d41["civ_count"] == 63 and _av["builder_count"] == 1, \
    "civ_count (%d) is the record count, builders (%d) is the answer" \
    % (_d41["civ_count"], _av["builder_count"])
print("  describe() answers availability: Huskarl holders/builders %r, .dat records %d"
      % (_av["builders"], _d41["civ_count"]))

# The decisive case: War Galley is `ResearchRequired` for all 56 dock civs, so a
# reader using has() would say NOBODY can build it.  holders and builders must be
# different lists, and this is the node that proves the two are not one question.
_av21 = tk.describe(21)["availability"]
assert _av21 is not None, "War Galley has no availability"
assert _av21["holder_count"] == 0, _av21["holders"]
assert _av21["builder_count"] == 56, _av21["builders"]
assert _av21["pending_in"] == _av21["builders"], \
    "every War Galley builder should be pending research"
assert len(_av21["absent_from"]) == 6, _av21["absent_from"]
print("  and separates holder from builder: War Galley holders %d, builders %d"
      % (_av21["holder_count"], _av21["builder_count"]))

# A unit genuinely gated off must be reported as blocked, not as absent: it is
# LISTED in the tree with NotAvailable, which needs a status change, not a row.
_av5 = tk.describe(5)["availability"]
assert _av5["holder_count"] == 1 and _av5["builder_count"] == 24, _av5
assert len(_av5["blocked_in"]) == 38 and not _av5["absent_from"], _av5
print("  and keeps 'listed but unobtainable' (%d civs) apart from 'absent' (%d)"
      % (len(_av5["blocked_in"]), len(_av5["absent_from"])))

# Everything reported for a real unit must be a real answer; a field present but
# None would make the UI render "None" as if it were a name.
for _k in ("holders", "builders", "absent_from", "blocked_in", "pending_in"):
    assert _av[_k] is not None, _k
    assert all(isinstance(x, str) for x in _av[_k]), (_k, _av[_k])

# A .dat record that is NOT in any tech tree cannot answer this question at all,
# so `availability` must be None rather than an empty answer that looks like
# "nobody can build it".
#
# Which records those are is NOT "buildings".  Id 12 = Barracks and 82 = Castle
# are unit records in the .dat, and the engine keeps their build rows in a
# SECOND tech-tree key (`civ_techs_buildings`, `Use Type` = Building).  Until
# 2026-10-31 the read side asked the Unit space only, so `describe(12)` said
# "in no tech tree" about the Barracks -- which all 62 civs can build -- and
# that sentence was the defect, not the answer.  The unit branch now passes
# `CT.UNIT_USE_TYPES + CT.BUILDINGS_USE_TYPES`, so 12 answers 62/62.
#
# The ids kept below are records with zero rows in every space, measured across
# all 62 files: 1 is Rome's legion record, 10 the legacy Archery-Range record.
for _uid in (1, 10):
    assert tk.describe(_uid).get("availability") is None, \
        "unit %d is not in any tech tree, so availability must be None" % _uid
_av12 = tk.describe(12).get("availability")
assert _av12 is not None and _av12["builder_count"] == 62, \
    "the Barracks is a Building row, not a missing record: %r" % (_av12,)
print("  not-in-any-tech-tree records report availability None, not empty lists;"
      " and the Barracks answers 62/62 out of the Building key")

# The donor's Building ID is where the copied row would be produced.  When the
# receiving civ cannot reach that building, the plan must SAY SO in its own
# sentence -- buried among the six cosmetic "inherited ..." lines it reads like
# decoration, and the user has no other clue.  Hand-verified case: ARMENIANS has
# no building 104 anywhere in its 173 rows (its own Monk reads 1806), while
# BRITONS does.  Same request, different truth for the two civs.
# These sentences are shown to the player verbatim, so the assertions look for
# the FACT (the tree has no such building / the field was copied) rather than one
# English phrase: pinning the wording turned a translation into a crash.
_pa = tk.plan({"intent": "unit.availability", "unit": 775,
               "civ": "Armenians", "action": "grant"})
_pb = tk.plan({"intent": "unit.availability", "unit": 775,
               "civ": "British", "action": "grant"})
_warn = "科技树里根本没有这座建筑"
assert _pa.get("editable") is True, _pa
assert any(_warn in w for w in (_pa.get("warnings") or [])), _pa.get("warnings")
assert not any(_warn in w for w in (_pb.get("warnings") or [])), _pb.get("warnings")
assert any("建筑编号" in w and "照抄" in w for w in _pb.get("warnings") or []), \
    "the plain inherited-Building-ID note must still be emitted: %s" % _pb
print("  and names a building the receiver can't reach, silently for one that can")

# 8f-2. the TECH space.  A technology's availability lives in the same files but
# a DIFFERENT id space: a tech row's Node ID is the .dat tech ARRAY INDEX, and
# the whole point is that id 8 names a Longbowman row in one space and a Town
# Watch row in the other.  So the two answers must be obtained independently --
# dropping `use_types` anywhere answers confidently about the wrong entity.
_av_t = tk.describe(22, kind="tech").get("availability")
assert _av_t is not None, "Loom has no availability in the tech space"
assert _av_t["space"] == "Tech", _av_t["space"]
assert _av_t["builder_count"] == 62, _av_t["builder_count"]
assert len(_av_t["builders"]) == 62, len(_av_t["builders"])
# The same integer, asked as a unit, must NOT be handed the tech's answer.
assert tk.describe(8, kind="unit")["availability"]["space"] == "Unit", \
    "unit id 8 was answered from the tech space"
assert tk.describe(8, kind="tech")["availability"]["space"] == "Tech", \
    "tech id 8 was answered from the unit space"
# A UniqueTech is one civ's, in both directions.
_av_y = tk.describe(3, kind="tech")["availability"]
assert _av_y["holders"] == ["BRITONS"], _av_y["holders"]
assert _av_y["builders"] == ["BRITONS"], _av_y["builders"]
print("  describe() answers technology availability: Loom offered by %d civs, "
      "Yeomen by %r" % (_av_t["builder_count"], _av_y["builders"]))

# A grant into the tech space, planned and built like any other intent.  The
# checks that matter are the ones a dropped `use_types` would pass: the row that
# lands must be a TECH row and the unit rows must be untouched.
_t_plan = tk.plan({"intent": "tech.availability", "tech": 3, "civ": "Goths",
                   "action": "grant"})
assert _t_plan["editable"] is True, _t_plan.get("reason")
assert _t_plan["space"] == "Tech", _t_plan
assert "研究" in _t_plan["description"], _t_plan["description"]
assert "建造" not in _t_plan["description"], _t_plan["description"]
_tech_root = tempfile.mkdtemp(prefix="aoe2mod tech avail ")
try:
    _t_man = tk.build({"intent": "tech.availability", "tech": 3,
                       "civ": "Goths", "action": "grant"},
                      os.path.join(_tech_root, "tech mod"),
                      title="Goths get Yeomen", author="aoe2mod test")
    assert _t_man["verification"]["ok"] is True, _t_man["verification"]
    assert _t_man["space"] == "Tech", _t_man
    assert _t_man["node_id"] == 3, _t_man
    assert "technology" in " ".join(_t_man["verification"]["not_proven"]), \
        _t_man["verification"]["not_proven"]
    _t_back = _CT.load_trees(os.path.join(_tech_root, "tech mod"))
    _t_key = _CT.civ_file_stem("Goths")
    assert list(_t_back) == [_t_key], list(_t_back)
    assert _CT.has(_t_back[_t_key], 3, _CT.TECH_USE_TYPES), \
        "the granted technology is absent from the emitted tree"
    assert len(_CT.rows_of(_t_back[_t_key])) == \
        len(_CT.rows_of(tk._trees()[_t_key])) + 1, "not exactly one row added"
    # `os.listdir` on the mod ROOT only ever shows `info.json` and `resources`,
    # so the old assertion here (`".dat" not in the listing`) was true for every
    # possible mod and pinned nothing.  What is true, and worth pinning, is the
    # emitter's carrier rule: a JSON file under `resources/_common/dat/` forces
    # the base `.dat` along or the game will not start -- so the tech mod DOES
    # carry one, byte-identical to the shipped file.
    _t_dat = os.path.join(_tech_root, "tech mod", "resources", "_common", "dat",
                          "empires2_x2_p1.dat")
    assert os.path.isfile(_t_dat), "the tech mod lost its carrier .dat"
    assert _t_man["dat_is_carrier"] is True and _t_man["changes_dat"] is False, \
        {k: _t_man.get(k) for k in ("dat_is_carrier", "changes_dat")}
finally:
    shutil.rmtree(_tech_root, ignore_errors=True)
print("  a tech.availability build adds one TECH row, edits no .dat byte, and "
      "carries the shipped .dat unchanged")

# 8f-3. the BUILD-PANEL half.  An availability edit has to land in both the tree
# file and the pre-baked panel file the menu is supplied from, because the tree
# write alone proved nothing in game (2026-10-14).  These assertions pin the
# three shapes the panel half can take, because collapsing them would let the
# product claim a no-op as a success:
#   * the panel ALREADY lists the node -> an honest no-op, no panel file shipped;
#   * the panel lacks it -> an entry is synthesised from a measured donor;
#   * a revoke -> the entry comes out.
# `_panel_plan_ok`-style shadowing is avoided on purpose: the report is read from
# the same build that wrote the files.
_BP = _BP_MODULE
_panel_root = tempfile.mkdtemp(prefix="aoe2mod panel avail ")
try:
    # A grant that is real work for the TREE and none for the PANEL: the shipped
    # files disagree here (tree NotAvailable, panel lists it) -- measured, not
    # guessed, via `_probe/probe_panel_wire_cases.py`.
    _d_before = tk.plan({"intent": "unit.availability", "unit": 569,
                         "civ": "Armenians", "action": "grant"})
    assert _d_before["editable"] is True, _d_before
    _m1 = tk.build({"intent": "unit.availability", "unit": 569,
                    "civ": "Armenians", "action": "grant"},
                   os.path.join(_panel_root, "noop"),
                   title="t", author="aoe2mod test")
    assert _m1["panel"]["ok"] is True, _m1["panel"]
    assert _m1["panel"]["mode"] == "none", _m1["panel"]
    assert _m1["panel"]["panel_name"] == "futuravailableunits.json", _m1["panel"]
    _f1 = sorted(os.path.relpath(os.path.join(r, n),
                 os.path.join(_panel_root, "noop")).replace(os.sep, "/")
                 for r, _d, ns in os.walk(os.path.join(_panel_root, "noop"))
                 for n in ns)
    assert not any("futuravailableunits" in f for f in _f1), \
        "a no-op panel edit still shipped the 1.3 MB panel file: %s" % _f1
    assert any("CivTechTrees" in f for f in _f1), _f1

    # A grant the panel cannot already satisfy -> a synthesised entry, and the
    # entry must come from a donor that really lists it (not invented).
    _m2 = tk.build({"intent": "unit.availability", "unit": 5,
                    "civ": "British", "action": "grant"},
                   os.path.join(_panel_root, "add"),
                   title="t", author="aoe2mod test")
    assert _m2["panel"]["mode"] == "add_entry", _m2["panel"]
    assert _m2["panel"]["before_entries"] == 0, _m2["panel"]
    assert _m2["panel"]["after_entries"] == 1, _m2["panel"]
    assert _m2["panel"]["entry"]["ID"] == 5, _m2["panel"]["entry"]
    assert _m2["panel"]["donor"], "the synthesised entry records no donor"
    # The building comes from the RECEIVER's own tree row, so read it from there
    # instead of repeating the literal -- the assertion must fail if the product
    # placed the entry under some other building.
    _b_bldg = _CT.row_for(tk._trees()["BRITONS"], 5, _CT.UNIT_USE_TYPES)["Building ID"]
    _p_txt, _p_obj = _BP.load_panel(os.path.join(
        _panel_root, "add", "resources", "_common", "dat",
        "futuravailableunits.json"))
    assert _BP.has_entry(_p_obj, "Britons", _b_bldg, 5, _BP.UNITS_KEY), \
        "the emitted panel does not list the granted unit"
    # The panel edit must be surgical: the other civilizations' bytes are the
    # shipped ones, so a diff that touched them would be a corrupted menu.
    _p_before, _ = _BP.load_panel(os.path.join(tk.game_root, _BP.PANEL_REL))
    _ok_s, _info_s = _BP.verify_surgical(_p_before, _p_txt)
    assert _ok_s is True, _info_s
    assert _info_s["kind"] == "insert", _info_s
    assert _info_s["outside_is_untouched"] is True, _info_s
    # ...and the entry's RequiredAge is inherited from the target's own tree row,
    # not from the donor's, or the menu would gate it at the wrong age.
    assert _m2["panel"]["entry"]["RequiredAge"] == \
        _CT.row_for(tk._trees()["BRITONS"], 5, _CT.UNIT_USE_TYPES)["Age ID"], \
        _m2["panel"]["entry"]

    # A revoke really removes one, and says how many it found before.
    _m3 = tk.build({"intent": "unit.availability", "unit": 692,
                    "civ": "Vikings", "action": "revoke"},
                   os.path.join(_panel_root, "revoke"),
                   title="t", author="aoe2mod test")
    assert _m3["panel"]["mode"] == "remove_entry", _m3["panel"]
    assert _m3["panel"]["removed"] == 1, _m3["panel"]
    assert (_m3["panel"]["before_entries"], _m3["panel"]["after_entries"]) == \
        (1, 0), _m3["panel"]

    # The TECH space.  A tech ROW carries a Building ID when the civ has one,
    # and `row_for` returns None when it does not -- so the panel half must fall
    # back to the same donor `CT.donor_row` picks for the tree file, and must say
    # it did.  Without that fallback a legal grant fails with "no building is
    # known", which is a lie: Britons has it.
    _m4 = tk.build({"intent": "tech.availability", "tech": 3, "civ": "Goths",
                    "action": "grant"},
                   os.path.join(_panel_root, "tech"),
                   title="t", author="aoe2mod test")
    assert _m4["space"] == "Tech", _m4
    assert _m4["panel"]["mode"] == "add_entry", _m4["panel"]
    assert _m4["panel"]["building_from"] == "BRITONS", _m4["panel"]
    assert _m4["panel"]["donor"] == "Britons", _m4["panel"]
    # The building is the DONOR ROW's `Building ID`, looked up rather than
    # written down: Yeomen is a Castle tech, so guessing "109" from a nearby
    # probe would have asserted the wrong building and passed for the wrong
    # reason.  The measured value is asserted against the row it came from.
    _dr_civ, _dr = _CT.donor_row(tk._trees(), 3, _CT.TECH_USE_TYPES)
    assert _dr_civ == "BRITONS", _dr_civ
    _dr_bldg = _dr["Building ID"]
    _tp_txt, _tp_obj = _BP.load_panel(os.path.join(
        _panel_root, "tech", "resources", "_common", "dat",
        "futuravailableunits.json"))
    assert _BP.has_entry(_tp_obj, "Goths", _dr_bldg, 3, _BP.TECHS_KEY), \
        ("the granted technology is not in the panel's Techs array under "
         "building %r" % _dr_bldg)
    # ...and exactly once: a duplicate would draw the button twice.
    assert _BP.count_entries(_tp_obj, "Goths", 3, _BP.TECHS_KEY) == 1, \
        _BP.count_entries(_tp_obj, "Goths", 3, _BP.TECHS_KEY)
finally:
    shutil.rmtree(_panel_root, ignore_errors=True)
print("  an availability build also edits the pre-baked build panel, and a "
      "no-op panel is reported rather than shipped")

# 8g. the loose-file strategy: a reskin writes .sld files and no .dat at all.
# The three things worth pinning are (a) it routes to the loose path rather than
# trying to patch bytes, (b) it ships BOTH x1 and x2 for every animation, and
# (c) its manifest carries the honesty boundary -- without it a caller reading
# `proven`/`not_proven` finds the key absent exactly where the doubt is largest.
_sprite_plan = tk.plan({"intent": "unit.sprite", "unit": "弓兵", "donor": "长弓兵"})
assert _sprite_plan["editable"] is True, _sprite_plan.get("reason")
assert _sprite_plan["changes_dat"] is False, _sprite_plan
assert _sprite_plan["mod_contains_dat"] is False, _sprite_plan
assert _sprite_plan["edit_count"] == _sprite_plan["file_count"] > 0, _sprite_plan
assert "长弓兵" in _sprite_plan["description"] or "Longbowman" in _sprite_plan["description"], \
    _sprite_plan["description"]
_sprite_root = tempfile.mkdtemp(prefix="aoe2mod sprite ")
try:
    _s_man = tk.build({"intent": "unit.sprite", "unit": "弓兵", "donor": "长弓兵"},
                      os.path.join(_sprite_root, "sprite mod"),
                      title="弓兵变成长弓兵", author="aoe2mod test")
    assert _s_man["changes_dat"] is False, _s_man
    assert not _s_man.get("dat"), "a reskin must not ship a .dat: %s" % _s_man.get("dat")
    _s_files = [f["rel"] for f in _s_man["files"] if f["rel"].endswith(".sld")]
    assert _s_files, "no .sld files were emitted"
    assert all(f.startswith("resources/_common/drs/graphics/") for f in _s_files), _s_files
    # x1 and x2 travel together: replacing only one makes UHD and HD disagree.
    _s_names = sorted(os.path.basename(f) for f in _s_files)
    _s_x1 = [n for n in _s_names if n.endswith("_x1.sld")]
    _s_x2 = [n for n in _s_names if n.endswith("_x2.sld")]
    assert len(_s_x1) == len(_s_x2) == len(_s_x1) > 0, (_s_x1, _s_x2)
    assert sorted(n.replace("_x1.sld", "") for n in _s_x1) == \
        sorted(n.replace("_x2.sld", "") for n in _s_x2), "x1/x2 pairs do not line up"
    _s_dir = os.path.join(_sprite_root, "sprite mod", "resources", "_common",
                          "drs", "graphics")
    assert sorted(os.listdir(_s_dir)) == _s_names, os.listdir(_s_dir)
    _s_ver = _s_man["verification"]
    assert _s_ver["ok"] is True, _s_ver
    # The honesty boundary has to be present AND has to say the load is untested;
    # the module promises this in its own docstring, so a missing key is a
    # silent regression in the one place a caller looks for doubt.
    assert _s_ver.get("proven") and _s_ver.get("not_proven"), _s_ver
    _s_doubt = " ".join(_s_ver["not_proven"])
    assert "sld" in _s_doubt, _s_doubt
    assert "running game" in _s_doubt, _s_doubt
    assert not _s_ver.get("identical_to_target"), _s_ver
    # The frame grid: the engine pairs an animation with the art by
    # frame_count/angle_count and then plays the wrong frames rather than
    # refusing, so the preview must carry the structured numbers, not only a
    # sentence.  "Archer <- Longbowman" changes the death grid (45x16 vs 30x16).
    assert _sprite_plan.get("grid_mismatches"), _sprite_plan.get("warnings")
    _s_anims = [g["animation"] for g in _sprite_plan["grid_mismatches"]]
    assert "death" in _s_anims, _s_anims
    _s_gm0 = _sprite_plan["grid_mismatches"][0]
    assert _s_gm0["target"] and _s_gm0["donor"], _s_gm0
    assert any("帧格子" in w for w in _sprite_plan.get("warnings") or ()), \
        _sprite_plan.get("warnings")
    # ... and a swap whose grids agree must not invent one.
    _s_ok = tk.plan({"intent": "unit.sprite", "unit": 594, "donor": 4})
    if _s_ok.get("editable"):
        assert not _s_ok.get("grid_mismatches") or \
            _s_ok["grid_mismatches"] == [], _s_ok["grid_mismatches"]
finally:
    shutil.rmtree(_sprite_root, ignore_errors=True)
print("  a reskin routes to the loose-file path, ships paired x1/x2 .sld files, "
      "no .dat, and states the in-game load as unproven")

# 8g. a reskin sentence INSIDE a bundle.
# Before the `loose_files` strategy joined `_split_by_strategy`, this exact list
# raised "intent 'unit.sprite' declares compile strategy 'loose_files', which
# this build does not implement" -- the single-intent entry point accepted a
# request the bundle entry point refused.  A player asking for "villagers are
# tougher AND the archer looks like a longbowman" got an error, and the two
# halves worked fine one at a time.
_sb_root = tempfile.mkdtemp(prefix="aoe2mod sprite bundle ")
try:
    _sb = [
        {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 5},
        {"intent": "unit.sprite", "unit": 4, "donor": 8},
    ]
    _sb_plan = tk.plan_bundle(_sb)
    assert _sb_plan["sprite_refusals"] == [], _sb_plan["sprite_refusals"]
    assert len(_sb_plan["sprites"]) == 1, _sb_plan["sprites"]
    assert _sb_plan["sprite_file_count"] == 20, _sb_plan["sprite_file_count"]
    _sb_man = tk.build_bundle(_sb, os.path.join(_sb_root, "mixed"),
                              title="mixed sprite bundle", author="aoe2mod test")
    _sb_sld = [f["rel"] for f in _sb_man["files"] if f["rel"].endswith(".sld")]
    assert len(_sb_sld) == 20, len(_sb_sld)
    assert _sb_man["mod_contains_dat"] is True, _sb_man
    assert _sb_man["sprite_verification"]["ok"] is True, _sb_man["sprite_verification"]
    # The number on the preview has to be the number the build writes, counting
    # FILES for the reskin and BYTES-IN-PLACE for the .dat.  Counting only the
    # byte patcher's edits is how a bundle previews 1,701 and ships 1,721.
    assert _sb_plan["edit_count"] == _sb_man["edit_count"], \
        (_sb_plan["edit_count"], _sb_man["edit_count"])

    # Two sentences that need ONE file to hold two pictures.  `reskin.plan` guards
    # this INSIDE a sentence, but a bundle is where two sentences first meet, so
    # without a second guard in `_sprite_bundle` the later one would overwrite the
    # earlier in silence while the manifest described both.
    _sb_clash = tk.plan_bundle([
        {"intent": "unit.sprite", "unit": 4, "donor": 8},
        {"intent": "unit.sprite", "unit": 4, "donor": 24},
    ])
    assert len(_sb_clash["sprite_refusals"]) == 1, _sb_clash["sprite_refusals"]
    _sb_why = _sb_clash["sprite_refusals"][0]["reason"]
    # Assert what the sentence MEANS, not the template that says it: this string
    # is printed on screen ("有一句没做成：<reason>") and will be reworded, and a
    # check pinned to the old wording turns silently into a no-op the day it is.
    assert "装不下两张" in _sb_why, _sb_why
    # No English template left in it.  A file name is DATA -- the player needs it
    # to see which file the two sentences met on -- so strip those before judging.
    assert not re.search(r"[A-Za-z]{2,}",
                         re.sub(r"[\w.\-]+\.(sld|png|dds)", " ", _sb_why)), _sb_why
    # Both sentences, in the user's own words.  An English unit name or a raw
    # filename would be the locator's key leaking onto the screen.
    assert "长弓兵" in _sb_why and "弩手" in _sb_why, _sb_why

    # ...and a bundle of NOTHING but reskins must still ship no .dat: a redundant
    # copy pins the file at today's bytes.
    _sb_only = tk.build_bundle([{"intent": "unit.sprite", "unit": 4, "donor": 8}],
                               os.path.join(_sb_root, "sld only"),
                               title="sld only bundle", author="aoe2mod test")
    assert _sb_only["mod_contains_dat"] is False, _sb_only
    assert _sb_only["verification"]["ok"] is True, _sb_only["verification"]
finally:
    shutil.rmtree(_sb_root, ignore_errors=True)
print("  and a reskin sentence composes into a bundle with a .dat sentence, "
      "counts its files in the preview, and refuses a cross-sentence clash "
      "by naming both sentences")

# 9. real installed mods, ordered by the engine's Priority
prof = G.find_profile_root()
print("\nprofile:", prof)
for m in tk.mods():
    print("  prio %-2s %-6s exists=%-5s %s"
          % (m["priority"], "on" if m["enabled"] else "off", m["exists"], m["name"][:58]))

print("\nALL API CHECKS PASSED")
