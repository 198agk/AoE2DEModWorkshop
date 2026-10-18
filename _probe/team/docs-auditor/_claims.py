# -*- coding: utf-8 -*-
"""Consolidated re-measurement of doc numeric claims."""
import sys, io, os, json, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.getcwd()
G = r"d:\games\steam\steamapps\common\AoE2DE"

print("=== 1. icons.json ===")
ic = json.load(open(os.path.join(G, "widgetui", "icons.json"), encoding="utf-8-sig"))
print("segments:", len(ic), sorted(ic))
nonempty = 0
for k, v in ic.items():
    if isinstance(v, dict):
        nonempty += sum(1 for vv in v.values() if vv not in (None, "", "None"))
    elif isinstance(v, list):
        nonempty += sum(1 for vv in v if vv not in (None, "", "None"))
print("non-empty values:", nonempty)
for k, v in ic.items():
    n = len(v) if hasattr(v, "__len__") else 0
    ne = 0
    if isinstance(v, dict):
        ne = sum(1 for vv in v.values() if vv not in (None, "", "None"))
    print("   %-22s %4d  nonempty %4d" % (k, n, ne))

print("\n=== 2. materials overlap ===")
m1 = json.load(open(os.path.join(G, "widgetui", "materials.json"), encoding="utf-8-sig"))
mp = os.path.join(G, "modes", "Pompeii", "widgetui", "morematerials.json")
m2 = json.load(open(mp, encoding="utf-8-sig"))
def names(d):
    s = set()
    for e in d.get("Materials", []):
        md = e.get("MaterialDef") or {}
        if isinstance(md, dict) and md.get("Name"):
            s.add(md["Name"])
    return s
a, b = names(m1), names(m2)
print(" materials.json entries:", len(m1.get("Materials", [])), "names:", len(a))
print(" morematerials.json entries:", len(m2.get("Materials", [])), "names:", len(b))
print(" overlap:", len(a & b))

print("\n=== 3. .box font files ===")
bx = []
for dirpath, dirnames, filenames in os.walk(G):
    for f in filenames:
        if f.endswith(".box"):
            bx.append(os.path.join(dirpath, f))
print(" .box count:", len(bx))
for p in bx[:8]:
    print("   ", os.path.relpath(p, G), os.path.getsize(p))

print("\n=== 4. installed mods: do any ship sld/slp/smp ===")
prof = r"C:\Users\26913\Games\Age of Empires 2 DE"
hits = []
mpath = None
for acct in os.listdir(prof):
    p = os.path.join(prof, acct, "mods")
    if os.path.isdir(p):
        mpath = p
        break
print(" mods dir:", mpath)
mods = sorted(os.listdir(mpath)) if mpath else []
print(" mod folders:", len(mods))
for m in mods:
    exts = collections.Counter()
    for dp, dn, fn in os.walk(os.path.join(mpath, m)):
        for f in fn:
            exts[os.path.splitext(f)[1].lower()] += 1
    print("   %-60s %s" % (m[:58], dict(exts)))
