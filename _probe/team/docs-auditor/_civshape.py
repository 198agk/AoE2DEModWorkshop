import sys, io, os, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))
from aoe2mod.dat import parser as P
from aoe2mod.game import locations as LOC
import os
g = LOC.find_game_root()
raw, how = P.load_dat(os.path.join(g,"resources","_common","dat","empires2_x2_p1.dat"))
d = P.Parser(raw).parse()
c0 = d["civs"][0]
print("civ keys:", list(c0.keys()))
u0 = c0.get("units") or []
print("units in civ0:", len(u0))
if u0: print("unit keys:", list(u0[0].keys()))
print("tribe_name:", c0.get("name") or c0.get("tribe_name"))
