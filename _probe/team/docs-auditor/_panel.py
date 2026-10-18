import sys, io, os, json, glob, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for n in ["test_button_slots.py","test_panel_wire.py"]:
    print(n, "->", glob.glob("_probe/"+n))
print("probe_panel_era*:", glob.glob("_probe/probe_panel_era*"))
G = r"d:\games\steam\steamapps\common\AoE2DE"
p = os.path.join(G,"resources","_common","dat","futuravailableunits.json")
d = json.load(open(p,encoding="utf-8-sig"))
print("top keys:", list(d.keys())[:6])
# find civ map
def civmap(d):
    for k in ("Civs","Civilizations","civs"):
        if k in d: return d[k]
    return d
c = civmap(d)
print("civ count:", len(c))
bcount = {}
for civ, v in c.items():
    b = v.get("Buildings") if isinstance(v,dict) else None
    if b is None: continue
    n = len(b) if isinstance(b,list) else len(b)
    bcount[civ]=n
if bcount:
    vals = sorted(bcount.values())
    print("buildings per civ: min %d max %d distinct %s" % (vals[0], vals[-1], sorted(set(vals))))
else:
    k0 = list(c)[0]
    print("sample civ shape:", json.dumps(c[k0], ensure_ascii=False)[:300])
