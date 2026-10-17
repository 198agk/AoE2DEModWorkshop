"""Print every string in a cost plan EXCEPT the giant civs list, plus raw edit labels."""
import sys

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")

import aoe2mod.api as A  # noqa: E402
import aoe2mod.intent.compiler as C  # noqa: E402
from aoe2mod.dat import families as F  # noqa: E402
from aoe2mod.dat import locate as L  # noqa: E402


def strings_of(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("civs", "civ_indices", "unit_ids", "location_ids"):
                continue
            yield from strings_of(v, "%s.%s" % (path, k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from strings_of(v, "%s[%d]" % (path, i))


tk = A.open_toolkit()
tk._ensure()
intents, bindings = C.load_schema()

# --- Part A: what the user sees from plan()
CASES = [
    {"intent": "tech.cost", "tech": "Loom", "resource": "gold", "value": 30},
    {"intent": "unit.cost", "unit": "Archer", "resource": "wood", "value": 30},
    {"intent": "unit.cost", "unit": "Villager", "resource": "food", "delta": 5},
]
print("=== PART A: every string plan() reports ===")
for case in CASES:
    try:
        plan = tk.plan(case)
    except Exception as exc:  # noqa: BLE001
        print("SKIP", case["intent"], exc)
        continue
    print("-- %s %s" % (case["intent"], case.get("tech") or case.get("unit")))
    for p, s in strings_of(plan):
        print("     %-22s %r" % (p, s))

# --- Part B: the raw labels _targets_for_unit/_targets_for_tech yield ---
print()
print("=== PART B: raw labels from the target walkers ===")
for name, call in (
    ("unit Archer cost", lambda: C._targets_for_unit(bindings, 4, None, "cost_entry")),
    ("tech Loom cost", lambda: (lambda t: C._targets_for_tech(bindings["tech_fields"] if False else {}, t, 22))(None)),
):
    pass

# unit walker, done properly
b = bindings["unit_fields"]["cost"]
print("binding for unit cost_entry:", {k: v for k, v in b.items() if k != "note"})
p = None
try:
    from aoe2mod.dat import parser as P
    pass
except Exception:
    pass

u = None
try:
    hits = C.unit_targets(tk._civs, 4, {"cost"}, tk._stats)
    print("unit_targets returned:", type(hits).__name__, len(hits) if hasattr(hits, "__len__") else "?")
    for h in hits[:2]:
        print("   hit:", h if not isinstance(h, (list, tuple)) else h[:3])
except Exception as exc:  # noqa: BLE001
    print("unit_targets EXC:", exc)

# direct: walk one record
idx, rec = L.find_units(tk._civs, 4)[0]
# find the unit dict the walker needs
for civ in tk._civs:
    for r in civ.get("units", ()) or ():
        if r.get("id") == 4:
            tgs = list(C._targets_for_unit(bindings, r, None, "cost_entry"))
            print("   _targets_for_unit(cost_entry) yields:",
                  [(t[3], t[4]) for t in tgs])
            break
    else:
        continue
    break

# tech walker
tb = bindings["tech_fields"]["cost"]
print()
print("binding for tech cost_entry:", {k: v for k, v in tb.items() if k != "note"})
tech_hits = L.find_techs(tk._tech_records(), 22)
print("find_techs(22):", tech_hits[:1] and (tech_hits[0][0], tech_hits[0][1].get("name")))
tgs = list(C._targets_for_tech(tb, tech_hits[0][1], tech_hits[0][0]))
print("   _targets_for_tech(cost_entry) yields:", [(t[3],) for t in tgs])
