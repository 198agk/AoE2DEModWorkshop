import sys, io, os, json, glob, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\dat"
main = json.load(open(os.path.join(G,"futuravailableunits.json"), encoding="utf-8-sig"))
paph = json.load(open(os.path.join(G,"paphosfutureavailableunits.json"), encoding="utf-8-sig"))
allp = dict(main); allp.update(paph)
print("total civs across both panels:", len(allp))
def bids(c):
    b = c.get("Buildings") or []
    return [e.get("ID") for e in b] if isinstance(b, list) else [int(k) for k in b]
n118 = sum(1 for c in allp.values() if 118 in bids(c))
print("civs WITH building 118 block:", n118, "/", len(allp))
missing = [k for k,c in allp.items() if 118 not in bids(c)]
print("civs WITHOUT 118:", missing)
# the 10 named buildings presence anywhere in a civ's panel
named = {12:"兵营",68:"磨坊",70:"房屋",72:"木栅栏",562:"伐木场",584:"采矿场",598:"哨站",792:"木城门",236:"炮塔",45:"船坞"}
for bid, label in named.items():
    cnt = sum(1 for c in allp.values() if bid in bids(c))
    print("  building %-3d %-6s appears in %d/%d civ panels" % (bid, label, cnt, len(allp)))
# how many civs have ALL 10 missing
all10 = [k for k,c in allp.items() if not any(b in bids(c) for b in named)]
print("civs where NONE of the 10 named appear:", len(all10))
