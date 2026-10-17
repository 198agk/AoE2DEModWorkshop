"""Print the FULL plan text for cost intents, to see which label reaches the user."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json
import sys

sys.path.insert(0, _HERE_PATH(".."))

import aoe2mod.api as A  # noqa: E402

CASES = [
    {"intent": "tech.cost", "tech": "Loom", "resource": "gold", "value": 30},
    {"intent": "unit.cost", "unit": "Archer", "resource": "wood", "value": 30},
    {"intent": "unit.cost", "unit": "Villager", "resource": "food", "delta": 5},
]

tk = A.open_toolkit()
for case in CASES:
    try:
        plan = tk.plan(case)
    except Exception as exc:  # noqa: BLE001
        print("SKIP", case["intent"], exc)
        continue
    print("=== %s %s" % (case["intent"], case.get("tech") or case.get("unit")))
    print(json.dumps(plan, ensure_ascii=False, indent=2, default=str))
    print()
