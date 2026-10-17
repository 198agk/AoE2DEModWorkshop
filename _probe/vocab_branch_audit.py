"""Are AGE's vendored vocabulary tables the AOE2 branch, or another game's?

AGE_Frame/Lists.cpp builds `effect_attribute_names` and `class_names` by adding
entries inside mutually exclusive `if (GenieVersion < genie::GV_SWGB)` branches.
A generator that concatenates the raw Add list and then keys by enumerate() takes
BOTH branches.  This probe checks the result against the .dat itself.

Ground truth used here is the data's own tech names: a tech called
"C-Bonus, TC Wood cost" that multiplies attribute 104 tells us what 104 means
without any table at all.
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(HERE, "datparse")]

from aoe2mod import api as A                      # noqa: E402
from aoe2mod.dat import locate as L               # noqa: E402

SCHEMA = os.path.join(ROOT, "aoe2mod", "schema")
ATTRS = json.load(open(os.path.join(SCHEMA, "effect_attributes.json"),
                       encoding="utf-8"))["attributes"]

print("=== attribute ids named after the WRONG engine branch? ===")
# AGE lists these under `if (GenieVersion < GV_SWGB)` (the Star Wars / AoE1
# branch).  BASE is GV_C32 = 54, and 54 < 55, so AGE's own code takes the OTHER
# branch and calls 104 "Wood Costs".
SUSPECT = {101: "Train Time (types 70-80)",
           104: "Wood Costs (types 70-80)",
           105: "Gold Costs (types 70-80)",
           106: "Stone Costs (types 70-80)",
           19: "Enable Smart Projectiles (type 60)"}
for k, want in sorted(SUSPECT.items()):
    got = ATTRS.get(str(k))
    print("  attr %-4d vendored=%-28s DE branch says=%s  %s"
          % (k, got, want, "OK" if got == want else "MISMATCH"))

print()
print("=== what the dat says those attributes do ===")
tk = A.open_toolkit()
tk._ensure()
effs, _ = L.locate_effects(tk._raw)
techs = L.locate_techs(tk._raw, tk._parsed[4], tk._parsed[3])

for want in (104, 105, 106, 101):
    names = []
    for t in techs:
        eid = t.get("effect_id")
        if eid is None or eid < 0 or eid >= len(effs):
            continue
        for c in effs[eid]["commands"]:
            if c["type"] in (0, 4, 5) and c["c"] == want:
                nm = (t.get("name") or "")
                if nm not in names:
                    names.append(nm)
    print("  attr %-4d used by %d techs; first names: %s"
          % (want, len(names), names[:4]))

print()
print("=== class table: is the label aligned with the dat's class value? ===")
CLASSES = json.load(open(os.path.join(SCHEMA, "armor_classes.json"),
                         encoding="utf-8"))["classes"]
# AGE's class_names has `No Class/Invalid Class` at index 0, then the real list.
# If the generator enumerated the raw Add list correctly for DE, index i must
# hold the entry whose prefix number is i-1.
bad = 0
for i in range(1, 62):
    label = CLASSES.get(str(i))
    if label is None:
        continue
    prefix = label.split(" - ", 1)[0]
    try:
        p = int(prefix)
    except ValueError:
        continue
    if p != i - 1:
        bad += 1
        if bad <= 12:
            print("  index %-3d holds %-28s (prefix %d, expected %d)"
                  % (i, label, p, i - 1))
print("  misaligned entries in 1..61: %d" % bad)
print("  first entry: %r" % (CLASSES.get("0"),))
print("  entries 61..64 (unreachable for AoE2): %s"
      % [CLASSES.get(str(k)) for k in (61, 62, 63, 64)])
