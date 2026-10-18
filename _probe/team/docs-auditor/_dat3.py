# -*- coding: utf-8 -*-
import sys, os, io, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.getcwd())
from aoe2mod.dat import parser as P
p = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
t0=time.time()
data, how = P.load_dat(p)
dat, leftovers = P.parse_dat(data) if hasattr(P,'parse_dat') else (None,None)
print("dir parse fns:", [n for n in dir(P) if n.startswith('parse') or n.startswith('read_dat')])
