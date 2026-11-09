import sys, io, os, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))
from aoe2mod.dat import parser as P
from aoe2mod.game import locations as LOC
import os
g = LOC.find_game_root()
dat = os.path.join(g,"resources","_common","dat","empires2_x2_p1.dat")
raw, how = P.load_dat(dat)
d = P.Parser(raw).parse()
print("top keys:", list(d.keys()))
for k,v in d.items():
    if isinstance(v, list): print("  ", k, "list", len(v))
    elif isinstance(v, dict): print("  ", k, "dict", list(v.keys())[:6])
