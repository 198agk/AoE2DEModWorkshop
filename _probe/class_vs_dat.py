"""Does effect B / packed-armour-class use the label NUMBER or the list POSITION?

The vendored armor_classes.json was built by `enumerate(class_names)`, and
AGE's list literally starts with a sentinel ("No Class/Invalid Class") followed
by "0 - Archer".  So the file says CLASSES["0"] == "No Class" and
CLASSES["1"] == "Archer".

Ground truth that needs no table at all: the .dat's OWN unit `Class` field.
Archer is unit 4 and its Class field is a number; "C-Bonus, Archers +20% HP"
targets B=<that number>.  If they agree, the stored value is a VALUE and the
table must be keyed by the label's own number.

Also checks the packed attribute 8/9 high byte against the armour class ids the
unit actually carries, which is a different list in AoE2.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(HERE, "datparse")]

import json                                          # noqa: E402
from aoe2mod import api as A                          # noqa: E402
from aoe2mod.dat import locate as L                   # noqa: E402

SCHEMA = os.path.join(ROOT, "aoe2mod", "schema")
CLASSES = json.load(open(os.path.join(SCHEMA, "armor_classes.json"),
                         encoding="utf-8"))["classes"]

tk = A.open_toolkit()
tk._ensure()
civs = tk._civs

# ---- 1. what Class does the dat give each of these units? -------------------
NAMES = ["Archer", "Militia", "Knight", "Monk", "Galley", "Spearman",
         "Skirmisher", "Scout Cavalry", "Villager", "Trade Cart", "War Elephant",
         "Camel Rider", "Hand Cannoneer", "Petard", "Trebuchet", "Battering Ram"]
ix = A.__dict__ and None
from aoe2mod.semantic import index as semantic        # noqa: E402
six = semantic.index()

print("=== the dat's own Class field per unit ===")
seen = {}
for name in NAMES:
    try:
        ent = six.resolve_one("unit", name)
    except Exception as exc:                          # noqa: BLE001
        print("  %-16s (no unit)  %s" % (name, exc))
        continue
    hits = L.find_units(civs, ent.id) if hasattr(L, "find_units") else None
    if not hits:
        continue
    cls = None
    for h in hits:
        u = h[-1]                       # find_units yields (civ, ?, unit)
        if "class" in u:
            cls = u["class"]
            break
    seen[name] = cls
    print("  %-16s id=%-6d dat Class=%s    CLASSES[%r]=%r"
          % (name, ent.id, cls, str(cls),
             CLASSES.get(str(cls)) if cls is not None else None))

# ---- 2. the tech names that state their own target --------------------------
effs, _ = L.locate_effects(tk._raw)
techs = L.locate_techs(tk._raw, tk._parsed[4], tk._parsed[3])
bmap = {}
for t in techs:
    eid = t.get("effect_id")
    if eid is None or eid < 0 or eid >= len(effs):
        continue
    for c in effs[eid]["commands"]:
        if c["type"] in (0, 4, 5) and c["b"] is not None and c["b"] != -1:
            bmap.setdefault(c["b"], set()).add(t.get("name") or "")

print()
print("=== does B equal the dat's Class for the unit the tech names? ===")
PAIRS = [("Archer", ["+1 Archer range", "Archers +20% HP", "Archer range"]),
         ("Militia", ["Infantry Cost", "Infantry"]),
         ("Monk", ["+5 monk HP", "Monk armor"]),
         ("Galley", ["Ships +20% HP", "Warship cost"]),
         ("Spearman", ["Spearman", "Pikeman"]),
         ("Villager", ["Villager regeneration"]),
         ("War Elephant", ["War Elephant armor"]),
         ("Hand Cannoneer", ["Gunpowder armor", "Gunpowder units"])]
for unit, keys in PAIRS:
    want = seen.get(unit)
    found = {}
    for b, names in bmap.items():
        for nm in names:
            if any(k.lower() in nm.lower() for k in keys):
                found.setdefault(b, []).append(nm)
    top = sorted(found.items(), key=lambda kv: -len(kv[1]))[:4]
    print("  %-15s dat Class=%-4s  B used: %s" % (
        unit, want,
        "; ".join("B=%-4d [%s] %s" % (b, CLASSES.get(str(b)) or "MISSING",
                                     "; ".join(sorted(n)[:2])[:52])
                  for b, n in top)))

print()
print("=== control: what the file currently says for the well-known ids ===")
for v in (0, 6, 12, 18, 22, 3, 4, 47, 36):
    print("  value %-3d -> file says %-26s | prefix-reading says %r"
          % (v, CLASSES.get(str(v)),
             next((lab for lab in CLASSES.values()
                   if lab.split(" - ", 1)[0] == str(v)), None)))
