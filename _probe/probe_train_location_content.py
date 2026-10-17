"""The train_locations CONTENT, not its length.

Presence is not the gate (every tree-modelled unit has >=1 train location).  The
43/43 difference must be inside the entries.  Print them raw.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
civs = tk._civs


def rec(civ_name, uid):
    for c in civs:
        if c["name"] == civ_name:
            for u in c["units"]:
                if u["id"] == uid:
                    return u
    return None


for uid, label, cs in [(41, "Huskarl", ["Goths", "British"]),
                       (5, "Hand Cannoneer", ["British", "Turks"]),
                       (83, "Villager", ["British", "Goths"])]:
    print("unit %d %s" % (uid, label))
    for c in cs:
        u = rec(c, uid)
        print("   %-9s train_locations = %s"
              % (c, json.dumps(u.get("train_locations"), default=str)))
        print("             costs = %s" % json.dumps(u.get("costs"), default=str))
    print()

# And the full diff of a single pair, field by field, so we see exactly what
# separates "can" from "cannot".
a = rec("Goths", 41)
b = rec("British", 41)
print("=== Goths vs British, unit 41 (Huskarl), every field ===")
for k in sorted(set(a) | set(b)):
    if k.startswith("_") and k not in ("_dll_name",):
        continue
    va, vb = a.get(k), b.get(k)
    mark = "   <<<" if va != vb else ""
    print("  %-26s %-40s %s%s"
          % (k, json.dumps(va, default=str)[:40],
             json.dumps(vb, default=str)[:40], mark))
