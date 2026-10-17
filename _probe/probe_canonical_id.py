# -*- coding: utf-8 -*-
"""Is there a data-backed way to tell the canonical id from its age variants?

futuravailableunits.json lists 87 "Archery Range" (age 2) but NOT 10/14, which
are also called "Archery Range" in the .dat.  Dump the full Builder entry so the
shape is unambiguous, then check whether the unlisted variants are reachable
through civ tech-tree nodes.
"""
import os
import json
import collections

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
D = os.path.join(GAME, "resources", "_common", "dat")

with open(os.path.join(D, "futuravailableunits.json"), encoding="utf-8") as f:
    fau = json.load(f)

print("=== every buildable unit listed for Britons, grouped by builder ===")
blk = fau["Britons"]
for b in blk["Buildings"]:
    us = b.get("Units") or []
    print("  builder %-4s %-22s -> %2d units" % (b["ID"], b["Name"], len(us)))
    for u in us[:4]:
        print("       %-5s %-24s age=%s prereq=%s"
              % (u["ID"], u["Name"], u.get("RequiredAge"), u.get("PrereqTech")))
    if len(us) > 4:
        print("       ... +%d more" % (len(us) - 4))

print()
print("=== is there a global canonical list? all distinct (ID,Name) in the file ===")
allu = collections.defaultdict(set)
for civ, blk in fau.items():
    if not isinstance(blk, dict):
        continue
    for b in blk.get("Buildings", []) or []:
        for u in b.get("Units", []) or []:
            allu[u["Name"]].add(u["ID"])
print("  distinct names:", len(allu))
for name in ("House", "Archery Range", "Stable", "Barracks", "Castle", "Town Center"):
    print("    %-16s -> %s" % (name, sorted(allu.get(name, []))))

print()
print("=== civ tech tree: which of the House ids appear as nodes? ===")
CT = os.path.join(D, "CivTechTrees")
files = sorted(os.listdir(CT))
print("  civ techtree files:", len(files))
sample = os.path.join(CT, "Britons.json")
if os.path.exists(sample):
    t = json.load(open(sample, encoding="utf-8"))
    print("  Britons.json top keys:", list(t)[:12])
else:
    print("   no Britons.json; first file:", files[0])
    t = json.load(open(os.path.join(CT, files[0]), encoding="utf-8"))
    print("  top keys:", list(t)[:12])
print(json.dumps(t, ensure_ascii=False)[:900])
