# -*- coding: utf-8 -*-
"""Resolve the remaining icons.json sections to real on-disk files.

CivEmblem/InGameCivEmblem already resolved to wpfg/resources/civ_emblems.
This tries to resolve the other sections by trying candidate
"directory + stem" splits against the actual disk, then reports which
candidate directories exist at all.  Read-only.
"""
import os
import json
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WJ = os.path.join(GAME, "widgetui")
WPFG_RES = os.path.join(GAME, "resources", "_common", "wpfg", "resources")

icons = json.load(open(os.path.join(WJ, "icons.json"), encoding="utf-8"))

# every directory under wpfg/resources plus the widgetui texture tree
cands = []
for base in (WPFG_RES, os.path.join(WJ, "textures")):
    for b, subs, files in os.walk(base):
        if files:
            cands.append(b)

print("=== candidate asset directories ===")
for c in sorted(cands):
    n = len(os.listdir(c))
    print("%4d  %s" % (n, c.replace(GAME, "<GAME>")))
print()

index = {}   # lowercase stem (no ext) -> directory
for c in cands:
    for f in os.listdir(c):
        stem, ext = os.path.splitext(f)
        if ext.lower() in (".png", ".jpg", ".dds"):
            index.setdefault(stem.lower(), []).append(c)


def resolve(v):
    """Try every split of value by '_' into dirpart + stem, dirpart is
    a suffix of the token list.  Return hits as <dir>/<stem>."""
    toks = v.split("_")
    hits = []
    for k in range(1, len(toks) + 1):
        stem = "_".join(toks[len(toks) - k:])
        dirpart = "_".join(toks[:len(toks) - k])
        for c in index.get(stem.lower(), []):
            hits.append((dirpart, c.replace(GAME, "<GAME>"), stem))
    return hits


print("=== sections ===")
for sec, val in icons.items():
    if not isinstance(val, dict):
        continue
    sample = list(val.items())[:3]
    vals = [s[1] for s in sample if isinstance(s[1], str)]
    print("\n[%s] %d entries; sample values: %s" % (sec, len(val), vals))
    for v in vals[:2]:
        if not isinstance(v, str):
            continue
        h = resolve(v)
        if h:
            for dirpart, c, stem in h[:4]:
                print("    %-34s -> dir=%-22s %s" % (v, dirpart or "<none>", c))
        else:
            print("    %-34s -> UNRESOLVED" % v)
