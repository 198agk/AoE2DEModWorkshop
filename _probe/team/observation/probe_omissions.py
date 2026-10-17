"""Identify (a) the 22 barracks-trainable units never in any civ's cache@12,
(b) what tree rows 215 / 602 / 875 are."""

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
from aoe2mod.dat import parser as P, locate

data, how = P.load_dat(os.path.join(ROOT, "resources", "_common", "dat", "empires2_x2_p1.dat"))
p = P.Parser(data)
p.parse()
civs = locate.locate(data, parser=p)[0]

barracks_units = set()
for c in civs:
    for u in c.get("units", []):
        for tl in u.get("train_locations", []):
            if tl["unit_id"] == 12:
                barracks_units.add(u["id"])
                break

cache = json.load(open(os.path.join(ROOT, "resources", "_common", "dat",
                                    "futuravailableunits.json"), encoding="utf-8-sig"))
cache_at12 = set()
for civ, v in cache.items():
    for b in v.get("Buildings", []):
        if b["ID"] == 12:
            for e in b.get("Units", []):
                cache_at12.add(e["ID"])

# name + node type per unit id, from the .dat and every tree
dat_name = {}
for c in civs:
    for u in c.get("units", []):
        dat_name.setdefault(u["id"], u.get("name"))
node_types = {}
for f in os.listdir(TREES):
    if not f.endswith(".json"):
        continue
    t = json.load(open(os.path.join(TREES, f), encoding="utf-8-sig"))
    for r in t.get("civ_techs_units", []):
        node_types.setdefault(r["Node ID"], set()).add(r.get("Node Type"))

print("=== (a) barracks-trainable in .dat but NEVER in any civ's cache@12 ===")
only_dat = sorted(barracks_units - cache_at12)
for uid in only_dat:
    nt = sorted(node_types.get(uid, [])) or ["<no tree row>"]
    print("   %-6s %-16s nodeType(s)=%-30s in_dat_records=%s"
          % (uid, dat_name.get(uid), ",".join(nt),
             sum(1 for c in civs for u in c.get("units", []) if u["id"] == uid)))

print("\n=== (b) what are tree rows 215 / 602 / 875 at building 12? ===")
for f in ("BRITONS.json", "GOTHS.json", "INCAS.json"):
    t = json.load(open(os.path.join(TREES, f), encoding="utf-8-sig"))
    print("   --- %s ---" % f)
    for r in t.get("civ_techs_units", []):
        if r.get("Building ID") == 12 and r.get("Node ID") in (215, 602, 875):
            print("      %s" % json.dumps(r, ensure_ascii=False, sort_keys=True))
    for r in t.get("civ_techs_buildings", []):
        if r.get("Node ID") in (215, 602, 875):
            print("      [building row] %s" % json.dumps(r, ensure_ascii=False, sort_keys=True))

print("\n=== (c) the 2 RegionalUnit + 4 UniqueUnit among those 22 ===")
for uid in only_dat:
    nt = node_types.get(uid, set())
    if nt & {"RegionalUnit", "UniqueUnit"}:
        print("   %-6s %-16s %s  cache@12-anywhere=False" % (uid, dat_name.get(uid), sorted(nt)))

print("\n=== (d) sanity: does the cache contain unit 215 / 602 / 875 anywhere? ===")
for uid in (215, 602, 875):
    spots = [(civ, b["ID"]) for civ, v in cache.items() for b in v.get("Buildings", [])
             for e in b.get("Units", []) if e["ID"] == uid]
    print("   unit %-5s appears %d times in cache: %s" % (uid, len(spots), spots[:6]))
print("\nDONE")
