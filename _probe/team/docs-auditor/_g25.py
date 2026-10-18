import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE"
j = json.load(open(os.path.join(G,"widgetui","screentechtree.json"), encoding="utf-8-sig"))
wtype=[]; wall=[]
def walk(o):
    if isinstance(o, dict):
        if "Type" in o: wtype.append(o)
        wall.append(o)
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(j)
print("dicts with Type:", len(wtype))
print("with Type and Name:", len([w for w in wtype if w.get("Name")]))
print("distinct Name among those:", len({w["Name"] for w in wtype if w.get("Name")}))
print("all dicts:", len(wall))
# icon widgets and their enum mapping
ic = [w for w in wtype if "Icon" in str(w.get("Name") or "")]
print("icon widgets:", len(ic), [w["Name"] for w in ic])
