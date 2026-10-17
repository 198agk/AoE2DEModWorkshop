import os, io, json, sys
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import parse_dat as P

OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
BASE = r"D:\Games\Steam\steamapps\common\AoE2TS\..\_common\dat"
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
CTT = os.path.join(BASE, "CivTechTrees")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

# --- verbatim copy of parse_dat.read_creatable with a train-location capture ----
def read_train_location_cap(r):
    # parse_dat.read_train_location has NO return statement; capture the fields here
    a = r.i16(); b = r.i16(); c = r.u8(); d = r.i32()
    return (a, b, c, d)

def read_creatable_cap(r):
    tl = []
    for _ in range(3):
        P.read_resource_cost(r)
    n = r.i16()
    for _ in range(n):
        tl.append(read_train_location_cap(r))
    r.f32(); r.f32()
    r.u8(); r.u8()
    r.i32()
    r.i16(); r.i16()
    r.i16()
    r.i16()
    r.f32(); r.f32()
    r.i16(); r.i16()
    r.i16()
    r.i32(); r.u8(); r.f32()
    r.i16(); r.i32(); r.i32(); r.i16()
    r.f32(); r.f32(); r.f32()
    r.f32()
    r.u8()
    r.f32(); r.f32(); r.f32()
    r.i32()
    r.i32()
    r.u8()
    r.i16()
    return tl

# --- verbatim copy of parse_dat.read_unit, plus icon_id / train_locations -------
def read_unit_cap(r):
    u = {}
    u["type"] = r.u8()
    u["id"] = r.i16()
    r.i32()
    r.i32()
    u["class"] = r.i16()
    r.i16_array(2)
    r.i16()
    r.i16()
    r.u8()
    u["hit_points"] = r.i16()
    r.f32()
    r.u8()
    r.f32(); r.f32(); r.f32()
    r.i16()
    r.i16()
    r.i16()
    r.i16()
    r.u8(); r.u8()
    u["icon_id"] = r.i16()
    r.u8()
    r.i16()
    r.u8()
    r.u8()
    r.i16_array(2)
    r.i16_array(2)
    r.f32(); r.f32()
    r.u8()
    r.u8()
    r.i16()
    r.u8()
    r.i16()
    r.f32()
    r.u8(); r.u8(); r.u8(); r.u8(); r.u8()
    r.f32()
    r.u8()
    r.i32(); r.i32()
    r.u8(); r.u8(); r.u8(); r.u8()
    r.u8(); r.u8(); r.u8()
    r.u8(); r.u8(); r.i16()
    r.u8(); r.u8()
    r.f32(); r.f32(); r.f32()
    r.i32(); r.i32()
    for _ in range(3):
        P.read_resource_storage(r)
    dgc = r.u8()
    for _ in range(dgc):
        P.read_damage_graphic(r)
    r.i16(); r.i16()
    r.u32(); r.u32(); r.u32(); r.u32()
    r.u8(); r.u8()
    u["name"] = r.debug_string()[1]
    r.i16()
    r.i16()

    t = u["type"]
    if t == P.UNIT_TYPE_AOE_TREES:
        return u
    if t >= P.UNIT_TYPE_FLAG:
        r.f32()
    else:
        return u
    if t >= P.UNIT_TYPE_DEAD_FISH:
        P.read_dead_fish(r)
    if t >= P.UNIT_TYPE_BIRD:
        P.read_bird(r)
    if t >= P.UNIT_TYPE_COMBATANT:
        P.read_type50(r)
    if t == P.UNIT_TYPE_PROJECTILE:
        P.read_projectile(r)
    if t >= P.UNIT_TYPE_CREATABLE:
        u["train_locations"] = read_creatable_cap(r)
    if t == P.UNIT_TYPE_BUILDING:
        P.read_building(r)
    return u

