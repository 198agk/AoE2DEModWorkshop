import sys, io, os, collections, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))
from aoe2mod.dat import parser as P, locate as L
from aoe2mod.game import locations as LOC
import os
g = LOC.find_game_root()
raw, how = P.load_dat(os.path.join(g,"resources","_common","dat","empires2_x2_p1.dat"))
with contextlib.redirect_stdout(io.StringIO()):
    civs, start, gv, end = L.locate(raw)
print("civs:", len(civs), "gv:", gv)
# distinct train maps over ALL unit records
maps = collections.Counter()
barracks = set()
for c in civs:
    for u in c["units"]:
        tl = u.get("train_locations") or []
        key = tuple(sorted((t["unit_id"], t["button_id"]) for t in tl))
        maps[key] += 1
        for t in tl:
            pass
print("distinct train maps (all unit records):", len(maps))
# units trainable at building 12 -- train_locations have no building id! check units.py/buttons
u0 = None
for c in civs:
    for u in c["units"]:
        if u.get("train_locations"):
            u0 = u; break
    if u0: break
print("sample unit with train_locations keys:", sorted(u0.keys()))
print("  train_locations:", u0["train_locations"][:3])
