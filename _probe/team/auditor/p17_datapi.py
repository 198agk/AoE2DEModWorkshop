# -*- coding: utf-8 -*-
import sys, inspect, os, json
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
from aoe2mod.dat import parser as P
print("parser module names:", [n for n in dir(P) if not n.startswith("_")])
print("Parser methods:", [n for n in dir(P.Parser) if not n.startswith("__")])
print("read_unit sig:", inspect.signature(P.read_unit))
import aoe2mod.api as A
print("api names:", [n for n in dir(A) if not n.startswith("_")])

# The control: Villager HP. In the .dat, read_unit collects hp only when collect is set.
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
for tag, p in (("SHIPPED", os.path.join(GAME, r"resources\_common\dat\empires2_x2_p1.dat")),
               ("BUNDLE", os.path.join(GAME, r"..\..\..\..\..\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Bundle VillagerHP plus Britons HandCannon\resources\_common\dat\empires2_x2_p1.dat"))):
    p = os.path.normpath(p)
    print()
    print("==", tag, os.path.isfile(p), os.path.getsize(p) if os.path.isfile(p) else None)
    if not os.path.isfile(p):
        continue
    pr = P.Parser(p)
    print("  parser attrs:", [n for n in dir(pr) if not n.startswith("__")][:40])
    try:
        coll = {}
        s = pr.parse_all(collect=coll) if "collect" in inspect.signature(pr.parse_all).parameters else pr.parse_all()
        print("  parse_all ok, top keys:", list(s.keys())[:20])
    except Exception as e:
        print("  parse_all err:", type(e).__name__, e)
