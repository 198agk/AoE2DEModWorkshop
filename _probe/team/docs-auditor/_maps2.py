import sys, io, os, collections, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Software\AI\帝国项目")
from aoe2mod.dat import parser as P, locate as L
from aoe2mod.game import locations as LOC
g = LOC.find_game_root()
raw, _ = P.load_dat(os.path.join(g,"resources","_common","dat","empires2_x2_p1.dat"))
with contextlib.redirect_stdout(io.StringIO()):
    civs, start, gv, end = L.locate(raw)
def trainmap(c):
    m = {}
    for u in c["units"]:
        tl = u.get("train_locations") or []
        ids = tuple(sorted(t["unit_id"] for t in tl if t["unit_id"] and t["unit_id"] > 0))
        if ids: m[u["id"]] = ids
    return m
maps = [trainmap(c) for c in civs]
uniq = collections.Counter()
for m in maps:
    uniq[tuple(sorted((k, v) for k, v in m.items()))] += 1
print("distinct per-civ train maps:", len(uniq), "-> sizes", sorted(uniq.values(), reverse=True)[:6])
# Barracks (building 12) units for each civ
for target in ("BRITONS", None):
    for c in civs:
        if target and c["name"].upper() != target: continue
        m = trainmap(c)
        b = m.get(12, ())
        print("%-14s building12 trains %d units: %s" % (c["name"], len(b), b[:12]))
        break
# how many civs share the britons map
bri = [c["name"] for c in civs if c["name"].upper()=="BRITONS"]
if bri:
    bm = tuple(sorted(trainmap([c for c in civs if c["name"]==bri[0]][0]).items()))
    same = [c["name"] for c,m in zip(civs,maps) if tuple(sorted(m.items()))==bm]
    print("civs sharing BRITONS map:", len(same), same[:8])
