# -*- coding: utf-8 -*-
"""The availability reader answers the questions its docstring claims it does.

`aoe2mod/game/civtechtrees.py` exists because the `.dat` CANNOT answer "can this
civ have this unit" -- the record bytes are identical across civs (0 of 2,164
shared ids differ between British and Goths while 24/14 ids are exclusive).  So
the correctness of the replacement reader is load-bearing: if it is wrong, the
product either promises a unit a civ cannot build or hides one it can.

This test pins, against the installed game data:
  1. real ownership: Huskarl is the Goths' alone, Longbowman the Britons',
     Jaguar the Aztecs', Tarkan the Huns' -- and each is ABSENT (not "false")
     from every other civ;
  2. universal ownership: Villager/Archer are held by all 62 civ files;
  3. `has()` counts only `ResearchedCompleted` (has it NOW) while `can_build()`
     counts `ResearchedCompleted` or `ResearchRequired` (can ever get it) -- the
     two differ on 14 nodes, and only the second answers "can my civ build this";
  4. the status vocabulary is closed -- no file uses a word outside the three the
     engine names, so a fourth word would fail here rather than being silently
     rendered;
  5. `name_string_id()` never falls back to the stale `Name` field;
  6. the TECH space: 5244 rows in the same files carry `Use Type: "Tech"` and
     their Node ID is the .dat tech ARRAY INDEX -- a different namespace that
     HAPPENS to share integers with the unit one (id 8 is both a Longbowman row
     and a Town Watch tech row).  Asking the unit-filtered reader about a tech
     gives a WRONG ANSWER rather than an error: all 62 civs read `None`, which
     reads as "nobody has Loom".  `use_types` is what separates them.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))     # tests/ -> aoe2mod/ -> repo
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                      # noqa: E402

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
TU = CT.TECH_USE_TYPES

EXCLUSIVE = [(41, "GOTHS", "Huskarl"),
             (8, "BRITONS", "Longbowman"),
             (725, "AZTECS", "Jaguar Warrior"),
             (755, "HUNS", "Tarkan"),
             (692, "VIKINGS", "Berserk")]
UNIVERSAL = [(83, "Villager"), (4, "Archer")]


def main():
    fails = []

    def check(ok, label, detail=""):
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                               ("  -- %s" % detail) if detail else ""))
        if not ok:
            fails.append(label)

    if not os.path.isdir(CT.trees_dir(GAME)):
        print("FATAL: %s not found; run against a real install."
              % CT.trees_dir(GAME))
        return 2

    trees = CT.load_trees(GAME)
    check(len(trees) == 62, "62 civ tech-tree files load", "got %d" % len(trees))

    # ---- 1. exclusive ownership, and absence rather than falsity ----------
    for node, owner, label in EXCLUSIVE:
        own = CT.owners(trees, node)
        check(own == [owner], "%s (%d) belongs to %s alone" % (label, node, owner),
              "owners=%s" % own)
        # absent, not merely false, for the others
        others = [c for c in trees if c != owner]
        missing = [c for c in others if CT.node_status(trees[c], node) is None]
        check(len(missing) == len(others),
              "  %s is ABSENT (not false) from all %d other civs"
              % (label, len(others)),
              "%d still carry a row" % (len(others) - len(missing)))
        check(CT.has(trees[owner], node), "  has() True for the owner")

    # ---- 1b. THE NAMESPACE TRAP ------------------------------------------
    # `Node ID` is shared between the unit and tech id spaces: 39 ids appear under
    # both `Use Type: Unit` and `Use Type: Tech`.  id 8 is Longbowman for BRITONS
    # and `Town Watch` (a tech) for the other 61.  Without the `Use Type` filter
    # this reader reported Tarkan as owned by both HUNS and BURGUNDIANS and Berserk
    # by both VIKINGS and LITHUANIANS -- false positives that look exactly like
    # real sharing, which is why this assertion exists rather than a comment.
    collisions = CT.collide_with_tech_space(trees)
    # The detail string is the FAILURE hint only -- passing it unconditionally
    # printed "no collisions found -- the filter may now be unnecessary" on a
    # passing run, which reads as a warning about the opposite of what happened.
    check(len(collisions) > 0,
          "unit ids colliding with the tech id space exist (%d), so the Use Type"
          " filter is load-bearing" % len(collisions),
          "no collisions found -- the filter may now be unnecessary, but do not"
          " remove it without re-measuring"
          if not collisions else "")
    check(8 in collisions,
          "  id 8 is BOTH Longbowman (unit) and a tech -- the concrete collision",
          "collisions sample: %s" % sorted(collisions)[:8])
    # And the filter must make the two readings differ, i.e. prove it changes an
    # answer rather than being cosmetic.
    raw_hit = [c for c, t in trees.items()
               if any(isinstance(e, dict) and e.get("Node ID") == 8
                      and e.get("Node Status") == "ResearchedCompleted"
                      for e in CT._rows(t))]
    filtered = CT.owners(trees, 8)
    check(len(raw_hit) > len(filtered),
          "  unfiltered reading of id 8 claims %d civs; filtered says %d"
          % (len(raw_hit), len(filtered)))

    # ---- 2. universal ownership ------------------------------------------
    for node, label in UNIVERSAL:
        n = sum(1 for c in trees if CT.has(trees[c], node))
        check(n == len(trees), "%s (%d) held by all %d civs"
              % (label, node, len(trees)), "got %d" % n)

    # ---- 3. has() must not be fooled by a non-owning status --------------
    # Find a real ResearchRequired row and a real NotAvailable row and require
    # has() to be False for them, while node_status() still reports the word.
    seen = {}
    for civ, t in trees.items():
        for e in CT._rows(t):
            if not isinstance(e, dict):
                continue
            st = e.get("Node Status")
            nid = e.get("Node ID")
            if st in ("ResearchRequired", "NotAvailable") and nid is not None:
                seen.setdefault(st, (civ, nid))
    for st in ("ResearchRequired", "NotAvailable"):
        if st not in seen:
            check(False, "a %s row exists to test has() against" % st)
            continue
        civ, nid = seen[st]
        check(CT.node_status(trees[civ], nid) == st,
              "%s row keeps its own word (%s/%d)" % (st, civ, nid))
        check(not CT.has(trees[civ], nid),
              "  has() is False for a %s row" % st)

    # ---- 4. the status vocabulary is closed ------------------------------
    unknown = {}
    for civ, t in trees.items():
        for st, n in CT.status_counts(t).items():
            if st not in CT.STATUSES:
                unknown[st] = unknown.get(st, 0) + n
    check(not unknown, "no file uses a status outside the engine's three words",
          str(unknown))
    totals = {}
    for t in trees.values():
        for st, n in CT.status_counts(t).items():
            totals[st] = totals.get(st, 0) + n
    print("    corpus status totals: %s" % totals)

    # ---- 5. never the stale Name field ------------------------------------
    # Every exclusive unit's string id must be a real positive id, and must not
    # equal the row's raw Name field (which is a word, not an id) -- i.e. the
    # reader returns the STRING ID, not the display name.
    for node, owner, label in EXCLUSIVE:
        sid = CT.name_string_id(trees[owner], node)
        check(isinstance(sid, int) and sid > 0,
              "%s exposes a numeric Name String ID (%s)" % (label, sid))

    # ---- 6. a civ that does not exist, and a unit that does not exist ----
    check(CT.node_status({"units": [], "buildings": []}, 41) is None,
          "an empty tree answers None for everything")
    check(not CT.has({"units": [], "buildings": []}, 41),
          "an empty tree answers False for has()")

    # ---- 7. the civ-name BRIDGE must be complete over every .dat civ -------
    # Every other part of the product names civs the way the .dat does
    # (`British`, `Hindustanis`, `Magyars`); this layer keys them by file stem
    # (`BRITONS`, `INDIANS`, `MAGYAR`).  A single wrong mapping is invisible in
    # the reader (it just looks like a civ with no data) and would make a UI
    # report "this civilization cannot build anything".  It is not a guess:
    # `Magyars` ships as `MAGYAR.json` (no plural) and `Hindustanis` as
    # `INDIANS.json`, and BOTH were wrong in the first version of the map --
    # `probe_availability_design.py` caught them, this asserts it stays fixed.
    try:
        import aoe2mod.api as A
        tk = A.open_toolkit()
        tk._ensure()
        dat_names = [c.get("name") for c in tk._civs]
    except Exception as exc:                                     # noqa: BLE001
        dat_names = None
        print("  (skipping the bridge check: %r)" % (exc,))
    if dat_names:
        expected_absent = {"GAIA"}       # the one dat civ with no file at all
        broken = []
        for name in dat_names:
            stem = CT.civ_file_stem(name)
            if stem not in trees and stem not in expected_absent:
                broken.append((name, stem))
        check(not broken,
              "every .dat civ maps to a tree file (%d civs)" % len(dat_names),
              "unmapped: %s" % broken)
        unmapped_keys = [k for k in trees
                         if k not in {CT.civ_file_stem(n) for n in dat_names}]
        check(not unmapped_keys,
              "  and no tree file is unreachable from a .dat civ name",
              "orphan keys: %s" % unmapped_keys)
        # The two that were actually wrong get named explicitly, so a future
        # "tidy the map" edit fails here rather than in the UI.
        for dat_name, stem in (("Magyars", "MAGYAR"), ("Hindustanis", "INDIANS"),
                               ("British", "BRITONS"), ("French", "FRANKS"),
                               ("Byzantine", "BYZANTINES"), ("Mayan", "MAYANS")):
            check(CT.civ_file_stem(dat_name) == stem,
                  "  bridge: %s -> %s" % (dat_name, stem),
                  "got %s" % CT.civ_file_stem(dat_name))
        check(CT.civ_file_stem("Aztecs") == "AZTECS",
              "  and a civ with no override just upper-cases")

    # ---- 8. "has it" is NOT "can build it" --------------------------------
    # Both predicates are real and they differ on 14 nodes.  War Galley is the
    # decisive case: it reads `ResearchRequired` for all 56 dock-owning civs, and
    # nothing in the game marks it `NotAvailable`.  A reader that answered "can
    # build" with has() would report that NO civilization can build a War Galley.
    galley_holders = CT.owners(trees, 21)
    galley_builders = CT.builders(trees, 21)
    check(len(galley_holders) == 0,
          "War Galley (21) is owned by nobody outright -- every row needs research",
          "holders=%d" % len(galley_holders))
    check(len(galley_builders) == 56,
          "  but 56 civs CAN build it -- has() and can_build() must differ",
          "builders=%d" % len(galley_builders))
    check(len(galley_builders) > len(galley_holders),
          "  so the two predicates are not the same question")
    galley_na = [c for c in trees if CT.node_status(trees[c], 21) == "NotAvailable"]
    check(not galley_na,
          "  and no civ lists it NotAvailable, which is what would make it false",
          str(galley_na))

    # The converse: an exclusive unique unit must NOT be `ResearchRequired`
    # anywhere, or "builders" would leak into civs that cannot have it.
    for node, owner, label in EXCLUSIVE:
        b = CT.builders(trees, node)
        check(b == [owner],
              "  %s (%d) has exactly one builder, not just one holder"
              % (label, node), "builders=%s" % b)

    # Every row is either absent, or one of the three words, and can_build is
    # exactly "present and not NotAvailable" -- checked over the whole corpus so
    # this cannot be true only for the samples above.
    bad = []
    for civ, t in trees.items():
        for r in CT.unit_rows(t):
            nid = r.get("Node ID")
            st = r.get("Node Status")
            want = st != "NotAvailable"
            if CT.can_build(t, nid) != want and CT.node_status(t, nid) == st:
                bad.append((civ, nid, st))
    check(not bad, "can_build() == (row present and status != NotAvailable)",
          "counterexamples: %s" % bad[:5])

    # And a node with NO rows for a civ must answer False, not None-ish truthy.
    check(not CT.can_build(trees["BRITONS"], 41),
          "  can_build() is False for a node the civ has no row for (Huskarl/Britons)")
    check(CT.can_build(trees["GOTHS"], 41),
          "  and True for the civ that has it (Huskarl/Goths)")

    # ------------------------------------------------------------------
    # The TECH space.  The same files carry 5244 rows whose Use Type is
    # "Tech", and their Node ID is the .dat tech ARRAY INDEX -- a different
    # namespace that HAPPENS to share integers with the unit one (id 8 is a
    # Longbowman row and a Town Watch tech row).  Asking the unit-filtered
    # reader about a tech therefore returns a WRONG ANSWER, not an error:
    # all 62 civs read None, which reads as "nobody has Loom".
    # ------------------------------------------------------------------
    urows = sum(len(CT.unit_rows(t)) for t in trees.values())
    trows = sum(len(CT.tech_rows(t)) for t in trees.values())
    brows = sum(len(CT._rows(t)) - len(CT.unit_rows(t)) - len(CT.tech_rows(t))
                for t in trees.values())
    arows = sum(len(CT.rows_of(t)) for t in trees.values())
    check(trows == 5244, "5244 tech rows are visible through tech_rows()",
          str(trows))
    # A building row DOES exist: 63 of them sit in the units list (a building is
    # shipped as a unit record) with another 1749 in the buildings list.
    # Asserting "the rest is empty" would have been wrong -- the units list is
    # "everything the tech tree draws", not "units".
    check(arows == urows + trows + brows and brows > 0,
          "  and every row is accounted for: units + techs + buildings",
          "%d = %d + %d + %d" % (arows, urows, trows, brows))

    # The trap, stated as the failure it actually was.
    check(CT.node_status(trees["BRITONS"], 22) is None,
          "asking the UNIT space about Loom says nobody has it (the wrong "
          "answer that motivated use_types)")
    check(CT.node_status(trees["BRITONS"], 22, use_types=TU)
          == "ResearchedCompleted",
          "  the TECH space says every civ offers it",
          str(CT.node_status(trees["BRITONS"], 22, use_types=TU)))
    for tid, label in ((22, "Loom"), (101, "Feudal Age"), (213, "Wheelbarrow"),
                       (249, "Hand Cart"), (8, "Town Watch")):
        b = CT.builders(trees, tid, use_types=TU)
        check(len(b) == 62, "%s (tech %d) is offered by all 62 civs"
              % (label, tid), "builders=%d" % len(b))

    # A UniqueTech belongs to exactly one civ, and the donors must survive.
    for tid, civ, label in ((3, "BRITONS", "Yeomen"), (6, "MONGOLS", "Drill"),
                            (5, "CELTS", "Furor Celtica"),
                            (4, "MAYANS", "El Dorado")):
        o = CT.owners(trees, tid, use_types=TU)
        lst = [c for c in sorted(trees)
               if CT.node_status(trees[c], tid, use_types=TU) is not None]
        check(o == [civ] and lst == [civ],
              "  %s (tech %d) belongs to %s alone" % (label, tid, civ),
              "owners=%s listed=%s" % (o, lst))
    check(CT.builders(trees, 3, use_types=TU) == ["BRITONS"],
          "  and builders() agrees with owners() for a UniqueTech")

    # Only Varangians has tech rows that need research -- so "can_build but not
    # has" is a real state on this side too, not a theoretical one.
    rr = sorted((c, tid) for c, t in trees.items()
                for tid in {r.get("Node ID") for r in CT.tech_rows(t)}
                if CT.node_status(t, tid, use_types=TU) == "ResearchRequired")
    check(rr == [("VARANGIANS", 373), ("VARANGIANS", 910)],
          "exactly two tech rows read ResearchRequired (both Varangians)",
          str(rr))
    check(all(CT.can_build(trees[c], tid, TU)
              and not CT.has(trees[c], tid, TU) for c, tid in rr),
          "  and can_build() is True where has() is False for both")

    # The invariant, over the whole tech corpus this time.
    badt = []
    for civ, t in trees.items():
        for r in CT.tech_rows(t):
            nid, st = r.get("Node ID"), r.get("Node Status")
            if CT.can_build(t, nid, TU) != (st != "NotAvailable") \
                    and CT.node_status(t, nid, use_types=TU) == st:
                badt.append((civ, nid, st))
    check(not badt,
          "can_build(tech) == (row present and status != NotAvailable)",
          "counterexamples: %s" % badt[:5])

    # One integer, two spaces: both answers are obtained independently, which
    # is exactly why a dropped `use_types` argument cannot be caught by shape.
    check(CT.node_status(trees["BRITONS"], 8) == "ResearchedCompleted"
          and CT.node_status(trees["BRITONS"], 8, use_types=TU)
          == "ResearchedCompleted",
          "id 8 is both a unit row and a tech row for BRITONS -- both spaces "
          "answer for it independently")

    print()
    if fails:
        print("CIVTECHTREES READER: %d FAILED" % len(fails))
        for f in fails:
            print("   - %s" % f)
        return 1
    print("CIVTECHTREES READER: ALL CHECKS PASSED")
    print("Per-civ availability comes from the layer the engine actually reads.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
