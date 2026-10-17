# -*- coding: utf-8 -*-
"""Is a population cost mechanically editable, or is it deliberately out of scope?

describe() reports `population: 1` for an Archer, and the slot IS a normal
cost slot (type 4).  The schema's `resource` enum and dat_bindings'
`resource_types` both stop at 3 (gold), so the field is visible but not
editable.  Test whether adding it would actually work, and measure how many
units have one.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A                # noqa: E402
from aoe2mod.dat import locate as L         # noqa: E402
from aoe2mod.intent import compiler as C    # noqa: E402

tk = A.open_toolkit()
tk._ensure()
civs = tk._civs

# How common is a type-4 slot?
types = {}
with_pop = set()
for c in civs:
    for u in c["units"]:
        for slot in (u.get("costs") or ()):
            types[slot["type"]] = types.get(slot["type"], 0) + 1
            if slot["type"] == 4 and slot["amount"]:
                with_pop.add(u["id"])
print("cost slot types across all civs:", dict(sorted(types.items())))
print("distinct units with a nonzero population cost:", len(with_pop))
print("Archer(4) slots:",
      [(s["type"], s["amount"], s["flag"]) for s in
       next(u for c in civs for u in c["units"] if u["id"] == 4 and c["index"] == 1)["costs"]])

# Do it by hand: bind type 4 and see whether a target is produced and writable.
bindings = C.load_schema()[1]
b = dict(bindings["cost_entry"])
b["resource_types_inverted"] = {"population": 4}
hits = L.find_units(civs, 4)
print("\nArcher records found:", len(hits))
targets = []
for ci, cname, u in hits:
    targets.extend(C._targets_for_unit(bindings, u, b))
print("targets produced for population:", len(targets))
if targets:
    off = targets[0]["off"] if isinstance(targets[0], dict) else targets[0]
    print("first target:", targets[0])
    raw = tk._raw
    import struct
    print("current value at that offset:",
          struct.unpack_from("<h", raw, off)[0] if isinstance(off, int)
          else "n/a")

# And through the normal pipeline with the enum widened in memory.
intents = C.load_schema()[0]
it = dict(intents["intents"]["unit.cost"])
it["fields"] = dict(it["fields"])
it["fields"]["resource"] = dict(it["fields"]["resource"])
it["fields"]["resource"]["enum"] = ["food", "wood", "gold", "stone", "population"]
intents2 = {"intents": dict(intents["intents"])}
intents2["intents"]["unit.cost"] = it
b2 = dict(bindings)
b2["resource_types"] = dict(bindings["resource_types"])
b2["resource_types"]["population"] = 4
try:
    r = C.resolve({"intent": "unit.cost", "unit": 4, "resource": "population",
                   "value": 0}, intents2, bindings=b2)
    print("\nresolve with population:", r.describe(), "| raw:", r.raw)
    edits = C.compile_edits(tk._raw, civs, r, b2, intents2,
                            tail=tk._parsed[4], gv=tk._parsed[3])
    print("compile_edits ok, edits:", len(edits[1]))
except Exception as exc:
    print("\nFAILED:", type(exc).__name__, exc)
