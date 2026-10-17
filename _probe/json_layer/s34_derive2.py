import os, io, json, sys, collections
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import parse_dat as P

OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
CTT = os.path.join(BASE, "CivTechTrees")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

# ---------------- capture reader (byte-exact; verified in s29/s30) --------
def read_tl_cap(r):
    return (r.i16(), r.i16(), r.u8(), r.i32())
def read_creatable_cap(r):
    tl = []
    for _ in range(3):
        P.read_resource_cost(r)
    n = r.i16()
    for _ in range(n):
        tl.append(read_tl_cap(r))
    r.f32(); r.f32(); r.u8(); r.u8(); r.i32(); r.i16(); r.i16(); r.i16(); r.i16()
    r.f32(); r.f32(); r.i16(); r.i16(); r.i16(); r.i32(); r.u8(); r.f32()
    r.i16(); r.i32(); r.i32(); r.i16(); r.f32(); r.f32(); r.f32(); r.f32(); r.u8()
    r.f32(); r.f32(); r.f32(); r.i32(); r.i32(); r.u8(); r.i16()
    return tl
def read_unit_cap(r):
    u = {}
    u["type"] = r.u8(); u["id"] = r.i16(); r.i32(); r.i32(); u["class"] = r.i16()
    r.i16_array(2); r.i16(); r.i16(); r.u8(); u["hit_points"] = r.i16(); r.f32(); r.u8()
    r.f32(); r.f32(); r.f32(); r.i16(); r.i16(); r.i16(); r.i16(); r.u8(); r.u8()
    u["icon_id"] = r.i16(); r.u8(); r.i16()
    u["enabled"] = r.u8()          # Enabled
    u["disabled"] = r.u8()         # Disabled
    r.i16_array(2); r.i16_array(2)
    r.f32(); r.f32(); r.u8(); r.u8(); r.i16(); r.u8(); r.i16(); r.f32()
    r.u8(); r.u8(); r.u8(); r.u8(); r.u8(); r.f32(); r.u8(); r.i32(); r.i32()
    r.u8(); r.u8(); r.u8(); r.u8(); r.u8(); r.u8(); r.u8(); r.u8(); r.u8(); r.i16()
    r.u8(); r.u8(); r.f32(); r.f32(); r.f32(); r.i32(); r.i32()
    for _ in range(3):
        P.read_resource_storage(r)
    dgc = r.u8()
    for _ in range(dgc):
        P.read_damage_graphic(r)
    r.i16(); r.i16(); r.u32(); r.u32(); r.u32(); r.u32(); r.u8(); r.u8()
    u["name"] = r.debug_string()[1]; r.i16(); r.i16()
    t = u["type"]
    if t == P.UNIT_TYPE_AOE_TREES: return u
    if t >= P.UNIT_TYPE_FLAG: r.f32()
    else: return u
    if t >= P.UNIT_TYPE_DEAD_FISH: P.read_dead_fish(r)
    if t >= P.UNIT_TYPE_BIRD: P.read_bird(r)
    if t >= P.UNIT_TYPE_COMBATANT: P.read_type50(r)
    if t == P.UNIT_TYPE_PROJECTILE: P.read_projectile(r)
    if t >= P.UNIT_TYPE_CREATABLE: u["train_locations"] = read_creatable_cap(r)
    if t == P.UNIT_TYPE_BUILDING: P.read_building(r)
    return u
def read_civ_cap(r):
    r.u8(); nm = r.debug_string()[1]; n = r.i16(); r.i16(); r.i16(); r.f32_array(n); r.u8()
    m = r.i16(); ptrs = r.i32_array(m); us = []
    for i in range(m):
        if ptrs[i] != 0:
            us.append(read_unit_cap(r))
    return nm, us

data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()
st8 = [s for s in p.stage_offsets if s[0].startswith("8")][0]
r2 = P.Reader(data); r2.pos = st8[1]
n = r2.i16(); civs = {}
for _ in range(n):
    nm, us = read_civ_cap(r2)
    civs[nm] = us
w("integrity: pos=%d stage8end=%d ok=%s" % (r2.pos, st8[2], r2.pos == st8[2]))

