# -*- coding: utf-8 -*-
"""Count widgetui widgets the way the engine nests them: {"Collection": {...}} -> nested groups."""
import sys, io, os, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE\widgetui"

def walk_widgets(obj, out, depth=0):
    if not isinstance(obj, dict):
        return
    for k, v in obj.items():
        if not isinstance(v, dict):
            continue
        if "type" in v:
            out.append(v)
            walk_widgets(v.get("widgets") or {}, out, depth + 1)
        else:
            walk_widgets(v, out, depth + 1)

files = [f for f in os.listdir(G) if f.endswith(".json")]
withw, tot, types = 0, 0, set()
perfile = []
for f in files:
    d = json.load(open(os.path.join(G, f), encoding="utf-8-sig"))
    out = []
    if isinstance(d, dict) and "Collection" in d:
        walk_widgets(d["Collection"], out)
    elif isinstance(d, dict) and "widgets" in d:
        walk_widgets(d.get("widgets") or {}, out)
    if out:
        withw += 1
        tot += len(out)
        for v in out:
            t = v.get("type")
            if t is not None:
                types.add(t)
        perfile.append((len(out), f))
perfile.sort(reverse=True)
print(" json files:", len(files))
print(" with widgets:", withw, " total widgets:", tot, " distinct types:", len(types))
print(" top 5:", perfile[:5])

# also: count of top-level widget entries regardless of nesting depth
print("\n--- alt count: every dict directly under Collection ---")
c = collections.Counter()
for f in files:
    d = json.load(open(os.path.join(G, f), encoding="utf-8-sig"))
    if isinstance(d, dict) and "Collection" in d:
        c[f] = len(d["Collection"])
print(" files with Collection:", len(c), " total entries:", sum(c.values()))
