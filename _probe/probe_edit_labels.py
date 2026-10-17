"""What label reaches the edit list a user/UI reads after a build?

plan()'s `description` comes from Resolved.describe_target(), but each written
Edit carries `Edit.where` = "<where> <label>", and the label comes from the
target walker.  A walker that hardcodes "cost type %d" leaks the raw resource id
into text a user reads, even though the preview sentence looks right.

This prints the Edit.where values for a cost edit on both the unit and tech path
so the leak is visible rather than inferred.
"""
import sys

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")

import aoe2mod.api as A  # noqa: E402
import aoe2mod.intent.compiler as C  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
intents, bindings = C.load_schema()

CASES = [
    {"intent": "unit.cost", "unit": "Archer", "resource": "wood", "value": 30},
    {"intent": "unit.cost", "unit": "Villager", "resource": "food", "delta": 5},
    {"intent": "tech.cost", "tech": "Loom", "resource": "gold", "value": 30},
]

for case in CASES:
    r = C.resolve(case, intents, bindings=bindings)
    b = C._binding_for(bindings, r, case["intent"])
    where_name = case["intent"]
    print("=== %s  (binding label = %r)" % (where_name, b.get("label")))
    if r.kind == "tech":
        # The tech walker labels are asserted directly in test_compiler.py
        # (Edit.where must start with "tech[22] 成本 gold"); skip here.
        print("   (tech labels asserted in aoe2mod/tests/test_compiler.py)")
    else:
        hit = C.L.find_units(tk._civs, r.entity.id)[0]
        rec = hit[2]
        tg = list(C._targets_for_unit(bindings, rec, b))
        print("   walker labels:", [t[3] for t in tg])
        print("   what a user would read in the edit list:",
              ["%s %s" % (case["intent"], t[3]) for t in tg])
    print()
