# -*- coding: utf-8 -*-
"""What does a bundle do when one sentence is not an in-place .dat patch?

A player's sentence can mix them: "villagers are tougher AND let Britons
build Huskarls".  Today `plan_bundle` previews both sentences happily and then
the fold raises.  This probe records exactly what the user sees, so the
behaviour is a decision rather than an accident.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A
import aoe2mod.intent.compiler as C

tk = A.open_toolkit()

MIXED = [
    {"intent": "unit.stat", "unit": "Villager", "stat": "hit_points", "delta": 5},
    # 41 by id: the NAME "Huskarl" is ambiguous (41 and 759 are both 近卫军),
    # which is a useful fact of its own but not what this probe is about.
    {"intent": "unit.availability", "unit": 41, "civ": "British",
     "action": "grant"},
]

print("=== plan_bundle(mixed) ===")
try:
    pb = tk.plan_bundle(MIXED)
    print("  it returned; descriptions =", pb.get("descriptions"))
    print("  edit_count =", pb.get("edit_count"))
except Exception as exc:
    print("  %s: %s" % (type(exc).__name__, exc))

print()
print("=== build_bundle(mixed) ===")
try:
    man = tk.build_bundle(MIXED, os.path.join(ROOT, "_probe", "out_bundle_mixed"),
                          author="probe")
    print("  it built:", sorted(man))
except Exception as exc:
    print("  %s: %s" % (type(exc).__name__, exc))

print()
print("=== plan_bundle(availability only) ===")
try:
    pb = tk.plan_bundle([MIXED[1]])
    print("  it returned; descriptions =", pb.get("descriptions"))
    print("  edit_count =", pb.get("edit_count"))
except Exception as exc:
    print("  %s: %s" % (type(exc).__name__, exc))

print()
print("=== a single sentence still works on its own ===")
print("  plan(unit.stat) ->", tk.plan(MIXED[0]).get("description"))
print("  plan(unit.availability) ->", tk.plan(MIXED[1]).get("description"))
