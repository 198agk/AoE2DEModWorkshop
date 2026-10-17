"""THE SIX DISCRIMINATORS, verbatim.

Rows where the shipped TREE licenses a unit at building X but the matching
shipped CACHE does not list it at all (or lists it at a different building).
Each one is externally checkable against real AoE2 civ knowledge, so each one
tells us which file the GAME obeys.
"""
import json
import os

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(ROOT, "resources", "_common", "dat")
TREES = os.path.join(DAT, "CivTechTrees")

CACHES = {}
for fn in ("futuravailableunits.json", "paphosfutureavailableunits.json"):
    CACHES[fn] = json.load(open(os.path.join(DAT, fn), encoding="utf-8-sig"))

cache_key = {}
for fn, obj in CACHES.items():
    for k in obj:
        cache_key.setdefault(k.upper(), []).append((fn, k))

TREES_BY_STEM = {}
for f in sorted(os.listdir(TREES)):
    if f.endswith(".json"):
        TREES_BY_STEM[f[:-5]] = json.load(
            open(os.path.join(TREES, f), encoding="utf-8-sig"))

CASES = [
    ("GEORGIANS", 49, 588, "Siege Onager"),
    ("SICILIANS", 49, 588, "Siege Onager"),
    ("SPARTANS", 2172, 13, "Fishing Ship"),
    ("ARMENIANS", 1806, 125, "Monk"),
    ("ARMENIANS", 1806, 1811, "Warrior Priest"),
    ("GEORGIANS", 1806, 125, "Monk"),
]

for stem, bid, uid, nm in CASES:
    print("\n" + "=" * 72)
    print("%s  bldg %s  uid %s  (%s)" % (stem, bid, uid, nm))
    t = TREES_BY_STEM.get(stem)
    if t is None:
        print("   no tree file")
        continue
    rows = [r for r in t.get("civ_techs_units", []) if r.get("Node ID") == uid]
    for r in rows:
        print("   TREE row: %s" % json.dumps(r, ensure_ascii=False, sort_keys=True))
    # what the cache for this civ says about the unit, anywhere
    for fn, obj in CACHES.items():
        ck = cache_key.get(stem, [])
        for _f, k in ck:
            if _f != fn:
                continue
            hits = []
            for b in obj[k].get("Buildings", []):
                for e in b.get("Units", []):
                    if e.get("ID") == uid:
                        hits.append((b["ID"], b.get("Name"), e.get("RequiredAge"),
                                     e.get("PrereqTech")))
            print("   CACHE[%s] '%s': %s" % (fn[:9], k, hits if hits else "NOWHERE"))

print("\n\n=== also: is the unit even in that civ's Building list? ===")
for stem, bid, uid, nm in CASES:
    for fn, obj in CACHES.items():
        for _f, k in cache_key.get(stem, []):
            if _f != fn:
                continue
            ids = [b["ID"] for b in obj[k].get("Buildings", [])]
            print("   %-10s %-9s bldg %-5s present=%-5s  (civ has %d blocks)"
                  % (stem, fn[:9], bid, bid in ids, len(ids)))
print("\nDONE")
