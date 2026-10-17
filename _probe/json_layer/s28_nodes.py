import os, io, json, sys
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import parse_dat as P

OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
CTT = os.path.join(BASE, "CivTechTrees")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

b = json.loads(open(os.path.join(CTT, "BRITONS.json"), "rb").read().decode("utf-8-sig"))
w("BRITONS civ_id=%r  buildings=%d units=%d" % (b["civ_id"], len(b["civ_techs_buildings"]), len(b["civ_techs_units"])))
w("\n--- first 4 building nodes verbatim")
for n in b["civ_techs_buildings"][:4]:
    w("  %s" % json.dumps(n, ensure_ascii=False))
w("\n--- first 6 unit nodes verbatim")
for n in b["civ_techs_units"][:6]:
    w("  %s" % json.dumps(n, ensure_ascii=False))
w("\n--- unit nodes whose Node ID is small (<=30)")
for n in b["civ_techs_units"]:
    if n.get("Node ID", 999) <= 30:
        w("  %s" % json.dumps(n, ensure_ascii=False))
w("\n--- all distinct key sets in units list")
ks = {}
for n in b["civ_techs_units"]:
    ks.setdefault(tuple(sorted(n.keys())), []).append(n.get("Name"))
for k, v in ks.items():
    w("  %d nodes missing/present: %s   e.g. %s" % (len(v), list(k), v[:3]))

# Does Link ID or Node ID match the .dat unit-id concept?
data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()
civ = [c for c in st["civs"] if c["name"] == "British"][0]
civunit_ids = set(u["id"] for u in civ["units"])
names = {}
for u in civ["units"]:
    names.setdefault(u["id"], u["name"])
w("\n.dat British civ has %d units; ids 0..%d" % (len(civunit_ids), max(civunit_ids)))
for field in ("Node ID", "Link ID", "Building ID", "Trigger Tech ID", "Name String ID"):
    vals = [n.get(field) for n in b["civ_techs_units"] if field in n]
    if not vals: continue
    inunit = sum(1 for v in vals if v in civunit_ids)
    w("  units list field %-16s n=%-4d matching .dat British unit ids: %d" % (field, len(vals), inunit))
for field in ("Node ID", "Link ID", "Building ID", "Name String ID"):
    vals = [n.get(field) for n in b["civ_techs_buildings"] if field in n]
    if not vals: continue
    w("  bldg  list field %-16s n=%-4d matching .dat British unit ids: %d  e.g. %s" % (
        field, len(vals), sum(1 for v in vals if v in civunit_ids), vals[:8]))

w("\n--- resolve node names via .dat unit names (Node ID -> name)")
ok = 0
for n in b["civ_techs_units"][:25]:
    nid = n.get("Node ID")
    w("   NodeID=%-6s file_name=%-28s dat_name=%-24s LinkID=%s" % (
        nid, n.get("Name"), names.get(nid, "<none>"), n.get("Link ID")))
    if nid in names: ok += 1
w("  of first 25 unit nodes, Node ID resolves to a .dat British unit name for %d" % ok)

w("\n--- resolve via Link ID")
ok = 0
for n in b["civ_techs_units"][:25]:
    lid = n.get("Link ID")
    if lid is not None and lid in names: ok += 1
    w("   LinkID=%-6s file_name=%-28s dat_name=%s" % (lid, n.get("Name"), names.get(lid, "<none>")))
w("  of first 25 unit nodes, Link ID resolves for %d" % ok)

# tech tree .dat ids vs CivTechTrees building ids: check the 5 extras exist as .dat units
alldat = set()
for c in st["civs"]:
    for u in c["units"]:
        alldat.add(u["id"])
w("\ntotal distinct .dat unit ids across all civs: %d" % len(alldat))
for x in (1734, 1806, 1808, 1889, 2415, 199, 1893):
    who = [c["name"] for c in st["civs"] if any(u["id"] == x for u in c["units"])]
    nmp = None
    for c in st["civs"]:
        for u in c["units"]:
            if u["id"] == x: nmp = u["name"]; break
        if nmp: break
    w("  id %-5d in .dat: %-5s name=%-24s civs=%d %s" % (x, x in alldat, nmp, len(who), who[:4]))

open(os.path.join(OUT, "s28_nodes.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
