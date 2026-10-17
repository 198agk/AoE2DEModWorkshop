import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, sys, collections, glob
sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
import parse_dat as P

OUT = _HERE_PATH("_probe", "json_layer")
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
CTT = os.path.join(BASE, "CivTechTrees")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()

# ---- tech tree: full read, keep per-node records ------------------------
tt_off = [s for s in p.stage_offsets if s[0].startswith("10")][0][1]
def grp(r):
    k = r.u8()
    return list(r.i32_array(k)) if k else []
def cmn(r):
    d = {}
    d["slots_used"] = r.i32(); d["research"] = r.i32_array(10); d["mode"] = r.i32_array(10)
    return d

r = P.Reader(data); r.pos = tt_off
tail = [r.i32() for _ in range(7)]
n_age = r.u8(); n_bld = r.u8(); n_unit = r.i16(); n_res = r.u8(); n_grp = r.i32()
AGES = []
for _ in range(n_age):
    a = {"ID": r.i32(), "status": r.u8(), "Buildings": grp(r), "Units": grp(r), "Techs": grp(r)}
    a["common"] = cmn(r)
    a["num_building_levels"] = r.u8(); a["bld_per_zone"] = list(r.raw(10))
    a["grp_len_per_zone"] = list(r.raw(10)); a["max_age_length"] = r.u8(); a["line_mode"] = r.i32()
    AGES.append(a)
BLD = {}
for _ in range(n_bld):
    b = {"ID": r.i32(), "status": r.u8(), "Buildings": grp(r), "Units": grp(r), "Techs": grp(r)}
    b["common"] = cmn(r)
    b["location"] = r.u8(); b["utt"] = list(r.raw(P.AGES)); b["utf"] = list(r.raw(P.AGES))
    b["line_mode"] = r.i32(); b["enabling"] = r.i32()
    BLD[b["ID"]] = b
UNI = {}
for _ in range(n_unit):
    u = {"ID": r.i32(), "status": r.u8(), "upper": r.i32(), "common": cmn(r)}
    u["vertical"] = r.i32(); u["group"] = grp(r); u["location"] = r.i32()
    u["required"] = r.i32(); u["line_mode"] = r.i32(); u["enabling"] = r.i32()
    UNI[u["ID"]] = u
RES = {}
for _ in range(n_res):
    q = {"ID": r.i32(), "status": r.u8(), "upper": r.i32(),
         "Buildings": grp(r), "Units": grp(r), "Techs": grp(r), "common": cmn(r)}
    q["vertical"] = r.i32(); q["location"] = r.i32(); q["line_mode"] = r.i32()
    RES[q["ID"]] = q
w("tech tree re-read: ages=%d bld=%d unit=%d res=%d pos=%d stage10end=%s exact=%s"
  % (len(AGES), len(BLD), len(UNI), len(RES), r.pos,
     [s for s in p.stage_offsets if s[0].startswith("10")][0][2],
     r.pos == [s for s in p.stage_offsets if s[0].startswith("10")][0][2]))
w("  age node: %s" % {k: v for k, v in AGES[0].items() if k != "common"})
w("  bld node sample: %s" % {k: v for k, v in BLD[87].items() if k != "common"})
w("  unit node sample(id=4): %s" % {k: v for k, v in UNI[4].items() if k != "common"})
w("  res node sample: %s" % (list(RES.values())[0] and {k: v for k, v in list(RES.values())[0].items() if k != "common"}))

# ---- key namespaces: are JSON tech-node ids .dat RESEARCH ids? ---------
res_ids = set(RES)
tech_ids = set()
_t = st.get("techs") or []
if isinstance(_t, int) and "first_techs" in st:
    _t = st["first_techs"]
for t in _t:
    if isinstance(t, dict):
        tech_ids.add(t.get("id"))
