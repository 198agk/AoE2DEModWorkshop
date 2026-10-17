# -*- coding: utf-8 -*-
"""Earlier probe reported 'SPRITES 1 mod 3 files d1=3' but my last walk found 0
files under drs/graphics.  Which is right, and what is under drs/ at all?"""
import os

MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
PREFIXES = [
    "resources/_common/drs/graphics/",
    "resources/_common/drs/sounds/",
    "resources/_common/drs/",
]

found = {p: [] for p in PREFIXES}
allfiles = 0
for dp, dn, fn in os.walk(MODS):
    for f in fn:
        allfiles += 1
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, MODS).replace(os.sep, "/")
        # strip the local/ or subscribed/ first segment
        parts = rel.split("/", 2)
        rel2 = parts[2] if len(parts) > 2 else rel
        for pre in PREFIXES:
            if rel2.startswith(pre):
                found[pre].append((rel2, os.path.getsize(p)))

print("total files in mods tree: %d" % allfiles)
for pre in PREFIXES:
    rows = found[pre]
    print()
    print("%-40s %d file(s)" % (pre, len(rows)))
    for r in sorted(rows)[:30]:
        print("    %-70s %d B" % r)

print()
print("any .sld anywhere in the mods tree?")
n = 0
for dp, dn, fn in os.walk(MODS):
    for f in fn:
        if f.lower().endswith(".sld"):
            n += 1
            if n <= 10:
                print("    %s" % os.path.join(dp, f))
print("  .sld count: %d" % n)

print()
print("does the GAME tree ship any loose file under drs/ other than graphics/?")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
base = os.path.join(GAME, "resources", "_common", "drs")
for entry in sorted(os.listdir(base)):
    p = os.path.join(base, entry)
    if os.path.isdir(p):
        c = sum(len(f) for _, _, f in os.walk(p))
        print("  %-20s dir  %d files" % (entry, c))
    else:
        print("  %-20s file %d B" % (entry, os.path.getsize(p)))
