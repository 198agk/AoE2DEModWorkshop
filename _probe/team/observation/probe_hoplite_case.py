"""THE DECISIVE CASE: Hoplite (2110/2111) is RegionalUnit at Barracks 12 in the
tree but NEVER appears in any civ's cache@12 -- the same unit CLASS as Champi
Scout.  Compare tree@12 vs cache@12 for its civs, and dump the cache's whole
view of those units anywhere.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json
import os
import sys

sys.path.insert(0, _HERE_PATH("..", "..", ".."))
ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
TREES = os.path.join(ROOT, "resources", "_common", "dat", "CivTechTrees")
cache = json.load(open(os.path.join(ROOT, "resources", "_common", "dat",
                                    "futuravailableunits.json"), encoding="utf-8-sig"))

TARGETS = {751: "Eagle Scout", 752: "Eagle Warrior", 753: "Elite Eagle Warrior",
           1901: "Fire Lancer", 1903: "Elite Fire Lancer",
           2110: "Hoplite", 2111: "Elite Hoplite",
           2550: "Champi Scout", 2552: "Champi Warrior", 2554: "Elite Champi Warrior",
           2588: "Champi Runner",
           2703: "Varangian Guard", 2704: "Elite Varangian Guard"}

print("=== A. where in the cache does each of the 13 RegionalUnit barracks units appear? ===")
for uid, nm in TARGETS.items():
    spots = {}
    for civ, v in cache.items():
        for b in v.get("Buildings", []):
            for e in b.get("Units", []):
                if e["ID"] == uid:
                    spots.setdefault(b["ID"], []).append(civ)
    if not spots:
        print("   %-6s %-22s *** NOWHERE in the entire cache ***" % (uid, nm))
    else:
        for bid, civs in sorted(spots.items()):
            tag = "   <== BUILDING 12 (Barracks)" if bid == 12 else ""
            print("   %-6s %-22s bldg=%-5s civs=%s%s" % (uid, nm, bid, civs, tag))

print("\n=== B. for the Hoplite civs (Athenians, Spartans, Thracians): tree@12 vs cache@12 ===")
for stem in ("ATHENIANS", "SPARTANS", "THRACIANS"):
    fp = os.path.join(TREES, stem + ".json")
    if not os.path.exists(fp):
        print("   %s: no tree file" % stem)
        continue
    t = json.load(open(fp, encoding="utf-8-sig"))
    tset = sorted({r["Node ID"] for r in t.get("civ_techs_units", [])
                   if r.get("Building ID") == 12
                   and r.get("Node Status") in ("ResearchedCompleted", "ResearchRequired")})
    # find the cache key
    key = None
    for k in cache:
        if k.replace(" ", "").upper() == stem or k.upper() == stem:
            key = k
            break
    print("   --- %s (cache key=%s) ---" % (stem, key))
    print("      tree@12  = %s" % [(i, TARGETS.get(i, "")) for i in tset])
    if key:
        cset = sorted({e["ID"] for b in cache[key].get("Buildings", []) if b["ID"] == 12
                       for e in b.get("Units", [])})
        print("      cache@12 = %s" % [(i, TARGETS.get(i, "")) for i in cset])
        print("      tree_only = %s" % [(i, TARGETS.get(i, "")) for i in sorted(set(tset) - set(cset))])
        print("      cache_only= %s" % [(i, TARGETS.get(i, "")) for i in sorted(set(cset) - set(tset))])
    else:
        print("      *** no cache key for this civ ***")
        print("      (cache has such keys: %s)" % [k for k in cache if stem[:5] in k.upper()])

print("\n=== C. does the cache have Athenians / Spartans / Thracians at all? ===")
for k in sorted(cache.keys()):
    if any(s in k.upper() for s in ("ATHEN", "SPART", "THRAC", "HOPLITE")):
        print("   cache key: %r" % k)
print("   total cache keys: %d" % len(cache))

print("\n=== D. Champi Scout's four civs, in full, for contrast ===")
for key in ("Incas", "Mapuche", "Muisca", "Tupi"):
    cset = sorted({e["ID"] for b in cache[key].get("Buildings", []) if b["ID"] == 12
                   for e in b.get("Units", [])})
    print("   %-9s cache@12 = %s" % (key, [(i, TARGETS.get(i, "")) for i in cset]))
print("\nDONE")
