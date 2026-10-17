"""THE DECISIVE NUMBER for the A-half prediction.

For every civ x building, take the tree's UNIT-space rows (Use Type == "Unit")
that are licensed (ResearchedCompleted | ResearchRequired), split them into
"unconditional" (no Prerequisite IDs) and "prerequisite-gated", and ask whether
the matching cache (futuravailable / paphos, whichever names the civ) lists
them.  The mod's added Britons row for 2550 is UNCONDITIONAL (no Prerequisite
IDs field, status ResearchedCompleted).  So the predictive question is:

  Is an UNCONDITIONAL unit-space tree row ever absent from the cache?

If yes (any count), the tree alone might add the button.
If zero, the cache is a faithful projection of unconditional tree rows, and
adding a row to the tree that the cache does not carry should change nothing.
"""
import json
import os

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(ROOT, "resources", "_common", "dat")
TREES = os.path.join(DAT, "CivTechTrees")
OVERRIDE = {"BRITONS": "Britons", "FRANKS": "Franks", "BYZANTINES": "Byzantines",
            "MAYANS": "Mayans", "INDIANS": "Hindustanis", "MAGYAR": "Magyars"}

caches = {}
for name in ("futuravailableunits.json", "paphosfutureavailableunits.json"):
    caches[name] = json.load(open(os.path.join(DAT, name), encoding="utf-8-sig"))


def cache_key(stem):
    if stem in OVERRIDE:
        return OVERRIDE[stem]
    for name, obj in caches.items():
        for k in obj:
            if k.replace(" ", "").upper() == stem:
                return k
    return None


def which_cache(key):
    for name, obj in caches.items():
        if key in obj:
            return name, obj[key]
    return None, None


tot_uncond = tot_cond = 0
absent_uncond = []   # (civ, bldg, uid, name, status)
absent_cond = []
for f in sorted(os.listdir(TREES)):
    if not f.endswith(".json"):
        continue
    stem = f[:-5]
    key = cache_key(stem)
    name, blk = which_cache(key) if key else (None, None)
    if blk is None:
        continue
    cache_items = {}   # bldg -> {uid}
    for b in blk.get("Buildings", []):
        cache_items[b["ID"]] = {e["ID"] for e in b.get("Units", [])}
    t = json.load(open(os.path.join(TREES, f), encoding="utf-8-sig"))
    for r in t.get("civ_techs_units", []):
        if r.get("Use Type") != "Unit":
            continue
        if r.get("Node Status") not in ("ResearchedCompleted", "ResearchRequired"):
            continue
        bid = r.get("Building ID")
        uid = r.get("Node ID")
        prereq = r.get("Prerequisite IDs")
        has_pre = bool(prereq) and any(p not in (0, None) for p in prereq)
        present = uid in cache_items.get(bid, set())
        if has_pre:
            tot_cond += 1
            if not present:
                absent_cond.append((key, bid, uid, r.get("Name"), r.get("Node Status"), prereq))
        else:
            tot_uncond += 1
            if not present:
                absent_uncond.append((key, bid, uid, r.get("Name"), r.get("Node Status")))

print("=== UNIT-space licensed tree rows across all 62 trees ===")
print("    unconditional (no Prerequisite IDs): %d" % tot_uncond)
print("    prerequisite-gated                  : %d" % tot_cond)
print("\n    *** UNCONDITIONAL rows ABSENT from the matching cache: %d ***" % len(absent_uncond))
for r in absent_uncond:
    print("        civ=%-12s bldg=%-5s uid=%-6s %-22s %s" % r)

print("\n    prerequisite-gated rows absent from the cache: %d of %d"
      % (len(absent_cond), tot_cond))
from collections import Counter
c = Counter((r[0]) for r in absent_cond)
print("      by civ: %s" % dict(c))
print("      sample: %s" % (absent_cond[:12],))

print("\n=== the mod's exact shape: 2550 in the BRITONS tree, unconditional ===")
t = json.load(open(os.path.join(TREES, "BRITONS.json"), encoding="utf-8-sig"))
for r in t.get("civ_techs_units", []):
    if r.get("Node ID") == 2550:
        print("    shipped BRITONS.json 2550: %s" % json.dumps(r, ensure_ascii=False, sort_keys=True))
mod = os.path.join(r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local",
                   "aoe2mod Smoke5 TreeVsPanel", "resources", "_common", "dat",
                   "CivTechTrees", "BRITONS.json")
t2 = json.load(open(mod, encoding="utf-8-sig"))
for r in t2.get("civ_techs_units", []):
    if r.get("Node ID") == 2550:
        print("    mod     BRITONS.json 2550: %s" % json.dumps(r, ensure_ascii=False, sort_keys=True))
print("\n    Britons cache@12 has 2550: %s" % (2550 in {e["ID"] for b in
      caches["futuravailableunits.json"]["Britons"]["Buildings"] if b["ID"] == 12
      for e in b.get("Units", [])}))
print("    Incas tree 2550 row == mod row? ",
      json.dumps([r for r in json.load(open(os.path.join(TREES, "INCAS.json"),
                 encoding="utf-8-sig"))["civ_techs_units"] if r.get("Node ID") == 2550][0],
                 ensure_ascii=False, sort_keys=True))
print("\nDONE")
