import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, sys
sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
import parse_dat as P

OUT = _HERE_PATH("_probe", "json_layer")
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
CTT = os.path.join(BASE, "CivTechTrees")
POMP = r"D:\Games\Steam\steamapps\common\AoE2DE\modes\Pompeii\resources\_common\dat"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

# ---- 1. civilizations.json tech_tree_name vs CivTechTrees filenames
civj = json.loads(open(os.path.join(BASE, "civilizations.json"), "rb").read().decode("utf-8-sig"))
ttn = [c["tech_tree_name"] for c in civj["civilization_list"]]
files = sorted(f[:-5] for f in os.listdir(CTT) if f.endswith(".json"))
w("civilizations.json records: %d" % len(civj["civilization_list"]))
w("tech_tree_name values  (%d): %s" % (len(ttn), ttn))
w("CivTechTrees files      (%d): %s" % (len(files), files))
w("tech_tree_name NOT having a file: %s" % [t for t in ttn if t not in files])
w("files NOT in tech_tree_name    : %s" % [f for f in files if f not in ttn])
w("exact set match: %s" % (set(ttn) == set(files)))
w("order identical: %s" % (ttn == files))

# ---- 2. dat tech-tree ID sets
data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()
r = P.Reader(data); r.pos = [s for s in p.stage_offsets if s[0].startswith("10")][0][1]
r.i32(); r.i32(); r.i32(); r.i32(); r.i32(); r.i32(); r.i32()
ages_n = r.u8(); bld_n = r.u8(); unit_n = r.i16(); res_n = r.u8(); tug = r.i32()
def grp(r):
    n = r.u8(); return list(r.i32_array(n)) if n else []
def cmn(r):
    r.i32(); r.i32_array(10); r.i32_array(10)
for _ in range(ages_n):
    r.i32(); r.u8(); grp(r); grp(r); grp(r); cmn(r); r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()
dat_bld = []
for _ in range(bld_n):
    dat_bld.append(r.i32()); r.u8(); grp(r); grp(r); grp(r); cmn(r); r.u8(); r.skip(P.AGES); r.skip(P.AGES); r.i32(); r.i32()
dat_unit = []
dat_unit_grp = {}
for _ in range(unit_n):
    uid = r.i32(); dat_unit.append(uid); r.u8(); r.i32(); cmn(r); r.i32()
    g = grp(r); dat_unit_grp[uid] = g
    r.i32(); r.i32(); r.i32(); r.i32()
dat_res = []
for _ in range(res_n):
    dat_res.append(r.i32()); r.u8(); r.i32(); grp(r); grp(r); grp(r); cmn(r); r.i32(); r.i32(); r.i32()
w("\n.dat techtree: bld=%d unit=%d res=%d final==file: %s" % (len(dat_bld), len(dat_unit), len(dat_res), r.pos == len(data)))
D_BLD, D_UNIT, D_RES = set(dat_bld), set(dat_unit), set(dat_res)
w(".dat tech-tree bld IDs (%d): %s" % (len(D_BLD), sorted(D_BLD)))
w(".dat tech-tree res IDs (%d)" % len(D_RES))
w(".dat unit connections carrying a group: %s" % {k: v for k, v in list(dat_unit_grp.items()) if v})

# ---- 3. each CivTechTrees file vs dat id sets
w("\n%-14s %5s %5s %6s %6s %5s %5s %6s %6s" % ("CIV", "#bld", "#unit", "bld<=dat", "bldNOT", "u<=dat", "uNOT", "resIn", "ageIDs"))
rows = []
for f in files:
    d = json.loads(open(os.path.join(CTT, f + ".json"), "rb").read().decode("utf-8-sig"))
    b = d["civ_techs_buildings"]; u = d["civ_techs_units"]
    bid = [n.get("Building ID") for n in b]
    uid = [n.get("Node ID") for n in u]
    bs, us = set(bid), set(uid)
    bn = sorted(bs - D_BLD); un = sorted(us - D_UNIT)
    ages = sorted(set(n.get("Age ID") for n in b + u))
    rows.append((f, len(b), len(u), len(bs & D_BLD), bn, len(us & D_UNIT), un, ages))
    w("%-14s %5d %5d %6d %6s %5d %6s %6s %6s" % (f, len(b), len(u), len(bs & D_BLD), bn[:4], len(us & D_UNIT), un[:4], "", ages))
allb = set(); allu = set()
for f in files:
    d = json.loads(open(os.path.join(CTT, f + ".json"), "rb").read().decode("utf-8-sig"))
    allb |= set(n.get("Building ID") for n in d["civ_techs_buildings"])
    allu |= set(n.get("Node ID") for n in d["civ_techs_units"])
w("\nunion of all CivTechTrees Building IDs: %d  outside .dat bld set: %s" % (len(allb), sorted(allb - D_BLD)))
w("union of all CivTechTrees Node IDs    : %d  outside .dat unit set: %s" % (len(allu), sorted(allu - D_UNIT)[:40]))
w("union covers .dat unit-techtree ids? missing %d  e.g. %s" % (len(D_UNIT - allu), sorted(D_UNIT - allu)[:40]))
w("union covers .dat building ids?     missing %d  e.g. %s" % (len(D_BLD - allb), sorted(D_BLD - allb)))

# ---- 4. Pompeii per-civ schema
w("\n--- Pompeii CivTechTrees schema")
pf = sorted(os.listdir(os.path.join(POMP, "CivTechTrees")))
w("files: %s" % pf)
for f in pf[:3]:
    d = json.loads(open(os.path.join(POMP, "CivTechTrees", f), "rb").read().decode("utf-8-sig"))
    w("  %s top keys=%s" % (f, list(d.keys())))
    n = d["civ_techs_buildings"][0]
    w("    first bld node keys: %s" % list(n.keys()))
    n2 = d["civ_techs_units"][0]
    w("    first unit node keys: %s" % list(n2.keys()))
mono = json.loads(open(os.path.join(POMP, "civTechTrees.json"), "rb").read().decode("utf-8-sig"))
w("Pompeii civTechTrees.json top keys=%s civs=%d" % (list(mono.keys()), len(mono["civs"])))
w("  civ_ids: %s" % [c["civ_id"] for c in mono["civs"]])
w("  first bld node keys: %s" % list(mono["civs"][0]["civ_techs_buildings"][0].keys()))
w("  first unit node keys: %s" % list(mono["civs"][0]["civ_techs_units"][0].keys()))
# keyset diff
kper = set()
for f in pf:
    d = json.loads(open(os.path.join(POMP, "CivTechTrees", f), "rb").read().decode("utf-8-sig"))
    for n in d["civ_techs_buildings"] + d["civ_techs_units"]:
        kper |= set(n.keys())
kmon = set()
for c in mono["civs"]:
    for n in c["civ_techs_buildings"] + c["civ_techs_units"]:
        kmon |= set(n.keys())
w("\nPompeii per-civ node keys (%d): %s" % (len(kper), sorted(kper)))
w("Pompeii mono  node keys (%d): %s" % (len(kmon), sorted(kmon)))
w("mono-only keys: %s" % sorted(kmon - kper))
w("per-civ-only keys: %s" % sorted(kper - kmon))

open(os.path.join(OUT, "s27_ctt_join.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[1200:9000])
