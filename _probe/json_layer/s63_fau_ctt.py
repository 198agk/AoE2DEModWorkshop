import os, io, json
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")
def load(n):
    return json.loads(open(os.path.join(BASE, n), "rb").read().decode("utf-8-sig"))

fau = load("futuravailableunits.json")
civs = load("civilizations.json")["civilization_list"]
ctt = os.path.join(BASE, "CivTechTrees")

w("=== IS CivTechTrees 'Node Status' == presence in futuravailableunits.json ? ===")
# futuravailableunits keys are internal_name style (Britons, ...)
w("  fau top keys n=%d sample=%s" % (len(fau), list(fau)[:8]))

def fau_ids(civ):
    ent = fau.get(civ)
    if not ent: return None
    out = set()
    for b in ent.get("Buildings", []):
        if "ID" in b: out.add(("B", b["ID"]))
        for u in b.get("Units", []):
            if "ID" in u:
                out.add(("B", u["ID"]))
                for t in u.get("Techs", []):
                    if "ID" in t: out.add(("T", t["ID"]))
        for t in b.get("Techs", []):
            if isinstance(t, dict) and "ID" in t: out.add(("T", t["ID"]))
    return out

pool = {}
n_missingciv = 0
for c in civs:
    name = c.get("internal_name")
    tt = c.get("tech_tree_name")
    fp = os.path.join(ctt, tt + ".json")
    if name == "Gaia" or not os.path.exists(fp):
        continue
    fs = fau_ids(name)
    if fs is None:
        n_missingciv += 1
        continue
    j = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    for lst, tag in ((j.get("civ_techs_buildings", []), "B"), (j.get("civ_techs_units", []), "U")):
        for nd in lst:
            st = nd.get("Node Status")
            nid = nd.get("Node ID")
            present = (tag, nid) in fs
            pool.setdefault(st, [0, 0])[0 if present else 1] += 1
w("  civs with no futuravailableunits entry: %d" % n_missingciv)
w("  cross-tab Node Status x (Node present in futuravailableunits):")
for st in sorted(pool):
    w("    %-22s present=%-6d absent=%-6d  absent%%=%.1f%%" % (st, pool[st][0], pool[st][1],
        100.0 * pool[st][1] / max(1, sum(pool[st]))))

w("")
w("=== total footprint ===")
tot_json = 0
for f in os.listdir(BASE):
    if f.endswith(".json"):
        tot_json += os.path.getsize(os.path.join(BASE, f))
n_ctt = 0; sz_ctt = 0
for f in os.listdir(ctt):
    if f.endswith(".json"):
        n_ctt += 1; sz_ctt += os.path.getsize(os.path.join(ctt, f))
w("  root .json n=%d total=%d B" % (len([f for f in os.listdir(BASE) if f.endswith('.json')]), tot_json))
w("  CivTechTrees n=%d total=%d B" % (n_ctt, sz_ctt))
w("  JSON layer total = %d B (%.2f MB) vs .dat 12023754 B inflated 93268152 B" % (
    tot_json + sz_ctt, (tot_json + sz_ctt) / 1048576.0))
open(os.path.join(OUT, "s63_fau_ctt.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
