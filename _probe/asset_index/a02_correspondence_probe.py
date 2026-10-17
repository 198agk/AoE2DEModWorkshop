#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a02_correspondence_probe.py -- nail down the graphic -> .sld correspondence rule."""
import json
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE

G = json.load(open(os.path.join(OUT, "graphics_raw.json"), encoding="utf-8"))
INV = json.load(open(os.path.join(OUT, "sld_inventory.json"), encoding="utf-8"))

main = set(INV["graphics"])
pomp = set(INV["pompeii"])
small = set(INV["small_trees"])
allf = main | pomp | small
all_lower = {f.lower(): f for f in allf}
main_lower = {f.lower(): f for f in main}

print("graphics records : %d" % len(G))
print("sld on disk      : main=%d pomp=%d small=%d union=%d"
      % (len(main), len(pomp), len(small), len(allf)))

# ---- candidate rules -------------------------------------------------------
# R1: file field is verbatim the .sld filename
# R2: file field + ".sld"
# R3: name field is verbatim the .sld filename
# R4: name field + ".sld"
# R5: slp field == numeric part of filename? (test separately)
def count(pred):
    return sum(1 for g in G if pred(g))

rules = {
    "file == sld filename (verbatim)": lambda g: g["file"] in allf or g["file"].lower() in all_lower,
    "file + '.sld' == sld filename": lambda g: (g["file"] + ".sld").lower() in all_lower,
    "name == sld filename (verbatim)": lambda g: g["name"] in allf or g["name"].lower() in all_lower,
    "name + '.sld' == sld filename": lambda g: (g["name"] + ".sld").lower() in all_lower,
}
for k, f in rules.items():
    print("%-40s : %5d / %d" % (k, count(f), len(G)))

# ---- dig into what 'file' actually is --------------------------------------
sample = [g for g in G[:60]]
print("\nraw repr of first 20 file/name pairs:")
for g in G[1:21]:
    print("  slot=%-5d file=%-42r name=%r" % (g["slot"], g["file"], g["name"]))

# suffix histogram of the file field
suf = collections.Counter()
for g in G:
    f = g["file"]
    if not f:
        suf["<empty>"] += 1
    elif f.lower().endswith(".sld"):
        suf["ends .sld"] += 1
    elif f.lower().endswith("_x1") or f.lower().endswith("_x2"):
        suf["ends _x1/_x2 (no ext)"] += 1
    else:
        if "." in f:
            suf["other-with-dot: " + f.rsplit(".", 1)[1]] += 1
        else:
            suf["other-no-dot"] += 1
print("\nfile-field suffix histogram:")
for k, v in suf.most_common(20):
    print("   %-28s %d" % (k, v))

# name field suffix histogram
suf2 = collections.Counter()
for g in G:
    n = g["name"]
    if not n:
        suf2["<empty>"] += 1
    elif n.lower().endswith("_x1") or n.lower().endswith("_x2"):
        suf2["ends _x1/_x2"] += 1
    elif n.lower().endswith(".sld"):
        suf2["ends .sld"] += 1
    else:
        suf2["other"] += 1
print("name-field suffix histogram:")
for k, v in suf2.most_common(20):
    print("   %-28s %d" % (k, v))

# ---- strict test: file+'.sld' in disk set, case-insensitive ----------------
ok = 0
miss = []
for g in G:
    fn = g["file"]
    if fn and (fn + ".sld").lower() in all_lower:
        ok += 1
    elif fn:
        miss.append(g)
print("\nSTRICT file+'.sld' hit : %d ; miss with nonempty file: %d" % (ok, len(miss)))
print("miss examples (first 30):")
for g in miss[:30]:
    print("   slot=%-6d file=%-44r slp=%d" % (g["slot"], g["file"], g["slp"]))

# do misses end in _x2?
m2 = sum(1 for g in miss if g["file"].lower().endswith("_x2"))
print("misses ending _x2: %d ; ending _x1: %d"
      % (m2, sum(1 for g in miss if g["file"].lower().endswith("_x1"))))

# ---- empty-file graphics ---------------------------------------------------
empty = [g for g in G if not g["file"]]
print("\ngraphics with empty file field: %d" % len(empty))
print("  of those, empty name too: %d" % sum(1 for g in empty if not g["name"]))
print("  of those, slp == 0       : %d" % sum(1 for g in empty if g["slp"] == 0))
print("  of those, slp == -1      : %d" % sum(1 for g in empty if g["slp"] == -1))
print("  sample:", [(g["slot"], g["name"][:20], g["slp"]) for g in empty[:10]])

# ---- x1/x2 pairing check ---------------------------------------------------
x1 = [f for f in main if f.endswith("_x1.sld")]
x2 = [f for f in main if f.endswith("_x2.sld")]
print("\nmain x1=%d x2=%d ; x2 == x1 with suffix swapped: %d"
      % (len(x1), len(x2), sum(1 for f in x1 if f[:-6] + "x2.sld" in main)))
