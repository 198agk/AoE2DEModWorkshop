# -*- coding: utf-8 -*-
"""Find every widgetui JSON that references civ emblems, and how."""
import os, json, re

W = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
pat = re.compile(r"emblem", re.I)

print("=== JSON files mentioning 'emblem' (case-insensitive) ===")
hits = []
for root, ds, fs in os.walk(W):
    if os.sep + "textures" + os.sep in root + os.sep:
        continue
    for f in fs:
        if not f.lower().endswith(".json"):
            continue
        fp = os.path.join(root, f)
        txt = open(fp, "r", encoding="utf-8", errors="replace").read()
        n = len(pat.findall(txt))
        if n:
            hits.append((n, fp, txt))
for n, fp, txt in sorted(hits, reverse=True):
    print("   %-46s %4d hits" % (os.path.relpath(fp, W), n))
print("   files:", len(hits))

print()
print("=== distinct emblem-ish literals found ===")
lits = {}
for n, fp, txt in hits:
    for m in re.finditer(r'"([^"]*emblem[^"]*)"', txt, re.I):
        lits.setdefault(m.group(1), set()).add(os.path.relpath(fp, W))
for k in sorted(lits):
    v = sorted(lits[k])
    print("   %-52s %s" % (k, v[:3]))

print()
print("=== icons.json InGameCivEmblem / CivEmblem raw values (first 6 each) ===")
ic = json.load(open(os.path.join(W, "icons.json"), "r", encoding="utf-8"))
print("   top-level keys:", list(ic.keys())[:20])
for sec in ("InGameCivEmblem", "CivEmblem", "CivHero"):
    d = ic.get(sec)
    if isinstance(d, dict):
        items = list(d.items())[:6]
        print("   %s: n=%d  %s" % (sec, len(d), items))
    else:
        print("   %s: %r" % (sec, type(d)))
