# -*- coding: utf-8 -*-
"""Black-box end-to-end: "let the Britons build the Huskarl", through the API.

Walks ONLY the public surface -- open a toolkit, plan, build, then read the mod
back off disk the way the engine would.  Nothing here reaches into the trees
dict the build mutated; if the file on disk is right, it is right.

PROVEN by this script:
  * the emitted file is byte-identical to a re-serialisation of the tree the API
    produced, so nothing was lost in the emitter;
  * it lands at resources/_common/dat/CivTechTrees/BRITONS.json;
  * it re-parses, and the named unit is `ResearchedCompleted` in it;
  * exactly one row was added and every other row is unchanged;
  * the mod contains NO .dat;
  * a second civ's file is untouched on disk.

NOT PROVEN: that a running game offers the unit.  This layer has never been
observed in-game (no mod on this install ships a CivTechTrees file), and this
script says so in its own output rather than letting the reader assume it.
"""
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                          # noqa: E402
from aoe2mod.game import civtechtrees as CT                      # noqa: E402

FAILS = []


def check(cond, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", label,
                           ("  -- %s" % detail) if detail and not cond else ""))
    if not cond:
        FAILS.append(label)
    return cond


def main():
    tk = A.open_toolkit()
    game_root = tk.game_root
    trees_dir = CT.trees_dir(game_root)
    print("game root : %s" % game_root)
    print("trees dir : %s" % trees_dir)
    print()

    # Huskarl is a Goths-only unit; every other civ must not have it.
    subject = tk.search("Huskarl", kind="unit", limit=5)
    print("search 'Huskarl': %s" % subject)
    uid = subject[0]["id"]
    print("unit id   : %s" % uid)
    print()

    # Where does it live BEFORE the build?  Read it from disk, not from the API.
    before_path = os.path.join(trees_dir, "BRITONS.json")
    with open(before_path, "rb") as fh:
        britons_before = fh.read()
    other_path = os.path.join(trees_dir, "AZTECS.json")
    with open(other_path, "rb") as fh:
        aztecs_before = fh.read()

    # ---- 1. plan --------------------------------------------------------
    intent = {"intent": "unit.availability", "unit": uid, "civ": "British",
              "action": "grant"}
    print("INTENT %s" % json.dumps(intent, ensure_ascii=False))
    plan = tk.plan(intent)
    print("PLAN   %s" % json.dumps({k: v for k, v in plan.items()
                                    if k in ("description", "editable", "mode",
                                             "civ", "donor", "writes",
                                             "mod_contains_dat", "edit_count",
                                             "holder_count")},
                                   ensure_ascii=False, indent=2))
    check(plan["editable"], "the plan is editable")
    check(plan["mode"] == "add_row", "the mode is add_row", str(plan.get("mode")))
    check(plan["civ"] == "BRITONS", "the civ resolved to the tree key BRITONS",
          str(plan.get("civ")))
    check(plan["mod_contains_dat"] is False, "the plan says no .dat is written")
    if FAILS:
        print("  (stopping: the plan failed)")
        return 1

    # ---- 2. build -------------------------------------------------------
    out = tempfile.mkdtemp(prefix="aoe2_avail_e2e_")
    try:
        man = tk.build(intent, out, title="Availability probe",
                       author="aoe2mod probe")
        print("BUILD  %s" % json.dumps(
            {k: man[k] for k in sorted(man)
             if k not in ("verification",)},
            ensure_ascii=False, default=str)[:1200])
        print()
        v = man["verification"]
        print("VERIFICATION")
        for k in ("serializer_is_exact", "serialize_reparses",
                  "untouched_rows_identical", "emitted_matches_intended",
                  "path_is_engine_relative", "ok",
                  "before_unit_rows", "after_unit_rows",
                  "node_rows_before", "node_rows_after",
                  "node_status_before", "node_status_after"):
            print("   %-28s %s" % (k, v.get(k)))
        print("   emitted_path                 %s" % v.get("emitted_path"))
        print()

        check(v["ok"], "verification.ok", json.dumps(v)[:400])
        check(v["serializer_is_exact"],
              "the serializer reproduces the shipped BRITONS.json byte for byte")
        check(v["emitted_matches_intended"], "the file on disk equals the emitted bytes")
        check(v["path_is_engine_relative"],
              "the file sits under resources/_common/dat/CivTechTrees/")
        check(v["node_status_before"] is None,
              "Britons did NOT have the Huskarl before",
              str(v["node_status_before"]))
        check(v["node_status_after"] == "ResearchedCompleted",
              "Britons HAVE the Huskarl after",
              str(v["node_status_after"]))
        check(v["after_unit_rows"] == v["before_unit_rows"] + 1,
              "exactly one row was added (%s -> %s)"
              % (v["before_unit_rows"], v["after_unit_rows"]))
        check(v["untouched_rows_identical"],
              "every other row is unchanged",
              json.dumps({"vanished": v.get("other_names_vanished"),
                          "appeared": v.get("other_names_appeared")}))

        # ---- 3. read the mod back the way the engine would --------------
        rel = os.path.join(CT.CIVTECHTREES_REL, "BRITONS.json")
        p = os.path.join(out, rel)
        check(os.path.isfile(p), "the mod ships %s" % rel)
        with open(p, "rb") as fh:
            blob = fh.read()
        back = json.loads(blob.decode("utf-8"))
        check(CT.serialize(back) == blob,
              "re-serialising what is on disk reproduces it exactly")
        check(CT.node_status(back, uid) == "ResearchedCompleted",
              "re-reading the mod finds the unit as available")
        check(CT.name_string_id(back, uid) is not None,
              "and the added row carries a Name String ID to display",
              str(CT.name_string_id(back, uid)))
        # The donor was not moved: Goths must still have it.
        got = os.path.join(trees_dir, "GOTHS.json")
        with open(got, "rb") as fh:
            goths = json.loads(fh.read().decode("utf-8"))
        check(CT.node_status(goths, uid) == "ResearchedCompleted",
              "the donor civilization (GOTHS) still has it on disk")

        # ---- 4. no .dat anywhere in the mod -----------------------------
        dat_files = []
        for dirpath, _dirs, files in os.walk(out):
            for fn in files:
                if fn.lower().endswith(".dat"):
                    dat_files.append(os.path.join(dirpath, fn))
        check(not dat_files, "the mod contains no .dat file", str(dat_files))
        check(man.get("mod_contains_dat") is False, "and the manifest says so")
        check(man.get("edit_count") == 0,
              "and edit_count is 0 .dat bytes", str(man.get("edit_count")))

        # ---- 5. a second civ is untouched on disk -----------------------
        with open(other_path, "rb") as fh:
            check(fh.read() == aztecs_before,
                  "another civilization's file on disk was not modified")
        with open(before_path, "rb") as fh:
            check(fh.read() == britons_before,
                  "the GAME's own BRITONS.json was not modified either")

        # ---- 6. a build does not change what the tool says about the game --
        # The .dat path patches an immutable `bytes`, so planning again after a
        # build gives the same answer.  This path edits JSON, so it is the one
        # that could leak the change into the session's picture of the game.
        again = tk.plan(intent)
        check(again.get("editable") and again.get("mode") == "add_row",
              "planning again after the build gives the SAME answer (the build "
              "did not edit the tool's picture of the game)",
              json.dumps({k: again.get(k) for k in ("editable", "mode",
                                                    "description")},
                         ensure_ascii=False))
        check(tk.plan(intent)["description"] == plan["description"],
              "   and the description is unchanged too",
              "%r vs %r" % (again.get("description"), plan["description"]))

        # ---- 7. refuse the 1,364 units that are in no tech tree ---------
        dead = tk.search("Barracks", kind="unit", limit=1)
        if dead:
            bad = tk.plan({"intent": "unit.availability", "unit": dead[0]["id"],
                           "civ": "British", "action": "grant"})
            check(not bad.get("editable", True),
                  "a unit that is in no tech tree is refused",
                  str(bad.get("description")))
            check("tech tree" in (bad.get("description") or ""),
                  "   and the refusal says WHY, not 'unknown unit'",
                  str(bad.get("description")))
    finally:
        shutil.rmtree(out, ignore_errors=True)

    print()
    if FAILS:
        print("AVAILABILITY E2E: %d FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("AVAILABILITY E2E: ALL CHECKS PASSED")
    print("PROVEN: the mod's bytes, its path, its content, and that nothing else")
    print("        in the game's data or the mod was disturbed.")
    print("NOT PROVEN: that a running game offers the unit. This layer has never")
    print("        been observed in-game.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
