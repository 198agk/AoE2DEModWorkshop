# -*- coding: utf-8 -*-
"""Audit probe 7: does the .dat ITSELF carry per-civ buildable-unit lists
(the civ record has 'units' / 'unit_pointers_total'), and are there competing
dat variants / CivTechTrees dirs / panel files?"""
import json, os, sys, glob
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import aoe2mod.api as A
from aoe2mod.game import buildpanel as BP

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)


tk = A.open_toolkit(); tk._ensure()
data, civs, civs_start, gv, tail, how = tk._parsed

head("7a: the .dat's PER-CIV unit list -- is availability in the .dat at all?")
bi = None
for i, c in enumerate(civs):
    if str(c.get("name")).upper().startswith("BRITON"):
        bi = i
print("   Britons civ index = %s name=%r" % (bi, civs[bi].get("name") if bi is not None else None))
c = civs[bi]
print("   civ record keys:", sorted(c))
u = c.get("units")
print("   units type=%s len=%s" % (type(u), len(u) if u is not None else None))
print("   unit_pointers_total =", c.get("unit_pointers_total"))
if isinstance(u, list) and u:
    print("   sample units entries:", json.dumps(u[:5], ensure_ascii=False)[:400])
    try:
        ids = [x if isinstance(x, int) else x.get("id") for x in u]
    except Exception as e:
        ids = None
        print("   (ids extract failed: %s)" % e)
    if ids is not None:
        print("   n ids=%d ; 74 in=%s ; 2550 in=%s ; 83 in=%s" % (len(ids), 74 in ids, 2550 in ids, 83 in ids))
        print("   first 40 ids:", ids[:40])

head("7b: competing .dat variants and CivTechTrees dirs on disk")
pats = [
    os.path.join(GAME, "resources", "_common", "dat", "*.dat"),
    os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees", "*.json"),
    os.path.join(GAME, "**", "futuravailableunits.json"),
    os.path.join(GAME, "**", "CivTechTrees", "BRITONS.json"),
]
for p in pats:
    hits = glob.glob(p, recursive=True)
    print("   %-70s -> %d" % (p.replace(GAME, "<GAME>"), len(hits)))
    for h in hits[:8]:
        print("        %8d B  %s" % (os.path.getsize(h), h.replace(GAME, "<GAME>")))

head("7c: any *.dlc / *.pkg / package dirs that could shadow loose JSON?")
for sub in ("resources", "resources/_common", "resources/_common/dat"):
    d = os.path.join(GAME, sub)
    if os.path.isdir(d):
        names = sorted(os.listdir(d))
        odd = [n for n in names if not n.endswith((".json", ".dat", ".txt", ".xml"))]
        print("   %-28s %d entries; non-json/dat names: %s" % (sub, len(names), odd[:12]))

head("7d: BP panel sources / ambiguity for Britons (is one file authoritative?)")
allp = BP.load_all(GAME)
print("   load_all -> %d civ keys" % len(allp))
b = allp.get("Britons")
if b:
    print("   key=%r ambiguous=%r" % (b.get("key"), b.get("ambiguous")))
    print("   sources=%s" % json.dumps(b.get("sources"), ensure_ascii=False)[:400])
    print("   path=%s" % b.get("path"))
print("   BP.PANEL_REL =", getattr(BP, "PANEL_REL", None))
print("   BP dir consts:", [n for n in dir(BP) if n.isupper()])

head("7e: unitlines.json lines that name a Building")
o = json.load(open(os.path.join(GAME, "resources/_common/dat/unitlines.json"), encoding="utf-8-sig"))
for i, ln in enumerate(o["UnitLines"]):
    if isinstance(ln, dict) and ln.get("Building") is not None:
        print("   [%d] %s" % (i, json.dumps(ln, ensure_ascii=False)[:300]))
