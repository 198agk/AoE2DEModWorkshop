# -*- coding: utf-8 -*-
"""Audit probe 4: could any OTHER shipped file supply the Barracks menu entries
for Britons -- i.e. is the "tree vs panel" framing a false dichotomy?"""
import json, os, re, sys
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
D = os.path.join(GAME, "resources", "_common", "dat")


def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)


head("4a: every file under resources/_common/dat that mentions 2550 / 74 / 1350")
pat = re.compile(rb"2550")
pat74 = re.compile(rb"(?<![0-9])74(?![0-9])")
names = []
for root, _d, fs in os.walk(D):
    for f in fs:
        names.append(os.path.join(root, f))
print("   files scanned: %d" % len(names))
for p in sorted(names):
    try:
        raw = open(p, "rb").read()
    except OSError:
        continue
    a = bool(pat.search(raw))
    b = bool(pat74.search(raw))
    if a or b:
        print("   %-46s %9d B  2550=%s  74=%s"
              % (os.path.relpath(p, D), len(raw), a, b))

head("4b: do the small dat JSONs contain the ids as real keys?")
for n in ("linkedUnits.json", "linkedTechs.json", "unitlines.json",
          "sharedbuildings.json", "unitcategories.json"):
    p = os.path.join(D, n)
    if not os.path.isfile(p):
        print("   %-22s MISSING" % n); continue
    o = json.load(open(p, encoding="utf-8-sig"))
    s = json.dumps(o)
    print("   %-22s %7d B  top=%s" % (n, os.path.getsize(p),
                                      list(o)[:6] if isinstance(o, dict) else type(o).__name__))
    for probe in ("2550", "1350", "Champi Scout"):
        print("        contains %-13s %r" % (probe, probe in s))
    # does "74" appear as a VALUE anywhere
    found = []

    def walk(x, path="$"):
        if len(found) > 6:
            return
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, path + "." + str(k))
        elif isinstance(x, list):
            for i, v in enumerate(x[:50]):
                walk(v, path + "[%d]" % i)
        elif x == 74:
            found.append(path)
    walk(o)
    print("        exact value 74 at: %s" % (found[:7] or "none"))

head("4c: is there a per-civ or per-building menu JSON anywhere in the game tree?")
hits = []
for root, dirs, fs in os.walk(os.path.join(GAME, "resources")):
    dirs[:] = [d for d in dirs if d.lower() not in ("_common",)]
    for f in fs:
        fl = f.lower()
        if "availableunit" in fl or "buildpanel" in fl or fl == "futuravailableunits.json":
            hits.append(os.path.relpath(os.path.join(root, f), GAME))
for h in hits[:40]:
    print("   ", h)
print("   total: %d" % len(hits))

head("4d: the .dat itself -- does it carry a train location for 2550 at 12?")
import aoe2mod.api as A
tk = A.open_toolkit(); tk._ensure()
data, civs, civs_start, gv, tail, how = tk._parsed
print("   how=%s gv=%s civs=%d" % (how, gv, len(civs)))
for ci, c in enumerate(civs):
    if c.get("name", "").lower() in ("britons", "incas"):
        us = c.get("units", [])
        print("   civ[%d] %-10s unit records=%d" % (ci, c.get("name"), len(us)))
        for uid in (2550, 74, 83):
            l = [u for u in us if u.get("id") == uid]
            if l:
                u = l[0]
                print("      unit %-5d type=%-4s hp=%-6s name=%r"
                      % (uid, u.get("type"), u.get("hit_points"), u.get("name")))
