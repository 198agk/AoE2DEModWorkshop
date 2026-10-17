"""RE-VERIFY the single most load-bearing claim in the report.

Claim under test: 'Goths cannot train Huskarls according to the cache, yet they
really can' -- i.e. the cache OMITS a real, tree-licensed barracks unit (759
Huskarl / 761 Elite Huskarl), which proves the cache is NOT the button list.

If this claim is wrong, the whole 'the tree licenses, the cache only feeds
greyed previews' reading collapses.  So check it from four directions.
"""
import json
import os

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
CACHE = os.path.join(ROOT, "resources", "_common", "dat", "futuravailableunits.json")
TREES = os.path.join(ROOT, "resources", "_common", "dat", "CivTechTrees")

obj = json.load(open(CACHE, encoding="utf-8-sig"))
print("cache civ keys: %d" % len(obj))

TARGETS = {759: "Huskarl", 761: "Elite Huskarl", 886: "Tarkan", 887: "Elite Tarkan",
           74: "Militia", 2550: "Champi Scout", 93: "Spearman"}

print("\n=== 1. EVERY civ+building where the cache lists 759 / 761 (Huskarl) ===")
found = []
for civ, v in obj.items():
    for b in v.get("Buildings", []):
        for e in b.get("Units", []):
            if e["ID"] in (759, 761):
                found.append((civ, b["ID"], b.get("Name"), e["ID"], TARGETS[e["ID"]], e.get("RequiredAge")))
if found:
    for r in found:
        print("   civ=%-12s bldg=%-5s %-16s unit=%-5s %-14s age=%s" % r)
else:
    print("   *** 759/761 appear NOWHERE in the whole shipped cache, for any civ ***")

print("\n=== 2. the Goths cache, building by building (all units) ===")
goths = obj.get("Goths")
print("   Goths in cache:", goths is not None, "| blocks:", len(goths.get("Buildings", [])) if goths else 0)
if goths:
    for b in goths["Buildings"]:
        ids = [(e["ID"], e.get("Name"), e.get("RequiredAge")) for e in b.get("Units", [])]
        marker = "  <== Barracks" if b["ID"] == 12 else ""
        print("   bldg %-5s %-18s n=%-3d %s%s" % (b["ID"], b.get("Name"), len(ids), ids, marker))

print("\n=== 3. the Goths TREE rows for 759 / 761 ===")
t = json.load(open(os.path.join(TREES, "GOTHS.json"), encoding="utf-8-sig"))
rows = t.get("civ_techs_units", [])
print("   GOTHS.json unit rows: %d" % len(rows))
for r in rows:
    if r.get("Node ID") in (759, 761):
        print("   TREE %s" % json.dumps(r, ensure_ascii=False, sort_keys=True))

print("\n=== 4. Goths barracks: cache vs tree(ResearchedCompleted|ResearchRequired) ===")
cache12 = sorted({e["ID"] for b in goths["Buildings"] if b["ID"] == 12 for e in b.get("Units", [])})
lic = sorted({r["Node ID"] for r in rows
              if r.get("Building ID") == 12
              and r.get("Node Status") in ("ResearchedCompleted", "ResearchRequired")})
print("   cache@12 = %s" % cache12)
print("   tree@12  = %s" % lic)
print("   tree_only (tree licenses, cache omits) = %s"
      % [(i, TARGETS.get(i, "")) for i in sorted(set(lic) - set(cache12))])
print("   cache_only (cache lists, tree denies)  = %s"
      % [(i, TARGETS.get(i, "")) for i in sorted(set(cache12) - set(lic))])

print("\n=== 5. does a real Goths player train Huskarls? (the .dat train host) ===")
import sys
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
from aoe2mod.dat import parser as P, locate
data, how = P.load_dat(os.path.join(ROOT, "resources", "_common", "dat", "empires2_x2_p1.dat"))
p = P.Parser(data)
p.parse()
civs, cs, gv, tail = locate.locate(data, parser=p)
print("   63-civ records walked:", len(civs))
for uid in (759, 761, 886, 887):
    hits = locate.find_units(civs, uid)
    hosts = {}
    for ci, cname, u in hits:
        hs = tuple(sorted({tl["unit_id"] for tl in u.get("train_locations", [])}))
        hosts.setdefault(hs, []).append(cname)
    print("   unit %-5s %-14s records=%-3d train hosts -> %s"
          % (uid, TARGETS[uid], len(hits), {k: len(v) for k, v in hosts.items()}))
print("\nDONE")