w("")
w("=" * 74)
w("D. Which .dat namespace do JSON tech/unit node ids belong to?")
w("=" * 74)
w("  .dat RES (research connection) ids: %d ; tech records: %d" % (len(res_ids), len(tech_ids)))
tag = collections.Counter()
for fp in sorted(glob.glob(os.path.join(CTT, "*.json"))):
    d = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    for nd in d["civ_techs_units"]:
        nid = nd["Node ID"]
        nt = nd.get("Node Type", "<MISSING>")
        if nt in ("Unit", "UnitUpgrade", "RegionalUnit", "UniqueUnit"):
            tag[(nt, "in .dat UnitConnection")] += 1 if nid in UNI else 0
            tag[(nt, "NOT in UnitConnection")] += 0 if nid in UNI else 1
        else:
            tag[(nt, "in .dat RES")] += 1 if nid in res_ids else 0
            tag[(nt, "in tech records")] += 1 if nid in tech_ids else 0
for k in sorted(tag, key=str):
    w("     %-34s %s = %d" % (str(k[0]), k[1], tag[k]))

# ---- field-by-field agreement JSON vs .dat ------------------------------
w("")
w("=" * 74)
w("E. Field-by-field: can the JSON be reconstructed from the .dat?")
w("=" * 74)
civalign = {}
cj = json.loads(open(os.path.join(BASE, "civilizations.json"), "rb").read().decode("utf-8-sig"))
datnames = [c["name"] for c in st["civs"]]
for i, rec in enumerate(cj["civilization_list"]):
    if i < len(datnames):
        civalign[rec["tech_tree_name"]] = datnames[i]
w("  civ align sample: %s" % list(civalign.items())[:4])

ag = collections.Counter()
for fp in sorted(glob.glob(os.path.join(CTT, "*.json"))):
    civ = os.path.basename(fp)[:-5]
    dn = civalign.get(civ)
    d = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    for nd in d["civ_techs_units"]:
        nid = nd["Node ID"]
        c = UNI.get(nid)
        ag["AgeID_vs_LocationInAge: %s" % (
            "MATCH" if (c and c["location"] == nd["Age ID"]) else ("NO-DAT" if not c else "DIFFER"))] += 1
        if c:
            if nd.get("Trigger Tech ID") is not None:
                ag["TriggerTech_vs: RequiredResearch MATCH" if c["required"] == nd["Trigger Tech ID"]
                   else ("EnablingResearch MATCH" if c["enabling"] == nd["Trigger Tech ID"] else "NEITHER")] += 1
    for nd in d["civ_techs_buildings"]:
        nid = nd["Node ID"]
        b = BLD.get(nid)
        ag["bld AgeID_vs_LocationInAge: %s" % (
            "MATCH" if (b and b["location"] == nd["Age ID"]) else ("NO-DAT" if not b else "DIFFER"))] += 1
for k in sorted(ag):
    w("     %-52s %d" % (k, ag[k]))

# ---- unit availability: per-civ Enabled flag vs JSON Node Status -------
w("")
w("=" * 74)
w("F. Per-civ .dat Enabled flag vs JSON Node Status (all 62 civs pooled)")
w("=" * 74)
# need per-civ unit records again
def _read_tl(r):
    return (r.i16(), r.i16(), r.u8(), r.i32())
def _read_creatable(r):
    tl = []
    for _ in range(3):
        P.read_resource_cost(r)
    n = r.i16()
    for _ in range(n):
        tl.append(_read_tl(r))
    r.f32(); r.f32(); r.u8(); r.u8(); r.i32(); r.i16(); r.i16(); r.i16(); r.i16()
    r.f32(); r.f32(); r.i16(); r.i16(); r.i16(); r.i32(); r.u8(); r.f32()
    r.i16(); r.i32(); r.i32(); r.i16(); r.f32(); r.f32(); r.f32(); r.f32(); r.u8()
    r.f32(); r.f32(); r.f32(); r.i32(); r.i32(); r.u8(); r.i16()
    return tl
