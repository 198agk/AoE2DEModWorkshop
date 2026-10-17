#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a12_icons_full.py -- full icon linkage + per-civ variance probe.

Establishes: unit IconID -> ingameunits atlas entry (by EMBEDDED NUMBER),
tech IconID -> ingametechs entry, building IconID -> ingamebuildings entry.
Also dumps techs_raw.json and answers: which unit fields actually differ per civ.
"""
import json, os, sys, collections, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import parse_dat as P

DAT = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"

C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
atl = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
mats = [e.get("MaterialDef", e) for e in J["Materials"]]
matnames = set(m.get("Name", "") for m in mats)


def emb_map(atlas_name):
    """number -> texture entry, using the embedded numeric stem."""
    out, weird = {}, []
    for t in atl[atlas_name]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1]
        stem = stem.rsplit(".", 1)[0]
        head = stem.split("_")[0]
        if head.isdigit():
            out[int(head)] = t
        else:
            weird.append(t)
    return out, weird


EMB_UNIT, weird_u = emb_map("ingameunits")
EMB_TECH, weird_t = emb_map("ingametechs")
EMB_BLD, weird_b = emb_map("ingamebuildings")
print("ingameunits    numeric entries=%d weird=%d" % (len(EMB_UNIT), len(weird_u)))
print("ingametechs    numeric entries=%d weird=%d %s"
      % (len(EMB_TECH), len(weird_t), [w["FileName"] for w in weird_t]))
print("ingamebuildings numeric entries=%d weird=%d %s"
      % (len(EMB_BLD), len(weird_b), [(w["RefName"], w["FileName"]) for w in weird_b]))

# ------------------------------------------------------------------ TECHES
data, how = P.load_dat(DAT)
st = P.Parser(data).parse()
techs = st["techs"]
print("\nparsed techs: %d  (leftover=%s)" % (len(techs), st.get("leftover")))
json.dump(techs, open(os.path.join(HERE, "techs_raw.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
tico = [t["icon_id"] for t in techs]
pos = [i for i in tico if i > 0]
print("tech icon_id: >0 %d  distinct %d  min=%d max=%d"
      % (len(pos), len(set(pos)), min(pos), max(pos)))
ok = sum(1 for i in set(pos) if i in EMB_TECH)
print("tech icon_id resolves in ingametechs (embedded number): %d / %d distinct"
      % (ok, len(set(pos))))
gap = sorted(i for i in set(pos) if i not in EMB_TECH)
print("tech icon ids NOT in atlas: %d -> %s" % (len(gap), gap[:40]))
# is the tech icon id ALSO a unit icon id? (shared icon namespace?)
uni = set(u["icon_id"] for c in C for u in c["units"] if u.get("icon_id", 0) > 0)
print("tech icon ids that are also unit icon ids: %d / %d" % (len(set(pos) & uni), len(set(pos))))
print("tech icon id range that overlaps unit icon ids 1..936: %d"
      % len([i for i in set(pos) if 1 <= i <= 936]))
# sample techs
print("\nsample tech icon resolutions (first 8 with icon>0):")
n = 0
for t in techs:
    if t["icon_id"] > 0 and n < 8:
        e = EMB_TECH.get(t["icon_id"])
        print("   civ%-3d %-22s icon=%-4d -> %s" % (t["civ"], t["name"][:22], t["icon_id"],
                                                    e["FileName"] if e else "MISS"))
        n += 1

# ---------------------------------------------------------------- BUILDINGS
print("\n--- building 'icon' note ---")
print("ingamebuildings RefName samples:",
      [t["RefName"] for t in atl["ingamebuildings"]["Textures"][:5]])

# --------------------------------------------------------- PER-CIV VARIANCE
print("\n--- per-civ variance of unit fields (which fields actually differ?) ---")
byid = {}
for ci, civ in enumerate(C):
    for u in civ["units"]:
        byid.setdefault(u["id"], {})[ci] = u
GFX = ["standing_1", "standing_2", "dying", "undead", "attack_graphic", "attack_graphic2",
       "garrison_graphic", "spawning_graphic", "upgrade_graphic", "hero_glow_graphic",
       "idle_attack_graphic", "special_graphic", "construction_graphic", "snow_graphic",
       "destruction_graphic", "destruction_rubble_graphic", "researching_graphic",
       "research_completed_graphic"]
shared = [uid for uid, d in byid.items() if len(d) == 63]
print("unit ids present in all 63 civs: %d" % len(shared))
diff_icon = sum(1 for uid in shared
                if len(set(byid[uid][c]["icon_id"] for c in byid[uid])) > 1)
diff_name = sum(1 for uid in shared
                if len(set(byid[uid][c]["name"] for c in byid[uid])) > 1)
diff_gfx = 0
diff_any = 0
for uid in shared:
    d = byid[uid]
    sigg = set()
    for c in d:
        sigg.add(tuple(d[c].get(f) for f in GFX))
    if len(sigg) > 1:
        diff_gfx += 1
    if len(sigg) > 1 or len(set(d[c]["icon_id"] for c in d)) > 1 or len(set(d[c]["name"] for c in d)) > 1:
        diff_any += 1
print("of those, graphic-ref set differs per civ: %d" % diff_gfx)
print("of those, icon_id differs per civ:         %d" % diff_icon)
print("of those, dat name differs per civ:        %d" % diff_name)
print("of those, ANY of the above differs:        %d" % diff_any)
if diff_name:
    ex = [uid for uid in shared if len(set(byid[uid][c]["name"] for c in byid[uid])) > 1][:5]
    for uid in ex:
        print("   id %d names: %s" % (uid, sorted(set(byid[uid][c]["name"] for c in byid[uid]))[:6]))
if diff_icon:
    ex = [uid for uid in shared if len(set(byid[uid][c]["icon_id"] for c in byid[uid])) > 1][:8]
    for uid in ex:
        print("   id %d icons: %s" % (uid, sorted(set(byid[uid][c]["icon_id"] for c in byid[uid]))))

# ------------------------------------------------- UNITS PRESENT IN ONE CIV
allids = set(byid)
print("\ndistinct unit ids overall: %d" % len(allids))
print("in 1 civ only: %d ; in 63: %d" % (sum(1 for u in allids if len(byid[u]) == 1), len(shared)))
cnt = collections.Counter(len(v) for v in byid.values())
print("civ-membership count histogram: %s" % dict(cnt))

# --------------------------------------------------------------- UNIT ICONS
print("\n--- unit icon coverage (all distinct unit ids, best civ) ---")
uicon = {uid: None for uid in allids}
for uid, d in byid.items():
    vals = set(d[c]["icon_id"] for c in d)
    uicon[uid] = vals
has = sum(1 for uid, v in uicon.items() if any(x > 0 for x in v))
res = sum(1 for uid, v in uicon.items() if any(x in EMB_UNIT for x in v if x > 0))
print("distinct unit ids: %d" % len(allids))
print("with any positive IconID in some civ: %d" % has)
print("resolving to an ingameunits entry:    %d" % res)
print("IconID<=0 everywhere (no icon):       %d" % (len(allids) - has))
bad = [uid for uid, v in uicon.items() if any(x > 0 for x in v) and not any(x in EMB_UNIT for x in v if x > 0)]
print("positive IconID that does NOT resolve: %d -> %s" % (len(bad), bad[:20]))

# IconID that varies per civ
vary = [uid for uid, v in uicon.items() if len(v) > 1]
print("unit ids whose IconID varies by civ: %d -> %s" % (len(vary), vary[:20]))
