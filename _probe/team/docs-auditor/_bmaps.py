import sys, io, os, collections, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Software\AI\帝国项目")
from aoe2mod.dat import parser as P, locate as L
from aoe2mod.game import locations as LOC
g = LOC.find_game_root()
raw, _ = P.load_dat(os.path.join(g,"resources","_common","dat","empires2_x2_p1.dat"))
with contextlib.redirect_stdout(io.StringIO()):
    civs, start, gv, end = L.locate(raw)
def bmap(c):
    m = collections.defaultdict(list)
    for u in c["units"]:
        for t in (u.get("train_locations") or []):
            b = t["unit_id"]
            if b and b > 0: m[b].append(u["id"])
    return {b: tuple(sorted(set(v))) for b, v in m.items()}
bmaps = [bmap(c) for c in civs]
sig = [tuple(sorted((b, v) for b, v in m.items())) for m in bmaps]
cnt = collections.Counter(sig)
print("distinct per-civ building->units maps:", len(cnt), "sizes:", sorted(cnt.values(), reverse=True)[:6])
for c, m in zip(civs, bmaps):
    if c["name"] == "British":
        print("British: barracks(12) trains %d distinct units" % len(m.get(12, ())))
        print("  ids:", m.get(12, ()))
        print("  distinct buildings with train entries:", len(m))
        break
# civ-invariance excluding civ-specific unit ids
print()
print("total unit records across civs:", sum(len(c["units"]) for c in civs))
