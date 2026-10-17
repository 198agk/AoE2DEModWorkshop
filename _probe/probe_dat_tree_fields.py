"""Two dat-side per-civ signals nobody has measured yet.

1. `Civ.TechTreeID` (genieutils `Civ.h:50`, "ID of the technology tree for a
   civ").  British 254, French 258, Gaia 348.  The dat ships exactly ONE
   TechTree object, so if these ids are distinct per civ they must index
   something else -- and the obvious candidate is the `CivTechTrees/<STEM>.json`
   layer that our `unit.availability` intent writes.

2. The dat TechTree's `UnitConnection` records carry `Status` ("always 2"),
   `RequiredResearch` ("Upgrades unit"), and `EnablingResearch` ("Makes
   available.  Used by units, which need a research to be available").  Our
   parser reads and discards all three.  Their value distributions say whether
   they carry information or are decorative.
"""
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
import aoe2mod.dat.parser as P  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data, civs, civs_start, gv, tail, how = tk._parsed

print("=" * 72)
print("1. Civ.TechTreeID")
print("=" * 72)
ids = [(c["name"], c.get("tech_tree_id")) for c in civs]
vals = [v for _n, v in ids]
print("   distinct values : %d of %d civs" % (len(set(vals)), len(vals)))
print("   ordered per civ :")
for i in range(0, len(ids), 6):
    print("     " + "  ".join("%-14s=%-5s" % (n, v) for n, v in ids[i:i + 6]))
print("   min=%s max=%s" % (min(vals), max(vals)))

# Is TechTreeID an index into a file list?  Compare with sorted tree stems and
# with civilizations.json's own fields.
trees = CT.load_trees(tk.game_root)
stems = sorted(trees.keys())
print("   tree files on disk: %d" % len(stems))
print("   TechTreeID coincides with a sorted file index? %s"
      % [i for i, v in enumerate(vals) if 0 <= v < len(stems) and i == v][:8])

cj = os.path.join(tk.game_root, "resources", "_common", "dat", "civilizations.json")
with open(cj, "r", encoding="utf-8") as fh:
    cobj = json.load(fh)
clist = cobj.get("civilization_list", [])
print("   civilizations.json entries: %d" % len(clist))
if clist:
    print("   civilizations.json keys    : %s" % sorted(clist[0].keys()))
    for e in clist[:6]:
        print("     %-16s %s" % (str(e.get("internal_name"))[:16],
                                {k: v for k, v in e.items()
                                 if k not in ("internal_name",)}))

print()
print("=" * 72)
print("2. dat TechTree connections")
print("=" * 72)

# Re-walk the tech tree capturing the fields our parser throws away.
import aoe2mod.dat.parser as P2


class Cap(P.Reader):
    pass


r = P.Reader(data, gv=gv)
r.seek(tail)   # tail is the offset of the TechTree section
tt_ages = r.u8()
tt_bldgs = r.u8()
if r.gv >= P.GV_C32:
    tt_units = r.i16()
else:
    tt_units = r.u8()
if r.gv == P.GV_CCV2:
    tt_res = r.i16()
else:
    tt_res = r.u8()
groups = r.i32()
print("   counts: ages=%d buildings=%d units=%d research=%d groups=%d"
      % (tt_ages, tt_bldgs, tt_units, tt_res, groups))

age_status = []
for _ in range(tt_ages):
    r.i32(); age_status.append(r.u8())
    for _ in range(3):
        n = r.u8()
        if n:
            r.i32_array(n)
    r.i32(); r.i32_array(10); r.i32_array(10)
    r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()

b_stat, b_enab = [], []
for _ in range(tt_bldgs):
    r.i32(); b_stat.append(r.u8())
    for _ in range(3):
        n = r.u8()
        if n:
            r.i32_array(n)
    r.i32(); r.i32_array(10); r.i32_array(10)
    r.u8(); r.skip(5); r.skip(5); r.i32(); b_enab.append(r.i32())

u_ids, u_stat, u_up, u_req, u_enab = [], [], [], [], []
for _ in range(tt_units):
    u_ids.append(r.i32())
    u_stat.append(r.u8())
    u_up.append(r.i32())
    r.i32(); r.i32_array(10); r.i32_array(10)
    r.i32()
    n = r.u8()
    if n:
        r.i32_array(n)
    r.i32()
    u_req.append(r.i32())
    r.i32()
    u_enab.append(r.i32())

print("   age Status values          : %s" % Counter(age_status).most_common())
print("   building Status values     : %s" % Counter(b_stat).most_common())
print("   building EnablingResearch  : %s" % Counter(b_enab).most_common(6))
print("   unit Status values         : %s" % Counter(u_stat).most_common())
print("   unit RequiredResearch      : distinct %d, %s"
      % (len(set(u_req)), Counter(u_req).most_common(5)))
print("   unit EnablingResearch      : distinct %d, %s"
      % (len(set(u_enab)), Counter(u_enab).most_common(5)))
print("   unit UpperBuilding         : distinct %d" % len(set(u_up)))
print("   first 12 unit connections  :")
for i in range(min(12, len(u_ids))):
    print("     id=%-6d status=%-3d upper=%-6d required=%-6d enabling=%-6d"
          % (u_ids[i], u_stat[i], u_up[i], u_req[i], u_enab[i]))

print("   ids in the tree cover the units civs can build? %s"
      % ("see next probe"))

# Hand Cannoneer is the sharp test: the tree layer says 38 civs cannot have it.
print("   unit 5 (Hand Cannoneer) in the dat tree connections: %s"
      % (5 in u_ids))
print("   unit 21 (War Galley) in the dat tree connections  : %s"
      % (21 in u_ids))

# Does TechTreeID select an entry in civilizations.json's tech_tree_name?
if clist and len(clist) == len(civs):
    tt_names = [e.get("tech_tree_name") for e in clist]
    print()
    print("   civ order matches civilizations.json order? %s"
          % all(civs[i]["name"] for i in range(len(civs))))
    print("   tech_tree_name per civ (first 8): %s" % tt_names[:8])
    print("   tree file stems                 (first 8): %s" % stems[:8])
