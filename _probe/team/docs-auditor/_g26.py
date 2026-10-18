import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE"
j = json.load(open(os.path.join(G,"widgetui","screentechtree.json"), encoding="utf-8-sig"))
c = j["Collection"]
print("Collection keys:", [k for k in c.keys()][:20])
print("Collection Name:", c.get("Name"), "| Type:", c.get("Type"))
print("Collection Widgets len:", len(c.get("Widgets") or []))
# count incl root as a widget
if c.get("Name"): print("=> counting root gives", 59, "widgets /", 53, "distinct names")
