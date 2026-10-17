"""The .dat's OWN TechTree (parser stage 10) is a per-unit availability model
that lives entirely in the .dat -- which is what the user says the game reads.

    read_unit_connection():  ID, Status, UpperBuilding, common, VerticalLine,
                             <group>, LocationInAge, RequiredResearch, LineMode,
                             EnablingResearch

`RequiredResearch` / `EnablingResearch` are exactly "you cannot build this until
research X".  If this is the real gate, then the count of connections and the set
of ids it names should look like a civilization's buildable list.

Measure, do not assume:
  * the counts the parser recovered (ages / buildings / units / research)
  * how many unit connections carry a non-zero RequiredResearch or EnablingResearch
  * whether the civs' tech_tree_id values are even distinct (a per-civ gate needs
    more than one tree, or the id is not a tree selector)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.parser as P  # noqa: E402
from aoe2mod.dat.parser import load_dat  # noqa: E402

DAT = (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
       r"\empires2_x2_p1.dat")

data, how = load_dat(DAT)
p = P.Parser(data)
# The parser needs the stage-10 tail; run it all (it is ~5 s).
st = p.parse()

tt = st.get("tech_tree")
print("civs: %d" % st["civ_count"])
ids = [c["tech_tree_id"] for c in st["civs"]]
from collections import Counter
print("civ.tech_tree_id histogram: %s" % sorted(Counter(ids).items()))
print()
print("dat TechTree counts: ages %s buildings %s units %s research %s  "
      "groups %s"
      % (tt["ages"], tt["buildings"], tt["units"], tt["research"],
         tt["total_unit_tech_groups"]))
print()
print("dat TechTree keys: %s" % sorted(tt.keys()))
for k in ("unit_connections", "research_connections", "building_connections"):
    v = tt.get(k)
    if isinstance(v, list) and v:
        print("  %-22s n=%-5d sample %s" % (k, len(v), v[0]))
