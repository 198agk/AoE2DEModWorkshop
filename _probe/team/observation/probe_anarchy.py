"""IS THE CACHE THE LIVE BUTTON LIST, OR THE GREYED-PREVIEW LIST?

The Goths' Barracks Huskarl (759/761) sits in the TREE at building 12 with
Node Status ResearchRequired and Prerequisite Tech 16; the CACHE omits both.
If tech 16 is the Goths unique tech 'Anarchy', then the Barracks Huskarl is a
REAL in-game button the cache does not know about -> the cache is not the live
button list.

Also prints the Goths' full building-12 tree block so the tech rows are visible,
and the cache's PrereqTech usage.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json
import os
import sys

sys.path.insert(0, _HERE_PATH("..", "..", ".."))
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.dat import locate as L          # noqa: E402

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(ROOT, "resources", "_common", "dat")
TREES = os.path.join(DAT, "CivTechTrees")

blob, how = P.load_dat(os.path.join(DAT, "empires2_x2_p1.dat"))
p = P.Parser(blob)
p.parse()
civs, civs_start, gv, tail = L.locate(blob, parser=p)
techs = L.locate_techs(blob, tail, gv)
print("gv=%s  civs=%d  techs=%d" % (gv, len(civs), len(techs)))

WANT = {16: "?", 483: "?", 35: "?", 320: "?", 265: "?", 365: "?", 550: "?"}
for t in techs:
    tid = t.get("id")
    if tid in WANT:
        WANT[tid] = t.get("name")
for k, v in sorted(WANT.items()):
    print("    tech %-5d = %r" % (k, v))

print("\n=== GOTHS tree, Building ID 12 (barracks) — every row ===")
g = json.load(open(os.path.join(TREES, "GOTHS.json"), encoding="utf-8-sig"))
for r in g["civ_techs_units"]:
    if r.get("Building ID") == 12:
        print("    uid=%-6s %-18s %-20s %-16s age=%s prereq=%s"
              % (r.get("Node ID"), r.get("Name"), r.get("Node Type"),
                 r.get("Node Status"), r.get("Age ID"),
                 r.get("Prerequisite IDs")))
print("    --- building rows with Building ID 12 ---")
for r in g["civ_techs_buildings"]:
    if r.get("Building ID") == 12:
        print("    bid=%-6s %-18s %-16s" % (r.get("Node ID"), r.get("Name"),
                                           r.get("Node Status")))

print("\n=== GOTHS tree rows that ARE techs at the Castle (Anarchy?) ===")
for r in g["civ_techs_units"]:
    if r.get("Node Type") == "Research" and r.get("Building ID") in (12, 82):
        print("    %-18s uid=%-6s bldg=%-4s age=%s" % (r.get("Name"), r.get("Node ID"),
                                                       r.get("Building ID"), r.get("Age ID")))

print("\n=== cache: all PrereqTech values that appear, with the entry's name ===")
c = json.load(open(os.path.join(DAT, "futuravailableunits.json"), encoding="utf-8-sig"))
seen = {}
for civ, blk in c.items():
    for b in blk.get("Buildings", []):
        for e in b.get("Units", []):
            if e.get("PrereqTech"):
                seen.setdefault(e["PrereqTech"], []).append((civ, b["ID"], e["ID"], e.get("Name")))
print("    distinct PrereqTech values: %s" % sorted(seen))
for k in sorted(seen):
    print("    PrereqTech %-5s used %3d times, e.g. %s" % (k, len(seen[k]), seen[k][:3]))

print("\n=== GOTHS cache, buildings 12 and 82, verbatim ===")
for b in c["Goths"]["Buildings"]:
    if b["ID"] in (12, 82):
        print("    bldg %-4s %-10s units=%s" % (b["ID"], b.get("Name"),
              [(e["ID"], e.get("Name"), e.get("RequiredAge")) for e in b.get("Units", [])]))
print("\nDONE")
