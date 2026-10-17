# -*- coding: utf-8 -*-
"""RequiredAge of the ambiguous building ids, read from futuravailableunits.json.

Shape: {civ: {"Buildings": [ {"ID":..., "Name":..., "Units":[{"ID":..,"Name":..,
"RequiredAge":N,"PrereqTech":..}] } ] }}

If the House variants sit at RequiredAge 1/2/3/4, they are age swaps and an edit
that only touches id 70 silently reverts when the player ages up.
"""
import os
import json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
FAU = os.path.join(GAME, "resources", "_common", "dat", "futuravailableunits.json")
with open(FAU, encoding="utf-8") as f:
    d = json.load(f)

TARGETS = {
    "House":        [70, 191, 192, 463, 464, 465],
    "Barracks":     [12, 20, 132, 498],
    "Castle":       [82, 2418],
    "Town Center":  [71, 109, 141, 142, 481, 482, 483, 484],
    "Stable":       [86, 101, 153],
    "Archery Range": [10, 14, 87],
}
WANT = {i for ids in TARGETS.values() for i in ids}

# collect (civ, buildingName, unitID, unitName, RequiredAge, PrereqTech)
found = {}
for civ, blk in d.items():
    if not isinstance(blk, dict):
        continue
    for b in blk.get("Buildings", []) or []:
        for u in b.get("Units", []) or []:
            uid = u.get("ID")
            if uid in WANT:
                found.setdefault(uid, []).append(
                    (civ, u.get("Name"), u.get("RequiredAge"), u.get("PrereqTech")))

print("=== RequiredAge / PrereqTech per ambiguous building id ===")
for label, ids in TARGETS.items():
    print("-- %s" % label)
    for uid in ids:
        rows = found.get(uid, [])
        if not rows:
            print("   id %-6s (not listed as buildable anywhere)" % uid)
            continue
        ages = sorted({r[2] for r in rows if r[2] is not None})
        techs = sorted({r[3] for r in rows if r[3] is not None})
        names = sorted({r[1] for r in rows})
        print("   id %-6s civs %-3s ages=%-12s prereq=%-14s name=%s"
              % (uid, len(rows), ages, techs, names))
    print()

print("=== summary: do the House variants occupy distinct ages? ===")
for uid in TARGETS["House"]:
    print("   %-6s ages=%s" % (uid, sorted({r[2] for r in found.get(uid, [])})))
