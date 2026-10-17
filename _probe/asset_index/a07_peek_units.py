#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a07_peek_units.py -- inspect the captured unit->graphic references."""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
G = json.load(open(os.path.join(HERE, "graphics_raw.json"), encoding="utf-8"))
INV = json.load(open(os.path.join(HERE, "sld_inventory.json"), encoding="utf-8"))
ALL = set(INV["graphics"]) | set(INV["pompeii"]) | set(INV["small_trees"])
LOW = {f.lower() for f in ALL}
glyph = {g["slot"]: g for g in G}

print("civs=%d" % len(C))
g0 = C[0]
print("Gaia units=%d  civ1 %s units=%d" % (len(g0["units"]), C[1]["name"], len(C[1]["units"])))

KEYS = ["standing_1", "standing_2", "dying", "undead", "attack_graphic", "attack_graphic2",
        "garrison_graphic", "spawning_graphic", "upgrade_graphic", "hero_glow_graphic",
        "idle_attack_graphic", "special_graphic", "construction_graphic", "snow_graphic",
        "destruction_graphic", "destruction_rubble_graphic", "researching_graphic",
        "research_completed_graphic", "icon_id", "old_portrait_pict"]

# field presence + nonzero + resolvable
print("\n%-30s %8s %8s %8s %8s" % ("field", "present", "nonzero", "neg", "resolv"))
for k in KEYS:
    pres = nz = neg = res = 0
    for c in C:
        for u in c["units"]:
            v = u.get(k)
            if v is None:
                continue
            pres += 1
            if v != 0:
                nz += 1
            if v < 0:
                neg += 1
            if v > 0:
                gg = glyph.get(v)
                if gg and (gg["file"] + ".sld").lower() in LOW:
                    res += 1
    print("%-30s %8d %8d %8d %8d" % (k, pres, nz, neg, res))

# sample: find the Archer by name in a playable civ
def find(namepat, cividx=1):
    for u in C[cividx]["units"]:
        if namepat.lower() in u["name"].lower():
            return u
    return None

for nm in ["Archer", "Villager", "Knight", "Militia", "Town Center", "Barracks", "Castle", "Stable", "Monastery", "Skirmisher"]:
    u = find(nm)
    if not u:
        print("\n%s: NOT FOUND" % nm)
        continue
    print("\n=== %s  id=%d class=%d type=%d hp=%d icon=%d ==="
          % (u["name"], u["id"], u["class"], u["type"], u["hit_points"], u.get("icon_id", -99)))
    for k in KEYS:
        v = u.get(k)
        if v is None or v == 0:
            continue
        gg = glyph.get(v)
        if gg:
            f = gg["file"] + ".sld"
            print("   %-28s gid=%-6d -> file=%-46r exists=%s | name=%r"
                  % (k, v, gg["file"], f.lower() in LOW, gg["name"][:36]))
        else:
            print("   %-28s gid=%-6d -> <no such graphic slot>" % (k, v))
    if u.get("damage_graphics"):
        print("   damage_graphics: %s" % u["damage_graphics"][:6])

# How much does civ vary? compare British(1) vs Franks for a fixed id
print("\n--- per-civ variation of standing_1 for a few unit ids ---")
ids = [4, 8, 74, 83, 93]
byid = {}
for c in C[:4]:
    byid[c["name"]] = {u["id"]: u for u in c["units"]}
for uid in ids:
    row = []
    for nm, d in byid.items():
        u = d.get(uid)
        row.append("%s=%s" % (nm, u.get("standing_1") if u else "-"))
    print("   unit %-5d %s" % (uid, "  ".join(row)))
