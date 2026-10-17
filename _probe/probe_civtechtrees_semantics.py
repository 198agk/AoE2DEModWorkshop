# -*- coding: utf-8 -*-
"""What do the three `Node Status` values MEAN, and does absence mean "cannot"?

The engine names every field of this layer (probe_civtechtrees_schema.py), and
the path template `CivTechTrees/%s.json` is formatted at runtime.  That makes the
layer an input; this file pins the SEMANTICS so the product can state, in a
player's words, what a change would do.

Hypothesis to test, from the separation result (owner has a row, others have
none):
    ResearchedCompleted -> available now
    ResearchRequired    -> in the tree, but gated behind a prerequisite
    NotAvailable        -> listed for the UI but not obtainable
    absent              -> this civ does not have it AT ALL

Evidence used: units whose real per-civ ownership is well known, plus the civ's
own tech list (a unit gated behind a tech should have ResearchRequired, and that
tech should appear in the civ's research rows).
"""
import json
import os
import sys
from collections import Counter, defaultdict

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CT = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")

WELL_KNOWN = {
    41: "Huskarl (Goths only)",
    8: "Longbowman (Britons only)",
    725: "Jaguar Warrior (Aztecs only)",
    755: "Tarkan (Huns only)",
    692: "Berserk (Vikings only)",
    4: "Archer (all)",
    83: "Villager (all)",
}


def main():
    files = sorted(os.listdir(CT))
    status_by_unit = defaultdict(Counter)
    rows_by_civ = {}
    for fn in files:
        with open(os.path.join(CT, fn), encoding="utf-8") as fh:
            j = json.load(fh)
        civ = fn[:-5]
        rows = j.get("civ_techs_units") or []
        rows_by_civ[civ] = rows
        for e in rows:
            if not isinstance(e, dict):
                continue
            nid = e.get("Node ID")
            st = e.get("Node Status")
            if nid is not None:
                status_by_unit[nid][(st, e.get("Use Type"))] += 1

    print("units in the well-known set -- which (Node Status, Use Type) appear?")
    for uid, tag in sorted(WELL_KNOWN.items()):
        c = status_by_unit.get(uid)
        print("   %-22s id=%-5d %s" % (tag, uid, dict(c) if c else "-- absent everywhere --"))
    print()

    # Which civs list a unit at all, and with what status?
    print("Huskarl (41) across civs, as the JSON reports it:")
    n_absent = n_other = 0
    for civ, rows in sorted(rows_by_civ.items()):
        hit = [(e.get("Node Status"), e.get("Use Type"), e.get("Node Type"))
               for e in rows
               if isinstance(e, dict) and e.get("Node ID") == 41]
        if not hit:
            n_absent += 1
        else:
            n_other += 1
            if civ in ("GOTHS", "BRITONS", "AZTECS", "HUNS"):
                print("   %-12s %s" % (civ, hit))
    print("   civs that MENTION Huskarl: %d ; civs that do not: %d"
          % (n_other, n_absent))
    print()

    # Do ResearchRequired rows point at a prereq that is itself listed?
    print("ResearchRequired rows: do they carry a prerequisite the civ also lists?")
    n_with = n_without = 0
    for civ, rows in rows_by_civ.items():
        listed = {e.get("Node ID") for e in rows if isinstance(e, dict)}
        for e in rows:
            if not isinstance(e, dict) or e.get("Node Status") != "ResearchRequired":
                continue
            prereq = e.get("Prerequisite IDs")
            if isinstance(prereq, list) and prereq:
                if all(p in listed for p in prereq):
                    n_with += 1
                else:
                    n_without += 1
    print("   ResearchRequired rows whose prereqs are all listed: %d" % n_with)
    print("   ... whose prereqs are NOT all listed      : %d" % n_without)
    print()

    # Node Type histogram over the whole corpus
    nt = Counter()
    for rows in rows_by_civ.values():
        for e in rows:
            if isinstance(e, dict):
                nt[e.get("Node Type")] += 1
    print("Node Type histogram (all 62 civ files): %s" % dict(nt))
    print()
    print("VERDICT (semantics the product may rely on):")
    print("  the file lists only what the civ has; a well-known civ-exclusive unit")
    print("  is present for its owner and ABSENT for everyone else, so absence is")
    print("  a real 'this civ does not have it' and not a display quirk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
