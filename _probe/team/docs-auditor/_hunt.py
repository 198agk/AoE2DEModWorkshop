import sys, io, os, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Software\AI\帝国项目")
from aoe2mod.dat import parser as P
from aoe2mod.game import locations as LOC
g = LOC.find_game_root()
raw, how = P.load_dat(os.path.join(g,"resources","_common","dat","empires2_x2_p1.dat"))
d = P.Parser(raw).parse()
h = d["unit_headers"][0]
print("unit_header keys:", list(h.keys())[:40])
c0 = d["civs"][0]["units"][0]
print("civ unit keys:", list(c0.keys()))
# hunt for train_locations key
found = []
def walk(o, path="", depth=0):
    if depth > 4: return
    if isinstance(o, dict):
        for k,v in o.items():
            if "train" in k.lower(): found.append(path+"/"+k)
            walk(v, path+"/"+k, depth+1)
    elif isinstance(o, list) and o:
        walk(o[0], path+"[0]", depth+1)
walk(d)
print("train* keys:", sorted(set(found))[:20])
