# -*- coding: utf-8 -*-
"""Full cross-product sweep: every (entity shape x every schema option).

The earlier scanner covered 4 of the 11 unit stats.  A schema option that no
test ever exercises is a schema option whose binding can be missing, misnamed
or wrongly typed without anyone noticing -- exactly how max_range/reload_time
sat unbound for months.  This sweeps the ENTIRE declared option space, so a
newly added stat is covered the moment it enters the schema.
"""
import os, sys, itertools, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from aoe2mod import api as A
from aoe2mod.intent import compiler as C

# The locator's own vocabulary, which must never reach a user.  Deliberately
# narrow: "训练时间[0]" and "研究时间[0]" keep an index on purpose.
_RAW_LABEL = re.compile(r"(cost type\s*\d+|attack cls\s*\d+|armour cls\s*\d+|"
                        r"location\[|train\[|creatable tail|hit_points|max_range)")

tk = A.open_toolkit()
intents_schema, bindings = C.load_schema()
_ = tk.version

STATS = intents_schema["intents"]["unit.stat"]["fields"]["stat"]["options"]
RES = intents_schema["intents"]["unit.cost"]["fields"]["resource"]["options"]
CLASS = intents_schema["intents"]["unit.attack_class"]["fields"]["kind"]["options"]
print("declared unit.stat options : %d %s" % (len(STATS), STATS))
print("declared cost resources    : %s" % (RES,))
print("declared attack_class kinds: %s" % (CLASS,))

UNITS = [12, 20, 70, 82, 10, 87, 4, 83, 38, 125, 448, 546, 209, 2418, 35, 2556]
TECHS = [22, 12, 13, 103, 102, 101, 50, 51, 430, 19, 0]

CASES = []
for uid in UNITS:
    for st in STATS:
        # a tiny positive delta keeps every non_negative field legal, so the
        # sweep measures binding coverage and not the sign guard.
        CASES.append({"intent": "unit.stat", "unit": uid, "stat": st, "delta": 1})
    for res in RES:
        CASES.append({"intent": "unit.cost", "unit": uid, "resource": res, "delta": 1})
    for k in CLASS:
        CASES.append({"intent": "unit.attack_class", "unit": uid, "kind": k, "delta": 1})
for tid in TECHS:
    CASES.append({"intent": "tech.research_time", "tech": tid, "delta": 1})
    for res in ("food", "wood", "gold", "stone"):
        CASES.append({"intent": "tech.cost", "tech": tid, "resource": res, "delta": 1})

# tech.effect was DECLARED in the schema and exercised by NO case here -- the
# one intent whose bytes land in a shared record had a handful of hand-written
# cases in test_tech_effect.py and nothing else.  The fix for the hole is the
# DECLARED_INTENTS check further down (schema-driven, so a seventh intent cannot
# slip through again); these cases exist so that check has something to find.
#
# Deliberately MINIMAL: one command, both directions.  Every case re-runs
# compile_intent, which re-walks the whole 85 MB tech section (~50 s), so the
# exhaustive version cannot live here -- it is _probe/sweep_tech_effect.py, which
# locates the arrays once and then checks every (tech, command) pair (8,005
# commands) in seconds.  This single case exists so the DECLARED_INTENTS guard
# below has something to find for `tech.effect`; it is not the coverage.
EFFECT_CASES = [{"intent": "tech.effect", "tech": 699, "command": 0, "delta": 1},
                {"intent": "tech.effect", "tech": 699, "command": 0, "delta": -1}]
CASES.extend(EFFECT_CASES)
print("tech.effect cases          : %d (exhaustive coverage in "
      "_probe/sweep_tech_effect.py)" % len(EFFECT_CASES))

# unit.availability is the first intent that does NOT compile by patching the
# .dat: its product is a CivTechTrees JSON file.  The generic loop below measures
# "plan agrees with compile_intent", and for this intent compile_intent refuses
# on purpose -- so it needs its own branch or it would be counted as a refusal
# and the guard would pass while testing nothing.  Both actions are listed so
# neither can go unexercised.
AVAIL_CASES = [{"intent": "unit.availability", "unit": 41, "civ": "British",
                "action": "grant"},
               {"intent": "unit.availability", "unit": 41, "civ": "Goths",
                "action": "revoke"},
               # The TECH space goes through the same machinery but a different
               # namespace: a tech row's Node ID is the .dat tech array index,
               # and the same integer is a unit id in the other space.  Without a
               # case here the whole tech half could be unwired and this sweep
               # would still say "agree on every case".
               {"intent": "tech.availability", "tech": 3, "civ": "Goths",
                "action": "grant"},
               {"intent": "tech.availability", "tech": 3, "civ": "British",
                "action": "revoke"}]
