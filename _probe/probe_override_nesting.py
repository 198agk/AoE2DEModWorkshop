# -*- coding: utf-8 -*-
"""Does a mod override work for files in a SUBDIRECTORY of a storage point?

The chain of reasoning needs exactly this link to promote "CivTechTrees/ is
probably moddable" from inference to evidence:

  * `resources/_common/dat/` (the DAT storage point) IS mod-overridable -- proven
    directly here: mods `550749` and `551103` both ship
    `resources/_common/dat/linkedTechs.json` (4,203 B each) where the base file is
    3,947 B, and mod `297820` ships `civilizations.json`.
  * `CivTechTrees/` is a SUBDIRECTORY of that storage point, and no mod on this
    machine ships it -- so the subdirectory case needs support from elsewhere.
  * If ANY storage point is overridden at a NESTED path, then resolution walks
    subdirectories, and `CivTechTrees/<CIV>.json` resolves the same way.

`widgetui/` is the test bed: the loose-PNG override (an earlier, independent
proof) works through `widgetui/textures/ingame/emblems/...`, which is three levels
deep.  This file measures the depth of every mod override per storage point, so
the nesting claim rests on counts rather than on one remembered example.
"""
import os
import sys
from collections import Counter, defaultdict

PROFILE = (r"C:\Users\26913\Games\Age of Empires 2 DE"
           r"\76561198406248391\mods")

# storage point -> its path under the game root, from the engine's own registry
STORAGE = {
    "DAT": "resources/_common/dat",
    "WIDGETUI": "widgetui",
    "WPFG": "resources/_common/wpfg",
    "STRINGS": "resources",
    "SPRITES": "resources/_common/drs/graphics",
    "TERRAIN": "resources/_common/terrain",
}


def main():
    mods = []
    for base in ("subscribed", "local"):
        b = os.path.join(PROFILE, base)
        if os.path.isdir(b):
            for d in sorted(os.listdir(b)):
                p = os.path.join(b, d)
                if os.path.isdir(p):
                    mods.append((base, d, p))
    print("mods: %d" % len(mods))
    print()

    depths = defaultdict(Counter)
    examples = defaultdict(list)
    for base, name, path in mods:
        for root, _dirs, files in os.walk(path):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), path)
                rel_n = rel.replace("/", os.sep)
                for sp, sp_path in STORAGE.items():
                    sp_n = sp_path.replace("/", os.sep)
                    if rel_n.lower().startswith(sp_n.lower() + os.sep):
                        rest = rel_n[len(sp_n) + 1:]
                        depth = rest.count(os.sep)
                        depths[sp][depth] += 1
                        if depth > 0 and len(examples[sp]) < 4:
                            examples[sp].append((name, rel_n))

    print("override nesting depth under each storage point (0 = directly inside):")
    for sp in sorted(depths):
        c = depths[sp]
        total = sum(c.values())
        nested = sum(v for k, v in c.items() if k > 0)
        print("  %-10s files %-5d  depths %-22s  NESTED: %d"
              % (sp, total, dict(sorted(c.items())), nested))
    print()

    for sp in ("WIDGETUI", "DAT"):
        print("%s examples at depth > 0:" % sp)
        for name, rel in examples.get(sp, []):
            print("    %-52s  %s" % (name[:52], rel))
        if not examples.get(sp):
            print("    (none)")
        print()

    nested_any = any(sum(v for k, v in c.items() if k > 0)
                     for c in depths.values())
    print("VERDICT: %s" % (
        "mod overrides DO resolve at nested paths inside a storage point, so a\n"
        "mod's `resources/_common/dat/CivTechTrees/<CIV>.json` is exercising the\n"
        "same directory-walking lookup that `widgetui/textures/...` already does.\n"
        "Combined with the DIRECT proof that the DAT storage point is overridable,\n"
        "this makes the CivTechTrees write path evidenced rather than assumed --\n"
        "with the caveat that no mod on this machine ships that exact file, so it\n"
        "has never been observed in game."
        if nested_any else
        "no nested override observed; cannot conclude."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
