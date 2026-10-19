# -*- coding: utf-8 -*-
"""Reproduce ONLY the availability cases of _probe/test_full_sweep.py.

The full sweep takes ~2 h because every tech.effect case re-walks the 85 MB tech
section.  The availability cases are cheap and are the ones touching code edited
this round (revoke's cascade), so when the long sweep reports an inconsistency
this narrows it down without waiting for the whole run.

The checks are now SCHEMA-DRIVEN, mirroring the sweep: whether a `.dat` half
exists is `compile.dat_half.actions`, not a hard-coded assumption.  Keeping this
in step with the sweep matters -- a disagreement between the two would send the
next reader hunting a defect that only one of them believes in.
"""
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A                            # noqa: E402
from aoe2mod.intent import compiler as C                # noqa: E402

CASES = [{"intent": "unit.availability", "unit": 41, "civ": "British",
          "action": "grant"},
         {"intent": "unit.availability", "unit": 41, "civ": "Goths",
          "action": "revoke"},
         {"intent": "tech.availability", "tech": 3, "civ": "Goths",
          "action": "grant"},
         {"intent": "tech.availability", "tech": 3, "civ": "British",
          "action": "revoke"}]

tk = A.open_toolkit()
intents_schema, _bindings = C.load_schema()
bad = []
for case in CASES:
    label = "%s.%s" % (case["intent"], case["action"])
    try:
        plan = tk.plan(case)
    except Exception as exc:
        bad.append((label, "plan raised %r" % (exc,)))
        traceback.print_exc()
        continue
    print("%-34s editable=%s edit_count=%s changes_dat=%s mod_contains_dat=%s"
          % (label, plan.get("editable"), plan.get("edit_count"),
             plan.get("changes_dat"), plan.get("mod_contains_dat")))
    if not plan.get("editable"):
        if not plan.get("description"):
            bad.append((label, "refused with no explanation"))
        continue
    try:
        C.compile_intent(tk.dat_path, case, parsed=tk._parsed, stats=tk._stats)
        bad.append((label, "compile_intent built an availability intent"))
    except C.IntentError:
        pass
    except Exception as exc:
        bad.append((label, "compile_intent raised %r not IntentError" % (exc,)))
        traceback.print_exc()

    dh = (intents_schema["intents"][case["intent"]]["compile"]
          .get("dat_half") or {})
    wants_dat = case["action"] in (dh.get("actions") or ())
    want_edits = int(((dh.get("write_operations_by_action") or {})
                      .get(case["action"], dh.get("write_operations")) or 0)
                     if wants_dat else 0)
    print("    schema dat_half: actions=%s write_operations_by_action=%s "
          "-> wants_dat=%s edits=%d"
          % (dh.get("actions") or [], dh.get("write_operations_by_action") or
             dh.get("write_operations"), wants_dat, want_edits))
    if bool(plan.get("changes_dat")) != wants_dat:
        bad.append((label, "plan changes_dat=%s but schema wants_dat=%s"
                    % (plan.get("changes_dat"), wants_dat)))
    if int(plan.get("edit_count") or 0) != want_edits:
        bad.append((label, "plan edit_count=%s but schema declares %s"
                    % (plan.get("edit_count"), want_edits)))
    if plan.get("mod_contains_dat") is not True:
        bad.append((label, "plan mod_contains_dat=%s, but the DAT storage point "
                           "forces a carried .dat"
                    % plan.get("mod_contains_dat")))

print()
print("availability inconsistencies: %d" % len(bad))
for label, why in bad:
    print("  BAD %-30s :: %s" % (label, why))
sys.exit(1 if bad else 0)
