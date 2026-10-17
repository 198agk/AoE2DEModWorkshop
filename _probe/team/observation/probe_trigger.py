"""The mod's added Britons row carries "Trigger Tech ID": 1350. Resolve that tech
and check how the shipped Incas row's mechanism is expressed in the tree, so the
report can say whether the added row is complete or missing a companion row."""
import json
import os
import sys

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.dat import locate as L          # noqa: E402

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(ROOT, "resources", "_common", "dat")
TREES = os.path.join(DAT, "CivTechTrees")
MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Smoke5 TreeVsPanel"

blob, how = P.load_dat(os.path.join(DAT, "empires2_x2_p1.dat"))
p = P.Parser(blob)
p.parse()
civs, civs_start, gv, tail = L.locate(blob, parser=p)
techs = L.locate_techs(blob, tail, gv)

print("=== tech 1350 and its neighbours 1349-1353 ===")
for i in range(1349, 1354):
    t = techs[i]
    print("    %-5d %-34r civ=%-4s effect=%s loc=%s btn=%s"
          % (i, t["name"], t["civ"], t["effect_id"],
             [r["location_id"] for r in t["research_locations"]],
             [r["button_id"] for r in t["research_locations"]]))

print("\n=== does any tree row anywhere carry these Trigger Tech IDs? ===")
for tid in (1350, 1351, 1352, 1402):
    hits = []
    for fn in sorted(os.listdir(TREES)):
        if not fn.endswith(".json"):
            continue
        d = json.load(open(os.path.join(TREES, fn), encoding="utf-8-sig"))
        for space in ("civ_techs_units", "civ_techs_buildings"):
            for r in d.get(space, []):
                if r.get("Trigger Tech ID") == tid:
                    hits.append((fn[:-5], space, r.get("Node ID"), r.get("Name"),
                                 r.get("Node Status")))
        for r in d.get("civ_techs_units", []):
            if r.get("Node ID") == tid and r.get("Use Type") == "Tech":
                hits.append((fn[:-5], "UNITSPACE-NODEID", r.get("Node ID"),
                             r.get("Name"), r.get("Node Status")))
    print("    TriggerTech/NodeID %-5d -> %d hit(s): %s" % (tid, len(hits), hits[:8]))

print("\n=== INCAS vs BRITONS vs MOD-BRITONS: rows for node 2550 and any node 1350 ===")
for label, path in (("INCAS-shipped", os.path.join(TREES, "INCAS.json")),
                    ("BRITONS-shipped", os.path.join(TREES, "BRITONS.json")),
                    ("BRITONS-mod", os.path.join(MOD, "resources", "_common", "dat",
                                                 "CivTechTrees", "BRITONS.json"))):
    d = json.load(open(path, encoding="utf-8-sig"))
    rows = [r for r in d["civ_techs_units"] if r.get("Node ID") == 2550]
    t1350 = [r for r in d["civ_techs_units"] if r.get("Node ID") == 1350]
    print("    %-16s n_units=%-4d row2550=%d row1350=%d"
          % (label, len(d["civ_techs_units"]), len(rows), len(t1350)))
    for r in rows:
        print("       2550: %s" % json.dumps(r, ensure_ascii=False, sort_keys=True))
    for r in t1350:
        print("       1350: %s" % json.dumps(r, ensure_ascii=False, sort_keys=True))

print("\n=== 2550 .dat physical record: type/class/hp for the British record ===")
for ci, cname, u in L.find_units(civs, 2550):
    if cname in ("British", "Incas"):
        print("    %-10s id=%s name=%r type=%s class=%s hp=%s train=%s"
              % (cname, u.get("id"), u.get("name"), u.get("type"), u.get("class"),
                 u.get("hit_points"),
                 [(tl.get("unit_id"), tl.get("button_id")) for tl in u.get("train_locations", [])]))
print("DONE")
