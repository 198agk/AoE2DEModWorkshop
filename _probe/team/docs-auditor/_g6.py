import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from aoe2mod.game import civtechtrees as CT, locations as LOC, buildpanel as BP
T = CT.load_trees(LOC.find_game_root())
b = T["BRITONS"]
rows = CT.rows_of(b)
bid = [r for r in rows if r.get("Use Type") == "Building"]
print("BRITONS rows:", len(rows))
print("Use Type == Building rows:", len(bid))
print("distinct Node ID among them:", len({r["Node ID"] for r in bid}))
from collections import Counter
print("Use Type histogram:", Counter(r.get("Use Type") for r in rows))
P = BP.load_all(LOC.find_game_root())
print("panel files:", len(P))
obj = None
for pk, rec in P.items():
    if "Britons" in rec["obj"]: obj = rec["obj"]
bl = BP.buildings(obj, "Britons")
print("Britons blocks:", len(bl))
b118 = next(x for x in bl if x.get("ID")==118)
print("118 Units len:", len(b118.get("Units") or []))
tid = {r["Node ID"] for r in bid}
inb = [e["ID"] for e in (b118.get("Units") or [])]
print("118 entries in tree Building rows:", sum(1 for i in inb if i in tid), "of", len(inb))
notin = [i for i in inb if i not in tid]
print("118 entries NOT tree building rows:", notin)
print("tree Building ids not in 118:", sorted(tid - set(inb)))
