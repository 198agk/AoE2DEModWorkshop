# -*- coding: utf-8 -*-
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE\widgetui"
d = json.load(open(os.path.join(G, "screentechtree.json"), encoding="utf-8-sig"))
w = d["Collection"]["Widgets"]
print("type:", type(w).__name__, "len:", len(w))
print(json.dumps(w, ensure_ascii=False)[:1500])
