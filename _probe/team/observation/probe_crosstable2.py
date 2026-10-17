# -*- coding: utf-8 -*-
"""CORRECTED CROSS-TABLE + the famous-unit referee table.

Fix applied: a tree row is LICENSED if Node Status is ResearchedCompleted OR
ResearchRequired (ResearchRequired = "you can have it once the prereq tech is
researched" -> a legitimate button).  Only NotAvailable / no-row is a DENIAL.
My first pass counted ResearchRequired as a denial, which inflated cache_only
from ~460 to ~1472.  Correcting that is the difference between "the cache is
badly out of sync" and "the cache is nearly faithful".

Referee table: units whose civ availability is common AoE2 knowledge
(Bulgarians no Paladin, etc).  If the CACHE lists a unit for a civ that
genuinely cannot build it, the cache alone cannot be what draws the button.
"""
import os, json, collections

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
TREEDIR = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")
CACHE = os.path.join(GAME, "resources", "_common", "dat", "futuravailableunits.json")

LICENSED = ("ResearchedCompleted", "ResearchRequired")

CACHE_CIV = {"British": "BRITONS", "French": "FRANKS", "Byzantine": "BYZANTINES",
             "Mayan": "MAYANS", "Hindustanis": "INDIANS", "Magyars": "MAGYAR"}

def stem_for(ck):
    if ck in CACHE_CIV:
        return CACHE_CIV[ck]
    cand = ck.upper().replace(" ", "_").replace("-", "_")
    if os.path.exists(os.path.join(TREEDIR, cand + ".json")):
        return cand
    for f in os.listdir(TREEDIR):
        s = f[:-5]
        if s.lower() == ck.lower():
            return s
    return None

obj = json.loads(open(CACHE, encoding="utf-8-sig").read())
trees = {}
for f in os.listdir(TREEDIR):
    if f.endswith(".json"):
        trees[f[:-5]] = json.load(open(os.path.join(TREEDIR, f), encoding="utf-8-sig"))

def tree_rows(stem):
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

co_list, to_list = [], []
co_b, to_b = collections.Counter(), collections.Counter()
for ck in sorted(obj):
    stem = stem_for(ck)
    if not stem or stem not in trees:
        continue
    tr, ca = tree_rows(stem), cache_entries(ck)
    lic = set(k for k, r in tr.items() if r.get("Node Status") in LICENSED)
    kk = set(ca)
    for b, u in (kk - lic):
        co_b[b] += 1
        co_list.append((ck, stem, b, u, ca[(b, u)].get("Name"),
                        tr.get((b, u), {}).get("Node Status")))
    for b, u in (lic - kk):
        to_b[b] += 1
        to_list.append((ck, stem, b, u, tr[(b, u)].get("Name"), tr[(b, u)].get("Age ID")))

print("=" * 100)
print("Q1 CORRECTED:  licensed := status in %s" % (LICENSED,))
print("=" * 100)
print("  cache_only (cache shows, tree DENIES) : %d   by building: %s" % (len(co_list), dict(sorted(co_b.items()))))
print("  tree_only  (tree licenses, cache omits): %d   by building: %s" % (len(to_list), dict(sorted(to_b.items()))))
print()
print("  cache_only EXCLUDING building 118 (villager menu, different convention):")
n = 0
for r in co_list:
    if r[2] == 118:
        continue
    n += 1
    if n <= 25:
        print("     %-12s bldg=%-5s unit=%-5s %-26s tree_says=%s" % (r[0], r[2], r[3], r[4], r[5]))
print("     ---- total non-118: %d" % n)
print()
print("  tree_only EXCLUDING building 118:")
n = 0
for r in to_list:
    if r[2] == 118:
        continue
    n += 1
    print("     %-12s bldg=%-5s unit=%-5s %-26s tree_age=%s" % (r[0], r[2], r[3], r[4], r[5]))
print("     ---- total non-118: %d" % n)

print()
print("=" * 100)
print("Q2 REFEREE TABLE - units whose civ availability is common knowledge")
print("=" * 100)
FAMOUS = [
    (569, 101, "Paladin", "Bulgarians", "no Paladin (famous)"),
    (569, 101, "Paladin", "Britons", "no Paladin (famous)"),
    (569, 101, "Paladin", "Aztecs", "no Paladin (no stable)"),
    (569, 101, "Paladin", "Byzantines", "no Paladin (famous)"),
    (569, 101, "Paladin", "Persians", "HAS Paladin"),
    (567, 12, "Champion", "Bulgarians", "no Champion (famous)"),
    (567, 12, "Champion", "Britons", "HAS Champion"),
    (567, 12, "Champion", "Goths", "HAS Champion"),
    (359, 12, "Halberdier", "Britons", "HAS Halberdier"),
    (359, 12, "Halberdier", "Aztecs", "has Halberdier?"),
    (492, 87, "Arbalester", "Bulgarians", "no Arbalester (famous)"),
    (492, 87, "Arbalester", "Britons", "HAS Arbalester"),
    (5, 87, "Hand Cannoneer", "Britons", "no Hand Cannoneer (famous)"),
    (5, 87, "Hand Cannoneer", "Bulgarians", "no Hand Cannoneer (famous)"),
    (5, 87, "Hand Cannoneer", "Turks", "HAS Hand Cannoneer"),
]
print("  %-11s %-7s %-16s %-14s %-14s %-9s %s" % ("civ", "bldg", "unit", "TREE", "CACHE", "agree?", "known fact"))
for uid, bid, uname, ck, fact in FAMOUS:
    stem = stem_for(ck)
    if not stem or stem not in trees:
        print("  %-11s (no tree)" % ck)
        continue
    tr, ca = tree_rows(stem), cache_entries(ck)
    row = tr.get((bid, uid))
    tstat = row.get("Node Status") if row else "NO ROW"
    tlic = tstat in LICENSED
    clic = (bid, uid) in ca
    print("  %-11s %-7s %-16s %-14s %-14s %-9s %s" % (
        ck, bid, uname, tstat, ("listed" if clic else "-"),
        ("YES" if tlic == clic else "*** NO ***"), fact))

print()
print("DONE")
