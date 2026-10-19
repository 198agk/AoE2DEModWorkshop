"""Pin the structural facts about the DAT storage-point layer.

Context: on 2026-10-14 ONE mod carried two halves.  Its `.dat` took effect in
game; its `resources/_common/dat/CivTechTrees/BRITONS.json` did not.  The user's
verbatim report was:

    "村民血量 1000/1000，而且派活之后仍然是 1000。靶场里不能造 火枪手，
     兵营里不能造 蔷琵侦察兵。"

This probe pins what can be established WITHOUT the game running, so the
explanations that are dead stay dead and the ones that are alive stay written
down.  Each assertion below kills or preserves one hypothesis:

  A. The DAT storage point is declared differently from every other one --
     it is the ONLY entry carrying `use_modes_path_for_mods`, and it is one of
     the entries with NO `replace` flag.  (Pompeii.json, 28 entries.)
     -> Kills "the DAT storage point is declared like the rest, so a mod's copy
        must be found the same way."  It is not declared like the rest.

  B. The tree layer is NOT structurally disqualified from being the build-panel
     model: every one of the 2,719 rows a civ "has" (ResearchedCompleted) names
     a Building ID that IS in that civ's own tree -- 0 exceptions over 62 civs.
     -> Kills the tidy "the tree is a flat capability list, so of course the
        panel ignores it" explanation.  The tree is internally consistent with a
        per-building reading.  The null result still needs a real cause.

  C. The aggregate `civTechTrees.json` (1,671,526 B, 17 civs, keys `civ_id` /
     `civ_techs_buildings` / `civ_techs_units`) exists ONLY under `modes/Pompeii`
     -- there is no `resources/_common/dat/civTechTrees.json` in the main tree.
     -> So the main game's per-civ template `CivTechTrees/%s.json` is the real
        main-tree path, and the aggregate is a mode-layer artifact.

  D. Row keys in the aggregate are exactly the per-civ row keys, so the two
     formats are the same object at different granularity.

ANSWERED SINCE (2026-10-19), and not in the direction this file expected: the
build panel reads NEITHER JSON file.  `futuravailableunits.json` is excluded in
both directions by two plain-game runs (Sicilians: panel silent, the game still
offered the unit; Poles: panel listed the unit AND its upgrade tech, the game
offered neither).  The tree is read -- the tech-tree PREVIEW screen reads it --
but a mod-side rewrite of it does not move the build menu (`dsh test v15`: two
tree files, both directions, byte-identical `.dat`, engine log confirming the
load, zero change on screen).  What DOES move the menu is a `.dat` `type 2`
Enable/Disable Unit command hung on a technology the civilization owns, where
the last command to fire wins (`dsh test v7` grant, `dsh test v17` revoke).
The 2026-10-14 failure was therefore neither form, nor name, nor scheduling.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                                  # noqa: E402
from aoe2mod.game import civtechtrees as CT              # noqa: E402

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
POMPEII = os.path.join(ROOT, "modes", "Pompeii", "Pompeii.json")
EXE = os.path.join(ROOT, "AoE2DE_s.exe")
AGG_MAIN = os.path.join(ROOT, "resources", "_common", "dat", "civTechTrees.json")
AGG_POMPEII = os.path.join(ROOT, "modes", "Pompeii", "resources", "_common",
                           "dat", "civTechTrees.json")

FAILS = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)


def main():
    print("DAT-LAYER STRUCTURE")
    print("=" * 74)

    # ---------------------------------------------------------------- A
    print()
    print("A  the DAT storage point's own declaration")
    sp = json.load(open(POMPEII, encoding="utf-8"))["storage_point_list"]
    flagged = [e["type"] for e in sp if "use_modes_path_for_mods" in e]
    replaced = sorted(e["type"] for e in sp if e.get("replace"))
    dat = [e for e in sp if e.get("type") == "DAT"]
    check(len(sp) == 28, "Pompeii declares 28 storage points", str(len(sp)))
    check(len(dat) == 1, "exactly one DAT entry")
    check(flagged == ["DAT"],
          "DAT is the ONLY entry carrying use_modes_path_for_mods",
          str(flagged))
    check("DAT" not in replaced,
          "and it is not one of the replace=true entries",
          "%d replace=true: %s" % (len(replaced), replaced))
    check(dat[0]["path"] == "resources\\_common\\dat",
          "its path is resources\\_common\\dat", dat[0]["path"])
    check(dat[0].get("use_modes_path_for_mods") is True,
          "use_modes_path_for_mods is true, not merely present")
    # strings + widgetui are the ones with FIELD evidence of mod override
    for t in ("STRINGS", "WIDGETUI"):
        e = [x for x in sp if x.get("type") == t]
        check(len(e) == 1 and "use_modes_path_for_mods" not in e[0],
              "%s is declared WITHOUT that flag (it demonstrably overrides)"
              % t, json.dumps(e[0], ensure_ascii=False) if e else "")

    # ---------------------------------------------------------------- B
    print()
    print("B  can the tree even be the build panel?  (per-building consistency)")
    tk = A.open_toolkit()
    trees = CT.load_trees(tk.game_root)
    check(len(trees) == 62, "62 tree files", str(len(trees)))
    total = ready = unreachable = nob = 0
    for civ in trees:
        tree = trees[civ]
        for row in CT.unit_rows(tree):
            total += 1
            if row.get("Node Status") != "ResearchedCompleted":
                continue
            ready += 1
            bid = row.get("Building ID")
            if bid is None:
                nob += 1
                continue
            if not CT.reaches_building(tree, bid):
                unreachable += 1
    check(total == 3686, "3,686 unit rows in total", str(total))
    check(ready == 2719, "2,719 of them read ResearchedCompleted", str(ready))
    check(nob == 0, "every one names a Building ID", str(nob))
    check(unreachable == 0,
          "0 have a producing building outside their own civ's tree",
          str(unreachable))
    print("       -> the tree is internally consistent with a per-building")
    print("          reading; 'the tree is the wrong shape' is NOT the answer")

    # ---------------------------------------------------------------- C
    print()
    print("C  the aggregate civTechTrees.json is a mode-layer artifact")
    check(not os.path.isfile(AGG_MAIN),
          "the main tree has NO resources/_common/dat/civTechTrees.json")
    check(os.path.isfile(AGG_POMPEII), "Pompeii ships one")
    if os.path.isfile(AGG_POMPEII):
        check(os.path.getsize(AGG_POMPEII) == 1671526,
              "it is 1,671,526 B", str(os.path.getsize(AGG_POMPEII)))
        agg = json.load(open(AGG_POMPEII, encoding="utf-8"))
        check(list(agg) == ["civs"], "top level is a single 'civs' list",
              str(list(agg)))
        check(len(agg["civs"]) == 17, "17 civ entries", str(len(agg["civs"])))
        want = {"civ_id", "civ_techs_buildings", "civ_techs_units"}
        keysets = {frozenset(c) for c in agg["civs"]}
        check(keysets == {frozenset(want)},
              "every entry carries exactly civ_id + the two row lists",
              str(keysets))

    # ---------------------------------------------------------------- D
    print()
    print("D  the aggregate uses the same row objects as the per-civ files")
    if os.path.isfile(AGG_POMPEII):
        agg = json.load(open(AGG_POMPEII, encoding="utf-8"))
        # NOTE 1: row key sets VARY WITHIN one file (measured earlier: two shapes
        # for tech rows, and unit rows split 12-key / 14-key).  Comparing one row
        # against one row is therefore too strict and fails for a reason that has
        # nothing to do with the two formats differing -- compare UNIONS.
        # NOTE 2: the first version of the second check read
        # `set(ukeys) <= set(arow) | ukeys`, which is true by construction -- an
        # always-true predicate, the exact trap this project already documented.
        # Both directions below are real comparisons.
        ukeys = {k for c in agg["civs"] for r in c["civ_techs_units"] for k in r}
        fkeys = {k for civ in trees for r in CT.unit_rows(trees[civ]) for k in r}
        check(ukeys == fkeys,
              "aggregate unit-row KEYS == per-civ unit-row KEYS",
              "only-in-aggregate %s / only-in-files %s"
              % (sorted(ukeys - fkeys), sorted(fkeys - ukeys)))
        # the row VALUES must also be the same shape language, not just names
        arow = agg["civs"][0]["civ_techs_units"][0]
        check("Node Status" in arow and "Use Type" in arow,
              "an aggregate row carries Node Status and Use Type",
              "keys %s" % sorted(arow))
        nrows = sum(len(c["civ_techs_units"]) for c in agg["civs"])
        check(nrows == 1700, "1,700 aggregate unit rows over 17 civs",
              str(nrows))

    # ---------------------------------------------------------------- E
    print()
    print("E  the engine names the per-civ file template")
    b = open(EXE, "rb").read()
    check(b.count(b"CivTechTrees/%s.json") == 1,
          "exe carries the template CivTechTrees/%s.json exactly once")
    i = b.find(b"CivTechTrees/%s.json")
    near = b[max(0, i - 200):i + 40].decode("ascii", "replace")
    for fld in ("civ_id", "civ_techs_buildings", "civ_techs_units"):
        check(fld in near, "field %r sits adjacent to the template" % fld)
    check(b.count(b"futuravailableunits.json") == 1,
          "exe names futuravailableunits.json exactly once too")

    print()
    print("=" * 74)
    if FAILS:
        print("DAT-LAYER STRUCTURE: %d CHECK(S) FAILED" % len(FAILS))
        for f in FAILS:
            print("   - %s" % f)
        return 1
    print("DAT-LAYER STRUCTURE: the DAT storage point is declared uniquely;")
    print("the tree is not disqualified by shape; the aggregate is mode-only.")
    print()
    print("ANSWERED SINCE (2026-10-19): the question this file deferred is closed,")
    print("            and the build panel follows none of these three JSON files.")
    print("            The panel file is excluded in BOTH directions (Sicilians: not")
    print("            listed, game offered it; Poles: listed with its tech, game")
    print("            offered neither).  The tree is read but does not move the")
    print("            menu (dsh test v15).  A `.dat` `type 2` command on a tech the")
    print("            civ owns does, last one to fire wins (v7 grant, v17 revoke).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
