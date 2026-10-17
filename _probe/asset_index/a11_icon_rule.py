#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a11_icon_rule.py -- discriminate the two candidate icon rules:
   R-index : icon_id == index into ingameunits.Textures[]
   R-embed : icon_id == the zero-padded number embedded in RefName/FileName
Only R-embed survives icon ids > 793, so test on those.
Also: what is a 'UnitIconsXXX' Material and how does it relate?
"""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
J = json.load(open(r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui\materials.json", encoding="utf-8"))
atl = {}
for e in J["AtlasTextures"]:
    d = e.get("AtlasDef", e)
    atl[d["Name"]] = d
mats = [e.get("MaterialDef", e) for e in J["Materials"]]

ts = atl["ingameunits"]["Textures"]
by_index = {i: t for i, t in enumerate(ts)}
by_embed = {}
for t in ts:
    num = int(t["FileName"].rsplit("/", 1)[-1].split("_")[0])
    by_embed[num] = t
print("ingameunits: entries=%d  embedded numbers=%d  min=%d max=%d"
      % (len(ts), len(by_embed), min(by_embed), max(by_embed)))
missing = sorted(set(range(0, 937)) - set(by_embed))
print("embedded numbers NOT present in 0..936: %d -> %s" % (len(missing), missing))

allu = [u for c in C for u in c["units"]]
ids = sorted(set(u["icon_id"] for u in allu if u.get("icon_id", 0) > 0))
print("\ndistinct positive icon ids: %d  range %d..%d" % (len(ids), min(ids), max(ids)))
hi = [i for i in ids if i > 793]
print("icon ids > 793: %d -> %s" % (len(hi), hi))

print("\n--- R-index  (icon_id -> Textures[icon_id]) ---")
ok_r = sum(1 for i in ids if i in by_index)
print("   resolves %d / %d distinct ids" % (ok_r, len(ids)))
print("--- R-embed  (icon_id -> entry whose number == icon_id) ---")
ok_e = sum(1 for i in ids if i in by_embed)
print("   resolves %d / %d distinct ids" % (ok_e, len(ids)))

for i in hi:
    print("   icon_id=%-5d R-index=%s  R-embed=%s"
          % (i, (by_index[i]["FileName"].rsplit("/", 1)[-1] if i in by_index else None),
             (by_embed[i]["FileName"].rsplit("/", 1)[-1] if i in by_embed else None)))

# ---- are R-index and R-embed the SAME for ids <= 793? -------------------
same = sum(1 for i in ids if i <= 793 and i in by_index and i in by_embed
           and by_index[i] is by_embed[i])
n_both = sum(1 for i in ids if i <= 793 and i in by_index and i in by_embed)
print("\nfor ids<=793 present in both: %d ; identical entry: %d" % (n_both, same))

# ---- UnitIconsXXX Material entries --------------------------------------
um = [m for m in mats if m.get("Name", "").startswith("UnitIcons")]
print("\nUnitIcons* Materials: %d" % len(um))
print("sample:", json.dumps(um[0], ensure_ascii=False))
print("        ", json.dumps(um[20], ensure_ascii=False))
# do the material names match atlas RefNames exactly?
refset = set(t["RefName"] for t in ts)
mn = set(m["Name"] for m in um)
print("material names == atlas RefNames: %d / %d" % (len(mn & refset), len(mn)))
print("materials not in atlas:", sorted(mn - refset)[:10])

# ---- tech icons ----------------------------------------------------------
ttech = atl["ingametechs"]["Textures"]
by_te = {}
for t in ttech:
    nm = t["FileName"].rsplit("/", 1)[-1][:-4]     # e.g. 000_crop_rotation
    try:
        by_te[int(nm.split("_")[0])] = t
    except ValueError:
        pass
print("\ningametechs: entries=%d numeric-stem=%d min=%d max=%d"
      % (len(ttech), len(by_te), min(by_te), max(by_te)))
TM = [m for m in mats if m.get("Name", "").startswith("TechIcons")]
print("TechIcons* Materials: %d" % len(TM))
print("sample tech material:", json.dumps(TM[0], ensure_ascii=False))

# ---- building icons ------------------------------------------------------
tb = atl["ingamebuildings"]["Textures"]
by_be = {}
for t in tb:
    nm = t["FileName"].rsplit("/", 1)[-1][:-4]
    by_be[int(nm.split("_")[0])] = t
print("\ningamebuildings: entries=%d numeric-stem=%d min=%d max=%d"
      % (len(tb), len(by_be), min(by_be), max(by_be)))
BM = [m for m in mats if m.get("Name", "").startswith("BuildingIcons")]
print("BuildingIcons* Materials: %d" % len(BM))
print("sample building material:", json.dumps(BM[0], ensure_ascii=False))