def alloc_unit(r):
    """byte-exact unit walk (verified 0/63 mismatch vs reference read_unit)"""
    t = r.u8(); uid = r.i16(); r.i32(); r.i32(); r.i16()
    r.i16_array(2); r.i16(); r.i16(); r.u8(); r.i16(); r.f32(); r.u8()
    r.f32(); r.f32(); r.f32(); r.i16(); r.i16(); r.i16(); r.i16(); r.u8(); r.u8()
    r.i16(); r.u8(); r.i16()
    en = r.u8(); dis = r.u8()
    r.i16_array(2); r.i16_array(2)
    r.f32(); r.f32(); r.u8(); r.u8(); r.i16(); r.u8(); r.i16(); r.f32()
    r.u8(); r.u8(); r.u8(); r.u8(); r.u8(); r.f32(); r.u8(); r.i32(); r.i32()
    for _ in range(9):
        r.u8()
    r.i16(); r.u8(); r.u8(); r.f32(); r.f32(); r.f32(); r.i32(); r.i32()
    for _ in range(3):
        P.read_resource_storage(r)
    for _ in range(r.u8()):
        P.read_damage_graphic(r)
    r.i16(); r.i16(); r.u32(); r.u32(); r.u32(); r.u32(); r.u8(); r.u8()
    r.debug_string(); r.i16(); r.i16()
    if t == P.UNIT_TYPE_AOE_TREES:
        return uid, en, dis, []
    if t >= P.UNIT_TYPE_FLAG:
        r.f32()
    else:
        return uid, en, dis, []
    if t >= P.UNIT_TYPE_DEAD_FISH: P.read_dead_fish(r)
    if t >= P.UNIT_TYPE_BIRD: P.read_bird(r)
    if t >= P.UNIT_TYPE_COMBATANT: P.read_type50(r)
    if t == P.UNIT_TYPE_PROJECTILE: P.read_projectile(r)
    tl = []
    if t >= P.UNIT_TYPE_CREATABLE:
        tl = _read_creatable(r)
    if t == P.UNIT_TYPE_BUILDING: P.read_building(r)
    return uid, en, dis, tl

st8 = [s for s in p.stage_offsets if s[0].startswith("8")][0]
r2 = P.Reader(data); r2.pos = st8[1]
nciv = r2.i16()
civs = {}
for _ in range(nciv):
    r2.u8(); nm = r2.debug_string()[1]; n = r2.i16(); r2.i16(); r2.i16(); r2.f32_array(n); r2.u8()
    m = r2.i16(); ptrs = r2.i32_array(m)
    recs = {}
    for i in range(m):
        if ptrs[i] != 0:
            uid, en, dis, tl = alloc_unit(r2)
            recs.setdefault(uid, (en, dis, tl))
    civs[nm] = recs
w("  civs re-read: %d ; stage8 end exact=%s" % (len(civs), r2.pos == st8[2]))

xt = collections.Counter()
for fp in sorted(glob.glob(os.path.join(CTT, "*.json"))):
    civ = os.path.basename(fp)[:-5]
    dn = civalign.get(civ)
    recs = civs.get(dn, {})
    d = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    for nd in d["civ_techs_units"]:
        rec = recs.get(nd["Node ID"])
        if rec is None:
            xt[(nd["Node Status"], "no-dat-record")] += 1
        else:
            en, dis, tl = rec
            xt[(nd["Node Status"], "en=%d dis=%d" % (en, dis))] += 1
w("  NodeStatus x .dat(en,dis):")
for k in sorted(xt, key=str):
    w("     %-34s %-22s %d" % (k[0], k[1], xt[k]))
# does TrainLocation[1] explain JSON 'Building ID' for unit nodes?
bt = collections.Counter()
for fp in sorted(glob.glob(os.path.join(CTT, "*.json"))):
    civ = os.path.basename(fp)[:-5]
    dn = civalign.get(civ)
    recs = civs.get(dn, {})
    d = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    for nd in d["civ_techs_units"]:
        if nd.get("Node Type", "<MISSING>") not in ("Unit", "UnitUpgrade", "RegionalUnit", "UniqueUnit"):
            continue
        rec = recs.get(nd["Node ID"])
        if not rec:
            continue
        en, dis, tl = rec
        bids = [x[1] for x in tl]
        bt["BuildingID in TrainLocations" if nd["Building ID"] in bids
           else ("TrainLocations EMPTY" if not bids else "NOT in TrainLocations")] += 1
w("  JSON unit-node `Building ID` vs .dat TrainLocation building: %s" % dict(bt))
open(os.path.join(OUT, "s35_derivable2.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
