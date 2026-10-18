# -*- coding: utf-8 -*-
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE\widgetui"
d = json.load(open(os.path.join(G, "screentechtree.json"), encoding="utf-8-sig"))
c = d["Collection"]
print("Collection keys:", list(c)[:10])
for k, v in list(c.items())[:3]:
    print("\n--", k, "->", type(v).__name__)
    print(json.dumps(v, ensure_ascii=False)[:900])
