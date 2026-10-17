# -*- coding: utf-8 -*-
"""THE NATURAL EXPERIMENT.

The shipped cache lists barracks units that the shipped tree calls NotAvailable,
for a handful of civs.  External civ knowledge (aoe2insights, community wikis)
knows whether those civs really have those units in game.  If the community
consensus matches the TREE, then the cache is NOT the literal button list and
adding a tree row (the mod's A half) cannot add a button.  If it matches the
CACHE, then the cache is the button list and the tree is advisory.

This costs zero games played: it is a question about a shipped, live product
whose answer millions of players already know.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, sys, json

ROOT = _HERE_PATH()
sys.path.insert(0, ROOT)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
import aoe2mod.game.buildpanel as BP
import aoe2mod.game.civtechtrees as CT

# --- cache -----------------------------------------------------------------
CACHE = os.path.join(GAME, "resources", "_common", "dat", "futuravailableunits.json")
text, obj = BP.load_panel(CACHE)

def cite(bid, unit_list):
    out = []
    for ck in obj:
        if not isinstance(obj[ck], dict):
            continue
        for blk in obj[ck].get("Buildings", []):
            if blk.get("ID") != bid:
                continue
            ids = [u.get("ID") for u in blk.get("Units", [])]
            if any(u in ids for u in unit_list):
                out.append((ck, [(u.get("ID"), u.get("Name"), u.get("RequiredAge"))
                                 for u in blk["Units"] if u.get("ID") in unit_list]))
    return out

# --- tree ------------------------------------------------------------------
trees = CT.load_trees(os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees"))

def tree_rows(civfile, bid, unit_list):
    if civfile not in trees:
        return None
    res = {}
    for r in trees[civfile]:
        if r.get("Use Type") == "Unit" and r.get("Building ID") == bid and r.get("Node ID") in unit_list:
            res[r["Node ID"]] = (r.get("Node Status"), r.get("Age ID"), r.get("Name"))
    return res

MB = [74, 75, 77, 473, 567, 93, 358, 359]
print("=" * 100)
print("JURCHENS / MUISCA - the two shipped civs where cache and tree DISAGREE at the barracks")
print("=" * 100)
for cache_key, stem in (("Jurchens", "JURCHENS"), ("Muisca", "MUISCA")):
    print()
    print("### %s (tree file %s.json)" % (cache_key, stem))
    tr = tree_rows(stem, 12, MB)
    print("  TREE rows at Barracks for the militia/spear lines:")
    for uid in MB:
        v = tr.get(uid) if tr else None
        print("     %-5s %-24s %s" % (uid, (v[2] if v else "(no row)"), (v[0], "age=%s" % v[1]) if v else ""))
    print("  CACHE entries at Barracks:")
    for ck, units in cite(12, MB):
        if ck != cache_key:
            continue
        for uid, nm, age in units:
            print("     %-5s %-24s age=%s" % (uid, nm, age))

print()
print("=" * 100)
print("ALL 11 shipped cache-vs-tree contradictions (cache shows it, tree says NotAvailable)")
print("=" * 100)
NAMES = {}
for r in trees.get("BRITONS", []):
    NAMES[r.get("Node ID")] = r.get("Name")
rows = []
for ck in obj:
    if not isinstance(obj[ck], dict):
        continue
    for blk in obj[ck].get("Buildings", []):
        bid = blk.get("ID")
        cache_ids = set(u.get("ID") for u in blk.get("Units", []))
        stem = None
        for s2 in trees:
            if s2.upper().replace("_", "").startswith(ck.upper()[:5]):
                stem = s2
                break
        # precise: reverse map from tree stem to cache key is not 1:1; use CT.civ_file_stem
        stem = CT.civ_file_stem(ck) or stem
        if not stem or stem not in trees:
            continue
        for r in trees[stem]:
            if r.get("Use Type") != "Unit" or r.get("Building ID") != bid:
                continue
            if r.get("Node ID") in cache_ids and r.get("Node Status") == "NotAvailable":
                rows.append((ck, stem, bid, r.get("Node ID"), r.get("Name"), r.get("Age ID")))
for row in rows:
    print("   %-12s %-12s bldg=%-4s unit=%-5s %-28s age=%s" % row)
print("   total:", len(rows))
