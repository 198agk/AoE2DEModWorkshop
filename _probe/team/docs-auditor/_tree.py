import sys, io, os, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\Software\AI\帝国项目")
from aoe2mod.game import civtechtrees as CT, locations as LOC
g = LOC.find_game_root()
trees = CT.load_trees(g)
t = trees["BRITONS"]
rows = CT.unit_rows(t)
print("BRITONS unit rows:", len(rows), " tech rows:", len(CT.tech_rows(t)))
print("sample row keys:", sorted(rows[0].keys())[:14])
b12 = [r for r in rows if r.get("Building ID")==12]
print("BRITONS barracks(12) tree rows:", len(b12))
for r in b12: print("   ", r.get("Node ID"), r.get("Name"), r.get("Status"), "Age", r.get("Age ID"))
print()
print("status_counts:", CT.status_counts(t))