def read_civ_cap(r):
    c = {}
    c["player_type"] = r.u8()
    c["name"] = r.debug_string()[1]
    n = r.i16()
    c["tech_tree_id"] = r.i16()
    c["team_bonus_id"] = r.i16()
    c["resources"] = r.f32_array(n)
    c["icon_set"] = r.u8()
    m = r.i16()
    ptrs = r.i32_array(m)
    c["units"] = []
    for i in range(m):
        if ptrs[i] != 0:
            c["units"].append(read_unit_cap(r))
    return c

data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()
st8off = [s for s in p.stage_offsets if s[0].startswith("8")][0][1]

r2 = P.Reader(data); r2.pos = st8off
n = r2.i16()
mine = {}
for _ in range(n):
    c = read_civ_cap(r2)
    mine[c["name"]] = c
ref = {c["name"]: c for c in st["civs"]}
bad = 0
for nm in ref:
    if len(ref[nm]["units"]) != len(mine[nm]["units"]):
        bad += 1; continue
    for a, b in zip(ref[nm]["units"], mine[nm]["units"]):
        if (a["type"], a["id"], a["class"], a["hit_points"], a["name"]) != (b["type"], b["id"], b["class"], b["hit_points"], b["name"]):
            bad += 1; break
w("VERIFY capture reader: civs mismatching reference = %d / %d  (0 == byte-exact)" % (bad, len(ref)))
w("  re-parse consumed input to pos=%d ; stage8 ended at 0x%X  end-of-civs ok=%s" % (
    r2.pos, [s for s in p.stage_offsets if s[0].startswith("8")][0][2], r2.pos == [s for s in p.stage_offsets if s[0].startswith("8")][0][2]))

# ------------------------------------------------------------------ derivability
from collections import Counter
w("\n" + "=" * 72)
w("DERIVABILITY TEST: are CivTechTrees node fields reproducible from the .dat?")
w("=" * 72)
glob = {}
for civdat, civfile in (("British", "BRITONS"), ("Aztecs", "AZTECS"), ("Mongols", "MONGOLS"),
                        ("French", "FRANKS"), ("Khitans", "KHITANS")):
    if civdat not in mine:
        w("\n--- SKIP %s (not a .dat civ name; .dat has %d civs)" % (civdat, len(mine)))
        continue
    units = mine[civdat]["units"]
    byid = {}
    for u in units:
        byid.setdefault(u["id"], u)
    d = json.loads(open(os.path.join(CTT, civfile + ".json"), "rb").read().decode("utf-8-sig"))
    nodes = d["civ_techs_units"]
    bnodes = d["civ_techs_buildings"]
    w("\n--- %s / %s.json : %d unit nodes + %d building nodes ; .dat civ has %d unit records" % (
        civdat, civfile, len(nodes), len(bnodes), len(units)))
    unitset = set(byid)
    present = [n for n in nodes if n["Node ID"] in unitset]
    absent = [n for n in nodes if n["Node ID"] not in unitset]
    w("  Node ID found among .dat civ unit ids: %d ; NOT found: %d" % (len(present), len(absent)))
    w("    sample not-found: %s" % [(n["Name"], n["Node ID"], n["Node Type"]) for n in absent[:6]])
    cmp1 = [(n["Node ID"], n["Picture Index"], byid[n["Node ID"]]["icon_id"]) for n in present]
    eq1 = sum(1 for a in cmp1 if a[1] == a[2])
    w("  Picture Index == .dat IconID : %d / %d   sample %s" % (eq1, len(cmp1), cmp1[:5]))
    ok2 = 0; tot2 = 0; ex2 = []
    for n in nodes:
        u = byid.get(n["Node ID"])
        if not u or "train_locations" not in u:
            continue
        tot2 += 1
        locs = [t[0] for t in u["train_locations"]]
        if n.get("Building ID") in locs:
            ok2 += 1
        elif len(ex2) < 5:
            ex2.append((n["Name"], n["Building ID"], locs))
    w("  Building ID in .dat TrainLocation bldg: %d / %d   mismatch e.g. %s" % (ok2, tot2, ex2))
    w("  units Node Status counts: %s" % dict(Counter(n["Node Status"] for n in nodes)))
    cr = {}
    for n in nodes:
        cr.setdefault(n["Node Status"], Counter())[
            "present" if n["Node ID"] in unitset else "ABSENT"] += 1
    w("  Node Status x (Node ID in .dat civ): %s" % {k: dict(v) for k, v in cr.items()})
    orders = {}
    for n in nodes:
        orders.setdefault(tuple(n.keys()), []).append(n["Name"])
    w("  units distinct key orders: %d" % len(orders))
    for o, names in list(orders.items()):
        w("     %2d nodes  %s   e.g. %s" % (len(names), list(o), names[:3]))
    bset = set(byid)
    bres = sum(1 for n in bnodes if n["Building ID"] in bset)
    w("  building Node ID present in .dat civ unit ids: %d / %d" % (bres, len(bnodes)))
    w("  building key order (first): %s" % list(bnodes[0].keys()))
    glob[civfile] = dict(units=len(nodes), bldgs=len(bnodes),
                         nodeid_present=len(present), nodeid_absent=len(absent),
                         pic_eq_icon=eq1, pic_tot=len(cmp1),
                         bldg_in_train=ok2, bldg_train_tot=tot2)

