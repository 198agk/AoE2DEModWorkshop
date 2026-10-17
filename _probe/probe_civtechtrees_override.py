# -*- coding: utf-8 -*-
"""Can a MOD override `CivTechTrees/<CIV>.json`, or only the game/mode can?

`aoe2mod/game/civtechtrees.py` can READ per-civ availability, but a data mod that
only reads is useless -- the product's promise is "make the Goths able to build X",
which means WRITING this layer.  So the write path has to be established, and the
honest way is to separate two questions:

  1. Is the file resolved RELATIVE TO A ROOT that a mod can substitute?
  2. Is there direct evidence of a mod doing it?

(2) is currently NO: a scan of the subscribed mods finds 0 overrides of this
directory.  That is a fact about the mods installed on this machine, not a fact
about the engine, so it cannot settle the design on its own.

(1) is decidable statically, and the strongest available evidence is the game's
own `modes/Pompeii/` tree, which ships its own `CivTechTrees/`.  If the mode tree's
files DIFFER from the main tree's, then the layer is resolved per-root rather than
being a single global file -- which is exactly the property a mod override needs.
If they are identical copies, the mode just mirrors the data and proves nothing
about substitution.
"""
import json
import os
import sys
from collections import defaultdict

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MAIN = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")
MODE = os.path.join(GAME, "modes", "Pompeii", "resources", "_common", "dat",
                    "CivTechTrees")


def load(d):
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if fn.lower().endswith(".json"):
            with open(os.path.join(d, fn), encoding="utf-8") as fh:
                out[fn] = json.load(fh)
    return out


def summarize(j):
    """A comparison key that ignores key order but keeps real content."""
    units = j.get("civ_techs_units") or []
    blds = j.get("civ_techs_buildings") or []

    def rows(rs):
        return sorted(repr(sorted(r.items())) for r in rs if isinstance(r, dict))

    return (j.get("civ_id"), len(units), len(blds), tuple(rows(units)),
            tuple(rows(blds)))


def main():
    main = load(MAIN)
    mode = load(MODE)
    print("main tree files: %d" % len(main))
    print("mode tree files: %d" % len(mode))
    if not mode:
        print("FATAL: the mode ships no CivTechTrees; this probe cannot conclude.")
        return 2

    both = sorted(set(main) & set(mode))
    only_mode = sorted(set(mode) - set(main))
    print("files in both: %d ; only in the mode: %s" % (len(both), only_mode))
    print()

    differing = []
    same = []
    for fn in both:
        if summarize(main[fn]) == summarize(mode[fn]):
            same.append(fn)
        else:
            differing.append(fn)
    print("mode file IDENTICAL to main : %d" % len(same))
    print("mode file DIFFERS from main : %d  %s" % (len(differing), differing[:10]))
    print()

    # Show what actually differs, so a 'differs' result is not just a key-order
    # artefact of my own comparison.
    for fn in differing[:3]:
        a, b = main[fn], mode[fn]
        ua, ub = a.get("civ_techs_units") or [], b.get("civ_techs_units") or []
        print("  %s: main units=%d mode units=%d  main civ_id=%s mode civ_id=%s"
              % (fn, len(ua), len(ub), a.get("civ_id"), b.get("civ_id")))
        ids_a = {r.get("Node ID"): r.get("Node Status") for r in ua
                 if isinstance(r, dict) and r.get("Use Type") == "Unit"}
        ids_b = {r.get("Node ID"): r.get("Node Status") for r in ub
                 if isinstance(r, dict) and r.get("Use Type") == "Unit"}
        added = sorted(set(ids_b) - set(ids_a))
        removed = sorted(set(ids_a) - set(ids_b))
        changed = sorted(k for k in set(ids_a) & set(ids_b) if ids_a[k] != ids_b[k])
        print("      unit nodes added by the mode: %s" % added[:8])
        print("      unit nodes removed         : %s" % removed[:8])
        print("      unit nodes status-changed  : %s" % changed[:8])
    print()

    # The conclusion, stated as a decision the product can act on.
    if differing or only_mode:
        print("VERDICT: the CivTechTrees layer is resolved PER ROOT -- the game's")
        print("own mode substitutes its own files for the base ones.  A mod that")
        print("ships resources/_common/dat/CivTechTrees/<CIV>.json at the same")
        print("relative path is therefore exercising the SAME substitution path")
        print("the mode uses.  Direct mod observation: still none on this machine.")
    else:
        print("VERDICT: the mode mirrors the base data byte-for-byte, so this")
        print("comparison proves nothing about substitution.  Do NOT claim mod")
        print("overrides work for this layer without an in-game test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
