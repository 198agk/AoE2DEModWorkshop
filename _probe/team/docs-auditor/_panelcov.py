import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\dat"
def load(n):
    return json.load(open(os.path.join(G,n), encoding="utf-8-sig"))
main = load("futuravailableunits.json")
paph = load("paphosfutureavailableunits.json")
print("main civs:", len(main), " paphos civs:", len(paph))
print("union:", len(set(main)|set(paph)), " overlap:", len(set(main)&set(paph)))
have118 = [c for c in main if "118" in main[c].get("Buildings", {})]
print("main civs with building 118:", len(have118), "/", len(main))
# paphos union coverage vs 62 trees
import glob
trees = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(G,"CivTechTrees","*.json")))
print("tree files:", len(trees))
missing = [c for c in trees if c not in main and c not in paph]
print("tree civs covered by neither panel:", missing)
print("sample Buildings keys count for Britons:", len(main["Britons"]["Buildings"]))
print("Britons has 12?", "12" in main["Britons"]["Buildings"])
