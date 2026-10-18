import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE"
p = os.path.join(G, "widgetui", "screentechtree.json")
raw = open(p, encoding="utf-8-sig").read()
j = json.loads(raw)
print("top keys:", list(j.keys()))
print("root has Widget:", isinstance(j.get("Widget"), dict))
byType = {}
allw = []
def walk(o):
    if isinstance(o, dict):
        if "Type" in o and "Name" in o: allw.append(o)
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(j)
print("dicts with Type+Name:", len(allw))
print("distinct Type:", sorted({w["Type"] for w in allw}))
names = [w.get("Name") for w in allw]
print("distinct Name:", len({n for n in names if n}))
print("dup names:", [n for n in set(names) if names.count(n)>1])
# enum check
ic = [w for w in allw if w.get("Type")=="Base" and "Icon" in str(w.get("Name"))]
print("Base*Icon:", len(ic), [w["Name"] for w in ic])
