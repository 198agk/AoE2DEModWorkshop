"""Which named units actually carry a class-12 (cavalry) attack entry?

The gate case I wrote expected `步弓手对骑兵攻击加2` to build.  Python refuses it:
`对骑兵` sets class_id 12, and the archer has no class-12 entry.  A gate case has
to name a unit the binding can actually resolve.
"""
import os, sys, json, io
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import aoe2mod.dat.parser as P
import aoe2mod.dat.locate as L

GAME = r"d:\games\steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources/_common/dat/empires2_x2_p1.dat")
raw, _ = P.load_dat(DAT)
p = P.Parser(raw); p.parse()
civs, _, gv, _ = L.locate(raw, p)
names = json.load(io.open("_golden/entity_names.json", encoding="utf-8"))
units = names.get("units") or names

civ = civs[1]
hits = []
for u in civ["units"]:
    t50 = u.get("type50") or {}
    cls = {a["class"] for a in (t50.get("attacks") or [])}
    if 12 in cls:
        nm = (u.get("name") or "").strip()
        hits.append((u["id"], nm, sorted(cls)))
print("units with class-12 attack:", len(hits))
for h in hits[:25]:
    print("  ", h)
