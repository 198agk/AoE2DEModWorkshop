# -*- coding: utf-8 -*-
"""How many FILE strings are named by records that DISAGREE about the name?"""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mod.api as A

tk = A.open_toolkit(); tk._ensure()
g = tk._stats["graphics"]

byname = collections.defaultdict(set)
for rec in g:
    f = (rec.get("file") or "").strip()
    n = (rec.get("name") or "").strip()
    if f and f != "None" and n:
        byname[f].add(n)

multi = {f: ns for f, ns in byname.items() if len(ns) > 1}
print("file strings named by >1 DISTINCT record name: %d of %d" % (len(multi), len(byname)))
for f, ns in sorted(multi.items())[:15]:
    print("   %-40s %s" % (f, sorted(ns)))

print()
print("=== the sheep's own files ===")
for f in ("a_herd_sheep_idleA_x1", "a_herd_sheep_deathA_x1", "a_herd_sheep_walkA_x1",
          "a_herd_sheep_attackA_x1"):
    hits = [(r.get("id"), r.get("name")) for r in g if (r.get("file") or "").strip() == f]
    print("   %-32s %s" % (f, hits))
