"""Is futuravailableunits.json the real per-civ gate, or a stale artifact?

Athenians / Spartans / Thracians have NO key in futuravailableunits.json, yet
they are playable and their trees license Hoplite (2110) at Barracks 12.  The
product ships a SECOND cache: paphosfutureavailableunits.json (the "Paphos"
mode, i.e. Chronicles).  If those civs appear there, the cache file IS the
per-mode per-civ gate and "absent from the cache" is a real possibility.
"""
import json
import os

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(ROOT, "resources", "_common", "dat")

for name in ("futuravailableunits.json", "paphosfutureavailableunits.json"):
    p = os.path.join(DAT, name)
    if not os.path.exists(p):
        print("%s: MISSING" % name)
        continue
    obj = json.load(open(p, encoding="utf-8-sig"))
    keys = sorted(obj.keys())
    print("=== %s (%d B) ===" % (name, os.path.getsize(p)))
    print("   civ keys: %d" % len(keys))
    print("   %s" % keys)
    for want in ("Athenians", "Spartans", "Thracians", "Britons", "Incas", "Achaemenids",
                 "Macedonians", "Puru", "Shu", "Wei", "Wu"):
        got = [k for k in keys if k.upper() == want.upper()]
        print("      %-14s -> %s" % (want, got if got else "ABSENT"))
    # Hoplite
    for k in keys:
        for b in obj[k].get("Buildings", []):
            for e in b.get("Units", []):
                if e["ID"] in (2110, 2111) and k.upper() in ("ATHENIANS", "SPARTANS", "THRACIANS"):
                    print("      HOPLITE %s: civ=%s bldg=%s age=%s name=%s"
                          % (e["ID"], k, b["ID"], e.get("RequiredAge"), e.get("Name")))
    print()

print("=== the two cache files' Britons barracks blocks, side by side ===")
for name in ("futuravailableunits.json", "paphosfutureavailableunits.json"):
    p = os.path.join(DAT, name)
    obj = json.load(open(p, encoding="utf-8-sig"))
    for k in obj:
        if k.upper() == "BRITONS":
            blk = [b for b in obj[k]["Buildings"] if b["ID"] == 12]
            ids = [(e["ID"], e.get("Name")) for b in blk for e in b.get("Units", [])]
            print("   %-38s Britons bldg12 = %s" % (name, ids))
            break
    else:
        print("   %-38s no Britons key" % name)

print("\n=== which civs appear in a tree file but in NEITHER cache? ===")
TREES = os.path.join(DAT, "CivTechTrees")
stems = sorted(f[:-5] for f in os.listdir(TREES) if f.endswith(".json"))
norm = {}
for name in ("futuravailableunits.json", "paphosfutureavailableunits.json"):
    obj = json.load(open(os.path.join(DAT, name), encoding="utf-8-sig"))
    for k in obj:
        norm.setdefault(k.replace(" ", "").upper(), []).append((name, k))
orphan = [s for s in stems if s not in norm]
print("   tree stems: %d" % len(stems))
print("   in NO cache: %s" % orphan)
for s in orphan:
    print("      %-16s -> %s" % (s, norm.get(s, "ABSENT from both")))
print("\nDONE")
