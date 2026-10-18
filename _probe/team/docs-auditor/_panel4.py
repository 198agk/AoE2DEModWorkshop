import sys, io, os, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\dat"
main = json.load(open(os.path.join(G,"futuravailableunits.json"), encoding="utf-8-sig"))
paph = json.load(open(os.path.join(G,"paphosfutureavailableunits.json"), encoding="utf-8-sig"))
allp = dict(main); allp.update(paph)
def blocks(c):
    b = c.get("Buildings") or []
    return {e["ID"]: e for e in b} if isinstance(b, list) else {}
def units_under(c, bid):
    bl = blocks(c)
    e = bl.get(bid)
    if not e: return []
    u = e.get("Units") or []
    return [x["ID"] for x in u] if u and isinstance(u[0], dict) else list(u)
named = {12:"barracks",68:"mill",70:"house",72:"palisade",562:"lumber",584:"mining",598:"outpost",792:"gate",236:"bombard",45:"dock"}
civs = [k for k in allp if k != "Gaia"]
print("civs (excl Gaia):", len(civs))
for bid,label in named.items():
    have = [k for k in civs if bid in units_under(allp[k],118)]
    print("  %-3d %-9s inside block 118: %d/%d civs" % (bid,label,len(have),len(civs)))
n118 = [k for k in civs if 118 in blocks(allp[k])]
print("civs with a 118 block:", len(n118), "/", len(civs))
# building rows in tree = 29?
import sys as _s; _s.path.insert(0, r"D:\Software\AI\帝国项目")
from aoe2mod.game import civtechtrees as CT, locations as LOC
trees = CT.load_trees(LOC.find_game_root())
t = trees["BRITONS"]
from aoe2mod.game import buildpanel as BP
print("tree building rows for BRITONS:", len({r.get("Building ID") for r in CT.unit_rows(t)}))
print("118 units count for Britons:", len(units_under(allp["Britons"],118)))
