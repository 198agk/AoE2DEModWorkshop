# -*- coding: utf-8 -*-
"""Pin the exact shipped relationship between each displayed_* field and the raw
entry the damage maths actually reads.

displayed_pierce_armour is NOT in the Type50 block -- it is the last field of the
Creatable block -- so it needs its own comparison.
"""
import sys
from collections import Counter
root = r"D:\Software\DeepSeek Harness\工作区2"
sys.path.insert(0, root)
from aoe2mod import api as A

tk = A.open_toolkit()
tk.version
civs = tk._civs

seen = set()
rows = []
for u in (u for c in civs for u in c["units"]):
    key = (u["id"], u.get("name"))
    if key in seen:
        continue
    seen.add(key)
    t50 = u.get("type50") or {}

    def raw(entries, cls):
        for entry in entries:
            if entry["class"] == cls:
                return entry["amount"]
        return None

    rows.append({
        "id": u["id"], "name": u.get("name"),
        "da": t50.get("displayed_attack"),
        "dma": t50.get("displayed_melee_armour"),
        "dpa": u.get("displayed_pierce_armour"),
        "a3": raw(t50.get("attacks") or [], 3),
        "a4": raw(t50.get("attacks") or [], 4),
        "m4": raw(t50.get("armors") or [], 4),
        "p3": raw(t50.get("armors") or [], 3),
    })

print("distinct units:", len(rows))
print()

def report(label, disp, raw_key, cover=None):
    eq = ne = missing = disp_none = 0
    ex = []
    for r in rows:
        d, v = r[disp], r[raw_key]
        if cover and not cover(r):
            continue
        if d is None:
            disp_none += 1
            continue
        if v is None:
            missing += 1
        elif d == v:
            eq += 1
        else:
            ne += 1
            if len(ex) < 10:
                ex.append((r["id"], r["name"], d, v))
    tot = eq + ne
    pct = (100.0 * eq / tot) if tot else 0.0
    print("%-30s vs %-4s  equal %-5d different %-4d (%.1f%% agree)  no raw entry %-5d  displayed-absent %d"
          % (label, raw_key, eq, ne, pct, missing, disp_none))
    for e in ex:
        print("      id %-6s %-30s displayed=%-6s raw=%s" % e)

# displayed_attack mirrors whichever of class 3 / 4 is the unit's real base
def has_atk(r):
    return (r["a3"] not in (None, 0)) or (r["a4"] not in (None, 0))

report("displayed_attack", "da", "a3", cover=lambda r: has_atk(r) and r["a3"] not in (None, 0))
report("displayed_attack", "da", "a4", cover=lambda r: has_atk(r) and r["a4"] not in (None, 0))
report("displayed_melee_armour", "dma", "m4", cover=lambda r: r["m4"] is not None)
report("displayed_pierce_armour", "dpa", "p3", cover=lambda r: r["p3"] is not None)

print()
print("Units where displayed_attack agrees with whichever base entry is nonzero:")
both = agree = diverge = 0
for r in rows:
    if r["da"] is None:
        continue
    cands = [v for v in (r["a3"], r["a4"]) if v not in (None, 0)]
    if not cands:
        continue
    both += 1
    if r["da"] in cands:
        agree += 1
    else:
        diverge += 1
print("   comparable %d | agrees %d | diverges %d" % (both, agree, diverge))
