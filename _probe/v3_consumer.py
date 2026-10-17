# -*- coding: utf-8 -*-
"""Which icons.json section / material drives the PLAYER-LIST emblem (V3)?

V3 = widgetui/textures/menu/civs/<civ>.png -> atlas defaultwidgets -> material
"<Civ>Icon" (e.g. BritonsIcon). Find who references those materials, and dump
every icons.json section with a sample value to see which one carries the V3 name.
"""
import os
import json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WJ = os.path.join(GAME, "widgetui")

with open(os.path.join(WJ, "icons.json"), "r", encoding="utf-8-sig") as f:
    ic = json.load(f)
print("icons.json top-level keys (%d):" % len(ic))
for k, v in ic.items():
    if isinstance(v, dict):
        items = list(v.items())[:3]
        print("  %-28s n=%-5d e.g. %s" % (k, len(v), items))
    else:
        print("  %-28s (%s) %r" % (k, type(v).__name__, str(v)[:60]))

print()
print("=== widgetui json referencing '<Civ>Icon' style material names ===")
probe = ["BritonsIcon", "CivIcon", "CivEmblem", "InGameCivEmblem", "UnitIcons",
         "IconBritons", "britons_icon", "CivIcons"]
for f in sorted(os.listdir(WJ)):
    if not f.endswith(".json"):
        continue
    p = os.path.join(WJ, f)
    try:
        with open(p, "r", encoding="utf-8-sig", errors="replace") as fh:
            txt = fh.read()
    except Exception:
        continue
    hits = {q: txt.count(q) for q in probe if q in txt}
    if hits:
        print("  %-42s %s" % (f, hits))

# does materials.json define a bare "CivIcon"/"CivEmblem"?
with open(os.path.join(WJ, "materials.json"), "r", encoding="utf-8-sig") as f:
    m = json.load(f)
names = {x["MaterialDef"]["Name"] for x in m["Materials"]}
print()
print("bare material names present?")
for q in ["CivIcon", "CivEmblem", "CivIcons", "InGameCivEmblem", "CivHero"]:
    print("   %-20s %s" % (q, q in names))

# every material whose name ends with "Icon" and comes from menu/civs
byreffile = {}
for a in m["AtlasTextures"]:
    for t in a["AtlasDef"].get("Textures", []):
        byreffile[t.get("RefName")] = t.get("FileName", "")
civicon = {md["Name"]: md for md in (x["MaterialDef"] for x in m["Materials"])
           if byreffile.get(md.get("TextureRef") or md.get("Name"), "").startswith("textures/menu/civs")}
print()
print("materials sourced from textures/menu/civs: n=%d" % len(civicon))
print("   names:", sorted(civicon)[:12], "...")
