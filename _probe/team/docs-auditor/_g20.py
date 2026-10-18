import sys, io, os, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
W = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\widgetui"
p = os.path.join(W, "screentechtree.json")
j = json.load(open(p, encoding="utf-8-sig"))
def widgets(o, out):
    for k,v in o.items():
        if k == "Widget" and isinstance(v, dict):
            out.append(v)
            for c in v.get("ChildWidgets") or []:
                widgets(c, out)
        elif isinstance(v,(dict,list)):
            widgets(v,out) if isinstance(v,dict) else [widgets(x,out) for x in v if isinstance(x,dict)]
    return out
ws = widgets(j, [])
print("screentechtree widgets:", len(ws))
types = {}
for w in ws:
    types.setdefault(w.get("Type"),0); types[w.get("Type")]+=1
print("distinct types:", len(types))
# icon-ish widget names
names = sorted({(w.get("Type"), w.get("Name")) for w in ws if "Icon" in str(w.get("Name")) or "icon" in str(w.get("Name"))})
print("icon widgets:", len(names))
for t,n in names[:25]: print("   ", t, n)
# panel file references across widgetui
hits = {}
for f in glob.glob(os.path.join(W,"**","*.json"), recursive=True):
    try: t = open(f, encoding="utf-8-sig", errors="replace").read()
    except Exception: continue
    for key in ("futuravailableunits","paphosfutureavailableunits","CivTechTrees"):
        if key in t: hits.setdefault(key,[]).append(os.path.basename(f))
print("\nwidgetui references:", {k:(len(v), v[:5]) for k,v in hits.items()})
