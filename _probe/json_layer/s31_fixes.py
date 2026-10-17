import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, re, sys, glob, collections
sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
import parse_dat as P

OUT = _HERE_PATH("_probe", "json_layer")
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
CTT = os.path.join(BASE, "CivTechTrees")
SRC = _HERE_PATH("_probe", "source")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

# ---------- exact genieutils TechTree class bodies ----------
w("=" * 74)
w("A. genieutils TechTree.h class bodies (VERBATIM field names)")
w("=" * 74)
tt = open(os.path.join(SRC, "genieutils", "include", "genie", "dat", "TechTree.h"),
          encoding="utf-8", errors="replace").read()
for m in re.finditer(r"class\s+(TechTree\w*|BuildingConnection|UnitConnection|ResearchConnection)\s*(?::[^{]*)?\{(.*?)\n\};", tt, re.S):
    w("  --- class %s ---" % m.group(1))
    for ln in m.group(2).splitlines():
        s = ln.strip()
        if s and not s.startswith("//") and not s.startswith("virtual") and not s.startswith("static") \
           and not s.startswith("public") and not s.startswith("private") and not s.startswith("TechTree(") \
           and not s.startswith("~") and not s.startswith("setGameVersion") and not s.startswith("//"):
            w("     " + s)
# also the UnitConnection / BuildingConnection enums of Status
for m in re.finditer(r"enum\s+class\s+(\w+)\s*\{(.*?)\}", tt, re.S):
    w("  --- enum %s ---" % m.group(1))
    for ln in m.group(2).splitlines():
        if ln.strip():
            w("     " + ln.strip())

# ---------- corrected Building ID test + refined Name test ----------
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
    u["icon_id"] = r.i16(); r.u8(); r.i16(); r.u8(); r.u8(); r.i16_array(2); r.i16_array(2)
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
w("")
w("=" * 74)
w("B. CORRECTED: CivTechTrees Building ID == .dat TrainLocation element [1]?")
w("=" * 74)
w("  (TrainLocation tuple = (i16, i16, u8, i32); element[1] is the train building)")
for civdat, civfile in (("British", "BRITONS"), ("Aztecs", "AZTECS"), ("Mongols", "MONGOLS"), ("Khitans", "KHITANS")):
    byid = {}
    for u in civs[civdat]:
        byid.setdefault(u["id"], u)
    d = json.loads(open(os.path.join(CTT, civfile + ".json"), "rb").read().decode("utf-8-sig"))
    ok1 = ok0 = tot = 0; ex = []
    for nd in d["civ_techs_units"]:
        u = byid.get(nd["Node ID"])
        if not u or "train_locations" not in u:
            continue
        tot += 1
        e0 = [t[0] for t in u["train_locations"]]
        e1 = [t[1] for t in u["train_locations"]]
        if nd.get("Building ID") in e1: ok1 += 1
        if nd.get("Building ID") in e0: ok0 += 1
        if nd.get("Building ID") not in e1 and len(ex) < 5:
            ex.append((nd["Name"], nd["Building ID"], e1))
    w("  %-10s Building ID in TrainLocation[1]: %3d / %3d   (in [0]: %d)   mismatch %s" % (
        civfile, ok1, tot, ok0, ex))

# ---------- refined Name test ----------
w("")
w("=" * 74)
w("C. CivTechTrees `Name` vs string table, normalizing soft line breaks")
w("=" * 74)
ST = os.path.join(GAME, "resources", "en", "strings", "key-value", "key-value-strings-utf8.txt")
strtab = {}
for line in open(ST, "rb").read().decode("utf-8-sig", errors="replace").splitlines():
    if not line.strip() or line.lstrip().startswith("//"):
        continue
    parts = line.split(None, 1)
    if len(parts) == 2 and parts[0].isdigit():
        strtab[int(parts[0])] = parts[1].strip().strip('"')
def norm(s):
    return re.sub(r"\s+", " ", s.replace("\\n", " ")).strip().lower()
tot = 0; soft = 0; real = []
for fp in sorted(glob.glob(os.path.join(CTT, "*.json"))):
    d = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    for lst in ("civ_techs_buildings", "civ_techs_units"):
        for nd in d[lst]:
            nm, sid = nd.get("Name"), nd.get("Name String ID")
            if nm is None or sid is None:
                continue
            tot += 1
            s = strtab.get(sid)
            if s is None:
                real.append((os.path.basename(fp), lst, sid, nm, "<ID NOT IN en TABLE>"))
            elif s == nm:
                pass
            elif norm(s) == norm(nm):
                soft += 1
            else:
                real.append((os.path.basename(fp), lst, sid, nm, s))
w("  total nodes with both fields: %d" % tot)
w("  exact match: %d" % (tot - soft - len(real)))
w("  soft-break-only difference (\\n vs space / case): %d  <-- NOT staleness" % soft)
w("  TRUE mismatches: %d" % len(real))
civcount = collections.Counter(r[0] for r in real)
w("  civs with true mismatches: %s" % dict(civcount))
for r in real[:60]:
    w("     %-16s %-19s sid=%-7d Name=%-30r table=%r" % r)

open(os.path.join(OUT, "s31_fixes.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
