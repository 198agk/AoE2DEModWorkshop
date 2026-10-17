#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a40_sprite_miss.py -- characterise the 189 'graphic named but no .sld stem' misses.

Are the dat Graphic.FileName values non-empty but absent from drs\\graphics?  If so,
where do those names live?  (Candidate: they are sprite names in a DIFFERENT container,
or the file is genuinely absent from this install.)  Honest answer either way.
"""
import json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
U = json.load(open(os.path.join(HERE, "index_units.json"), encoding="utf-8"))
G = json.load(open(os.path.join(HERE, "graphics_raw.json"), encoding="utf-8"))
GFX = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"

SLD = {}
for f in os.listdir(GFX):
    if f.lower().endswith(".sld"):
        SLD[f.lower()[:-4]] = f
# also index by family stem (drop the trailing _x1/_x2 and animation token)
GFXLIST = os.listdir(GFX)
SUB = collections.Counter()
LOW = set(x.lower() for x in GFXLIST)

slot2g = {g["slot"]: g for g in G}


def ok_sp(r):
    return any(v.get("resolution", "").startswith(("direct", "substituted"))
               for v in r["sprites"].values())


miss_names = collections.Counter()
rows = []
for r in U.values():
    if ok_sp(r):
        continue
    for f, v in r["sprites"].items():
        if v.get("resolution") != "unresolved":
            continue
        nm = v.get("FileName")
        if not nm:
            continue
        miss_names[nm] += 1
        # what DOES exist for this name?
        cands = [x for x in GFXLIST if x.lower().startswith(nm.lower())]
        rows.append((r["unit_id"], f, nm, cands[:3]))

print("distinct unresolved dat FileNames: %d   (total field slots: %d)"
      % (len(miss_names), sum(miss_names.values())))
print("\n=== top 30 unresolved names, with the nearest on-disk .sld that shares the prefix ===")
for nm, n in miss_names.most_common(30):
    cands = [x for x in GFXLIST if x.lower().startswith(nm.lower())][:3]
    print("  %-40s x%-4d near=%s" % (nm, n, cands))

print("\n=== do these names exist as ANY file (not just .sld) under drs\\graphics? ===")
found_other = collections.Counter()
for nm in miss_names:
    exts = [x for x in GFXLIST if x.lower().startswith(nm.lower())]
    if exts:
        found_other[tuple(sorted(set(os.path.splitext(x)[1].lower() for x in exts)))] += 1
for k, v in found_other.most_common():
    print("  extensions available under that prefix: %-30s %d names" % (str(k), v))

print("\n=== the sample rows ===")
for uid, f, nm, cands in rows[:15]:
    print("  id %-6d %-26s FileName=%-34s near=%s" % (uid, f, nm, cands))

print("\n=== how many unresolved names have NOTHING with that prefix? ===")
nothing = [nm for nm in miss_names
           if not [x for x in GFXLIST if x.lower().startswith(nm.lower())]]
print("  %d of %d names have no file of any kind with that prefix" % (len(nothing), len(miss_names)))
print("  sample: %s" % (nothing[:20],))
