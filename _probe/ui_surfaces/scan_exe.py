"""Scan the game exe for the JSON/XAML file names the engine knows about.

Answers: which data files can a mod supply, and is there an additive
("more*") variant per file, as morematerials.json suggests?

Read-only. Prints a compact summary.
"""
import os
import re
import collections

G = r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(G, "AoE2DE_s.exe")

b = open(EXE, "rb").read()
print("exe size", len(b))

# generic *.json / *.xaml / *.dat references
json_re = re.compile(rb"[A-Za-z0-9_\-\./\\]{3,90}\.json")
xaml_re = re.compile(rb"[A-Za-z0-9_\-\./\\]{3,90}\.xaml")

def harvest(rx):
    c = collections.Counter()
    for m in rx.finditer(b):
        s = m.group().decode("latin-1").replace("\\", "/")
        c[s] += 1
    return c

jc = harvest(json_re)
xc = harvest(xaml_re)
print("distinct .json strings:", len(jc))
print("distinct .xaml strings:", len(xc))

print("\n=== 'more*' json references ===")
for s, n in sorted(jc.items()):
    if "more" in s.lower():
        print("   %-58s x%d" % (s, n))

print("\n=== bare-name json (no path separator) ===")
bare = {s: n for s, n in jc.items() if "/" not in s}
print("   count:", len(bare))
for s, n in sorted(bare.items())[:200]:
    print("   %-58s x%d" % (s, n))

print("\n=== path-qualified json ===")
q = {s: n for s, n in jc.items() if "/" in s}
for s, n in sorted(q.items())[:80]:
    print("   %-70s x%d" % (s, n))

print("\n=== storage_point_list occurrences in exe ===")
print("   ", b.count(b"storage_point_list"), b.count(b"use_modes_path_for_mods"))

print("\n=== 'modes' path references ===")
c = collections.Counter()
for m in re.finditer(rb"[A-Za-z0-9_\-\./\\]{3,70}modes[A-Za-z0-9_\-\./\\]{0,70}", b):
    c[m.group().decode("latin-1")] += 1
for s, n in sorted(c.items())[:40]:
    print("   %-70s x%d" % (s, n))

print("\n=== wpfg references ===")
print("   ", b.count(b"wpfg"), b.count(b"WPFG"), b.count(b".xaml"))

print("\n=== key-value-modded references ===")
print("   ", b.count(b"key-value-modded"), b.count(b"modded-strings"))
