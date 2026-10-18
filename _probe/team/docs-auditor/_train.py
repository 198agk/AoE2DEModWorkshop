import sys, io, os, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Software\AI\帝国项目")
from aoe2mod.dat import parser as P
from aoe2mod.game import locations as LOC
g = LOC.find_game_root()
dat = os.path.join(g,"resources","_common","dat","empires2_x2_p1.dat")
raw, how = P.load_dat(dat)
d = P.Parser(raw).parse()
units = d["units"]
# train_locations of barracks building 12: units whose train locations include (12, ...)
train = collections.Counter()
maps = set()
for u in units:
    m = []
    for tl in (u.get("train_locations") or []):
        train[tl["building_id"]] += 1
        m.append((tl["building_id"], tl["button_id"]))
    maps.add(tuple(sorted(m)))
print("distinct train maps across unit records:", len(maps))
print("units trainable at building 12:", train.get(12))
print("distinct building ids in train_locations:", len(train))
