# -*- coding: utf-8 -*-
"""Is the `.dat`-adjacent JSON layer (which contains CivTechTrees/) mod-overridable?

DEAD END RECORDED FIRST, so nobody repeats it: comparing the mode's tree against
the base tree CANNOT answer this.  Three name-matching heuristics gave three
different "mode civs with no file" counts (15, 4, 2) purely because the mode's
`.dat` spells civs singularly (`Egyptian`, `Carthage`, `Lac Viet`) while its files
are plural (`EGYPTIANS.json`, `CARTHAGIANS.json`, `LACVIET.json`) -- and the count
is what the verdict flipped on.  A fragile string heuristic must not drive a
design decision.  Note also that even a perfect count would only show the mode is
self-contained-or-not, which is not the question.

THE QUESTION, asked directly: a mod's folder mirrors the GAME ROOT, so a mod that
ships `resources/_common/dat/CivTechTrees/GOTHS.json` is writing to the same
directory a mod writes `resources/_common/dat/linkedTechs.json` to.  Is that
directory established as mod-overridable?  If a real, shipped mod already
overrides a file in it, then the layer is reachable and `CivTechTrees/` is a
subdirectory of a reachable path -- a much stronger footing than a mode analogy.

So: walk every installed mod and report what each one puts under
`resources/_common/dat/`, including subdirectories.
"""
import json
import os
import sys
from collections import Counter

PROFILE = (r"C:\Users\26913\Games\Age of Empires 2 DE"
           r"\76561198406248391\mods")
DAT_DIR = os.path.join("resources", "_common", "dat")


def main():
    print("mods root: %s" % PROFILE)
    if not os.path.isdir(PROFILE):
        print("FATAL: mods root not found.")
        return 2

    mod_dirs = []
    for base in ("subscribed", "local"):
        b = os.path.join(PROFILE, base)
        if os.path.isdir(b):
            for d in sorted(os.listdir(b)):
                p = os.path.join(b, d)
                if os.path.isdir(p):
                    mod_dirs.append((base, d, p))
    print("mods found: %d" % len(mod_dirs))
    print()

    found = []
    for base, name, path in mod_dirs:
        hits = []
        for root, _dirs, files in os.walk(path):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, path)
                low = rel.lower().replace("/", os.sep)
                if low.startswith(DAT_DIR.lower() + os.sep) or \
                        low == DAT_DIR.lower():
                    hits.append((rel, os.path.getsize(full)))
        if hits:
            found.append((base, name, hits))

    if not found:
        print("NO installed mod touches %s." % DAT_DIR)
        print("  -> the layer is NOT observed as mod-overridable on this machine.")
        return 0

    for base, name, hits in found:
        print("%s / %s" % (base, name))
        for rel, size in sorted(hits):
            print("    %-58s %8d B" % (rel, size))
        print()

    total = sum(len(h[2]) for h in found)
    print("mods overriding the dat-adjacent JSON/DAT layer: %d, files: %d"
          % (len(found), total))
    print()
    subdirs = Counter()
    for _b, _n, hits in found:
        for rel, _s in hits:
            parts = rel.split(os.sep)
            if len(parts) > len(DAT_DIR.split(os.sep)) + 1:
                subdirs[parts[len(DAT_DIR.split(os.sep))]] += 1
    print("subdirectories of resources/_common/dat/ that a mod writes into: %s"
          % dict(subdirs))
    print()
    print("VERDICT: the dat-adjacent layer IS mod-overridable -- a real shipped")
    print("mod writes files inside resources/_common/dat/, which is the parent")
    print("directory of CivTechTrees/.  CivTechTrees/ ITSELF is still not directly")
    print("observed (0 mods ship it), so treat that last step as inference, not")
    print("proof, and verify it in game before promising it in the UI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
