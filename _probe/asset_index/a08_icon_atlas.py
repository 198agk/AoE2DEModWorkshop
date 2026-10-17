#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a08_icon_atlas.py -- inspect widgetui/materials.json atlases for icon mapping."""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
MAT = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui\materials.json"

J = json.load(open(MAT, encoding="utf-8"))
print("top keys:", list(J.keys()))
for k, v in J.items():
    if isinstance(v, list):
        print("  %-20s list[%d]" % (k, len(v)))
    elif isinstance(v, dict):
        print("  %-20s dict[%d]" % (k, len(v)))
    else:
        print("  %-20s %r" % (k, v))

# atlas defs
print("\n--- AtlasTextures entries ---")
for i, e in enumerate(J["AtlasTextures"][:60]):
    d = e.get("AtlasDef", e)
    print("  %2d keys=%s Name=%r Tex=%s" % (i, list(d.keys())[:8], d.get("Name"), len(d.get("Textures", []) or [])))

print("\n--- Materials entries, first 5 ---")
for e in J["Materials"][:5]:
    d = e.get("MaterialDef", e)
    print(json.dumps(d, ensure_ascii=False)[:600])
    print("  ---")

# find materials whose name mentions ingameunits / ingametechs
names = []
for e in J["Materials"]:
    d = e.get("MaterialDef", e)
    names.append(d.get("Name", ""))
c = collections.Counter(names)
print("\nmaterials named 'ingame*':")
for n in sorted(set(n for n in names if n.lower().startswith("ingame"))):
    print("   %-28s x%d" % (n, c[n]))
