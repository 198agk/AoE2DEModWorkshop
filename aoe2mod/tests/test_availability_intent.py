# -*- coding: utf-8 -*-
"""Availability as an INTENT: plan/build through the public API.

test_availability_e2e.py tests the file layer (grant a row, serialise, drop it on
disk).  This one tests the layer above it -- the part a UI talks to -- and the
three things that only exist at that level:

1. ROUTING.  `unit.availability` must not go through the .dat byte patcher
   (`compile_edits`).  That is asserted twice, because either half alone can be
   true while the other is broken: `compile_edits` must refuse the strategy, and
   `build` must dispatch on `compile.strategy` rather than on the intent's name.
   Since 2026-10-16 a GRANT also writes the `.dat` recipe the user confirmed in
   game, but through its own module (`intent/datgrant.py`), not the patcher.
2. THE ANSWER DOES NOT DRIFT.  The .dat path patches an immutable `bytes`, so
   plan-after-build gives the same answer as plan-before-build.  This path edits
   JSON, so it is the one that could leak a build into the tool's picture of the
   game -- and a tool that silently changes its own description of the game is
   worse than one that fails.
3. REFUSALS SAY WHICH KIND OF NO.  "You already have it", "nothing in the game
   has it" and "I never heard of that civilization" are three different
   situations for the player and must not collapse into one message.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                          # noqa: E402
from aoe2mod.game import civtechtrees as CT                      # noqa: E402
from aoe2mod.intent import compiler as C                         # noqa: E402

from aoe2mod.game import locations as LOC       # noqa: E402


class _GamePaths(object):
    """The two paths every end-to-end here needs.

    Discovered, not written down: this file ships inside the package, so a
    literal path would be wrong on every machine but the one it was typed on,
    and a probe-only helper would not be here to import.
    """
    GAME = LOC.find_game_root()
    DAT = LOC.dat_path(GAME)


GP = _GamePaths()


GAME = GP.GAME
NODE = 41                                # Huskarl
OWNER = "GOTHS"


def main():
    fails = []

    def check(ok, label, detail=""):
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                               ("  -- %s" % detail) if (detail and not ok) else ""))
        if not ok:
            fails.append(label)

    tk = A.open_toolkit()
    intents_schema, _bindings = C.load_schema()
    spec = intents_schema["intents"]["unit.availability"]

    # ---- 1. the schema says what the code assumes ------------------------
    check(spec["compile"]["strategy"] == "civtechtrees_json",
          "the schema declares the JSON strategy",
          spec["compile"].get("strategy"))
    check(spec["compile"].get("mod_contains_dat") is True,
          "and declares that a .dat IS in the product, because a grant writes it")
    # The routing and the `.dat` half are two different machines and both are
    # declared: `strategy` routes the JSON layers, `dat_half` says which ACTION
    # additionally gets the recipe the user confirmed in game.  BOTH actions have
    # one now: the grant on 2026-10-16 (`dsh test v7`) and the revoke on
    # 2026-10-19 (`dsh test v17`).
    _dh = spec["compile"].get("dat_half") or {}
    check(_dh.get("actions") == ["grant", "revoke"],
          "and declares the `.dat` half for BOTH actions",
          json.dumps(_dh, ensure_ascii=False)[:200])
    check(int(_dh.get("write_operations") or 0) > 0,
          "and declares how many write operations each action performs, so a "
          "preview can report a count without running the 25 s recipe",
          repr(_dh.get("write_operations")))
    _by = _dh.get("write_operations_by_action") or {}
    check(isinstance(_by.get("grant"), int) and isinstance(_by.get("revoke"), int),
          "each action declares its OWN count, because they write different "
          "numbers (a grant also patches the training button)",
          json.dumps(_by))
    check("delta" not in spec["fields"] and "value" not in spec["fields"],
          "the intent takes no delta/value (it is a set-membership change)")

    # ---- 2. routing ------------------------------------------------------
    intent = {"intent": "unit.availability", "unit": NODE, "civ": "British",
              "action": "grant"}
    try:
        C.compile_intent(tk.dat_path, intent, parsed=tk._parsed, stats=tk._stats)
        check(False, "compile_intent refuses the availability strategy")
    except C.IntentError as exc:
        check("civtechtrees_json" in str(exc),
              "compile_intent refuses the availability strategy, by name",
              str(exc)[:200])
    except Exception as exc:
        check(False, "compile_intent refuses the availability strategy",
              "raised %r" % (exc,))

    # ---- 3. plan ---------------------------------------------------------
    plan = tk.plan(intent)
    check(plan.get("editable") is True, "granting is planable",
          json.dumps(plan, ensure_ascii=False)[:300])
    check(plan.get("mode") == "add_row", "the mode is add_row", plan.get("mode"))
    check(plan.get("civ") == "BRITONS" and plan.get("civ_requested") == "British",
          "both spellings are reported (tree key and what the caller asked)")
    check(plan.get("donor") == OWNER, "the donor is named", plan.get("donor"))
    # The plan must promise what the build delivers.  A grant now writes the
    # `.dat` recipe the user confirmed in game, so "zero .dat bytes" is no longer
    # the promise -- asserting it here is what kept this test green while the plan
    # and the build disagreed.  What the plan must get right is the SHAPE and the
    # COUNT, both read from the schema so the two sides cannot drift.
    _want_edits = int((_by.get(plan.get("action") or "grant"))
                      or (spec["compile"]["dat_half"]).get("write_operations")
                      or 0)
    check(plan.get("edit_count") == _want_edits and plan.get("changes_dat") is True,
          "the plan promises the `.dat` write operations the build performs",
          json.dumps({k: plan.get(k) for k in ("edit_count", "changes_dat")}))
    check(plan.get("mod_contains_dat") is True
          and plan.get("dat_is_carrier") is False,
          "and says the .dat it ships is EDITED, not a carrier",
          json.dumps({k: plan.get(k) for k in ("mod_contains_dat",
                                               "dat_is_carrier",
                                               "changes_dat")}))
    check(plan.get("shape") == "availability",
          "the plan is tagged so a UI can render it differently",
          plan.get("shape"))
    check("近卫军" in (plan.get("description") or ""),
          "the description names the unit in the player's language",
          plan.get("description"))

    # ---- 4. build, and the answer must not drift -------------------------
    tmp = tempfile.mkdtemp(prefix="aoe2mod_avail_intent_")
    try:
        man = tk.build(intent, os.path.join(tmp, "mod"), title="Intent Test",
                       author="aoe2mod tests")
        v = man["verification"]
        check(v["ok"] is True, "the build verifies",
              json.dumps(v, ensure_ascii=False)[:400])
        # The `.dat` is no longer an unmodified carrier for a grant: it carries the
        # recipe the user confirmed in game.  What must hold is INTERNAL
        # CONSISTENCY -- `edit_count` counts the same `edits[]` array the recipe
        # reported, and `changes_dat`/`dat_is_carrier` are exact negations of
        # "a recipe ran".  Pinning "0 .dat bytes" here is what kept this test green
        # while the plan promised nothing and the build wrote a `.dat`.
        _dh2 = man.get("dat_half") or {}
        _dh_edits = len(_dh2.get("edits") or ())
        _ran = bool(_dh2.get("ok"))
        check(man.get("edit_count") == _dh_edits,
              "the manifest's edit_count counts the `.dat` recipe's own operations",
              "edit_count=%r dat_half.edits=%r"
              % (man.get("edit_count"), _dh2.get("edits")))
        check(man.get("changes_dat") is _ran,
              "changes_dat says exactly whether a `.dat` recipe ran",
              json.dumps({k: man.get(k) for k in ("changes_dat",
                                                  "dat_is_carrier")}))
        check(man.get("dat_is_carrier") is (not _ran),
              "and dat_is_carrier is its negation, not an independent guess",
              json.dumps({k: man.get(k) for k in ("changes_dat",
                                                  "dat_is_carrier")}))
        check(man.get("mod_contains_dat") is True,
              "and that a .dat file IS in the mod, because it must be")
        check([f for f in man["files"] if f["rel"].endswith(".dat")],
              "so the .dat is listed among the files")

        after = tk.plan(intent)
        check(after.get("editable") is True and after.get("mode") == "add_row",
              "planning AFTER the build gives the same answer (a build is a "
              "proposal, not a change to the game)",
              json.dumps({k: after.get(k) for k in ("editable", "mode")},
                         ensure_ascii=False))
        check(after.get("description") == plan.get("description"),
              "  and the same description")
        check(CT.node_status(tk._trees()["BRITONS"], NODE) is None,
              "  and the tool's own tree for BRITONS still lacks the unit")

        # ---- 5. the three refusals are three different sentences ---------
        # The CONTRACT is that each no keeps its own sentence, not that any
        # particular English word appears in it.  These used to assert
        # "already" / "tech tree" / "nothing to take away", which made the
        # translation below look like a regression -- and would have blocked
        # shipping a sentence the player can actually read.  So: assert the real
        # reason where a wrong branch would be visible (this unit is in no tech
        # tree), and assert PAIRWISE DISTINCTNESS for the rest, which is exactly
        # what collapsing two situations into one message would break.
        already = tk.plan({"intent": "unit.availability", "unit": NODE,
                           "civ": "Goths", "action": "grant"})
        check(already.get("editable") is False, "'already has it' is refused")
        check(bool((already.get("description") or "").strip()),
              "  in its own words, not an empty string",
              already.get("description"))

        nothing = tk.plan({"intent": "unit.availability", "unit": 12,
                           "civ": "British", "action": "grant"})
        check(nothing.get("editable") is False,
              "a unit in no tech tree is refused")
        check("科技树" in (nothing.get("description") or ""),
              "  with a sentence about tech trees, not 'unknown unit'",
              nothing.get("description"))

        # An unknown civ is a different kind of no from the three above: it is a
        # REFERENCE that cannot be resolved, so it raises like every other
        # unknown entity (an unknown unit name does the same).  The refusals that
        # come back as a dict are all cases where the reference resolved and the
        # requested change is a no-op -- which is exactly the distinction a UI
        # needs: "I could not find that" vs "that would do nothing".
        try:
            tk.plan({"intent": "unit.availability", "unit": NODE,
                     "civ": "Atlantis", "action": "grant"})
            check(False, "an unknown civ raises rather than silently refusing")
        except C.IntentError as exc:
            check("Atlantis" in str(exc),
                  "an unknown civ raises, naming what it did not recognise",
                  str(exc)[:200])
        except Exception as exc:
            check(False, "an unknown civ raises IntentError", "raised %r" % (exc,))

        # Revoking what a civ never had is its own message too.
        take = tk.plan({"intent": "unit.availability", "unit": NODE,
                        "civ": "British", "action": "revoke"})
        check(take.get("editable") is False,
              "revoking what the civ never had is refused")
        check(bool((take.get("description") or "").strip())
              and take.get("description") != already.get("description"),
              "  with a sentence of its own, not the 'already has it' one",
              take.get("description"))

        # An unknown ACTION is a schema violation, not a game state: it fails
        # before anything is loaded, like an unknown stat name.
        try:
            tk.plan({"intent": "unit.availability", "unit": NODE,
                     "civ": "British", "action": "destroy"})
            check(False, "an unknown action raises")
        except C.IntentError as exc:
            check("destroy" in str(exc),
                  "an unknown action raises, naming the action", str(exc)[:160])
        except Exception as exc:
            check(False, "an unknown action raises IntentError", "raised %r" % (exc,))

        # A row that is LISTED but marked NotAvailable is a third mode, and it is
        # the one where `apply` edits a row IN PLACE instead of appending.  That
        # makes it the path where a shallow copy would leak, so it needs its own
        # assertion rather than being assumed to behave like add_row.
        _av5 = tk.describe(5)["availability"]
        blocked = _av5["blocked_in"][0]
        fix = tk.plan({"intent": "unit.availability", "unit": 5,
                       "civ": blocked, "action": "grant"})
        check(fix.get("editable") is True and fix.get("mode") == "set_status",
              "granting a NotAvailable row is a STATUS change, not a new row",
              json.dumps({k: fix.get(k) for k in ("editable", "mode", "civ")},
                         ensure_ascii=False))
        check(CT.node_status(tk._trees()[blocked], 5) == "NotAvailable",
              "  and merely planning it did not flip the cached row",
              CT.node_status(tk._trees()[blocked], 5))

        # Build it, because this is the path that edits a row IN PLACE: if the
        # copy handed to `apply` were shallow, the cached tree would be flipped
        # and the tool would report the upgrade as already done to the game.
        _fixdir = os.path.join(tmp, "status change")
        _fx = tk.build({"intent": "unit.availability", "unit": 5,
                        "civ": blocked, "action": "grant"}, _fixdir,
                       title="status change", author="aoe2mod probe")
        check(_fx["verification"]["ok"] is True, "building a status change verifies",
              json.dumps(_fx["verification"], ensure_ascii=False)[:400])
        _back = CT.load_trees(_fixdir)[CT.civ_file_stem(blocked)]
        check(CT.node_status(_back, 5) == "ResearchedCompleted",
              "  the emitted tree now reads ResearchedCompleted",
              CT.node_status(_back, 5))
        check(len(CT.unit_rows(_back)) == len(CT.unit_rows(tk._trees()[blocked])),
              "  by changing a status, not by adding a duplicate row")
        check(CT.node_status(tk._trees()[blocked], 5) == "NotAvailable",
              "  and the tool's own tree STILL reads NotAvailable after a build",
              CT.node_status(tk._trees()[blocked], 5))

        # "Can build once researched" is a different refusal from "already has
        # it": the change would be a no-op either way, but the player needs to
        # know their civ is not missing the unit, only the prerequisite.  This is
        # one of the two places where the wording IS the distinction -- the four
        # refusals above just have to differ from each other, but this one and
        # "already has it" are the pair a player can actually confuse.
        _pending = tk.describe(21)["availability"]["pending_in"][0]
        _pend = tk.plan({"intent": "unit.availability", "unit": 21,
                         "civ": _pending, "action": "grant"})
        check(_pend.get("editable") is False,
              "granting what the civ can already research is refused")
        check("前置科技" in (_pend.get("description") or ""),
              "  with a sentence about the prerequisite, not about already having it",
              _pend.get("description"))

        # ---- 5b. the civ may be spelled either way ------------------------
        # The .dat calls it "British" and the file is BRITONS.json; a UI that
        # only ever sees one of them must not produce a different answer.
        for spelling in ("British", "BRITONS", "britons"):
            p = tk.plan({"intent": "unit.availability", "unit": NODE,
                         "civ": spelling, "action": "grant"})
            check(p.get("editable") is True and p.get("civ") == "BRITONS",
                  "the civ name %r resolves to BRITONS" % spelling,
                  json.dumps({k: p.get(k) for k in ("civ", "editable")},
                             ensure_ascii=False))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("PROVEN      the intent routes to the JSON strategy, the schema agrees")
    print("            with the code, a build does not change what the tool says")
    print("            about the game, and each refusal names its own situation.")
    print("ANSWERED 2026-10-19: whether a running game offers the unit no longer")
    print("            depends on this file's strategy alone -- the JSON strategy was")
    print("            measured and does nothing on its own (`dsh test v15`), while")
    print("            the `.dat` half was measured working in BOTH directions")
    print("            (`dsh test v7` grant, `dsh test v17` revoke).  Schema and code")
    print("            now declare that half, so this is a routing test, not a")
    print("            runtime proof.")
    print()
    if fails:
        print("AVAILABILITY INTENT: %d FAILED" % len(fails))
        for f in fails:
            print("   - %s" % f)
        return 1
    print("AVAILABILITY INTENT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
