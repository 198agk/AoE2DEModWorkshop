import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, io, collections, csv, re

D = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
P = os.path.join(D, "CivTechTrees")
out = io.StringIO()
def w(s=""):
    out.write(str(s) + "\n")

files = sorted(f for f in os.listdir(P) if f.endswith(".json"))
w("files=%d" % len(files))

civ_id_set = []
status_ctr = collections.Counter()
ntype_ctr = collections.Counter()
lntype_ctr = collections.Counter()
dntype_ctr = collections.Counter()
utype_ctr = collections.Counter()
rows = []
allb = {}   # civ -> set of Building ID
allu = {}   # civ -> set of (Node ID)
allunames = {}
nodeid_dup = 0
for f in files:
    j = json.loads(open(os.path.join(P, f), "rb").read().decode("utf-8-sig"))
    cid = j["civ_id"]
    civ_id_set.append(cid)
    b = j.get("civ_techs_buildings", [])
    u = j.get("civ_techs_units", [])
    rows.append((f, cid, len(b), len(u), len(set(x.get("Node ID") for x in b)), len(set(x.get("Node ID") for x in u))))
    allb[cid] = [x.get("Building ID") for x in b]
    allu[cid] = [x.get("Node ID") for x in u]
    allunames[cid] = {x.get("Node ID"): x.get("Name") for x in u}
    for x in b + u:
        status_ctr[x.get("Node Status")] += 1
        ntype_ctr[x.get("Node Type")] += 1
        lntype_ctr[x.get("Link Node Type")] += 1
        dntype_ctr[x.get("Draw Node Type")] += 1
        utype_ctr[x.get("Use Type")] += 1
    ids = [x.get("Node ID") for x in b + u]
    if len(ids) != len(set(ids)):
        nodeid_dup += 1

w("\n### civ_id values (%d)" % len(civ_id_set))
w("  " + ", ".join(civ_id_set))
w("  distinct=%d  duplicates=%s" % (len(set(civ_id_set)), [k for k, v in collections.Counter(civ_id_set).items() if v > 1]))

w("\n### Node Status enum: %s" % dict(status_ctr))
w("### Node Type enum: %s" % dict(ntype_ctr))
w("### Link Node Type enum: %s" % dict(lntype_ctr))
w("### Draw Node Type enum: %s" % dict(dntype_ctr))
w("### Use Type enum: %s" % dict(utype_ctr))
w("### civs where Node IDs collide between buildings+units: %d" % nodeid_dup)

w("\n### per-file counts")
w("%-24s %-16s %6s %6s %8s %8s" % ("file", "civ_id", "nbld", "nunit", "uniqB", "uniqU"))
for r in rows:
    w("%-24s %-16s %6d %6d %8d %8d" % r)

# cross-civ comparison: are the building node lists identical across civs?
sigs = collections.defaultdict(list)
for cid, lst in allb.items():
    sigs[tuple(lst)].append(cid)
w("\n### distinct civ_techs_buildings Building-ID sequences: %d (over %d civs)" % (len(sigs), len(allb)))
for sig, civs in sorted(sigs.items(), key=lambda kv: -len(kv[1]))[:12]:
    w("   n_civs=%-3d len=%-4d civs=%s" % (len(civs), len(sig), civs[:6]))

sigs2 = collections.defaultdict(list)
for cid, lst in allu.items():
    sigs2[tuple(lst)].append(cid)
w("\n### distinct civ_techs_units Node-ID sequences: %d" % len(sigs2))
for sig, civs in sorted(sigs2.items(), key=lambda kv: -len(kv[1]))[:12]:
    w("   n_civs=%-3d len=%-4d civs=%s" % (len(civs), len(sig), civs[:6]))

# union of all building IDs / unit node ids across civs
ub = collections.Counter()
for lst in allb.values():
    ub.update(lst)
w("\n### distinct Building ID values across all civs: %d" % len(ub))
w("   ids sorted: %s" % sorted(set(ub))[:200])
uu = collections.Counter()
for lst in allu.values():
    uu.update(lst)
w("\n### distinct unit Node ID values across all civs: %d" % len(uu))
w("   range: %d..%d" % (min(uu), max(uu)))

# do two civs with identical building sequences still differ in unit sequences?
w("\n### AZTECS vs BRITONS unit node ids equal? %s ; buildings equal? %s" % (
    allu.get("AZTECS") == allu.get("BRITONS"), allb.get("AZTECS") == allb.get("BRITONS")))
w("### BRITONS len(u)=%d  AZTECS len(u)=%d" % (len(allu.get("BRITONS", [])), len(allu.get("AZTECS", []))))

json.dump({c: {"buildings": allb[c], "units": allu[c], "unit_names": {str(k): v for k, v in allunames[c].items()}}
           for c in allb}, open(_HERE_PATH("_probe", "json_layer", "s11_ctt_index.json"), "w", encoding="utf-8"), ensure_ascii=False)
open(_HERE_PATH("_probe", "json_layer", "s11_ctt_enums.txt"), "w", encoding="utf-8").write(out.getvalue())
print(out.getvalue())
