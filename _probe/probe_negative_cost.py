# -*- coding: utf-8 -*-
"""Is a NEGATIVE cost already reachable through unit.cost?

_write_targets range-checks overflow but never sign, so "make wood cheaper" by
more than the current cost would store a negative amount.  A negative cost is
not a discount -- the engine reads it as a resource REQUIREMENT and it can make
a building unbuildable or, worse, grant resources.  Measure before fixing.
"""
import os
import sys

ROOT = r"D:\Software\DeepSeek Harness\工作区2"
sys.path.insert(0, ROOT)
from aoe2mod import api  # noqa: E402

tk = api.open_toolkit()
print("game:", tk.game_root, "| version:", tk.version)

# Archer id 4 = 25 wood.  Ask to remove 100.
for label, intent in (
    ("unit.cost Archer wood -5  (25 -> 20, legit)",
     {"intent": "unit.cost", "unit": "Archer", "resource": "wood", "delta": -5}),
    ("unit.cost Archer wood -100 (25 -> -75, NEGATIVE)",
     {"intent": "unit.cost", "unit": "Archer", "resource": "wood", "delta": -100}),
):
    try:
        out = tk.plan(intent)
        print("\n%s\n   plan OK: %s | edits %s"
              % (label, out["description"], out["edit_count"]))
    except Exception as exc:
        print("\n%s\n   REFUSED: %s: %s" % (label, type(exc).__name__, exc))

# What does describe() report as the stored amount today?
d = tk.describe(4)
print("\nArcher costs today:", d["stats"]["costs"])
