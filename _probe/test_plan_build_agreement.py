# -*- coding: utf-8 -*-
"""A plan must never promise an edit the build then refuses.

This is a product-invariant test, not a feature test.  Every intent has two
independent implementations -- `plan()` for the preview and `build()` for the
bytes -- and the whole point of a preview is that the two agree.  When they do
not, the screen tells a player "会改游戏数据 / 1 处改动", the player presses the
button, and gets an error.  That is worse than a refusal, because the refusal
came one click too late.

Measured defect that motivated this file
----------------------------------------
    plan({"intent": "tech.research_time", "tech": 22, "delta": 0})
      -> editable: True, changes_dat: True, edit_count: 1
    build(same) -> IntentError: nothing would change

`_describe_tech_targets` counts where the field LIVES (Loom does have one research
location) while `collect_targets` -- the function the write itself calls -- drops
a target whose value is unchanged.  The preview used the first and the build used
the second.  The unit branch had always used `collect_targets`; the tech branch
was the one that diverged.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import tempfile                                                # noqa: E402

import aoe2mod.api as A                                        # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
FAIL = []


def check(name, ok, detail=""):
    if ok:
        print("  ok %s" % name)
    else:
        FAIL.append(name)
        print("FAIL %s :: %s" % (name, detail))


#: Each case is a real intent plus the shape of answer the plan MUST give.
#: `refused` means the plan has to say so itself -- not that build happens to
#: raise later, which is exactly the bug this file exists to catch.
CASES = [
    # ---- must be refused by the PLAN --------------------------------
    ("tech research time, delta 0", {"intent": "tech.research_time",
                                     "tech": 22, "delta": 0}, "refused"),
    ("unit hit points, delta 0", {"intent": "unit.stat", "unit": 83,
                                  "stat": "hit_points", "delta": 0}, "refused"),
    ("loom has no wood cost", {"intent": "tech.cost", "tech": 22,
                               "resource": "wood", "delta": 10}, "refused"),
    ("villager has no wood cost", {"intent": "unit.cost", "unit": 83,
                                   "resource": "wood", "delta": 10}, "refused"),
    # ---- must be accepted -------------------------------------------
    ("unit hit points, real change", {"intent": "unit.stat", "unit": 83,
                                      "stat": "hit_points", "value": 1000},
     "accepted"),
    ("tech research time, real change", {"intent": "tech.research_time",
                                         "tech": 22, "delta": 5}, "accepted"),
    ("loom food cost, real change", {"intent": "tech.cost", "tech": 22,
                                     "resource": "gold", "delta": 10},
     "accepted"),
]


def main():
    tk = A.open_toolkit(game_root=GAME)
    for label, intent, want in CASES:
        plan = tk.plan(intent)
        editable = bool(plan.get("editable"))
        edits = plan.get("edit_count")
        changes = plan.get("changes_dat")

        if want == "refused":
            check("%s: the plan itself refuses" % label, not editable,
                  "editable=%r edit_count=%r" % (editable, edits))
            check("%s: and it claims no writes and no .dat change" % label,
                  not edits and not changes,
                  "edit_count=%r changes_dat=%r" % (edits, changes))
            check("%s: and it explains why" % label,
                  bool(plan.get("reason") or plan.get("description")),
                  str(plan)[:160])
            # The build must refuse too.  A plan that refuses while the build
            # succeeds would be the same divergence in the other direction.
            try:
                _build(tk, intent)
                check("%s: the build refuses as well" % label, False,
                      "build accepted an edit the plan refused")
            except Exception as exc:                       # noqa: BLE001
                check("%s: the build refuses as well" % label, True, str(exc))
        else:
            check("%s: the plan accepts" % label, editable and bool(edits),
                  "editable=%r edit_count=%r changes_dat=%r"
                  % (editable, edits, changes))
            # And the build really succeeds, with the same edit count.
            try:
                man = _build(tk, intent)
            except Exception as exc:                       # noqa: BLE001
                check("%s: the build accepts as well" % label, False, str(exc))
                continue
            check("%s: the build accepts as well" % label, bool(man.get("mod_dir")),
                  str(man)[:160])
            check("%s: and the two agree on how many writes" % label,
                  man.get("edit_count") == edits,
                  "plan=%r build=%r" % (edits, man.get("edit_count")))

    unknown_strategy(tk)

    print()
    if FAIL:
        print("PLAN/BUILD AGREEMENT FAILED (%d): %s" % (len(FAIL), FAIL))
        return 1
    print("PLAN AND BUILD AGREE ON EVERY CASE -- INCLUDING THE REFUSALS")
    return 0


def unknown_strategy(tk):
    """A strategy the chains do not implement must be refused by BOTH sides.

    Measured 2026-10-23: an intent declaring the made-up strategy
    `not_a_real_strategy` previewed as `editable=True, edit_count=1701` and only
    failed at build time.  Every other case in this file drifts on a *value*;
    this one drifts on the *dispatch*, which is the shape that matters more now
    that strategies are declared in data and a plugin or a typo can introduce a
    name no chain knows.  `plan()` had no final refusal, so it fell through into
    the byte-preview body and promised edits it could never write.
    """
    import copy

    import aoe2mod.intent.compiler as C

    intents, bindings = C.load_schema()
    fake = copy.deepcopy(intents)
    fake["intents"]["unit.probe_unknown_strategy"] = {
        "applies_to": "unit",
        "title": "probe",
        "fields": {"unit": {"type": "entity_ref", "kind": "unit",
                            "required": True},
                   "stat": {"type": "enum", "required": True,
                            "options": ["hit_points"], "label": "属性"},
                   "value": {"type": "int", "label": "设为"}},
        "compile": {"strategy": "not_a_real_strategy"},
        "safety": {"field_width_bits": 16, "signed": True},
    }
    saved = dict(C._SCHEMA_CACHE)
    C._SCHEMA_CACHE.clear()
    C._SCHEMA_CACHE[C.schema_key()] = (fake, bindings)
    probe = {"intent": "unit.probe_unknown_strategy", "unit": 83,
             "stat": "hit_points", "value": 40}
    try:
        try:
            got = tk.plan(probe)
            check("an unknown strategy is refused by the plan", False,
                  "plan accepted it: editable=%r edit_count=%r"
                  % (got.get("editable"), got.get("edit_count")))
        except Exception:                                  # noqa: BLE001
            check("an unknown strategy is refused by the plan", True)
        try:
            _build(tk, probe)
            check("an unknown strategy is refused by the build as well", False,
                  "build accepted it")
        except Exception:                                  # noqa: BLE001
            check("an unknown strategy is refused by the build as well", True)
    finally:
        C._SCHEMA_CACHE.clear()
        C._SCHEMA_CACHE.update(saved)


def _build(tk, intent):
    out = tempfile.mkdtemp(prefix="dsh_agree_")
    # `info.json` must be publishable: the emitter refuses an empty Author rather
    # than shipping a mod the game cannot list.
    return tk.build(intent, out, title="dsh plan-build agreement",
                    author="dsh", overwrite=True)


if __name__ == "__main__":
    sys.exit(main())
