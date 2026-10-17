"""Does any user-visible string still leak a raw resource TYPE NUMBER?

compiler.py:877 yielded the label "cost type %d" on the unit path while
compiler.py:632 already preferred the schema label.  A player reading a preview
must never see "cost type 3"; they must see the resource name.

This probe reads the plan text for tech and unit cost intents and FAILS if any
reported string contains "type <digits>".
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import re
import sys

sys.path.insert(0, _HERE_PATH(".."))

import aoe2mod.api as A  # noqa: E402

LEAK = re.compile(r"type\s+\d+")

CASES = [
    {"intent": "tech.cost", "tech": "Loom", "resource": "gold", "value": 30},
    {"intent": "tech.cost", "tech": "Crop Rotation", "resource": "food", "delta": 5},
    {"intent": "tech.cost", "tech": "Feudal Age", "resource": "food", "delta": 10},
    {"intent": "unit.cost", "unit": "Archer", "resource": "wood", "value": 30},
    {"intent": "unit.cost", "unit": "Villager", "resource": "food", "delta": 5},
    {"intent": "unit.cost", "unit": "Knight", "resource": "gold", "value": 100},
]

def strings_of(obj, path=""):
    """Every string anywhere in the plan result, with a path for reporting."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings_of(v, "%s.%s" % (path, k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from strings_of(v, "%s[%d]" % (path, i))

def main():
    tk = A.open_toolkit()
    bad = []
    for case in CASES:
        try:
            plan = tk.plan(case)
        except Exception as exc:  # noqa: BLE001
            print("SKIP %-58s %s" % (case["intent"], exc))
            continue
        hits = [(p, s) for p, s in strings_of(plan) if LEAK.search(s)]
        tag = "LEAK" if hits else "ok  "
        print("%s %-14s %-14s -> %s"
              % (tag, case["intent"], case.get("tech") or case.get("unit"),
                 hits or "no numeric type in any string"))
        bad.extend((case, p, s) for p, s in hits)

    print()
    if bad:
        print("COST LABELS LEAK RAW TYPE IDS IN USER-VISIBLE TEXT: %d" % len(bad))
        for case, p, s in bad:
            print("   %s  %s = %r" % (case["intent"], p, s))
        return 1
    print("NO COST LABEL LEAKS A RAW RESOURCE TYPE ID")
    return 0

if __name__ == "__main__":
    sys.exit(main())