CASES.extend(AVAIL_CASES)
print("availability cases         : %d (%d unit, %d tech; exhaustive coverage "
      "in _probe/test_availability_intent_e2e.py and "
      "_probe/test_tech_availability_e2e.py)"
      % (len(AVAIL_CASES), len(AVAIL_CASES) // 2, len(AVAIL_CASES) // 2))

bad = []
ok_both = refused = 0
shape = {}
for case in CASES:
    if case["intent"] == "tech.effect":
        # Addressed by position inside a shared record, so there is no per-option
        # sub-shape to enumerate; one key keeps the coverage guard meaningful.
        key = "tech.effect"
    elif case["intent"].endswith(".availability"):
        # The sub-shape here is the ACTION ("grant" / "revoke").  Both are listed
        # above, and both must agree with the JSON build path -- whose agreement
        # is checked where the bytes are, in the e2e test.  What is checked here
        # is that the PREVIEW and the strategy routing agree about which intent
        # is which, which is the failure that would look like "the button is
        # greyed out for one action but not the other".
        key = case["intent"] + "." + case["action"]
    elif case["intent"] == "tech.research_time":
        key = case["intent"]
    else:
        key = case["intent"] + "." + case.get("stat", case.get("resource",
                                                               case.get("kind", "")))
    if case["intent"].endswith(".availability"):
        try:
            plan = tk.plan(case)
        except Exception as exc:
            bad.append((case, "plan raised %r" % (exc,)))
            continue
        if not plan.get("editable"):
            # A refusal is a legal outcome, but it must say why.
            if not plan.get("description"):
                bad.append((case, "refused with no explanation"))
                continue
            refused += 1
            shape.setdefault(key, [0, 0])[1] += 1
            continue
        ok_both += 1
        shape.setdefault(key, [0, 0])[0] += 1
        # The strategy must be the one that routes to the JSON builder, and the
        # .dat compiler must refuse it -- if it ever stopped refusing, this
        # intent would silently start shipping a .dat through the byte patcher.
        try:
            C.compile_intent(tk.dat_path, case, parsed=tk._parsed,
                             stats=tk._stats)
            bad.append((case, "compile_intent built an availability intent; it "
                              "must route through the JSON strategy"))
        except C.IntentError:
            pass
        # What the preview may promise is DECLARED BY THE SCHEMA
        # (`compile.dat_half.actions`), and this block used to hard-code the
        # opposite: `edit_count == 0` and `mod_contains_dat is False`, i.e. "this
        # intent never writes a .dat".  That was true when availability was
        # JSON-only, and it became a false alarm the moment the in-game-proven
        # `datgrant` recipe was wired to `grant`.  Reading the declaration instead
        # of restating it means adding or removing a `.dat` half is a data edit
        # and this sweep follows, rather than contradicting it.
        _dh = (intents_schema["intents"][case["intent"]]["compile"]
               .get("dat_half") or {})
        _wants_dat = case["action"] in (_dh.get("actions") or ())
        _want_edits = int(((_dh.get("write_operations_by_action") or {})
                           .get(case["action"], _dh.get("write_operations"))
                           or 0)) if _wants_dat else 0
        if bool(plan.get("changes_dat")) != _wants_dat:
            bad.append((case, "plan changes_dat=%s but the schema declares a "
                              "`.dat` half for actions %s"
                        % (plan.get("changes_dat"), _dh.get("actions") or [])))
        if int(plan.get("edit_count") or 0) != _want_edits:
            bad.append((case, "plan claims %s .dat edits, schema declares %d"
                        % (plan.get("edit_count"), _want_edits)))
        # `mod_contains_dat` is NOT the same question as `changes_dat`: every
        # availability build writes its JSON under `resources/_common/dat/`, and a
        # mod that overrides that folder without `empires2_x2_p1.dat` makes the
        # game fail to start, so the emitter always carries the base `.dat` --
        # byte-identical when only JSON changed.  A plan saying "no .dat" here
        # would be describing a mod folder that cannot exist.
        if plan.get("mod_contains_dat") is not True:
            bad.append((case, "availability plan says mod_contains_dat=%s, but a "
                              "JSON file under the DAT storage point forces a "
                              "carried .dat" % plan.get("mod_contains_dat")))
        continue
    try:
        plan = tk.plan(case)
    except C.IntentError as exc:
        try:
            C.compile_intent(tk.dat_path, case, parsed=tk._parsed, stats=tk._stats)
            bad.append((case, "plan refused (%s) but build succeeded" % exc))
        except C.IntentError:
            refused += 1
            shape.setdefault(key, [0, 0])[1] += 1
        except Exception as exc2:
            bad.append((case, "build raised %r" % (exc2,)))
        continue
    except Exception as exc:
        bad.append((case, "plan raised %r" % (exc,)))
        continue
    try:
        rep = C.compile_intent(tk.dat_path, case, parsed=tk._parsed, stats=tk._stats)
    except C.IntentError as exc:
        refused += 1
        shape.setdefault(key, [0, 0])[1] += 1
        if plan["edit_count"] != 0:
            bad.append((case, "plan promised %d edits but build refused: %s" % (plan["edit_count"], exc)))
        continue
    except Exception as exc:
        bad.append((case, "build raised %r" % (exc,)))
        continue
    ok_both += 1
    shape.setdefault(key, [0, 0])[0] += 1
    if plan["edit_count"] != len(rep["edits"]):
        bad.append((case, "plan %d edits vs build %d" % (plan["edit_count"], len(rep["edits"]))))
    if plan["civ_count"] != rep["civs_edited"]:
        bad.append((case, "plan %d civs vs build %d" % (plan["civ_count"], rep["civs_edited"])))
    # Every label a user can read must be human.  A walker branch that hard-codes
    # its own literal instead of taking b["label"] leaks the locator's vocabulary
    # ("cost type 1", "attack cls 3") into the change list -- and plan() cannot
    # see it, because the preview sentence is a second implementation.  Scan the
    # EDIT list, not the plan.
    for _e in rep["edits"]:
        _lab = _e.where.split(" ", 2)[-1].replace(" (mirror)", "")
        if _RAW_LABEL.search(_lab):
            bad.append((case, "edit label leaks a raw id: %r" % _lab))

print()
print("per-option outcome (planned+built / refused):")
for k in sorted(shape):
    print("  %-42s %3d / %3d" % (k, shape[k][0], shape[k][1]))
print()
print("cases            : %d" % len(CASES))
print("planned + built  : %d" % ok_both)
print("refused          : %d" % refused)
print("inconsistencies  : %d" % len(bad))
for c, why in bad[:25]:
    print("  BAD %s :: %s" % (c, why))

# A sweep only covers what it actually builds.  If a declared option is never
# exercised, the sweep reports "agree" while testing nothing about it -- the
# same silent hole that let max_range sit unbound.  So assert coverage of the
# DECLARED option space, not just of the case list.
expected = set()
for st in STATS:
    expected.add("unit.stat." + st)
for res in RES:
    expected.add("unit.cost." + res)
for k in CLASS:
    expected.add("unit.attack_class." + k)
for res in ("food", "wood", "gold", "stone"):
    expected.add("tech.cost." + res)
expected.add("tech.research_time")
expected.add("tech.effect")
# Derived, not listed: an action added to the schema must be exercised or this
# sweep fails.  (Hand-writing the two names here would reproduce the exact hole
# the DECLARED_INTENTS guard below was added to close.)  Both id spaces, because
# the tech half is a separate code path through the same schema shape.
for _ai in ("unit.availability", "tech.availability"):
    for _a in intents_schema["intents"][_ai]["fields"]["action"]["options"]:
        expected.add(_ai + "." + _a)
exercised = set(shape)
# Every DECLARED intent must appear in the exercised set, not just every option
# of the intents this file happens to know about.  `tech.effect` sat declared and
# unexercised here for a whole round; enumerating the schema instead of hand-adding
# keys means a seventh intent cannot be added without this sweep failing first.
DECLARED_INTENTS = sorted(intents_schema["intents"])
# Prefix match, not `split(".")[0:2]`: an intent whose name has more than two
# segments would be silently mis-derived and then reported as unswept forever.
_covered_intents = {i for i in DECLARED_INTENTS
                    if any(k == i or k.startswith(i + ".") for k in exercised)}
_missing_intents = [i for i in DECLARED_INTENTS if i not in _covered_intents]
print()
print("declared intents            : %d %s" % (len(DECLARED_INTENTS),
                                              DECLARED_INTENTS))
print("intents with a built case   : %d" % len(_covered_intents))
print("DECLARED BUT UNSWEPT        : %s" % (_missing_intents or "none"))
for u in _missing_intents:
    bad.append((u, "declared intent never exercised by this sweep"))
uncovered = sorted(expected - exercised)
print()
print("declared option shapes    : %d" % len(expected))
print("actually exercised        : %d" % len(exercised & expected))
print("NEVER EXERCISED           : %s" % (uncovered or "none"))
for u in uncovered:
    bad.append((u, "declared option never exercised"))
print()
print("FULL CROSS-PRODUCT SWEEP: %s" % ("AGREE ON EVERY CASE" if not bad else "INCONSISTENCIES FOUND"))

# This file printed its verdict and then fell off the end, so it exited 0 even
# when it said INCONSISTENCIES FOUND.  `_probe/run_long.py` treats a non-zero
# exit as failure and had to match the verdict string instead -- which meant a
# sweep that found real defects still showed up as `exit=0` in the log, one
# character away from looking green.  A test must fail the way a test fails.
sys.exit(1 if bad else 0)
