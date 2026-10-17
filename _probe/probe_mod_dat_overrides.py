"""Which DAT-adjacent file do real published mods actually override?

The in-game test of 2026-10-14 showed the `.dat` half of a mod taking effect
while its `resources/_common/dat/CivTechTrees/BRITONS.json` half did nothing.
Before inventing an explanation, look at what the mods people actually publish
and play ship: if nobody ships a per-civ tree file but several ship
`futuravailableunits.json`, the ecosystem has already answered the question.

Also reports `info.json` CacheStatus, because a mod-level flag is one more
candidate explanation for the ignored override.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A      # noqa: E402

INTERESTING = {
    "CivTechTrees": "resources/_common/dat/CivTechTrees",
    "futuravailableunits.json": "resources/_common/dat/futuravailableunits.json",
    "paphosfutureavailableunits.json":
        "resources/_common/dat/paphosfutureavailableunits.json",
    "civilizations.json": "resources/_common/dat/civilizations.json",
    "linkedTechs.json": "resources/_common/dat/linkedTechs.json",
    "linkedUnits.json": "resources/_common/dat/linkedUnits.json",
    "unitlines.json": "resources/_common/dat/unitlines.json",
    "objreplacement.json": "resources/_common/dat/objreplacement.json",
    "sharedbuildings.json": "resources/_common/dat/sharedbuildings.json",
    "eras.json": "resources/_common/dat/eras.json",
    "maps.json": "resources/_common/dat/maps.json",
    "tech tree JSON (any)": "resources/_common/dat",
}


def main():
    tk = A.open_toolkit()
    mods = tk.mods()
    print("installed/subscribed mods: %d" % len(mods))
    print()

    tally = {k: [] for k in INTERESTING}
    for m in mods:
        d = m["path"]
        if not os.path.isdir(d):
            continue
        cache = None
        ip = os.path.join(d, "info.json")
        if os.path.isfile(ip):
            try:
                cache = json.loads(open(ip, "rb").read().decode("utf-8", "replace"),
                                   strict=False).get("CacheStatus")
            except Exception as exc:
                cache = "unreadable(%s)" % exc
        found = sorted({e for e in os.listdir(d)})[:0]
        hits = []
        for name, rel in INTERESTING.items():
            p = os.path.join(d, rel.replace("/", os.sep))
            if os.path.isfile(p):
                hits.append("%s (%d B)" % (name, os.path.getsize(p)))
            elif os.path.isdir(p):
                n = len([f for f in os.listdir(p) if f.lower().endswith(".json")])
                if name == "CivTechTrees":
                    hits.append("CivTechTrees/ (%d files)" % n)
                else:
                    hits.append("tech tree JSON (%d files)" % n)
        print("%-58s CacheStatus=%s" % (m["name"][:58], cache))
        if hits:
            for h in hits:
                print("      -> %s" % h)
        else:
            print("      -> (no DAT-layer file)")
        if found:
            print("   dir sample: %s" % found)

    print()
    print("=" * 74)
    print("SUMMARY: how many installed mods override each DAT-layer file")
    for name, rel in INTERESTING.items():
        c = 0
        for m in mods:
            p = os.path.join(m["path"], rel.replace("/", os.sep))
            if os.path.isfile(p) or (name == "CivTechTrees" and os.path.isdir(p)):
                c += 1
        print("   %-34s %d" % (name, c))


if __name__ == "__main__":
    main()
