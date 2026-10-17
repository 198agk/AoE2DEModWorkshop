#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a05_shorttoken_forensics.py -- what are the 1-char 'file' values (X/W/E/M/...)?
These are 4000+ graphics, so they matter for the coverage denominator."""
import json, os, collections, re

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "graphics_raw.json"), encoding="utf-8"))

short = [g for g in G if g["file"] and len(g["file"]) <= 2]
print("graphics with len(file)<=2 : %d" % len(short))
c = collections.Counter(g["file"] for g in short)
print("token histogram:", c.most_common(30))

for tok in ["X", "W", "E", "M", "F", "R", "B", "I"]:
    sub = [g for g in G if g["file"] == tok]
    if not sub:
        continue
    print("\n=== token %r : %d graphics ===" % (tok, len(sub)))
    print("  slots range: %d..%d" % (min(g["slot"] for g in sub), max(g["slot"] for g in sub)))
    print("  slp values  : %s" % sorted(set(g["slp"] for g in sub))[:12])
    print("  frame counts: %s" % sorted(set(g["frame_count"] for g in sub))[:12])
    print("  names sample: %s" % [g["name"] for g in sub[:6]])
    print("  particle    : %s" % [g["particle_effect"] for g in sub[:4]])
    print("  sample records:")
    for g in sub[:3]:
        print("     slot=%-6d name=%-28r slp=%-6d fc=%-4d ac=%-3d layer=%s id=%s"
              % (g["slot"], g["name"], g["slp"], g["frame_count"], g["angle_count"],
                 g["layer"], g["id"]))

# Are ALL short-token graphics in a particular slot neighborhood / all identical?
print("\n--- full token list by frequency (tokens with len<=3) ---")
c3 = collections.Counter(g["file"] for g in G if g["file"] and len(g["file"]) <= 3)
for k, v in c3.most_common(40):
    print("   %-10r %d" % (k, v))

# check marker values recorded? not in dump; check particle_effect field usage
print("\n--- particle_effect nonempty count: %d ---" % sum(1 for g in G if g["particle_effect"]))
pe = collections.Counter(g["particle_effect"] for g in G if g["particle_effect"])
print("  top particle effects:", pe.most_common(10))
