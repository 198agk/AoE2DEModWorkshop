import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE"
p = os.path.join(G, "widgetui", "screentechtree.json")
j = json.load(open(p, encoding="utf-8-sig"))
ws = []
def walk(o):
    if isinstance(o, dict):
        if "Widget" in o and isinstance(o["Widget"], dict): ws.append(o["Widget"])
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(j)
print("screentechtree widgets:", len(ws))
print("distinct Names:", len({w.get("Name") for w in ws if w.get("Name")}))
ic = [w for w in ws if "Icon" in str(w.get("Name") or "")]
print("widgets with 'Icon' in name:", len(ic))
for w in ic[:20]: print("   ", w.get("Type"), w.get("Name"))
