# -*- coding: utf-8 -*-
"""THE DECISIVE CROSS-TABLE.

For EVERY civ, at EVERY building, compare the two candidate sources:
  TREE  = tree rows with Node Status == "ResearchedCompleted"
  CACHE = futuravailableunits.json entries

Then ask the two questions that decide the reading matrix:
  cache_only  = cache lists it, tree does NOT call it ResearchedCompleted
                -> if non-empty, the cache is NOT a faithful projection of the
                   tree, and the tree alone cannot be the whole story.
  tree_only   = tree calls it ResearchedCompleted, cache does NOT list it
                -> if non-empty, the cache alone cannot be the whole story
                   either, i.e. BOTH files are consulted (or a third one is).

Read the tree files DIRECTLY with json.load - load_trees() has a signature I
got wrong twice and silently returned {} (an empty tree looks exactly like a
civ with no units).
"""
import os, sys, json, collections

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
TREEDIR = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")
CACHE = os.path.join(GAME, "resources", "_common", "dat", "futuravailableunits.json")

_kv = os.path.join(GAME, "resources", "zh", "strings", "key-value", "key-value-strings-utf8.txt")
STR = {}
for line in open(_kv, encoding="utf-8-sig"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    i = line.find(" ")
    if i < 0:
        continue
    k = line[:i]
    v = line[i + 1:].strip()
    if v.startswith('"') and v.endswith('"'):
        v = v[1:-1]
    STR[k] = v

CACHE_CIV = {  # cache key -> tree stem, the known non-obvious ones
    "British": "BRITONS", "Britons": "BRITONS", "French": "FRANKS", "Franks": "FRANKS",
    "Byzantine": "BYZANTINES", "Byzantines": "BYZANTINES", "Mayan": "MAYANS", "Mayans": "MAYANS",
    "Hindustanis": "INDIANS", "Indians": "INDIANS", "Magyars": "MAGYAR",
}

def stem_for(cache_key):
    if cache_key in CACHE_CIV:
        return CACHE_CIV[cache_key]
    cand = cache_key.upper().replace(" ", "_").replace("-", "_")
    p = os.path.join(TREEDIR, cand + ".json")
    if os.path.exists(p):
        return cand
    # fuzzy: strip trailing s / match by prefix
    for f in os.listdir(TREEDIR):
        s = f[:-5]
        if s.lower() == cache_key.lower():
            return s
        if s.lower().startswith(cache_key.lower()[:5]) and abs(len(s) - len(cache_key)) <= 6:
            return s
    return None

# ---------------------------------------------------------------- cache -----
obj = json.loads(open(CACHE, encoding="utf-8-sig").read())
# ---------------------------------------------------------------- trees -----
trees = {}
for f in os.listdir(TREEDIR):
    if f.endswith(".json"):
        trees[f[:-5]] = json.load(open(os.path.join(TREEDIR, f), encoding="utf-8-sig"))

print("cache civs: %d   tree files: %d" % (len(obj), len(trees)))

def tree_rows(stem):
    """(building_id, node_id) -> row  for Use Type == Unit."""
    o = trees.get(stem) or {}
    out = {}
    for r in (o.get("civ_techs_units") or []):
        if r.get("Use Type") == "Unit":
            out[(r.get("Building ID"), r.get("Node ID"))] = r
    return out

def cache_entries(ck):
    out = {}
    for blk in (obj.get(ck) or {}).get("Buildings", []):
        bid = blk.get("ID")
        for u in blk.get("Units", []):
            out[(bid, u.get("ID"))] = u
    return out

print()
print("=" * 104)
print("Q1: for each civ, is the cache EXACTLY the tree's ResearchedCompleted set?  (all buildings)")
print("=" * 104)
all_co = collections.Counter()
all_to = collections.Counter()
co_list = []
to_list = []
tot_pairs = 0
for ck in sorted(obj):
    stem = stem_for(ck)
    if not stem or stem not in trees:
        print("  %-14s -> NO TREE FILE (skipped)" % ck)
        continue
    tr = tree_rows(stem)
    ca = cache_entries(ck)
    trc = set(k for k, r in tr.items() if r.get("Node Status") == "ResearchedCompleted")
    kak = set(ca.keys())
    co = kak - trc
    to = trc - kak
    tot_pairs += 1
    for b, u in co:
        all_co[b] += 1
        co_list.append((ck, stem, b, u, (ca[(b, u)].get("Name")), tr.get((b, u), {}).get("Node Status")))
    for b, u in to:
        all_to[b] += 1
        to_list.append((ck, stem, b, u, (tr[(b, u)].get("Name")), tr[(b, u)].get("Age ID")))
print("  civs compared: %d" % tot_pairs)
print("  cache_only entries : %d   by building: %s" % (len(co_list), dict(all_co)))
print("  tree_only  entries : %d   by building: %s" % (len(to_list), dict(all_to)))

print()
print("=" * 104)
print("Q2: the 20 most decisive rows of each kind (excluding building 118 = the villager build menu)")
print("=" * 104)
print("  -- cache_only (cache shows a button the tree does not license) --")
n = 0
for row in co_list:
    if row[2] == 118:
        continue
    n += 1
    if n <= 20:
        print("     %-12s %-12s bldg=%-5s unit=%-5s %-26s tree_says=%s" % row)
print("     (non-118 cache_only total: %d)" % sum(1 for r in co_list if r[2] != 118))
print("  -- tree_only (tree licenses a button the cache does not show) --")
n = 0
for row in to_list:
    if row[2] == 118:
        continue
    n += 1
    if n <= 20:
        print("     %-12s %-12s bldg=%-5s unit=%-5s %-26s tree_age=%s" % row)
print("     (non-118 tree_only total: %d)" % sum(1 for r in to_list if r[2] != 118))

print()
print("=" * 104)
print("Q3: BARRELS OF THE DECISION - building 12 only, per civ")
print("=" * 104)
for ck in ("Britons", "Jurchens", "Muisca", "Incas", "Mapuche", "Tupi", "Byzantines", "Vikings", "Aztecs"):
    stem = stem_for(ck)
    if not stem or stem not in trees:
        continue
    tr = tree_rows(stem)
    ca = cache_entries(ck)
    trc = set(k for k, r in tr.items() if r.get("Node Status") == "ResearchedCompleted" and k[0] == 12)
    kak = set(k for k in ca if k[0] == 12)
    f = lambda S: sorted(u for _, u in S)
    print("  %-12s tree@12=%-34s cache@12=%-34s" % (ck, f(trc), f(kak)))
    print("  %-12s   cache_only=%-22s tree_only=%s" % ("", sorted(u for _, u in (kak - trc)), sorted(u for _, u in (trc - kak))))
print()
print("DONE")
