# -*- coding: utf-8 -*-
"""STUBBORN CASES.

Two directions came out of the corrected cross-table and they cannot both be
explained by one simple model:
  A) Bulgarians bldg 101 Paladin  : cache LISTS it, tree says NotAvailable.
                                    External fact: Bulgarians have NO Paladin.
  B) Goths bldg 12 Huskarl 759/761: tree LICENSES it, cache OMITS it.
                                    External fact: Goths DO train Huskarls.
The Goths/USH.. write the raw JSON both ways so I stop inferring from summaries.
"""
import os, json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
TREEDIR = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")
CACHE = os.path.join(GAME, "resources", "_common", "dat", "futuravailableunits.json")

obj = json.loads(open(CACHE, encoding="utf-8-sig").read())
trees = {}
for f in os.listdir(TREEDIR):
    if f.endswith(".json"):
        trees[f[:-5]] = json.load(open(os.path.join(TREEDIR, f), encoding="utf-8-sig"))

def cache_all_for(ck, unit_ids):
    print("  CACHE entries for %s, units %s:" % (ck, unit_ids))
    found = False
    for blk in (obj.get(ck) or {}).get("Buildings", []):
        for u in blk.get("Units", []):
            if u.get("ID") in unit_ids:
                found = True
                print("     bldg=%-5s %s" % (blk.get("ID"), json.dumps(u, ensure_ascii=False)))
    if not found:
        print("     (none anywhere in this civ)")

def tree_all_for(stem, unit_ids):
    print("  TREE rows for %s, units %s:" % (stem, unit_ids))
    found = False
    for sec in ("civ_techs_units", "civ_techs_buildings"):
        for r in (trees.get(stem) or {}).get(sec) or []:
            if r.get("Node ID") in unit_ids:
                found = True
                print("     [%s] bldg=%-5s %s" % (sec, r.get("Building ID"), json.dumps(r, ensure_ascii=False)))
    if not found:
        print("     (none anywhere in this civ)")

print("=" * 100)
print("CASE A: Bulgarians Paladin 569 - the cache lists a unit the civ famously cannot build")
print("=" * 100)
cache_all_for("Bulgarians", [569, 209])
tree_all_for("BULGARIANS", [569])
print("  tree rows for the Paladin TECH 209:")
tree_all_for("BULGARIANS", [209])
print("  -> compare a civ that HAS Paladin (Franks):")
cache_all_for("Franks", [569])
tree_all_for("FRANKS", [569])

print()
print("=" * 100)
print("CASE B: Goths Huskarl 759/761 - tree licenses at Barracks 12, cache allegedly omits")
print("=" * 100)
cache_all_for("Goths", [759, 761])
tree_all_for("GOTHS", [759, 761])
print("  Goths Barracks(12) cache block, verbatim unit ids:")
for blk in (obj.get("Goths") or {}).get("Buildings", []):
    if blk.get("ID") == 12:
        print("    ", [u.get("ID") for u in blk.get("Units", [])])
print("  Goths Castle(82) cache block, verbatim unit ids:")
for blk in (obj.get("Goths") or {}).get("Buildings", []):
    if blk.get("ID") == 82:
        print("    ", [u.get("ID") for u in blk.get("Units", [])])

print()
print("=" * 100)
print("CASE B2: Huns Tarkan 886/887 - tree licenses at Stable 101, cache allegedly omits")
print("=" * 100)
cache_all_for("Huns", [886, 887])
tree_all_for("HUNS", [886, 887])

print()
print("=" * 100)
print("CASE C: the four Champi civs + Britons, ONE last verbatim confirmation for the report")
print("=" * 100)
for ck, stem in (("Britons", "BRITONS"), ("Incas", "INCAS"), ("Mapuche", "MAPUCHE"),
                 ("Muisca", "MUISCA"), ("Tupi", "TUPI")):
    print("  --- %s ---" % ck)
    has = False
    for blk in (obj.get(ck) or {}).get("Buildings", []):
        if blk.get("ID") == 12:
            ids = [u.get("ID") for u in blk.get("Units", [])]
            print("     cache bldg12 ids:", ids)
            has = True
    if not has:
        print("     cache bldg12: NO BLOCK")
    rows = [r for r in (trees.get(stem) or {}).get("civ_techs_units", []) if r.get("Node ID") == 2550]
    print("     tree 2550 row:", json.dumps(rows[0], ensure_ascii=False) if rows else "(NONE)")
print()
print("DONE")
