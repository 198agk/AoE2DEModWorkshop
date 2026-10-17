# -*- coding: utf-8 -*-
"""Audit probe 8: .dat per-civ unit list -- correct name lookup first."""
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

head("8a: the 63 civ names as the .dat spells them")
print("   %r" % ([c.get("name") for c in civs],))
print("   civ[21] record keys:", sorted(civs[21]))

head("8b: per-civ 'units' list -- length, and does it contain 74 / 2550 / 83?")
print("   %-4s %-14s %-6s %-6s %-6s %-6s" % ("idx", "name", "n", "has74", "has2550", "has83"))
for i, c in enumerate(civs):
    u = c.get("units")
    ids = []
    if isinstance(u, list):
        for x in u:
            if isinstance(x, int):
                ids.append(x)
            elif isinstance(x, dict):
                ids.append(x.get("id"))
    print("   %-4d %-14s %-6s %-6s %-6s %-6s" % (i, c.get("name"), len(ids), 74 in ids, 2550 in ids, 83 in ids))

head("8c: is 'units' really a per-civ availability list, or a train-location list?")
c = civs[21]
u = c.get("units")
print("   civ[21] name=%r units[:6]=%s" % (c.get("name"), json.dumps(u[:6], ensure_ascii=False)[:500]))
print("   unit_pointers_total=%s len(units)=%s" % (c.get("unit_pointers_total"), len(u) if isinstance(u, list) else None))

head("8d: competing files on disk")
pats = [
    ("dat/*.dat", os.path.join(GAME, "resources", "_common", "dat", "*.dat")),
    ("dat/CivTechTrees/*.json", os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees", "*.json")),
    ("**/futuravailableunits.json", os.path.join(GAME, "**", "futuravailableunits.json")),
    ("**/CivTechTrees/BRITONS.json", os.path.join(GAME, "**", "CivTechTrees", "BRITONS.json")),
]
for label, p in pats:
    hits = glob.glob(p, recursive=True)
    print("   %-34s -> %d" % (label, len(hits)))
    for h in hits[:8]:
        print("        %10d B  %s" % (os.path.getsize(h), os.path.relpath(h, GAME)))

head("8e: BP.PANEL_REL and load_all ambiguity")
print("   BP.PANEL_REL =", getattr(BP, "PANEL_REL", None))
print("   BP upper consts:", [n for n in dir(BP) if n.isupper()])
allp = BP.load_all(GAME)
b = allp.get("Britons") or {}
print("   load_all civs=%d  Britons key=%r ambiguous=%r path=%s" % (len(allp), b.get("key"), b.get("ambiguous"), b.get("path")))
print("   sources=%s" % json.dumps(b.get("sources"), ensure_ascii=False)[:300])

head("8f: unitlines.json -- lines naming a Building, and the whole 74/2550 context")
o = json.load(open(os.path.join(GAME, "resources/_common/dat/unitlines.json"), encoding="utf-8-sig"))
for i, ln in enumerate(o["UnitLines"]):
    if isinstance(ln, dict) and ln.get("Building") is not None:
        print("   [%d] %s" % (i, json.dumps(ln, ensure_ascii=False)[:300]))
