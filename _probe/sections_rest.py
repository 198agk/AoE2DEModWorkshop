# -*- coding: utf-8 -*-
"""Resolve MapIcons / Notification / MenuIcons / StatIcons.

MapIcons values look like 'rm_arabia' -> likely maps.json's
map_icon_filename / mappool_icon_filename.  Check that link.
Read-only.
"""
import os
import json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WJ = os.path.join(GAME, "widgetui")
WR = os.path.join(GAME, "resources", "_common", "wpfg", "resources")

icons = json.load(open(os.path.join(WJ, "icons.json"), encoding="utf-8"))
maps = json.load(open(os.path.join(GAME, "resources", "_common", "dat",
                                   "maps.json"), encoding="utf-8"))

print("=== maps.json shape ===")
print("top keys:", list(maps.keys()))
ml = maps["map_list"]
print("map_list entries:", len(ml))
print("first entry keys:", list(ml[0].keys()))
print("first entry:", json.dumps(ml[0], indent=1)[:600])

mi = icons["MapIcons"]
vals = [v for v in mi.values() if isinstance(v, str) and v]
print()
print("=== MapIcons ===")
print("entries %d, non-empty %d, sample %s" % (len(mi), len(vals), vals[:5]))

# what are the actual filenames?
names = set()
for e in ml:
    for k in ("map_icon_filename", "mappool_icon_filename"):
        v = e.get(k)
        if isinstance(v, str) and v:
            names.add(v)
print("distinct icon filenames in maps.json:", len(names))
print("sample:", sorted(names)[:5])

# direct: does MapIcons value appear as a filename stem anywhere?
idx = {}
for base in (WR, os.path.join(WJ, "textures")):
    for b, subs, files in os.walk(base):
        for f in files:
            stem, ext = os.path.splitext(f)
            if ext.lower() in (".png", ".jpg", ".dds"):
                idx.setdefault(stem.lower(), []).append(
                    os.path.join(b, f).replace(GAME, "<GAME>"))
hit = [v for v in vals if v.lower() in idx]
print("MapIcons values found as a filename stem on disk: %d/%d"
      % (len(hit), len(vals)))
for v in vals[:3]:
    print("   %-24s -> %s" % (v, idx.get(v.lower(), "MISSING")[:2]))

# do maps.json filenames exist on disk?
ex = sum(1 for n in names if n.lower() in idx)
print("maps.json icon filenames found on disk: %d/%d" % (ex, len(names)))

print()
print("=== remainder: does the value exist in materials.json? ===")
mats = json.load(open(os.path.join(WJ, "materials.json"), encoding="utf-8"))
mn = set()
for m in mats["Materials"]:
    md = m.get("MaterialDef") or {}
    mn.add(md.get("Name"))
for sec in ("Notification", "MenuIcons", "StatIcons", "MapIcons"):
    vs = [v for k, v in icons[sec].items() if isinstance(v, str) and v]
    inmat = [v for v in vs if v in mn]
    ondisk = [v for v in vs if v.lower() in idx]
    print("%-13s %3d values  in Materials: %3d  as filename: %3d  sample=%s"
          % (sec, len(vs), len(inmat), len(ondisk), vs[:3]))
    if inmat[:2]:
        print("        material hit sample:", inmat[:2])
