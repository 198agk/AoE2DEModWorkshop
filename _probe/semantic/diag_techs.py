# -*- coding: utf-8 -*-
"""Why do 773 techs have a positive LanguageDLLName absent from the strings files?

Hypotheses:
  H1 the tech name id lives in a different string-id namespace (e.g. the
     CivTechTrees "Name String ID" / "Help String ID" pairing where
     Help = Name + 100000);
  H2 the id is present but under a DIFFERENT spelling of the key-value file we
     did not merge (we should search the raw files, not only numeric-key parses);
  H3 the id is a "name id" that the game resolves through a TechTree .json
     rather than the key-value strings.
"""
import json
import os
import re
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _gamepaths as GP  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "_raw_ids.json"), encoding="utf-8") as f:
    raw = json.load(f)

techs = raw["techs"]
missing = [t for t in techs
           if isinstance(t.get("LanguageDLLName"), int)
           and t["LanguageDLLName"] > 0]
print("techs with positive LanguageDLLName: %d" % len(missing))

sys.path.insert(0, HERE)
from strings_db import load_language, KV_FILES  # noqa: E402
en, _ = load_language("en")

unres = [t for t in missing if t["LanguageDLLName"] not in en]
res = [t for t in missing if t["LanguageDLLName"] in en]
print("resolved: %d ; unresolved positive: %d" % (len(res), len(unres)))

ids = sorted(t["LanguageDLLName"] for t in unres)
print("unresolved id range: %d .. %d" % (ids[0], ids[-1]))
print("unresolved id top values:", collections.Counter(ids).most_common(12))

# how are the unresolved ids distributed by magnitude prefix?
pref = collections.Counter(str(i)[0] for i in ids)
print("first-digit histogram:", dict(sorted(pref.items())))

# For the unresolved, do they have a resolvable Description/Help/TechTree?
print()
print("sample unresolved techs (id, internal, DLLName/Desc/Help/TechTree):")
for t in unres[:25]:
    print("   %-4d %-18s N=%-7s D=%-7s H=%-7s T=%-7s | N in en? %s"
          % (t["index"], t.get("name"), t.get("LanguageDLLName"),
             t.get("LanguageDLLDescription"), t.get("LanguageDLLHelp"),
             t.get("LanguageDLLTechTree"),
             t.get("LanguageDLLName") in en))

# -- H1: is Name+100000 the Help id, and does that resolve? --------------
print()
both = collections.Counter()
for t in unres:
    n = t["LanguageDLLName"]
    h = t.get("LanguageDLLHelp")
    d = t.get("LanguageDLLDescription")
    both[(h == n + 100000, d == n + 100000, t.get("LanguageDLLTechTree") == n + 100000)] += 1
print("(Help==N+100000, Desc==N+100000, Tree==N+100000) -> count:", dict(both))

# -- H2: search the RAW key-value files for the literal numeric id -------
GAME = os.path.join(GP.GAME, "resources")
targets = {str(i) for i in collections.Counter(ids).most_common(5)[0:1]}
for i in ids[:1]:
    targets.add(str(i))
pat = re.compile(r"^\s*(\d+)\s+\"")
hits = collections.Counter()
scanned = 0
for loc in ("en",):
    base = os.path.join(GAME, loc, "strings", "key-value")
    if not os.path.isdir(base):
        continue
    for fn in sorted(os.listdir(base)):
        if not fn.lower().endswith(".txt"):
            continue
        p = os.path.join(base, fn)
        scanned += 1
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = pat.match(line)
                if m and m.group(1) in targets:
                    hits[(fn, int(m.group(1)))] += 1
print()
print("raw-file scan over %d files in resources\\en\\strings\\key-value" % scanned)
for k, v in sorted(hits.items()):
    print("   %s -> id %d (x%d)" % (k[0], k[1], v))

# -- H3: cross-check against CivTechTrees Name String ID -----------------
CT = os.path.join(GAME, "_common", "dat", "CivTechTrees")
tree_name_ids = collections.Counter()
tree_node_to_nameid = {}
if os.path.isdir(CT):
    for fn in sorted(os.listdir(CT)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(CT, fn), encoding="utf-8") as f:
            d = json.load(f)
        for key in ("civ_techs_buildings", "civ_techs_units"):
            for node in d.get(key, []):
                nsid = node.get("Name String ID")
                nid = node.get("Node ID")
                if isinstance(nsid, int):
                    tree_name_ids[nsid] += 1
                    tree_node_to_nameid.setdefault(nid, set()).add(nsid)
print()
print("CivTechTrees distinct Name String IDs: %d" % len(tree_name_ids))
# how many resolved tech names come from tree ids
overlap = sum(1 for t in res if t["LanguageDLLName"] in tree_name_ids)
print("resolved techs whose id is also a CivTechTrees Name String ID: %d" % overlap)
overlap_u = sum(1 for t in unres if t["LanguageDLLName"] in tree_name_ids)
print("UNRESOLVED techs whose id IS a CivTechTrees Name String ID: %d" % overlap_u)

# -- and: are the unresolved tech ids actually TECH ids at all? ----------
print()
print("unresolved tech internal names (first 60):",
      [t.get("name") for t in unres[:60]])

with open(os.path.join(HERE, "_tech_diag.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump({
        "unresolved_tech_ids": sorted(set(ids)),
        "resolved_count": len(res),
        "unresolved_count": len(unres),
        "tree_name_string_ids": sorted(tree_name_ids),
    }, f, ensure_ascii=False)
print("wrote _tech_diag.json")
