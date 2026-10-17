#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a10_icon_link.py -- test whether unit.IconID indexes the 'ingameunits' atlas."""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
MAT = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui\materials.json"
J = json.load(open(MAT, encoding="utf-8"))
atl = {}
for e in J["AtlasTextures"]:
    d = e.get("AtlasDef", e)
    atl[d["Name"]] = d
mats = [e.get("MaterialDef", e) for e in J["Materials"]]
mnames = [m.get("Name", "") for m in mats]

# ---- what do icon ids look like? ----------------------------------------
allu = [u for c in C for u in c["units"]]
ico = [u["icon_id"] for u in allu if u.get("icon_id", 0) > 0]
print("units total=%d  icon_id>0: %d  distinct: %d  min=%d max=%d"
      % (len(allu), len(ico), len(set(ico)), min(ico), max(ico)))
print("icon_id>0 histogram head:", collections.Counter(ico).most_common(8))
print("count of distinct icon ids <= 793: %d" % len(set(i for i in ico if i <= 793)))

# ---- Materials whose name looks like an icon material -------------------
for pref in ["UnitIcons", "TechIcons", "BuildingIcons", "StatIcons", "Icons"]:
    hits = [n for n in mnames if n.startswith(pref)]
    print("\n%-14s materials: %d  first 10 = %s" % (pref, len(hits), sorted(hits)[:10]))

# ---- ingameunits atlas: decompose RefName / FileName --------------------
ts = atl["ingameunits"]["Textures"]
stems = [t["FileName"].rsplit("/", 1)[-1][:-4] for t in ts]
print("\ningameunits stems (first 10): %s" % stems[:10])
print("ingameunits stems (last 10) : %s" % stems[-10:])
L = collections.Counter(len(s.split("_")[0]) for s in stems)
print("leading-numeric width histogram: %s" % dict(L))
lead = [s.split("_")[0] for s in stems]
print("leading numbers: first 12=%s last 12=%s" % (lead[:12], lead[-12:]))
print("leading numbers distinct=%d min=%s max=%s" % (len(set(lead)), min(int(x) for x in lead), max(int(x) for x in lead)))
suf = collections.Counter(s.split("_", 1)[1] if "_" in s else "" for s in stems)
print("suffix (after first _): %s" % suf.most_common(10))

# ---- hypothesis A: icon_id == position in ingameunits Textures array ----
print("\n--- HYPOTHESIS A: icon_id indexes ingameunits.Textures in order ---")
byname = {}
for c in C[:1]:
    pass
# use Gaia? no. Use civ1 (British) which has 2164 units
civ = C[1]
samp = []
for uid in [4, 8, 38, 74, 83, 93, 448, 125, 280, 82, 23, 12, 70, 101]:
    u = next((x for x in civ["units"] if x["id"] == uid), None)
    if u:
        i = u.get("icon_id", 0)
        ent = ts[i] if 0 <= i < len(ts) else None
        samp.append((uid, u["name"], i, ent["RefName"] if ent else None,
                     ent["FileName"] if ent else None))
for s in samp:
    print("   unit %-5d %-34s icon=%-5s -> %s" % (s[0], s[1][:34], s[2], s[4]))

# ---- hypothesis B: RefName is UnitIcons<iconid><suffix> -----------------
print("\n--- HYPOTHESIS B: RefName contains zero-padded icon id ---")
byref = {}
for i, t in enumerate(ts):
    byref[t["RefName"]] = i
pref = collections.Counter(t["RefName"][:len("UnitIcons")] for t in ts)
print("RefName prefix check:", pref.most_common(3))
nums = []
for t in ts:
    r = t["RefName"]
    if r.startswith("UnitIcons"):
        nums.append(r[len("UnitIcons"):])
print("Remainder after 'UnitIcons': first 6 = %s" % nums[:6])
