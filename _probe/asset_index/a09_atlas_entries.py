#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a09_atlas_entries.py -- dump the ingameunits / ingameicons / ingametechs /
ingamebuildings atlas entries to learn the RefName convention."""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
MAT = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui\materials.json"
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"

J = json.load(open(MAT, encoding="utf-8"))
atl = {}
for e in J["AtlasTextures"]:
    d = e.get("AtlasDef", e)
    atl[d["Name"]] = d

for name in ["ingameunits", "ingameicons", "ingametechs", "ingamebuildings"]:
    d = atl[name]
    print("=" * 78)
    print("ATLAS %s  MaxW=%s MaxH=%s Cached=%s  entries=%d"
          % (name, d.get("MaxWidth"), d.get("MaxHeight"), d.get("Cached"), len(d.get("Textures", []))))
    print("  non-Textures keys: %s" % [k for k in d.keys() if k != "Textures"])
    for k in ("SDSource", "UHDSource", "HDSource", "DefaultSource"):
        if k in d:
            print("  %-14s = %r" % (k, d[k]))
    ts = d.get("Textures", [])
    print("  --- first 12 entries ---")
    for t in ts[:12]:
        print("   ", json.dumps(t, ensure_ascii=False))
    print("  --- last 6 entries ---")
    for t in ts[-6:]:
        print("   ", json.dumps(t, ensure_ascii=False))
    # key union
    ku = collections.Counter()
    for t in ts:
        for k in t:
            ku[k] += 1
    print("  key frequency: %s" % dict(ku))
    # RefName-ish fields
    for f in ("RefName", "Name", "TextureName", "Source"):
        vals = [t.get(f) for t in ts if f in t]
        if vals:
            print("  %s: %d values, first 15 = %s" % (f, len(vals), vals[:15]))