# ------------------------------------------------------------------ .dat TT status vocab
r3 = P.Reader(data); r3.pos = [s for s in p.stage_offsets if s[0].startswith("10")][0][1]
for _ in range(7):
    r3.i32()
ages_n = r3.u8(); bld_n = r3.u8(); unit_n = r3.i16(); res_n = r3.u8(); r3.i32()
def grp(r):
    k = r.u8()
    return list(r.i32_array(k)) if k else []
def cmn(r):
    r.i32(); r.i32_array(10); r.i32_array(10)
agest = []; bst = []; ust = []; rst = []
agelinks = []; bldlinks = []; unitlinks = []
for _ in range(ages_n):
    r3.i32(); agest.append(r3.u8()); grp(r3); grp(r3); grp(r3); cmn(r3); r3.u8(); r3.skip(10); r3.skip(10); r3.u8(); r3.i32()
for _ in range(bld_n):
    bid = r3.i32(); bst.append(r3.u8()); grp(r3); grp(r3); grp(r3); cmn(r3); r3.u8()
    r3.skip(P.AGES); r3.skip(P.AGES); r3.i32(); r3.i32()
for _ in range(unit_n):
    bid = r3.i32(); ust.append(r3.u8()); ub = r3.i32(); cmn(r3); vl = r3.i32()
    g = grp(r3); r3.i32(); r3.i32(); r3.i32(); r3.i32()
    if g:
        unitlinks.append((bid, g))
for _ in range(res_n):
    r3.i32(); rst.append(r3.u8()); r3.i32(); grp(r3); grp(r3); grp(r3); cmn(r3); r3.i32(); r3.i32(); r3.i32()
w("\n" + "=" * 72)
w(".dat TechTree Status byte vocabulary (same field the JSON calls Node Status)")
w("=" * 72)
w("ages  =%s" % dict(Counter(agest)))
w("bldgs =%s" % dict(Counter(bst)))
w("units =%s" % dict(Counter(ust)))
w("resch =%s" % dict(Counter(rst)))
w("all distinct .dat status bytes across the 4 tables: %s" % sorted(set(agest) | set(bst) | set(ust) | set(rst)))
w("JSON Node Status vocabulary (observed): ResearchedCompleted / ResearchRequired / NotAvailable / (None?)")
w("byte-exact tail: final pos=%d file=%d exact=%s" % (r3.pos, len(data), r3.pos == len(data)))
w("unit links in .dat tech-tree: %d entries, sample %s" % (len(unitlinks), unitlinks[:8]))

open(os.path.join(OUT, "s29_derivable.txt"), "w", encoding="utf-8").write(rep.getvalue())
json.dump(glob, open(os.path.join(OUT, "s29_derivable.json"), "w", encoding="utf-8"), indent=1)
print(rep.getvalue())
