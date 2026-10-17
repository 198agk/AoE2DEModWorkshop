import os, io, json, re, sys, glob, struct, collections
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import parse_dat as P

OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
CTT = os.path.join(BASE, "CivTechTrees")
SRC = r"D:\Software\DeepSeek Harness\工作区2\_probe\source"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

# ============================================================ A. source cross-check
w("=" * 74)
w("A. genieutils / AGE SOURCE cross-check for tech-tree & node vocabulary")
w("=" * 74)
needles = ["civ_techs", "civ_techs_buildings", "civ_techs_units", "ResearchedCompleted",
           "ResearchRequired", "Node Status", "Picture Index", "Trigger Tech ID",
           "Prerequisite IDs", "Prerequisite Types", "Building in new column",
           "civTechTrees", "CivTechTrees", "TechTreeAge", "TechTreeUnit", "TechTreeBuilding",
           "tech_tree", "NodeType", "NodeStatus", "node_type", "node_status", "TriggerTech",
           "prereq", "Prerequisite", "enabling_research", "EnablingResearch", "LineMode",
           "UpperBuilding", "VerticalLine", "LocationInAge", "status_"]
hits = collections.OrderedDict()
for root, dirs, files in os.walk(SRC):
    for fn in files:
        if not fn.lower().endswith((".cpp", ".h", ".hpp", ".c", ".py", ".cs")):
            continue
        fp = os.path.join(root, fn)
        try:
            txt = open(fp, "r", encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        low = txt.lower()
        for nd in needles:
            if nd.lower() in low:
                hits.setdefault(nd, []).append(os.path.relpath(fp, SRC))
for nd in needles:
    lst = hits.get(nd, [])
    w("  %-24s %3d file(s)  %s" % (nd, len(lst), lst[:4]))

w("")
w("-- genieutils TechTree class field names (verbatim from source) --")
for pat in ("TechTreeAge", "TechTreeBuilding", "TechTreeUnit", "TechTreeResearch"):
    rgx = re.compile(r"(class|struct)\s+" + pat + r"\b.*?\n\};", re.S)
    for root, dirs, files in os.walk(SRC):
        for fn in files:
            if not fn.lower().endswith((".h", ".hpp", ".cpp")):
                continue
            fp = os.path.join(root, fn)
            txt = open(fp, "r", encoding="utf-8", errors="replace").read()
            m = rgx.search(txt)
            if m:
                w("  --- %s --- (%s)" % (pat, os.path.relpath(fp, SRC)))
                for ln in m.group(0).splitlines():
                    if ln.strip():
                        w("     " + ln.rstrip())
                break

# ============================================================ B. mod overrides
w("")
w("=" * 74)
w("B. Do any installed mods override CivTechTrees / dat-dir JSONs?")
w("=" * 74)
for root, dirs, files in os.walk(MODS):
    for fn in files:
        if fn.lower().endswith(".json") and "dat" in root.lower() and "_common" in root.lower():
            fp = os.path.join(root, fn)
            w("  MOD dat-dir json: %s  (%d B)" % (os.path.relpath(fp, MODS), os.path.getsize(fp)))
w("  -- any CivTechTrees dir in mods? --")
found = False
for root, dirs, files in os.walk(MODS):
    if os.path.basename(root).lower() == "civtechtrees":
        found = True
        w("    %s : %s" % (os.path.relpath(root, MODS), files))
if not found:
    w("    NONE")

# ============================================================ C. Name vs Name String ID
w("")
w("=" * 74)
w("C. CivTechTrees `Name` field vs `Name String ID`: stale or authoritative?")
w("=" * 74)
# load string table (english key-value)
ST = None
for cand in (os.path.join(GAME, "resources", "en", "strings", "key-value"),
             os.path.join(GAME, "resources", "en", "strings")):
    if os.path.isdir(cand):
        for fn in os.listdir(cand):
            if fn.startswith("key-value-strings"):
                ST = os.path.join(cand, fn); break
    if ST:
        break
w("  string table: %s" % ST)
strtab = {}
if ST:
    raw = open(ST, "rb").read().decode("utf-8-sig", errors="replace")
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0].isdigit():
            strtab[int(parts[0])] = parts[1].strip().strip('"')
w("  parsed %d string ids" % len(strtab))

conflicts = []
total = 0
for fp in sorted(glob.glob(os.path.join(CTT, "*.json"))):
    d = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    for lst in ("civ_techs_buildings", "civ_techs_units"):
        for n in d[lst]:
            total += 1
            nm, sid = n.get("Name"), n.get("Name String ID")
            if nm is None or sid is None:
                continue
            s = strtab.get(sid)
            if s is not None and s != nm:
                conflicts.append((os.path.basename(fp), lst, sid, nm, s))
w("  total nodes: %d ; Name-vs-table conflicts: %d" % (total, len(conflicts)))
civs = sorted(set(c[0] for c in conflicts))
w("  civs with conflicts (%d): %s" % (len(civs), civs))
for c in conflicts[:45]:
    w("     %-16s %-20s sid=%-7d Name=%-26r table=%r" % c)

# ============================================================ D. generator / version markers
w("")
w("=" * 74)
w("D. generator / version / do-not-edit markers inside the dat-dir JSONs")
w("=" * 74)
pat = re.compile(r'"[^"]*(version|Version|generator|Generator|generated|Generated|do not|Do not|DO NOT|_comment|Comment|Hints?|hint)[^"]*"')
for fn in sorted(os.listdir(BASE)):
    if not fn.lower().endswith(".json"):
        continue
    fp = os.path.join(BASE, fn)
    raw = open(fp, "rb").read(4000).decode("utf-8-sig", errors="replace")
    ms = set(m.group(0) for m in pat.finditer(raw))
    if ms:
        w("  %-38s %s" % (fn, sorted(ms)[:6]))

# ============================================================ E. train-location sanity
w("")
w("=" * 74)
w("E. .dat TrainLocation raw dump for known units (is `Building ID` the train building?)")
w("=" * 74)
def read_tl_cap(r):
    return (r.i16(), r.i16(), r.u8(), r.i32())
def read_creatable_cap(r):
    tl = []
    for _ in range(3):
        P.read_resource_cost(r)
    n = r.i16()
    for _ in range(n):
        tl.append(read_tl_cap(r))
    for _ in range(50):
        pass
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
w("  re-parse integrity: pos=%d vs stage8 end=%d ok=%s" % (r2.pos, st8[2], r2.pos == st8[2]))
br = civs["British"]
byid = {}
for u in br:
    byid.setdefault(u["id"], u)
for uid in (4, 8, 83, 448, 13, 21, 492, 93, 74):
    u = byid.get(uid)
    if u:
        w("  unit id=%-4d name=%-16s type=%-3d icon=%-4d train_locations=%s" % (
            uid, u["name"], u["type"], u["icon_id"], u.get("train_locations")))
w("  ref-vs-cap on id 4: ref icon=%s" % ([(x["id"], getattr(x, "get", lambda *a: None)("icon_id")) for x in st["civs"][0]["units"] if x["id"] == 4][:1]))
w("  NOTE: reference parser does not expose icon_id/train_locations, so this capture is validated only by byte-exactness.")

open(os.path.join(OUT, "s30_crosscheck.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
