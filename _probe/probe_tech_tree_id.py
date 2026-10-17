"""What is `civ.tech_tree_id`?  Every civ carries a distinct value (63 distinct
integers from 1 to 1460).  If it indexes a TECH, then a civ-owned tech's effect
is applied automatically -- which would be the dat-side lever for "this civ may
build this unit", and the clean place to add a grant.

Print, for a few civs, the tech at that index: its name, civ field, and whether
its effect carries a type-2 Enable Unit command.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
import aoe2mod.dat.locate as L  # noqa: E402
import aoe2mod.intent.compiler as C  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data, civs, _cs, gv, tail, _how = tk._parsed
techs = L.locate_techs(data, tail, gv)
effects, _ = L.locate_effects(data)

print("techs: %d   civs: %d" % (len(techs), len(civs)))
print()

# Which techs carry a type-2 enable, and for which unit?
enable_techs = {}
for ti, t in enumerate(techs):
    for r in C.effect_rows(effects, t, fanout=None, ix=None):
        if r["type"] == 2 and r["raw"][2] == 1:
            enable_techs.setdefault(r["raw"][1], []).append(ti)

# Known unique units and the tech index that enables them (from the previous run).
KNOWN = {8: 263, 41: 16, 755: 1, 692: 399, 725: None, 291: None}
print("=== civ.tech_tree_id vs the tech that enables its unique unit ===")
UNIQUE = {8: ("Longbowman", "British"), 41: ("Huskarl", "Goths"),
          755: ("Tarkan", "Huns"), 692: ("Berserk", "Vikings"),
          46: ("War Elephant", "Persians"), 282: ("Mameluke", "Saracens")}
for c in civs:
    eth = UNIQUE.get(next((u for u in UNIQUE
                           if u in [x["id"] for x in c["units"]]), None))
    pass
for uid, (label, owner) in UNIQUE.items():
    c = next(x for x in civs if x["name"] == owner)
    tid = c["tech_tree_id"]
    t = techs[tid] if 0 <= tid < len(techs) else None
    rows = C.effect_rows(effects, t, fanout=None, ix=None) if t else []
    en = [r["raw"][1] for r in rows if r["type"] == 2 and r["raw"][2] == 1]
    print("  %-13s (unit %-3d %-14s)  tech_tree_id=%-5d %s"
          % (owner, uid, label, tid,
             ("tech name=%r civ=%s enables=%s"
              % (t.get("name"), t.get("civ"), en)) if t else "OUT OF RANGE"))
print()

# Do tech_tree_id values point at techs whose effect enables that civ's units?
print("=== for EVERY civ: does tech_tree_id index a tech? ===")
in_range = 0
carries_enable = 0
for c in civs:
    tid = c["tech_tree_id"]
    if 0 <= tid < len(techs):
        in_range += 1
        rows = C.effect_rows(effects, techs[tid], fanout=None, ix=None)
        if any(r["type"] == 2 for r in rows):
            carries_enable += 1
print("  tech_tree_id inside the tech array : %d of %d" % (in_range, len(civs)))
print("  ...and that tech carries a type-2  : %d" % carries_enable)
print()
print("=== what does the tech at tech_tree_id look like, for 5 civs? ===")
for c in civs[:5]:
    tid = c["tech_tree_id"]
    t = techs[tid] if 0 <= tid < len(techs) else None
    print("  %-12s tree_id=%-5d %s" % (c["name"], tid,
                                       (t.get("name"), t.get("civ"),
                                        t.get("effect_id")) if t else None))
