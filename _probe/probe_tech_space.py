# -*- coding: utf-8 -*-
"""After generalising the layer: does the tech space answer sensibly?

Before the change, `CT.node_status(trees, 22)` (Loom) returned None for all 62
civs -- "no civilization has Loom".  After, pass TECH_USE_TYPES and it should
answer.  This probe also pins the one claim that must not be guessed: what
`ResearchedCompleted` means on a TECH row.

Known-answer tests:
  * Loom / Feudal Age / Wheelbarrow are `ResearchedCompleted` for all 62 civs, and
    NOBODY starts the game with Feudal Age researched -> on a tech row the word
    cannot mean "already researched".  It means "this civ's tech tree offers it".
  * A unique tech (e.g. Yeomen, Britons) should be listed by its owner and ABSENT
    for the other 61, exactly like a unique unit.
  * `ResearchRequired` on a tech row is rare (2 rows, both VARANGIANS) and must
    stay reachable.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                      # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
TU = CT.TECH_USE_TYPES


def main():
    trees = CT.load_trees(GAME)
    names = json.load(open(os.path.join(ROOT, "aoe2mod", "semantic", "data",
                                        "tech_names.json"), encoding="utf-8"))
    fails = []

    def check(ok, label, detail=""):
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                               ("  -- " + str(detail)) if detail else ""))
        if not ok:
            fails.append(label)

    # 1. the tech rows are now reachable
    all_rows = sum(len([e for v in t.values() if isinstance(v, list)
                        for e in v if isinstance(e, dict)]) for t in trees.values())
    urows = sum(len(CT.unit_rows(t)) for t in trees.values())
    trows = sum(len(CT.tech_rows(t)) for t in trees.values())
    brows = sum(len([e for e in CT._rows(t)
                     if isinstance(e, dict) and e.get("Use Type") == "Building"])
                for t in trees.values())
    print("rows: every %d / unit %d / tech %d / building %d"
          % (all_rows, urows, trows, brows))
    check(trows == 5244, "5244 tech rows are visible through tech_rows()", trows)
    # Buildings are NOT absent from the units list: 63 building nodes sit inside
    # `civ_techs_units` while the other 1749 sit in `civ_techs_buildings`, so the
    # unit list is "everything the tech tree shows", not "units".
    check(all_rows == urows + trows + brows,
          "unit + tech + building accounts for every row",
          "%d - %d - %d - %d = %d" % (all_rows, urows, trows, brows,
                                      all_rows - urows - trows - brows))
    check(brows != 0, "building rows exist and are neither unit nor tech", brows)

    # 2. the trap is closed
    st_unit = Counter(CT.node_status(trees[c], 22) for c in trees)
    st_tech = Counter(CT.node_status(trees[c], 22, TU) for c in trees)
    check(st_unit == Counter({None: 62}),
          "asking the UNIT space about Loom still says nobody has it (the trap)",
          dict(st_unit))
    check(st_tech == Counter({"ResearchedCompleted": 62}),
          "asking the TECH space says all 62 civs offer Loom", dict(st_tech))

    # 3. semantic pin: ResearchedCompleted on a tech row cannot be 'already done'
    for nid, name, want in ((22, "Loom", 62), (101, "Feudal Age", 62),
                            (213, "Wheelbarrow", 62), (103, "Imperial Age", 62),
                            (249, "Hand Cart", 62)):
        n = len(CT.owners(trees, nid, "ResearchedCompleted", TU))
        check(n == want, "tech %d (%-13s) is offered by %d civs" % (nid, name, want), n)
    check(len(CT.owners(trees, 101, "ResearchedCompleted", TU)) == 62,
          "Feudal Age is 'available' for every civ -- so the word cannot mean "
          "'already researched'")

    # 4. unique techs behave like unique units
    for nid, name, civ in ((3, "Yeomen", "BRITONS"), (6, "Drill", "MONGOLS"),
                           (5, "Furor Celtica", "CELTS"), (4, "El Dorado", "MAYANS")):
        owners = CT.owners(trees, nid, "ResearchedCompleted", TU)
        listed = sorted(c for c in trees if CT.node_status(trees[c], nid, TU))
        check(owners == [civ] and listed == [civ],
              "tech %d (%-14s) belongs to %s alone" % (nid, name, civ),
              "owners=%s listed=%s" % (owners, listed))

    # 5. ResearchRequired stays reachable on the tech side
    rr = [(c, e.get("Node ID")) for c, t in trees.items()
          for e in CT.tech_rows(t) if e.get("Node Status") == "ResearchRequired"]
    check(len(rr) == 2, "two tech rows read ResearchRequired", rr)
    for civ, nid in rr:
        check(CT.can_build(trees[civ], nid, TU) and not CT.has(trees[civ], nid, TU),
              "%s tech %d is reachable but not held" % (civ, nid))

    # 6. can_build generalises: NotAvailable is the only 'no' that is listed
    bad = []
    for civ, t in trees.items():
        for e in CT.tech_rows(t):
            nid = e.get("Node ID")
            want = e.get("Node Status") != "NotAvailable"
            if CT.can_build(t, nid, TU) != want:
                bad.append((civ, nid, e.get("Node Status")))
    check(not bad, "can_build(tech) == (row present and status != NotAvailable)",
          bad[:4])

    # 7. the unit space is unchanged by the generalisation
    check(CT.owners(trees, 41, "ResearchedCompleted") == ["GOTHS"],
          "Huskarl is still owned by GOTHS alone")
    check(len(CT.builders(trees, 21)) == 56, "War Galley still has 56 builders",
          len(CT.builders(trees, 21)))
    check(CT.TECH_USE_TYPES != CT.UNIT_USE_TYPES,
          "the two spaces are distinct constants")

    # 8. builders/owners for a tech, measured
    print("\ntech availability on the known techs:")
    for nid, name in ((22, "Loom"), (3, "Yeomen"), (8, "Town Watch")):
        b = CT.builders(trees, nid, TU)
        o = CT.owners(trees, nid, "ResearchedCompleted", TU)
        print("   %-12s id=%-5d builders=%-3d owners=%-3d"
              % (name, nid, len(b), len(o)))
    sb = CT.builders(trees, 3, TU)
    check(sb == ["BRITONS"], "builders(tech) finds the unique-tech owner", sb)

    # 9. name_string_id, both spaces
    _h = CT.name_string_id(trees["GOTHS"], 41)
    check(_h is not None,
          "unit name id still resolves (Huskarl, GOTHS)", _h)
    check(CT.name_string_id(trees["BRITONS"], 41) is None,
          "and stays None for a civ with no such row (Huskarl, BRITONS)")
    y = CT.name_string_id(trees["BRITONS"], 3, TU)
    check(y is not None, "tech name id resolves for Yeomen", y)
    check(CT.node_status(trees["BRITONS"], 22) is None
          and CT.node_status(trees["BRITONS"], 22, TU) == "ResearchedCompleted",
          "one id, two spaces: the unit space says nothing, the tech space says yes")

    print("\n%s" % ("ALL TECH-SPACE CHECKS PASSED" if not fails
                    else "FAILED: %s" % fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
