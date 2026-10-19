# -*- coding: utf-8 -*-
r"""Which ENABLED mods could explain an in-game reading about civ availability?

Before any in-game experiment we have to know that nothing else on this machine
is already providing the same three engine paths (`.dat`, `CivTechTrees/*.json`,
`futuravailableunits.json`).  A confounder here turns a clean observation into
"ambiguous", which is exactly what happened to smoke5 (see
`_probe/team/auditor/REPORT.md`): a sibling mod shipped all three paths and the
control could not be attributed.

Earlier sessions said "the 4 enabled mods touch none of these" -- but the user's
mod list CHANGES (a mod gets published, another gets disabled), so that sentence
has to be re-measured, not quoted.  This probe measures it.  It only READS.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import locations as G            # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

# The three engine paths the availability question depends on.  A mod that ships
# any of them can move the answer.
WATCHED = (
    ("civtechtrees", "CivTechTrees/"),
    ("dat", "empires2_x2_p1.dat"),
    ("panel", "futuravailableunits.json"),
)


def classify(rel):
    """Which watched path does this mod-relative file name provide, if any?"""
    n = rel.replace("\\", "/").lower()
    for tag, needle in WATCHED:
        if needle.lower() in n:
            return tag
    return None


def main():
    prof = G.find_profile_root()
    print("profile : %s" % prof)
    mods = G.list_mods(prof)
    on = [m for m in mods if m["enabled"]]
    print("mods    : %d installed, %d enabled\n" % (len(mods), len(on)))

    conflicts = []
    for m in mods:
        found = []
        if m["exists"] and os.path.isdir(m["path"]):
            for root, _dirs, files in os.walk(m["path"]):
                for f in files:
                    tag = classify(os.path.relpath(os.path.join(root, f),
                                                   m["path"]))
                    if tag:
                        found.append((tag, os.path.relpath(
                            os.path.join(root, f), m["path"]).replace("\\", "/")))
        tags = sorted({t for t, _ in found})
        mark = "ON " if m["enabled"] else "off"
        if m["exists"]:
            state = ("SHIPS " + ",".join(tags)) if tags else "-"
        else:
            state = "(folder missing)"
        print("%s p%-3s %-52s %s" % (mark, m["priority"], str(m["title"])[:52],
                                     state))
        if tags and m["enabled"]:
            conflicts.append((m["title"], found))

    print()
    if conflicts:
        for title, found in conflicts:
            print("CONFLICT   %r ships:" % title)
            for tag, p in found:
                print("             [%s] %s" % (tag, p))
        print("\nCONFLICTING MODS: %d enabled mod(s) provide one of the three "
              "paths.\nDisable them before the next in-game reading, or that "
              "reading is unattributable." % len(conflicts))
        return 1
    print("CONFLICTING MODS: none. Every enabled mod is clear of all three "
          "paths\n(.dat / CivTechTrees / futuravailableunits), so an in-game "
          "reading about\nciv availability is attributable to the test mod or "
          "to shipped data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
