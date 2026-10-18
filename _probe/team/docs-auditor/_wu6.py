# -*- coding: utf-8 -*-
"""Proper widgetui census: Widgets is a list of {"Widget": {...}} with "Type"/"ChildWidgets"."""
import sys, io, os, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE\widgetui"

def collect(w, out):
    if isinstance(w, dict):
        w = [w]
    if not isinstance(w, list):
        return
    for item in w:
        if not isinstance(item, dict):
            continue
        node = item.get("Widget", item)
        if not isinstance(node, dict):
            continue
        out.append(node)
        ch = node.get("ChildWidgets")
        if ch:
            collect(ch, out)

files = [f for f in os.listdir(G) if f.endswith(".json")]
withw = tot = 0
types = collections.Counter()
materials = collections.Counter()
perfile = []
for f in files:
    d = json.load(open(os.path.join(G, f), encoding="utf-8-sig"))
    if not isinstance(d, dict):
        continue
    root = d.get("Collection")
    if not isinstance(root, dict):
        continue
    out = []
    collect(root.get("Widgets") or [], out)
    if out:
        withw += 1
        tot += len(out)
        for w in out:
            types[w.get("Type")] += 1
        perfile.append((len(out), f))

perfile.sort(reverse=True)
print("json files:", len(files))
print("with widgets:", withw, " total widgets:", tot, " distinct types:", len(types))
print("types:", dict(types))
print("top5:", perfile[:5])

# /surround ratio?  doc says Surround 1.09%
print("\nBase widgets:", types.get("Base"))

# material names containing 'Surround'
ms = collections.Counter()
def mats(w, acc):
    if isinstance(w, dict):
        w = [w]
    if not isinstance(w, list):
        return
    for item in w:
        if not isinstance(item, dict):
            continue
        node = item.get("Widget", item)
        if not isinstance(node, dict):
            continue
        for k, v in (node.get("StateMaterials") or {}).items():
            if isinstance(v, dict) and isinstance(v.get("Material"), str):
                acc[v["Material"]] += 1
        mats(node.get("ChildWidgets"), acc)

allmats = collections.Counter()
for f in files:
    d = json.load(open(os.path.join(G, f), encoding="utf-8-sig"))
    root = d.get("Collection") if isinstance(d, dict) else None
    if isinstance(root, dict):
        mats(root.get("Widgets"), allmats)
print("distinct materials:", len(allmats), " total refs:", sum(allmats.values()))