# ---------------- A. .dat enabled/disabled vs JSON Node Status -----------
w("")
w("=" * 74)
w("A. .dat per-civ unit Enabled/Disabled  VS  CivTechTrees `Node Status`")
w("=" * 74)
for civdat, civfile in (("British", "BRITONS"), ("Aztecs", "AZTECS"),
                        ("Mongols", "MONGOLS"), ("Khitans", "KHITANS"),
                        ("Athenians", "ATHENIANS")):
    byid = {}
    for u in civs[civdat]:
        byid.setdefault(u["id"], u)
    d = json.loads(open(os.path.join(CTT, civfile + ".json"), "rb").read().decode("utf-8-sig"))
    cross = collections.Counter()
    for nd in d["civ_techs_units"]:
        u = byid.get(nd["Node ID"])
        if not u:
            cross[(nd["Node Status"], "NO-DAT-RECORD")] += 1
            continue
        cross[(nd["Node Status"], "en=%d dis=%d" % (u["enabled"], u["disabled"]))] += 1
    w("  %-11s %s" % (civfile, civdat))
    for k in sorted(cross, key=lambda k: (k[0], k[1])):
        w("      NodeStatus=%-19s dat %-16s  n=%d" % (k[0], k[1], cross[k]))
    # global flag distribution for this civ
    fl = collections.Counter((u["enabled"], u["disabled"]) for u in civs[civdat])
    w("      .dat civ flag distribution (all %d records): %s" % (len(civs[civdat]), dict(fl)))

# ---------------- B. .dat tech tree connections --------------------------
w("")
w("=" * 74)
w("B. .dat TechTree UnitConnection fields for the JSON's unit ids")
w("=" * 74)
r3 = P.Reader(data); r3.pos = [s for s in p.stage_offsets if s[0].startswith("10")][0][1]
for _ in range(7):
    r3.i32()
ages_n = r3.u8(); bld_n = r3.u8(); unit_n = r3.i16(); res_n = r3.u8(); tot = r3.i32()
def grp(r):
    k = r.u8()
    return list(r.i32_array(k)) if k else []
def cmn(r):
    r.i32(); r.i32_array(10); r.i32_array(10)
for _ in range(ages_n):
    r3.i32(); r3.u8(); grp(r3); grp(r3); grp(r3); cmn(r3); r3.u8(); r3.skip(10); r3.skip(10); r3.u8(); r3.i32()
for _ in range(bld_n):
    r3.i32(); r3.u8(); grp(r3); grp(r3); grp(r3); cmn(r3); r3.u8(); r3.skip(P.AGES); r3.skip(P.AGES); r3.i32(); r3.i32()
UC = {}
ULINKS = {}
for _ in range(unit_n):
    uid = r3.i32(); status = r3.u8(); up = r3.i32(); cmn(r3); vl = r3.i32()
    g = grp(r3); loc = r3.i32(); req = r3.i32(); lm = r3.i32(); en = r3.i32()
    UC[uid] = dict(status=status, upper=up, vertical=vl, group=g, location=loc,
                   req_research=req, line_mode=lm, enabling=en)
r3 = P.Reader(data); r3.pos = [s for s in p.stage_offsets if s[0].startswith("10")][0][1]
for _ in range(7):
    r3.i32()
r3.u8(); r3.u8()
un2 = r3.i16(); r3.u8(); r3.i32()
for _ in range(ages_n):
    r3.i32(); r3.u8(); grp(r3); grp(r3); grp(r3); cmn(r3); r3.u8(); r3.skip(10); r3.skip(10); r3.u8(); r3.i32()
for _ in range(bld_n):
    r3.i32(); r3.u8(); grp(r3); grp(r3); grp(r3); cmn(r3); r3.u8(); r3.skip(P.AGES); r3.skip(P.AGES); r3.i32(); r3.i32()
for _ in range(un2):
    r3.i32(); r3.u8(); r3.i32(); cmn(r3); r3.i32(); grp(r3); r3.i32(); r3.i32(); r3.i32(); r3.i32()
w("  UnitConnections: %d ; tail exact=%s" % (len(UC), None))
d = json.loads(open(os.path.join(CTT, "BRITONS.json"), "rb").read().decode("utf-8-sig"))
w("  BRITONS.json unit nodes: NodeID -> .dat UnitConnection(required_research, enabling_research, location_in_age, vertical)")
nmatch = 0; ntot = 0
for nd in d["civ_techs_units"][:14]:
    c = UC.get(nd["Node ID"])
    w("     %-28s NodeID=%-5d json(TriggerTech=%-5s AgeID=%s Prereq=%s)  dat(required=%-5s enabling=%-5s loc=%s vert=%s)" % (
        nd["Name"], nd["Node ID"], nd.get("Trigger Tech ID"), nd.get("Age ID"),
        nd.get("Prerequisite IDs"), c and c["req_research"], c and c["enabling"], c and c["location"], c and c["vertical"]))
