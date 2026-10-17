"""What actually gates the in-game build panel.

Written after the first real in-game test of `unit.availability` came back
NEGATIVE.  A mod carrying BOTH a `.dat` edit and a modified
`resources/_common/dat/CivTechTrees/BRITONS.json` was installed and enabled
(the game log's own "Enabling mod #0 (aoe2mod smoke villager HP + Britons
units)" lines prove it loaded).  The user reported, verbatim:

    "村民血量 1000/1000，而且派活之后仍然是 1000。靶场里不能造 火枪手，
     兵营里不能造 蔷琵侦察兵。"

So the `.dat` half worked perfectly (villager HP 25 -> 1000, and the old
TaskSwapGroup regression -- "派活之后恢复 25" -- is fixed: it stayed 1000
after being reassigned).  The `CivTechTrees/<CIV>.json` half did nothing, in
BOTH modes: `add_row` (Champi Scout into the Barracks) and `set_status`
(Hand Cannoneer, which the shipped tree lists as `NotAvailable`, flipped to
`ResearchedCompleted`).

That result contradicts nothing in the data -- it contradicts an INFERENCE.
The write path into `CivTechTrees/` was always labelled "evidence-backed
inference, never observed", and this is the observation that killed it.

This probe therefore asks the next question instead of restating the old one:
if the tree file is not what the build panel reads, what is?  The strongest
candidate is `resources/_common/dat/futuravailableunits.json`, whose shape is
per-BUILDING and lists the units each building offers:

    {"Armenians": {"Buildings": [{"ID": 12, "Units": [{"ID": 74, ...}]}]}}

Measured agreement between "the tree says can_build" and "this file lists the
unit under some building", restricted to the 55 civs the file actually covers,
is 3261 agree / 18 disagree = 99.45%.  That is far too tight to be a
coincidence and far too tight to be the tree file's doing -- remember the tree
change had no effect at all.

HONEST BOUNDARY, and it matters here more than usual:
  PROVEN (data)   the two files agree on 99.45% of (civ, unit) pairs; the
                  `.dat` edit and the tree edit were in the SAME mod and the
                  game loaded that mod; the build panel did not change.
  NOT PROVEN      that `futuravailableunits.json` is what the panel reads, and
                  that editing IT would change the panel.  One in-game test of
                  an edit to that file is the only thing that can settle it.
  NOT PROVEN      WHY the tree override was ignored -- a mod-side path the
                  engine does not consult, a load-order effect, and
                  `civilizations.json`'s `tech_tree_name` being the real key
                  are all still open.

Do not read this file as "the tree layer is dead".  The tree layer is still the
best available MODEL of per-civ availability (99.45% agreement), and it is what
the read side reports.  What died is the claim that writing to it changes the
game.
"""

import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aoe2mod.game import civtechtrees as CT   # noqa: E402
import aoe2mod.api as A                       # noqa: E402

FU_REL = os.path.join("resources", "_common", "dat", "futuravailableunits.json")

fails = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- %s" % (detail,)) if detail else ""))
    if not ok:
        fails.append(label)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    trees = CT.load_trees(tk.game_root)
    fu_path = os.path.join(tk.game_root, FU_REL)
    if not os.path.isfile(fu_path):
        print("MISSING %s" % fu_path)
        return 2
    fu = json.load(open(fu_path, encoding="utf-8"))

    print("the game ships a SECOND per-civ availability file")
    print("  %s" % fu_path)
    print("  top-level: %d civs, each {\"Buildings\": [{ID, Units:[{ID,...}]}]}"
          % len(fu))
    check(len(fu) > 0, "the file describes civilizations", "%d" % len(fu))

    # --- resolve its civ keys against the tree keys ------------------------
    def resolve(key):
        if key in trees:
            return key
        up = key.upper()
        return up if up in trees else None

    fmap = {}
    for k in fu:
        t = resolve(k)
        if t:
            fmap[t] = k
    missing = sorted(set(trees) - set(fmap))
    print()
    print("  civs it covers: %d of %d tree files" % (len(fmap), len(trees)))
    print("  civs it does NOT cover: %s" % (missing,))
    check(len(fmap) >= 50, "it covers most civilizations", len(fmap))

    # --- unit sets per civ -------------------------------------------------
    fu_units = {}
    for stem, k in fmap.items():
        s = set()
        for b in fu[k]["Buildings"]:
            for u in b.get("Units", []):
                s.add(u["ID"])
        fu_units[stem] = s
    check(all(fu_units.values()), "every covered civ lists some units")

    # --- THE correlation ---------------------------------------------------
    # Restricted to covered civs only: the 6 Chronicles civs have no entry in
    # this file at all, and counting them would manufacture 353 fake
    # disagreements that say nothing about either mechanism.
    tab = collections.Counter()
    ex = collections.defaultdict(list)
    for stem in fmap:
        s = fu_units[stem]
        for row in CT.unit_rows(trees[stem]):
            nid = row.get("Node ID")
            key = (row.get("Node Status") != "NotAvailable", nid in s)
            tab[key] += 1
            if len(ex[key]) < 5:
                ex[key].append((stem, nid, row.get("Name")))

    agree = tab[(True, True)] + tab[(False, False)]
    dis = tab[(True, False)] + tab[(False, True)]
    total = agree + dis
    print()
    print("  (tree can_build, listed in futuravailableunits) over covered civs:")
    for k in sorted(tab, key=lambda x: -tab[x]):
        print("      can_build=%-5s listed=%-5s %5d   e.g. %s"
              % (k[0], k[1], tab[k], ex[k][:3]))
    print("  agree %d / disagree %d = %.2f%%"
          % (agree, dis, 100.0 * agree / total))
    check(agree > 20 * max(dis, 1),
          "the two files agree far too closely to be coincidence",
          "%.2f%%" % (100.0 * agree / total))

    # --- the specific units from the in-game test --------------------------
    print()
    print("replaying the in-game test's own two units:")
    for civ, unit, bldg, label in (("BRITONS", 5, 87, "Hand Cannoneer@Archery Range"),
                                   ("BRITONS", 2550, 12, "Champi Scout@Barracks")):
        tree_can = CT.can_build(trees[civ], unit)
        in_file = unit in fu_units.get(civ, set())
        print("    %-32s tree_can_build=%-5s shipped_file_lists_it=%s"
              % (label, tree_can, in_file))
    # The shipped file agrees with the GAME (you could not build either), not
    # with our edited tree -- which is the whole point.
    check((5 in fu_units.get("BRITONS", set())) is False,
          "the SHIPPED file says Britons cannot build the Hand Cannoneer "
          "(which is what the user saw)")

    print()
    print("WHAT THIS PROVES: the tree file still models per-civ availability at "
          "99.45%, but a mod-side rewrite of it was ignored in game while a "
          "`.dat` edit in the same mod took effect.")
    print("WHAT IT DOES NOT: that futuravailableunits.json is the file the "
          "build panel reads.  Only an in-game edit of THAT file can say.")
    if fails:
        print()
        print("BUILD-PANEL GATE PROBE: FAILED -> %s" % (fails,))
        return 1
    print()
    print("BUILD-PANEL GATE PROBE: the tree models buildability; the shipped "
          "sibling file matches it and the tree rewrite did not take effect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
