# -*- coding: utf-8 -*-
"""Sweep: does plan() ever promise work that build() then refuses?

The Barracks/attack bug was exactly this: plan said 252 edits, build raised
"has no 基础攻击 field".  plan() now filters through the same predicate the
compiler uses, so this sweep is the regression guard for that whole class.

For every (entity, intent) pair it asserts:
  plan.edit_count == len(build.edits)   (when the build succeeds)
  plan.edit_count == 0                  (exactly when the build refuses)
It also cross-checks plan's civ_count against the build's civs_edited.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A            # noqa: E402
from aoe2mod.intent import compiler as C  # noqa: E402

tk = A.open_toolkit()

# A spread of entity shapes, chosen to hit every awkward branch:
#   building with 4 age variants, building with 6, building with 2,
#   a lone combat unit, a villager, a siege unit, a hero/graphic-only unit,
#   a tech with 1 location, a tech with 2, a legacy-shaped tech, a resource.
UNITS = [12, 20, 70, 82, 10, 87, 4, 83, 38, 125, 448, 546, 209, 2418, 35, 2556]
TECHS = [22, 12, 13, 103, 102, 101, 50, 51, 430, 19, 0]

CASES = []
for uid in UNITS:
    CASES.append({"intent": "unit.stat", "unit": uid,
                  "stat": "hit_points", "delta": 1})
    CASES.append({"intent": "unit.stat", "unit": uid,
                  "stat": "movement_speed", "delta": 0.1})
    # range and reload are float32 and each mirrors a Displayed* panel field, so
    # one edit writes two slots -- swept here so plan's count can never drift
    # from the build's on the mirrored path either.
    CASES.append({"intent": "unit.stat", "unit": uid,
                  "stat": "max_range", "delta": 1})
    CASES.append({"intent": "unit.stat", "unit": uid,
                  "stat": "reload_time", "delta": -0.1})
    CASES.append({"intent": "unit.attack_class", "unit": uid, "delta": 1})
    CASES.append({"intent": "unit.cost", "unit": uid,
                  "resource": "wood", "delta": 1})
    # 'population' (type 4) is a real cost slot carried by 788 units and is now
    # in the schema's resource enum, so "make this unit take no population" is a
    # first-class intent -- swept like any other resource.
    CASES.append({"intent": "unit.cost", "unit": uid,
                  "resource": "population", "delta": 0})
for tid in TECHS:
    CASES.append({"intent": "tech.research_time", "tech": tid, "delta": 1})
    CASES.append({"intent": "tech.cost", "tech": tid,
                  "resource": "gold", "delta": 1})
    CASES.append({"intent": "tech.cost", "tech": tid,
                  "resource": "food", "delta": 1})

# --- ILLEGAL VALUES ---------------------------------------------------------
# The same class of bug as Barracks/attack, one level deeper: plan() used to
# count records without checking whether the resulting VALUE is writable, so
# "archer costs 100 less wood" previewed as 63 edits and then raised.  Each case
# here must be refused by BOTH paths, with the same message.
ILLEGAL = [
    ({"intent": "unit.cost", "unit": 4, "resource": "wood", "delta": -100},
     "unit cost past zero"),
    ({"intent": "unit.cost", "unit": 4, "resource": "wood", "value": -1},
     "unit cost set to -1"),
    ({"intent": "unit.cost", "unit": 4, "resource": "population", "value": -1},
     "population set to -1"),
    ({"intent": "unit.stat", "unit": 4, "stat": "hit_points", "delta": 40000},
     "unit hp overflowing i16"),
    ({"intent": "tech.cost", "tech": 22, "resource": "gold", "delta": -100},
     "tech cost past zero"),
    ({"intent": "tech.cost", "tech": 22, "resource": "gold", "value": -1},
     "tech cost set to -1"),
    ({"intent": "tech.research_time", "tech": 22, "value": -1},
     "tech research time set to -1"),
    ({"intent": "tech.research_time", "tech": 22, "value": 40000},
     "tech research time overflowing i16"),
    # float32 fields carry `non_negative` too, and the guard has to reach them:
    # it used to sit below the float early-return and was silently skipped.
    ({"intent": "unit.stat", "unit": 4, "stat": "max_range", "delta": -100},
     "range past zero"),
    ({"intent": "unit.stat", "unit": 4, "stat": "reload_time", "value": -1},
     "reload set to -1"),
]
# ...and fields with NO non_negative binding must still accept negatives: hit
# points are a signed range, and refusing them would be its own bug.  A faster
# unit is a SMALLER reload, so that negative is legal too.
LEGAL_NEGATIVE = [
    ({"intent": "unit.stat", "unit": 4, "stat": "hit_points", "value": -5},
     "negative hit_points is allowed"),
    ({"intent": "unit.cost", "unit": 4, "resource": "wood", "delta": -5},
     "a discount that stays positive is allowed"),
    ({"intent": "unit.stat", "unit": 4, "stat": "reload_time", "delta": -0.5},
     "a faster unit is a smaller reload, and stays positive"),
]

bad = []
ok_both = refused = 0
for case in CASES:
    try:
        plan = tk.plan(case)
    except C.IntentError as exc:
        # A user error (ambiguous name, unknown resource) must surface at plan
        # time too, and must be the SAME refusal the build gives.
        try:
            C.compile_intent(tk.dat_path, case, parsed=tk._parsed,
                             stats=tk._stats)
            bad.append((case, "plan refused (%s) but build succeeded" % exc))
        except C.IntentError:
            refused += 1
        except Exception as exc2:
            bad.append((case, "build raised %r" % (exc2,)))
        continue
    except Exception as exc:                       # a plan must never explode
        bad.append((case, "plan raised %r" % (exc,)))
        continue
    try:
        rep = C.compile_intent(tk.dat_path, case, parsed=tk._parsed,
                               stats=tk._stats)
    except C.IntentError as exc:
        refused += 1
        if plan["edit_count"] != 0:
            bad.append((case, "plan promised %d edits but build refused: %s"
                        % (plan["edit_count"], exc)))
        if "no " not in plan["description"] and "没有" not in plan["description"]:
            bad.append((case, "refusal not disclosed in the plan text: %r"
                        % plan["description"]))
        continue
    except Exception as exc:
        bad.append((case, "build raised %r" % (exc,)))
        continue
    ok_both += 1
    n = len(rep["edits"])
    if plan["edit_count"] != n:
        bad.append((case, "plan said %d edits, build made %d"
                    % (plan["edit_count"], n)))
    if plan["kind"] == "unit" and plan["civ_count"] != rep["civs_edited"]:
        bad.append((case, "plan said %d civs, build touched %d"
                    % (plan["civ_count"], rep["civs_edited"])))
    if "None" in plan["description"]:
        bad.append((case, "plan text leaked a Python None: %r"
                    % plan["description"]))

# Each illegal value must be refused by plan AND build, with the SAME wording --
# a plan that refuses "for a different reason" than the build is still a split.
neg_both = 0
for case, why in ILLEGAL:
    try:
        plan = tk.plan(case)
        bad.append((case, "%s: plan ACCEPTED an illegal value (%s edits)"
                    % (why, plan["edit_count"])))
    except C.IntentError as pexc:
        try:
            C.compile_intent(tk.dat_path, case, parsed=tk._parsed, stats=tk._stats)
            bad.append((case, "%s: build ACCEPTED an illegal value" % why))
        except C.IntentError as bexc:
            neg_both += 1
            if str(pexc) != str(bexc):
                bad.append((case, "%s: plan said %r, build said %r"
                            % (why, str(pexc), str(bexc))))
        except Exception as exc:
            bad.append((case, "%s: build raised %r" % (why, exc)))
    except Exception as exc:
        bad.append((case, "%s: plan raised %r" % (why, exc)))

# A legal negative must be accepted by BOTH, or the guard over-reaches.
pos_both = 0
for case, why in LEGAL_NEGATIVE:
    try:
        plan = tk.plan(case)
        rep = C.compile_intent(tk.dat_path, case, parsed=tk._parsed, stats=tk._stats)
    except Exception as exc:
        bad.append((case, "%s: refused a legal value (%r)" % (why, exc)))
        continue
    pos_both += 1
    if plan["edit_count"] != len(rep["edits"]):
        bad.append((case, "%s: plan said %d, build made %d"
                    % (why, plan["edit_count"], len(rep["edits"]))))

# --- PER-RECORD OVERFLOW INSIDE ONE FAMILY ----------------------------------
# Validating only hits[0] is not enough: the age variants of a building carry
# DIFFERENT baselines (a Barracks is 1200/1800/1500/2100 hp), so an extreme
# delta fits the Dark Age record and overflows the Castle one.  Sweep deltas
# across the real boundary instead of hardcoding the value that happens to
# break today -- the dats get rebalanced and a fixed case would quietly stop
# straddling anything.
STRADDLE = []
for delta in list(range(29500, 31500, 50)) + [32767, 32768, -32767, -32768]:
    STRADDLE.append((12, delta))      # Barracks: 4 ages, different baselines
    STRADDLE.append((70, delta))      # House:    6 ages
    STRADDLE.append((4, delta))       # Archer:   1 age (the control)
straddle_agree = 0
for uid, delta in STRADDLE:
    case = {"intent": "unit.stat", "unit": uid,
            "stat": "hit_points", "delta": delta}
    try:
        plan = tk.plan(case)
        pverdict = ("ok", plan["edit_count"])
    except C.IntentError as exc:
        pverdict = ("no", str(exc))
    except Exception as exc:
        bad.append((case, "plan raised %r" % (exc,)))
        continue
    try:
        rep = C.compile_intent(tk.dat_path, case, parsed=tk._parsed, stats=tk._stats)
        bverdict = ("ok", len(rep["edits"]))
    except C.IntentError as exc:
        bverdict = ("no", str(exc))
    except Exception as exc:
        bad.append((case, "build raised %r" % (exc,)))
        continue
    if pverdict[0] != bverdict[0]:
        bad.append((case, "unit %d delta %d: plan said %s, build said %s"
                    % (uid, delta, pverdict[0], bverdict[0])))
    elif pverdict[0] == "ok" and pverdict[1] != bverdict[1]:
        bad.append((case, "unit %d delta %d: plan said %d edits, build made %d"
                    % (uid, delta, pverdict[1], bverdict[1])))
    elif pverdict[0] == "no" and pverdict[1] != bverdict[1]:
        # Same verdict but a different reason is still a preview that would
        # mislead: the user is shown the plan's wording, not the build's.
        bad.append((case, "unit %d delta %d: plan said %r, build said %r"
                    % (uid, delta, pverdict[1], bverdict[1])))
    else:
        straddle_agree += 1
print("per-family overflow sweep : %d / %d agree"
      % (straddle_agree, len(STRADDLE)))

print("cases            : %d  (+%d illegal, +%d legal-negative, +%d straddling)"
      % (len(CASES), len(ILLEGAL), len(LEGAL_NEGATIVE), len(STRADDLE)))
print("planned + built  : %d" % ok_both)
print("refused          : %d" % refused)
print("illegal refused by both, same message : %d / %d" % (neg_both, len(ILLEGAL)))
print("legal negative accepted by both       : %d / %d" % (pos_both, len(LEGAL_NEGATIVE)))
print("inconsistencies  : %d" % len(bad))
for case, why in bad[:20]:
    print("  MISMATCH %s -> %s" % (case, why))

assert not bad, "%d plan/build inconsistencies" % len(bad)
print()
print("PLAN AND BUILD AGREE ON EVERY CASE")