w("  JSON `Trigger Tech ID` vs .dat `EnablingResearch` across all 62 civs' nodes:")
tt = 0; eq = 0; inuc = 0
for fp in sorted(__import__("glob").glob(os.path.join(CTT, "*.json"))):
    dd = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    for nd in dd["civ_techs_units"]:
        if "Trigger Tech ID" not in nd:
            continue
        tt += 1
        c = UC.get(nd["Node ID"])
        if c is None:
            continue
        inuc += 1
        if c["enabling"] == nd["Trigger Tech ID"]:
            eq += 1
w("     nodes with Trigger Tech ID=%d ; found in .dat UnitConnections=%d ; EnablingResearch equal=%d (%.1f%%)"
  % (tt, inuc, eq, 100.0 * eq / tt if tt else 0))
w("  JSON `Prerequisite IDs[0]` vs .dat `RequiredResearch`:")
pt = 0; peq = 0; pin = 0
for fp in sorted(__import__("glob").glob(os.path.join(CTT, "*.json"))):
    dd = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    for nd in dd["civ_techs_units"]:
        pr = nd.get("Prerequisite IDs")
        if not pr:
            continue
        pt += 1
        c = UC.get(nd["Node ID"])
        if c is None:
            continue
        pin += 1
        if c["req_research"] == pr[0]:
            peq += 1
w("     nodes with Prerequisite IDs=%d ; in .dat=%d ; RequiredResearch equal=%d" % (pt, pin, peq))

# ---------------- C. futuravailableunits derivability ---------------------
w("")
w("=" * 74)
w("C. futuravailableunits.json: derivable from .dat per-civ flags + tech tree?")
w("=" * 74)
fu = json.loads(open(os.path.join(BASE, "futuravailableunits.json"), "rb").read().decode("utf-8-sig"))
w("  civs in JSON: %d -> %s" % (len(fu), sorted(fu)))
w("  Gaia entry: %s" % json.dumps(fu.get("Gaia")))
w("  empty-Buildings civs: %s" % [k for k, v in fu.items() if not v.get("Buildings")])
# map JSON civ key (internal_name) -> .dat civ name via civilizations.json order
cj = json.loads(open(os.path.join(BASE, "civilizations.json"), "rb").read().decode("utf-8-sig"))
recs = cj["civilization_list"]
w("  civilizations.json records: %d" % len(recs))
datnames = [c["name"] for c in st["civs"]]
w("  .dat civ names(%d): %s" % (len(datnames), datnames[:8]))
w("  civjson internal_names(%d): %s" % (len(recs), [r["internal_name"] for r in recs[:8]]))
# align: .dat has Gaia first? check
w("  .dat[0]=%r  civjson[0].internal_name=%r" % (datnames[0], recs[0]["internal_name"]))
aligned = {}
for i, r in enumerate(recs):
    if i < len(datnames):
        aligned[r["internal_name"]] = datnames[i]
w("  aligned pairs (first 6): %s" % list(aligned.items())[:6])
tot_n = 0; eq_n = 0; miss = 0; rows = []
for civkey, dname in aligned.items():
    if civkey not in fu:
        continue
    entry = fu[civkey]
    for b in entry.get("Buildings", []):
        for u in b.get("Units", []):
            tot_n += 1
            uid = u["ID"]
            rec = None
            for x in civs[dname]:
                if x["id"] == uid:
                    rec = x; break
            if rec is None:
                miss += 1
                continue
            eq_n += 1
            if len(rows) < 10:
                rows.append((civkey, uid, u["Name"], u.get("RequiredAge"), rec["enabled"], rec["disabled"], rec["name"]))
w("  futuravailableunits unit entries checked=%d ; found in .dat civ=%d ; not found=%d" % (tot_n, eq_n, miss))
for r in rows:
    w("     %-12s id=%-5d %-22r RequiredAge=%-3s dat enabled=%d disabled=%d datname=%r" % r)
# age consistency: RequiredAge vs .dat UnitConnection location? and vs tech tree age groups
w("")
w("  RequiredAge distribution: %s" % dict(collections.Counter(
    u.get("RequiredAge") for k in fu for b in fu[k].get("Buildings", []) for u in b.get("Units", []))))
open(os.path.join(OUT, "s34_derive2.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
