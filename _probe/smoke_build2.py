"""Rebuild the smoke mod with changes that are visible by two independent routes.

Route A (zero clicks): villager line of sight.  At game start the fog reveal
radius comes straight from the unit record, so a big LOS shows up in the very
first frame.

Route B (one click): villager hit points, read from the unit tooltip / HP bar.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from aoe2mod import api as A  # noqa: E402

OUT = os.path.join(_ROOT, "_smoke", "VillagerHP_smoke")

tk = A.open_toolkit()
tk._ensure()

d = tk.describe(83, "unit")
print("=== before ===")
for k in ("hit_points", "line_of_sight", "movement_speed", "creation_time"):
    print("   %-16s %s" % (k, d["stats"].get(k)))

edits = [
    {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "value": 2500},
    {"intent": "unit.stat", "unit": 83, "stat": "line_of_sight", "value": 30},
]

for e in edits:
    p = tk.plan(e)
    print("   plan:", p["description"], "| edits", p["edit_count"])

# build() takes ONE intent, so fold both into the same dat by building twice
# into the same folder is not supported -- instead check whether the compiler
# accepts a list.
import inspect
print("build signature:", inspect.signature(tk.build))
