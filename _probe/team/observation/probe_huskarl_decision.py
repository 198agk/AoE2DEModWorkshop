"""Is the cache's omission of Goths 759/761 a REAL omission, or does unit
41/555 serve the Goths barracks button instead?

Check the .dat train hosts of 41/555 vs 759/761, and count how many of the
49 barracks-trainable units have a cache entry at building 12 in ANY civ.
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
from aoe2mod.dat import parser as P, locate

data, how = P.load_dat(os.path.join(ROOT, "resources", "_common", "dat", "empires2_x2_p1.dat"))
p = P.Parser(data)
p.parse()
civs, cs, gv, tail = locate.locate(data, parser=p)

print("=== train hosts of the Huskarl/Tarkan family ===")
for uid in (41, 555, 759, 761, 886, 887):
    hits = locate.find_units(civs, uid)
    if not hits:
        print("   unit %-5s -> NOT FOUND" % uid)
        continue
    u = hits[0][2]
    hosts = sorted({tl["unit_id"] for tl in u.get("train_locations", [])})
    print("   unit %-5s name=%-16s records=%-3d train hosts=%s"
          % (uid, u.get("name"), len(hits), hosts))

print("\n=== every distinct unit that names barracks 12 as a train host ===")
barracks_units = set()
for c in civs:
    for u in c.get("units", []):
        for tl in u.get("train_locations", []):
            if tl["unit_id"] == 12:
                barracks_units.add(u["id"])
                break
print("   distinct: %d" % len(barracks_units))

cache = json.load(open(os.path.join(ROOT, "resources", "_common", "dat",
                                    "futuravailableunits.json"), encoding="utf-8-sig"))
cache_at12 = set()
for civ, v in cache.items():
    for b in v.get("Buildings", []):
        if b["ID"] == 12:
            for e in b.get("Units", []):
                cache_at12.add(e["ID"])
print("   units with a cache entry at building 12 in ANY civ: %d" % len(cache_at12))

only_dat = sorted(barracks_units - cache_at12)
print("\n   >>> in the .dat as barracks-trainable but NEVER in any civ's cache@12: %d" % len(only_dat))

tree_types = {}
for f in os.listdir(os.path.join(ROOT, "resources", "_common", "dat", "CivTechTrees")):
    if not f.endswith(".json"):
        continue
    t = json.load(open(os.path.join(ROOT, "resources", "_common", "dat", "CivTechTrees", f),
                       encoding="utf-8-sig"))
    for r in t.get("civ_techs_units", []):
        tree_types.setdefault(r["Node ID"], set()).add(r.get("Node Type"))

print("\n   Node Type of each of those %d:" % len(only_dat))
hist = {}
for uid in only_dat:
    ts = tuple(sorted(tree_types.get(uid, {"<no tree row>"})))
    hist[ts] = hist.get(ts, 0) + 1
for k, v in sorted(hist.items(), key=lambda kv: -kv[1]):
    print("      %-40s %d" % (str(k), v))

print("\n   === the SAME question for units that DO have a cache@12 entry ===")
have = sorted(cache_at12 & barracks_units)
hist2 = {}
for uid in have:
    ts = tuple(sorted(tree_types.get(uid, {"<no tree row>"})))
    hist2[ts] = hist2.get(ts, 0) + 1
for k, v in sorted(hist2.items(), key=lambda kv: -kv[1]):
    print("      %-40s %d" % (str(k), v))

print("\n=== decisive: are there RegionalUnit / Unit units that are tree-licensed at 12")
print("    but absent from the cache at 12, for some civ? ===")
missing = []
for f in sorted(os.listdir(os.path.join(ROOT, "resources", "_common", "dat", "CivTechTrees"))):
    if not f.endswith(".json"):
        continue
    stem = f[:-5]
    t = json.load(open(os.path.join(ROOT, "resources", "_common", "dat", "CivTechTrees", f),
                       encoding="utf-8-sig"))
    for r in t.get("civ_techs_units", []):
        if r.get("Building ID") != 12:
            continue
        if r.get("Node Status") not in ("ResearchedCompleted", "ResearchRequired"):
            continue
        if r.get("Node Type") not in ("Unit", "RegionalUnit", "UniqueUnit", "UnitUpgrade"):
            continue
        missing.append((stem, r["Node ID"], r.get("Name"),
                        r.get("Node Type"), r.get("Node Status"), r.get("Age ID")))
print("   total tree-licensed unit rows at bldg 12 across all 62 trees: %d" % len(missing))

# per civ, does the cache agree?
print("\n   per-civ cache@12 vs tree-licensed@12 (only listing mismatches):")
CIVMAP = {"BRITONS": "Britons", "FRANKS": "Franks", "BYZANTINES": "Byzantines",
          "MAYANS": "Mayans", "INDIANS": "Hindustanis", "MAGYAR": "Magyars"}
nmis = 0
for f in sorted(os.listdir(os.path.join(ROOT, "resources", "_common", "dat", "CivTechTrees"))):
    if not f.endswith(".json"):
        continue
    stem = f[:-5]
    key = CIVMAP.get(stem, stem.capitalize())
    if key not in cache:
        # try a few capitalisations
        cand = [k for k in cache if k.upper() == stem]
        key = cand[0] if cand else None
    if key is None:
        continue
    t = json.load(open(os.path.join(ROOT, "resources", "_common", "dat", "CivTechTrees", f),
                       encoding="utf-8-sig"))
    tset = {r["Node ID"] for r in t.get("civ_techs_units", [])
            if r.get("Building ID") == 12
            and r.get("Node Status") in ("ResearchedCompleted", "ResearchRequired")}
    cset = {e["ID"] for b in cache[key].get("Buildings", []) if b["ID"] == 12
            for e in b.get("Units", [])}
    to = sorted(tset - cset)
    co = sorted(cset - tset)
    if to or co:
        nmis += 1
        print("      %-14s tree_only=%s cache_only=%s" % (key, to, co))
print("   civs with any mismatch: %d" % nmis)
print("\nDONE")
