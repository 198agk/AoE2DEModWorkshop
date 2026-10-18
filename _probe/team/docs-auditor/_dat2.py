# -*- coding: utf-8 -*-
import sys, os, io, zlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.getcwd())
from aoe2mod.dat import parser as P
p = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
data, how = P.load_dat(p)
print("how:", how, "raw bytes:", len(data), "first4:", data[:4])
