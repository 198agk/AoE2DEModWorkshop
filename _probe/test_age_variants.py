# -*- coding: utf-8 -*-
"""The age-variant fix, tested through the PRODUCT path (not the helper).

probe_building_ageup_defect.py showed the defect the old way: "Barracks hp +100"
wrote id 12 and nothing else, so the mod would stop applying at Feudal Age.
This asserts the fix: the same intent must now write every age variant, and the
plan must say so BEFORE the user agrees.
"""
import os
import sys
import contextlib
import io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A                 # noqa: E402
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.intent import compiler as C     # noqa: E402

FAIL = []


def check(name, cond, detail=""):
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  -- " + str(detail)) if detail else ""))
    if not cond:
        FAIL.append(name)


tk = A.open_toolkit()
tk._ensure()

print("=== A. a plan for a building must report the whole family ===")
bp = tk.plan({"intent": "unit.stat", "unit": 12, "stat": "hit_points", "delta": 100})
print("Barracks plan: %s | edits %d | civs %d | variants %s"
      % (bp["description"], bp["edit_count"], bp["civ_count"],
         bp.get("variants")))
check("Barracks plan reports 4 age variants",
      sorted(bp.get("variants") or []) == [20, 132, 498], bp.get("variants"))
check("Barracks plan writes 63 civs x 4 ages = 252 records",
      bp["edit_count"] == 252 and bp["civ_count"] == 63, bp["edit_count"])
check("Barracks plan lists every unit id it touches",
      bp.get("unit_ids") == [12, 20, 132, 498], bp.get("unit_ids"))

hp_plan = tk.plan({"intent": "unit.stat", "unit": 70, "stat": "hit_points", "delta": 100})
print("House plan: edits %d variants %s"
      % (hp_plan["edit_count"], hp_plan.get("variants")))
check("House plan reports 5 variants and 63 x 6 = 378 edits",
      sorted(hp_plan.get("variants") or []) == [191, 192, 463, 464, 465]
      and hp_plan["edit_count"] == 378, hp_plan["edit_count"])

print()
print("=== B. a lone unit must NOT be dragged into a family ===")
ap = tk.plan({"intent": "unit.stat", "unit": "Archer", "stat": "hit_points",
              "delta": 5})
print("Archer plan: edits %d variants %r" % (ap["edit_count"], ap.get("variants")))
check("Archer plan has no age variants", not ap.get("variants"))
check("Archer plan is still 63 records", ap["edit_count"] == 63, ap["edit_count"])

print()
print("=== C. the build really writes every age variant ===")
parsed = tk._parsed
rep = C.compile_intent(tk.dat_path, {"intent": "unit.stat", "unit": 12,
                                     "stat": "hit_points", "delta": 100},
                       parsed=parsed, stats=tk._stats)
ids_written = {}
for e in rep["edits"]:
    ids_written[e.off] = e
print("Barracks build: edits %d | verification %s | changed %d | left %d"
      % (rep["edit_count"], rep["verification"]["ok"],
         rep["verification"]["changed_bytes"], rep["verification"]["leftover"]))
check("build produced 252 edits", rep["edit_count"] == 252, rep["edit_count"])
check("build verified (exact EOF, every byte claimed)",
      rep["verification"]["ok"] and rep["verification"]["leftover"] == 0,
      rep["verification"]["problems"][:2])
check("every edit is an int16 hit_points write at a distinct offset",
      len({e.off for e in rep["edits"]}) == 252 and
      all(e.width == 2 for e in rep["edits"]))

# Read the four records back out of the patched stream with the UNMODIFIED
# parser: all four ages must show 100 more hp.
buf = bytearray(tk._raw)
for e in rep["edits"]:
    buf[e.off:e.off + e.width] = int(e.after).to_bytes(e.width, "little", signed=True)
p = P.Parser(bytes(buf))
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
civs, _, gv, _ = A.L.locate(bytes(buf), parser=p)
got = {}
for c in civs:
    if c["index"] != 1:
        continue
    for u in c["units"]:
        if u["id"] in (12, 20, 132, 498):
            got[u["id"]] = u["hit_points"]
print("civ 1 hp after: %s" % got)
check("all four ages got +100 (1200/1500/1800/2100 -> +100)",
      got == {12: 1300, 498: 1600, 132: 1900, 20: 2200}, got)

print()
print("=== D. the other two unit intents also span the family ===")
cp = tk.plan({"intent": "unit.cost", "unit": 12, "resource": "wood", "delta": 10})
print("Barracks wood cost plan: edits %d variants %s"
      % (cp["edit_count"], cp.get("variants")))
check("unit.cost on a Barracks spans the family too",
      len(cp.get("variants") or []) == 3, cp.get("variants"))

# A building has no displayed_attack, so unit.attack_class on one must not
# promise edits the build would refuse.
ap2 = tk.plan({"intent": "unit.attack_class", "unit": 12, "delta": 1})
print("Barracks attack plan: %s | edits %d" % (ap2["description"], ap2["edit_count"]))
check("unit.attack_class on a Barracks plans 0 edits", ap2["edit_count"] == 0,
      ap2["edit_count"])
check("and its description says so, rather than promising 252",
      "没有" in ap2["description"] and ap2["description"] != "兵营 基础攻击 +1",
      ap2["description"])
try:
    C.compile_intent(tk.dat_path, {"intent": "unit.attack_class", "unit": 12,
                                   "delta": 1}, parsed=tk._parsed, stats=tk._stats)
    check("and the build still refuses it", False, "no error raised")
except C.IntentError as exc:
    print("  build refused as expected: %s" % exc)
    check("and the build still refuses it", True)

print()
print("=== E. the sentinel cost slot never reaches the user ===")
d = tk.describe(70, "unit")
print("House costs: %s | variants: %s" % (d["stats"]["costs"], d.get("variants")))
check("no 'type -1' leaks into describe()",
      all("type -1" not in str(c) for c in d["stats"]["costs"]),
      d["stats"]["costs"])
check("describe() reports the family it belongs to",
      sorted(d.get("variants") or []) == [191, 192, 463, 464, 465],
      d.get("variants"))

d2 = tk.describe(4, "unit")
print("Archer costs: %s | variants: %r" % (d2["stats"]["costs"],
                                               d2.get("variants")))
check("Archer has no age variants in describe()", not d2.get("variants"))
# An Archer really does pay population (that is the 1-population slot), so the
# expectation is all three slots, not just the two resources.
check("Archer costs are real (wood 25, gold 45, population 1)",
      sorted((c["resource"], c["amount"]) for c in d2["stats"]["costs"])
      == [("gold", 45), ("population", 1), ("wood", 25)], d2["stats"]["costs"])

print()
if FAIL:
    print("FAILED: %s" % FAIL)
    sys.exit(1)
print("ALL AGE-VARIANT CHECKS PASSED")
