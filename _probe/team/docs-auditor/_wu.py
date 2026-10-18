# -*- coding: utf-8 -*-
import sys, io, os, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE\widgetui"

d = json.load(open(os.path.join(G, "screentechtree.json"), encoding="utf-8-sig"))
print("top keys:", list(d)[:20])
for k, v in d.items():
    print("  ", k, type(v).__name__, (len(v) if hasattr(v, "__len__") else ""))
