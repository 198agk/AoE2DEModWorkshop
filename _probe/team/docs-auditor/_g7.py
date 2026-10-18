import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from aoe2mod.game import locations as LOC, buildpanel as BP
P = BP.load_all(LOC.find_game_root())
obj = None
for pk, rec in P.items():
    if "Britons" in rec["obj"]: obj = rec["obj"]
bl = {x.get("ID"): x for x in BP.buildings(obj, "Britons")}
ten = [12,68,70,72,562,584,598,792,236,45]
print("Britons: is each of the 10 'missing everywhere' buildings a BLOCK?")
for b in ten:
    print("  %-4d block=%-5s name=%s" % (b, b in bl, (bl[b].get("Name") if b in bl else "-")))
print("\nall block ids for Britons:", sorted(bl))
