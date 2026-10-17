"""Tech ids are LIST INDICES (records carry no 'id' key). Resolve the ids that
matter, then state the Anarchy question precisely."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import sys

sys.path.insert(0, _HERE_PATH("..", "..", ".."))
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.dat import locate as L          # noqa: E402

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(ROOT, "resources", "_common", "dat")

blob, how = P.load_dat(os.path.join(DAT, "empires2_x2_p1.dat"))
p = P.Parser(blob)
p.parse()
civs, civs_start, gv, tail = L.locate(blob, parser=p)
techs = L.locate_techs(blob, tail, gv)

for i in (16, 35, 265, 320, 365, 483, 550):
    t = techs[i]
    print("    tech id %-5d = %-30r civ=%-4s loc=%s btn=%s time=%s"
          % (i, t["name"], t["civ"],
             [r["location_id"] for r in t["research_locations"]],
             [r["button_id"] for r in t["research_locations"]],
             [r["research_time"] for r in t["research_locations"]]))

print("\n--- every tech named *Anarchy* or *Perfusion* with its INDEX ---")
for i, t in enumerate(techs):
    if "Anarchy" in t["name"] or "Perfusion" in t["name"]:
        print("    index=%-6d %-24r civ=%s loc=%s"
              % (i, t["name"], t["civ"],
                 [r["location_id"] for r in t["research_locations"]]))

print("\n--- techs whose research_locations include building 12 (barracks) ---")
for i, t in enumerate(techs):
    locs = [r["location_id"] for r in t["research_locations"]]
    if 12 in locs:
        print("    index=%-6d %-30r civ=%s" % (i, t["name"], t["civ"]))
print("DONE")
