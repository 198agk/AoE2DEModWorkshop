# -*- coding: utf-8 -*-
"""Check the two failing assertions from test_age_variants.py.

Also prints the resource-name table so a cost expectation can be checked
against the schema rather than a hand-written list.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A                 # noqa: E402
from aoe2mod.intent import compiler as C     # noqa: E402

tk = A.open_toolkit()
tk._ensure()

print("=== does plan() expose that a Barracks has no attack? ===")
p = tk.plan({"intent": "unit.attack_class", "unit": 12, "delta": 1})
print("plan: %s" % {k: p[k] for k in ("description", "edit_count", "civ_count")})

print()
print("=== does build refuse it? ===")
try:
    C.compile_intent(tk.dat_path, {"intent": "unit.attack_class", "unit": 12,
                                   "delta": 1}, parsed=tk._parsed, stats=tk._stats)
    print("NOT REFUSED")
except C.IntentError as exc:
    print("refused: %s" % exc)

print()
print("=== what does an Archer really cost? ===")
d = tk.describe(4, "unit")
print(d["stats"]["costs"])
print()
print("=== and a House? (does it pay population?) ===")
print(tk.describe(70, "unit")["stats"]["costs"])
print()
print("=== resource names (from the schema, not a hardcoded map) ===")
print(A.open_toolkit().schema()["bindings"]["resource_types"])
