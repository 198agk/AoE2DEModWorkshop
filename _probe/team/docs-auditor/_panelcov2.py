import sys, io, os, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\dat"
main = json.load(open(os.path.join(G,"futuravailableunits.json"), encoding="utf-8-sig"))
paph = json.load(open(os.path.join(G,"paphosfutureavailableunits.json"), encoding="utf-8-sig"))
b = main["Britons"]["Buildings"]
print("Buildings type:", type(b).__name__, "len", len(b))
if isinstance(b, list):
    print("elem0 keys:", list(b[0].keys()))
    print("elem0:", json.dumps(b[0], ensure_ascii=False)[:220])
    ids = [e.get("ID") for e in b]
else:
    ids = list(b.keys())
print("building ids (first 40):", ids[:40])
print("has 118:", 118 in ids or "118" in ids)
print("has 12:", 12 in ids or "12" in ids)
trees = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(G,"CivTechTrees","*.json")))
m = {k.upper() for k in main} | {k.upper() for k in paph}
print("tree civs not covered:", [t for t in trees if t.upper() not in m])
print("union (upper):", len(m), "overlap:", len({k.upper() for k in main} & {k.upper() for k in paph}))
