"""THE DIRECTION TEST, final form.

If futuravailableunits.json were the LIVE button list, then a unit the cache
lists at building X would appear at X.  The Goths cache lists 41 GBRSK /
555 UGBRS ('Huskarl' / 'Elite Huskarl') at the CASTLE (82) and omits the tree's
Barracks rows 759 BHUSK / 761 BHUSKX.  So: does the shipped TREE contain rows
for 41 / 555 at all -- and if so, at which building and status?

* tree has 41/555 at Castle -> both files agree, no information
* tree has NO 41/555 rows anywhere -> the cache carries entries the tree's
  authority does not recognise, i.e. the cache is a stale superset and cannot
  be the live button list.
"""
import json
import os

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(ROOT, "resources", "_common", "dat")
TREES = os.path.join(DAT, "CivTechTrees")

WATCH = {41: "GBRSK/Huskarl", 555: "UGBRS/EliteHuskarl",
         759: "BHUSK/Barracks Huskarl", 761: "BHUSKX/Barracks Elite Huskarl",
         74: "Militia", 2550: "Champi Scout"}

rows = {}   # uid -> list of (stem, bldg, status, type, use)
n_tree = 0
for f in sorted(os.listdir(TREES)):
    if not f.endswith(".json"):
        continue
    t = json.load(open(os.path.join(TREES, f), encoding="utf-8-sig"))
    for key in ("civ_techs_units", "civ_techs_buildings"):
        for r in t.get(key, []):
            n_tree += 1
            uid = r.get("Node ID")
            if uid in WATCH:
                rows.setdefault(uid, []).append(
                    (f[:-5], r.get("Building ID"), r.get("Node Status"),
                     r.get("Node Type"), r.get("Use Type"), key))
print("tree rows scanned (units+buildings): %d" % n_tree)

for uid, nm in WATCH.items():
    got = rows.get(uid, [])
    print("\n--- %-6s %s : %d tree rows in the whole install ---" % (uid, nm, len(got)))
    if not got:
        print("    *** NO tree row references this unit ANYWHERE ***")
    else:
        buildings = sorted({g[1] for g in got})
        statuses = sorted({g[2] for g in got})
        stems = sorted({g[0] for g in got})
        print("    buildings=%s" % buildings)
        print("    statuses =%s" % statuses)
        print("    in %d civ trees" % len(stems))
        if len(stems) < 8:
            for g in got:
                print("       %s" % (g,))

print("\n=== the Goths' two files side by side, buildings 12 and 82 ===")
cache = json.load(open(os.path.join(DAT, "futuravailableunits.json"), encoding="utf-8-sig"))
for bid in (12, 82):
    cs = sorted({e["ID"] for b in cache["Goths"]["Buildings"] if b["ID"] == bid
                 for e in b.get("Units", [])})
    print("    cache Goths bldg %-3s = %s" % (bid, cs))
t = json.load(open(os.path.join(TREES, "GOTHS.json"), encoding="utf-8-sig"))
for bid in (12, 82):
    ts = sorted({r["Node ID"] for r in t["civ_techs_units"]
                 if r.get("Building ID") == bid
                 and r.get("Node Status") in ("ResearchedCompleted", "ResearchRequired")})
    print("    tree  Goths bldg %-3s = %s" % (bid, ts))
print("\nDONE")
