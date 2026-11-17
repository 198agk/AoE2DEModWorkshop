# -*- coding: utf-8 -*-
"""END TO END: "let the Britons build Huskars" -> an installable mod on disk.

This is the black-box test for the whole availability write path.  It uses ONLY
the product's public surface -- no probe internals -- and then verifies the
ARTIFACT the way the engine would: open it as a mod folder, find the file by the
path the engine formats (`CivTechTrees/%s.json`), read it, and check the change
is present and nothing else moved.

What it deliberately does NOT claim: that the running game grants the unit.
That needs an in-game load, which has not been done.  Everything up to the
file boundary is asserted here; the last step is labelled as unproven in the
output so the boundary is never lost.

Also asserts the two things a mod author cannot debug in game:
  * the `.dat` IS carried, UNMODIFIED, as a carrier -- this change needs no `.dat`
    byte, but the file must be present because the game fails to start when a mod
    overrides `resources/_common/dat/` without it (reported by the user twice in
    game; see `_probe/test_dat_carrier.py`), and
  * the emitted JSON is byte-identical to a re-serialisation of the edited tree,
    i.e. the writer did not reflow or re-escape anything.
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

from aoe2mod.game import civtechtrees as CT                      # noqa: E402
from aoe2mod.mod import emitter as E                             # noqa: E402

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
NODE = 41                    # Huskarl
OWNER = "GOTHS"              # who has it
TARGET = "BRITONS"           # who we grant it to


def main():
    fails = []

    def check(ok, label, detail=""):
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                               ("  -- %s" % detail) if (detail and not ok) else ""))
        if not ok:
            fails.append(label)

    trees = CT.load_trees(GAME)
    if len(trees) != 62:
        print("FATAL: expected 62 civ files, got %d" % len(trees))
        return 2

    # ---- 1. state before -------------------------------------------------
    check(CT.has(trees[OWNER], NODE), "%s has Huskarl (%d)" % (OWNER, NODE))
    check(not CT.has(trees[TARGET], NODE), "%s does not" % TARGET)
    donor_civ, donor = CT.donor_row(trees, NODE)
    check(donor_civ == OWNER, "the donor row comes from %s" % OWNER,
          "got %s" % donor_civ)

    # ---- 2. edit ---------------------------------------------------------
    target = trees[TARGET]
    before_rows = len(CT.unit_rows(target))
    row, warns = CT.grant(target, NODE, donor)
    check(CT.has(target, NODE), "the target now has it, in memory")
    check(len(CT.unit_rows(target)) == before_rows + 1,
          "exactly one row was appended")
    check(bool(warns), "the inherited fields were reported to the caller")

    # ---- 3. emit ---------------------------------------------------------
    tmp = tempfile.mkdtemp(prefix="aoe2mod_avail_")
    try:
        mod_dir = os.path.join(tmp, "Availability Test")
        rel = os.path.join("resources", "_common", "dat", "CivTechTrees",
                           "%s.json" % TARGET)
        info = E.make_info("Availability Test", author="probe",
                           description="grant one unit")
        man = E.emit_json_mod(mod_dir, {rel: CT.serialize(target)}, info,
                             base_dir=GAME)

        check(any(f["rel"].endswith(TARGET + ".json") for f in man["files"]),
              "the manifest lists the CivTechTrees file")
        # The `.dat` IS in the mod, but as an UNMODIFIED CARRIER.  The earlier
        # version of this test asserted the opposite ("no .dat was shipped") and
        # that assertion pinned a real defect: the user reported that exactly this
        # mod shape stops the game from starting.  `changes_dat` still reports the
        # truth about the CHANGE (no .dat byte was edited), while the file itself
        # is present because the DAT storage point requires it.
        check(man.get("changes_dat") is False,
              "no .dat BYTE was changed (this change edits JSON only)")
        check(man.get("dat_is_carrier") is True,
              "the .dat is carried unmodified, not edited")
        dat_abs = os.path.join(mod_dir, E.DAT_REL)
        check(os.path.exists(dat_abs),
              "the carrier .dat really is on disk (the game needs it there)")
        check(man.get("dat_identical_to_base") is True,
              "and it is byte-identical to the base game's .dat")
        check(os.path.exists(os.path.join(mod_dir, "info.json")),
              "info.json is at the mod root")

        # ---- 4. read it back the way the engine would ---------------------
        shipped = os.path.join(mod_dir, rel)
        check(os.path.exists(shipped), "the file is at the engine's own path")
        with open(shipped, "rb") as fh:
            blob = fh.read()

        # Byte-identical to a fresh serialisation of the same tree: proves the
        # writer did not reflow/re-escape on the way through the emitter.
        check(blob == CT.serialize(target),
              "the emitted bytes equal serialize(tree) exactly")
        # And it must still parse to the edited object.
        back = json.loads(blob.decode("utf-8"))
        check(back.get("civ_id") == TARGET, "civ_id survived", back.get("civ_id"))
        parsed_units = {e.get("Node ID"): e.get("Node Status")
                        for e in back.get("civ_techs_units") or []
                        if isinstance(e, dict) and e.get("Use Type") == "Unit"}
        check(parsed_units.get(NODE) == "ResearchedCompleted",
              "the granted node reads ResearchedCompleted from the FILE",
              parsed_units.get(NODE))

        # ---- 5. nothing else moved ---------------------------------------
        base_blob = open(os.path.join(GAME, rel), "rb").read()
        base = json.loads(base_blob.decode("utf-8"))
        bu = [e for e in base.get("civ_techs_units") or [] if isinstance(e, dict)]
        nu = [e for e in back.get("civ_techs_units") or [] if isinstance(e, dict)]
        check(len(nu) == len(bu) + 1,
              "exactly one row was added (%d -> %d)" % (len(bu), len(nu)))
        # Every pre-existing row must be untouched, key order included.
        by_id = {}
        for e in bu:
            by_id.setdefault((e.get("Node ID"), e.get("Use Type")), []).append(e)
        untouched = 0
        mutated = []
        for e in nu:
            key = (e.get("Node ID"), e.get("Use Type"))
            cand = by_id.get(key)
            if not cand:
                continue                      # the new row, or a second copy
            if json.dumps(cand[0], ensure_ascii=False) == json.dumps(e, ensure_ascii=False):
                untouched += 1
            else:
                mutated.append(key)
        check(not mutated, "no pre-existing row changed", mutated[:4])
        print("    (%d pre-existing rows verified byte-for-byte)" % untouched)

        # The buildings list must be completely untouched.
        check(json.dumps(base.get("civ_techs_buildings"), ensure_ascii=False)
              == json.dumps(back.get("civ_techs_buildings"), ensure_ascii=False),
              "the buildings list is untouched")

        # ---- 6. the OTHER civs must not be affected ----------------------
        check(CT.node_status(trees[OWNER], NODE) == "ResearchedCompleted",
              "the donor civ still has it (the copy did not move it)")
        others = [c for c in trees if c not in (OWNER, TARGET)
                  and CT.node_status(trees[c], NODE) is not None]
        check(not others, "no other civ gained or lost the node", others[:5])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("PROVEN      the edited tree serialises byte-exactly, lands at the path the")
    print("            engine formats, re-parses to the intended object, adds exactly")
    print("            one row, and leaves every other row and civ untouched.")
    print("ANSWERED 2026-10-19: this JSON-only path does NOT make a running game")
    print("            grant the unit.  `dsh test v15` installed exactly this shape --")
    print("            a CivTechTrees file over a byte-identical `.dat` -- in both")
    print("            directions, the engine logged loading the mod, and the build")
    print("            menu moved neither way.  What does grant it is the `.dat` half")
    print("            (`dsh test v7`, 2026-10-16: Dark Age Barracks showed the")
    print("            Champi Scout), which this file deliberately does not build.")
    print()
    if fails:
        print("AVAILABILITY END TO END: %d FAILED" % len(fails))
        for f in fails:
            print("   - %s" % f)
        return 1
    print("AVAILABILITY END TO END: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
