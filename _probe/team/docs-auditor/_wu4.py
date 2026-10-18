# -*- coding: utf-8 -*-
"""Count widgetui widgets via Collection.Widgets (nested)."""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE\widgetui"

def collect(w, out, depth=0):
    if not isinstance(w, dict):
        return
    for name, v in w.items():
        if not isinstance(v, dict):
            continue
        out.append(v)
        sub = v.get("Widgets")
        if isinstance(sub, dict):
            collect(sub, out, depth + 1)

files = [f for f in os.listdir(G) if f.endswith(".json")]
withw = tot = 0
types = set()
perfile = []
for f in files:
    d = json.load(open(os.path.join(G, f), encoding="utf-8-sig"))
    out = []
    cand = d.get("Collection") if isinstance(d, dict) else None
    if isinstance(cand, dict):
        collect(cand.get("Widgets") or {}, out)
    elif isinstance(d, dict):
        collect(d.get("Widgets") or {}, out)
    if out:
        withw += 1
        tot += len(out)
        for v in out:
            if v.get("type") is not None:
                types.add(v["type"])
            for key in ("type", "Type", "class", "Class"):
                pass
        perfile.append((len(out), f))
perfile.sort(reverse=True)
print("json files:", len(files), "with widgets:", withw, "total widgets:", tot, "distinct types:", len(types))
print("types sample:", sorted(types)[:12])
print("top5:", perfile[:5])
print("bottom5:", perfile[-5:])
