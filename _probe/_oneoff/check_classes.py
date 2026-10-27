import sys
sys.path.insert(0, '.')
import aoe2mod.dat.parser as P
import aoe2mod.dat.locate as L
GAME = r"d:/games/steam/steamapps/common/AoE2DE"
raw, how = P.load_dat(GAME + "/resources/_common/dat/empires2_x2_p1.dat")
p = P.Parser(raw)
p.parse()
L.locate(raw, p)
units = p.stats["civs"]["civs"][1]["units"]
for uid in (74, 82, 4, 83):
    u = next(x for x in units if x["id"] == uid)
    t50 = u.get("type50") or {}
    print(uid, "attacks:", [(a["class"], a["amount"]) for a in (t50.get("attacks") or [])])
    print("   armors:", [(a["class"], a["amount"]) for a in (t50.get("armors") or [])])
