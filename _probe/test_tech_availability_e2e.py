"""End-to-end: can a civilization be given a TECHNOLOGY?

Black box: only the public surface (`open_toolkit`, `plan`, `build`,
`describe`, and the `civtechtrees` reader the product itself uses).  The unit
side has had this test since `unit.availability` landed; this is its mirror for
the OTHER id space, and the mirror matters because the two spaces SHARE
integers: id 8 is a Longbowman row for BRITONS and a Town Watch TECH row for the
other 61, so an implementation that drops `use_types` somewhere does not fail
loudly -- it answers about the wrong entity.
"""
import os
import _gamepaths as GP
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A
from aoe2mod.game import civtechtrees as CT

GAME = GP.GAME
TU = CT.TECH_USE_TYPES
FAILS = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           "" if not detail else " -- %s" % detail))
    if not ok:
        FAILS.append(label)


def any_dat(root):
    for _d, _s, fs in os.walk(root):
        if any(f.endswith(".dat") for f in fs):
            return True
    return False


def main():
    tk = A.open_toolkit(GAME)
    tk._ensure()
    trees = tk._trees()
    britons = trees["BRITONS"]

    # Yeomen (3) is a UniqueTech: exactly one civ may research it.  Loom (22) is
    # offered by all 62, so it is the wrong probe for a GRANT -- but exactly the
    # right probe for "the civ already has it".
    yeomen = 3
    print("Yeomen (%d): owners %s" % (yeomen, CT.owners(trees, yeomen, use_types=TU)))

    # ---- read side ------------------------------------------------------
    for tid in (22, 8, 249, 101):
        av = tk.describe(tid, kind="tech").get("availability")
        check(av is not None and av["builder_count"] == 62,
              "tech %d is offered by all 62 civs" % tid,
              None if av is None else "builders=%s" % av["builder_count"])
        check(av is not None and av["space"] == "Tech",
              "tech %d says its space" % tid,
              None if av is None else av["space"])

    # The trap, both directions.  `node_status` takes ONE tree, not the corpus.
    check(tk.describe(8, kind="unit")["availability"]["space"] == "Unit",
          "unit id 8 still reports the UNIT space")
    check(tk.describe(8, kind="tech")["availability"]["space"] == "Tech",
          "tech id 8 reports the TECH space")
    check(CT.node_status(britons, 22) is None,
          "the unit-filtered reader still says nobody has Loom (that is why "
          "use_types exists)")
    check(CT.node_status(britons, 22, use_types=TU) == "ResearchedCompleted",
          "with the tech space Loom reads ResearchedCompleted",
          str(CT.node_status(britons, 22, use_types=TU)))

    # ---- plan: a grant that really adds a row ---------------------------
    intent = {"intent": "tech.availability", "tech": yeomen, "civ": "Goths",
              "action": "grant"}
    p = tk.plan(intent)
    print("PLAN   %s" % {k: p.get(k) for k in
                         ("description", "civ", "space", "mode", "donor",
                          "edit_count", "mod_contains_dat")})
    check(p["editable"] is True, "granting Yeomen to Goths is editable",
          str(p.get("reason", "")))
    check(p["mode"] == "add_row", "it is an add_row", str(p.get("mode")))
    check("研究" in p["description"] and "建造" not in p["description"],
          "the sentence uses the RESEARCH verb, not 'build'",
          p["description"])
    check(p["space"] == "Tech", "the plan says which space it is")
    # The plan must promise what the build delivers: no `.dat` BYTE changes, but an
    # unmodified carrier `.dat` IS included, because the game fails to start when a
    # mod overrides the DAT storage point without it.
    check(p["edit_count"] == 0 and p["changes_dat"] is False,
          "no .dat byte is changed")
    check(p["mod_contains_dat"] is True and p["dat_is_carrier"] is True,
          "and the plan says the carrier .dat will be included")

    # ---- build ----------------------------------------------------------
    tmp = tempfile.mkdtemp(prefix="aoe2mod techavail ")
    try:
        out = os.path.join(tmp, "tech mod")
        man = tk.build(intent, out, title="Goths get Yeomen",
                       author="aoe2mod probe")
        v = man["verification"]
        print("BUILD  ok=%s space=%s node=%s" % (v["ok"], man["space"],
                                                 man["node_name"]))
        check(v["ok"] is True, "the build verifies")
        check(man["space"] == "Tech", "the manifest says the space",
              man["space"])
        check(man["node_id"] == yeomen and man["node_name"],
              "the manifest names the node",
              "%s/%s" % (man["node_id"], man["node_name"]))
        check(v["serializer_is_exact"] and v["serialize_reparses"]
              and v["untouched_rows_identical"],
              "all three JSON assertions hold")
        check("technology" in " ".join(v["not_proven"]),
              "the honesty boundary says 'technology'",
              " ".join(v["not_proven"]))

        # Read back from disk, the way the engine would.
        back = CT.load_trees(out)
        key = CT.civ_file_stem("Goths")
        check(list(back) == [key], "the mod carries exactly one tree file",
              str(list(back)))
        check(CT.has(back[key], yeomen, TU),
              "GOTHS can research Yeomen on disk now")
        check(CT.node_status(back[key], yeomen, use_types=TU)
              == "ResearchedCompleted", "and its status says so")
        check(CT.has(britons, yeomen, TU),
              "BRITONS (the donor) still has it in the game's own copy")
        check(len(CT.rows_of(back[key])) == len(CT.rows_of(trees[key])) + 1,
              "granting a tech added exactly one row",
              "%d -> %d" % (len(CT.rows_of(trees[key])),
                            len(CT.rows_of(back[key]))))
        # The `.dat` must BE there (unmodified) -- the game fails to start when a
        # mod overrides the DAT storage point without it.  This assertion used to
        # require the opposite and so pinned that defect.
        check(any_dat(out),
              "the unmodified carrier .dat IS in the mod folder (the game needs it)")
        check(man.get("dat_is_carrier") is True
              and man.get("changes_dat") is False,
              "and the manifest distinguishes a carried .dat from a changed one")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- the 'no's stay different sentences -----------------------------
    # The separate sentences are the CONTRACT; the exact wording is not.  These
    # used to assert English words ("already", "nothing to take away"), which
    # made a legitimate wording change look like a regression -- and would have
    # blocked translating the sentence for the player who actually reads it.
    already = tk.plan({"intent": "tech.availability", "tech": yeomen,
                       "civ": "British", "action": "grant"})
    check(already["editable"] is False and bool(already["description"]),
          "a civ that already has it is refused in its own words",
          already["description"])
    absent = tk.plan({"intent": "tech.availability", "tech": yeomen,
                      "civ": "Goths", "action": "revoke"})
    check(absent["editable"] is False and bool(absent["description"]),
          "revoking what it never had says so",
          absent["description"])
    check(already["description"] != absent["description"],
          "and the two refusals are DIFFERENT sentences, not one repeated",
          "%r vs %r" % (already["description"], absent["description"]))

    # A NotAvailable row is a THIRD case: the civ is listed and cannot get it,
    # so the answer is a status change, not an added row.  Measured in
    # _probe/probe_tech_row_uniformity.py: all 857 NotAvailable tech rows have
    # another civ that does offer the tech.
    blocked = None
    for civ, t in sorted(trees.items()):
        for nid in range(0, 1510):
            if CT.node_status(t, nid, use_types=TU) == "NotAvailable" \
                    and CT.owners(trees, nid, use_types=TU):
                blocked = (civ, nid)
                break
        if blocked:
            break
    if blocked:
        civ, nid = blocked
        st = tk.plan({"intent": "tech.availability", "tech": nid, "civ": civ,
                      "action": "grant"})
        print("Status-change case: %s tech %d -> mode %s"
              % (civ, nid, st.get("mode")))
        check(st["editable"] is True and st.get("mode") == "set_status",
              "a listed-but-unavailable tech is a set_status",
              "%s / %s" % (st.get("editable"), st.get("mode")))
        check(st.get("was_status") == "NotAvailable",
              "and the plan says what it was", str(st.get("was_status")))
    else:
        check(False, "there is a NotAvailable tech row with another civ holding it")

    try:
        tk.plan({"intent": "tech.availability", "tech": yeomen, "civ": "Atlantis",
                 "action": "grant"})
        check(False, "an unknown civ must raise, not return a dict")
    except Exception as exc:
        check("Atlantis" in str(exc) or "unknown" in str(exc),
              "an unknown civ raises IntentError", str(exc))

    print()
    if FAILS:
        print("TECH AVAILABILITY E2E: FAILED -> %s" % FAILS)
        return 1
    print("TECH AVAILABILITY E2E: ALL CHECKS PASSED")
    print("PROVEN: a byte-exact CivTechTrees file under the engine's path, "
          "with the named tech row added and no other row changed.")
    print("NOT MEASURED: whether a running game offers the TECHNOLOGY.  The")
    print("  unit-space question was answered -- a tree-only write moves nothing")
    print("  (v15), and a `.dat` `type 2` command on a tech the civ owns does")
    print("  (v7/v17) -- but no experiment has ever put a tech row in front of")
    print("  the player and looked at the research panel.  Do not extrapolate the")
    print("  unit result to technologies without saying so.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
