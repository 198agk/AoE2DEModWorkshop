import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, sys, collections, glob
sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
import parse_dat as P

OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
USER = r"C:\Users\26913\Games\Age of Empires 2 DE"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()

# ---------- 1. per-civ Enabled=1 sets: identical across civs? ----------
def walk_unit(r):
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
        return uid, en, dis
    if t >= P.UNIT_TYPE_FLAG:
        r.f32()
    else:
        return uid, en, dis
    if t >= P.UNIT_TYPE_DEAD_FISH: P.read_dead_fish(r)
    if t >= P.UNIT_TYPE_BIRD: P.read_bird(r)
    if t >= P.UNIT_TYPE_COMBATANT: P.read_type50(r)
    if t == P.UNIT_TYPE_PROJECTILE: P.read_projectile(r)
    if t >= P.UNIT_TYPE_CREATABLE:
        for _ in range(3):
            P.read_resource_cost(r)
        r.i16()
        while True:
            break
        return uid, en, dis
    if t == P.UNIT_TYPE_BUILDING: P.read_building(r)
    return uid, en, dis
def walk_creatable_tail(r):
    """read the creatable tail fully after costs+count consumed already"""
    pass

# simpler: reuse a complete reader
def full(r):
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
        return uid, en, dis
    if t >= P.UNIT_TYPE_FLAG:
        r.f32()
    else:
        return uid, en, dis
    if t >= P.UNIT_TYPE_DEAD_FISH: P.read_dead_fish(r)
    if t >= P.UNIT_TYPE_BIRD: P.read_bird(r)
    if t >= P.UNIT_TYPE_COMBATANT: P.read_type50(r)
    if t == P.UNIT_TYPE_PROJECTILE: P.read_projectile(r)
    if t >= P.UNIT_TYPE_CREATABLE:
        for _ in range(3):
            P.read_resource_cost(r)
        for _ in range(r.i16()):
            r.i16(); r.i16(); r.u8(); r.i32()
        r.f32(); r.f32(); r.u8(); r.u8(); r.i32(); r.i16(); r.i16(); r.i16(); r.i16()
        r.f32(); r.f32(); r.i16(); r.i16(); r.i16(); r.i32(); r.u8(); r.f32()
        r.i16(); r.i32(); r.i32(); r.i16(); r.f32(); r.f32(); r.f32(); r.f32(); r.u8()
        r.f32(); r.f32(); r.f32(); r.i32(); r.i32(); r.u8(); r.i16()
    if t == P.UNIT_TYPE_BUILDING: P.read_building(r)
    return uid, en, dis

st8 = [s for s in p.stage_offsets if s[0].startswith("8")][0]
r2 = P.Reader(data); r2.pos = st8[1]
nciv = r2.i16()
civflags = {}
for _ in range(nciv):
    r2.u8(); nm = r2.debug_string()[1]; n = r2.i16(); r2.i16(); r2.i16(); r2.f32_array(n); r2.u8()
    m = r2.i16(); ptrs = r2.i32_array(m)
    d = {}
    for i in range(m):
        if ptrs[i] != 0:
            uid, en, dis = full(r2)
            d[uid] = (en, dis)
    civflags[nm] = d
w("civs=%d ; stage8 exact=%s" % (len(civflags), r2.pos == st8[2]))
en_sets = {k: frozenset(i for i, (e, dd) in v.items() if e == 1) for k, v in civflags.items()}
cnt = collections.Counter(len(s) for s in en_sets.values())
w("  per-civ count of Enabled==1 units: %s" % dict(cnt))
distinct = set(en_sets.values())
w("  DISTINCT Enabled==1 sets across 63 civs = %d" % len(distinct))
first = next(iter(en_sets))
w("  sample set size=%d, first 20 ids=%s" % (len(first), sorted(first)[:20]))
# is the flag perhaps 'this unit is a valid base unit' (same for all)?
same = len(distinct) == 1
w("  -> .dat Enabled flag is %s across all civs" % ("IDENTICAL (not per-civ availability)" if same else "per-civ varying"))
# Gaia
if "Gaia" in en_sets:
    w("  Gaia enabled count=%d ; equal to British set? %s" % (len(en_sets["Gaia"]), en_sets["Gaia"] == en_sets.get("British")))

# ---------- 2. futuravailableunits: per-civ RequiredAge variation ---------
w("")
w("=" * 78)
w("2. futuravailableunits: is RequiredAge per-civ (=> not derivable from global .dat TechTree)?")
w("=" * 78)
fu = json.loads(open(os.path.join(BASE, "futuravailableunits.json"), "rb").read().decode("utf-8-sig"))
by_id = collections.defaultdict(dict)     # uid -> {civ: age}
by_id_kind = collections.defaultdict(dict)
for civ, v in fu.items():
    for b in v.get("Buildings", []):
        for u in b.get("Units", []):
            if "RequiredAge" in u:
                by_id[u["ID"]][civ] = u["RequiredAge"]
                by_id_kind[u["ID"]][civ] = "unit"
        for t in b.get("Techs", []):
            if isinstance(t, dict) and "RequiredAge" in t:
                by_id[t["ID"]][civ] = t["RequiredAge"]
                by_id_kind[t["ID"]][civ] = "tech"
multi = {k: v for k, v in by_id.items() if len(set(v.values())) > 1}
w("  distinct ids with RequiredAge: %d" % len(by_id))
w("  ids whose RequiredAge DIFFERS between civs: %d" % len(multi))
for k in list(multi)[:6]:
    w("     id=%-6s kind=%-5s %s" % (k, by_id_kind[k][list(by_id_kind[k])[0]],
                                     dict(list(multi[k].items())[:8])))
# also: how many civs list each id at all
cover = collections.Counter(len(v) for v in by_id.values())
w("  number of civs listing an id (histogram of counts): %s" % dict(sorted(cover.items())[:12]))

# ---------- 3. global .dat tech tree ages -> unit age ----------
w("")
w("=" * 78)
w("3. .dat global TechTree age membership vs JSON RequiredAge")
w("=" * 78)
tt_off = [s for s in p.stage_offsets if s[0].startswith("10")][0][1]
def grp(r):
    k = r.u8()
    return list(r.i32_array(k)) if k else []
def cmn(r):
    r.i32(); r.i32_array(10); r.i32_array(10)
r = P.Reader(data); r.pos = tt_off
for _ in range(7):
    r.i32()
n_age = r.u8(); n_bld = r.u8(); n_unit = r.i16(); n_res = r.u8(); r.i32()
AGE_UNITS = {}
for idx in range(n_age):
    aid = r.i32(); r.u8(); b = grp(r); u = grp(r); t = grp(r); cmn(r)
    r.u8(); r.raw(10); r.raw(10); r.u8(); r.i32()
    AGE_UNITS[idx + 1] = set(u)
dat_age = {}
for a in sorted(AGE_UNITS):
    for uid in AGE_UNITS[a]:
        dat_age.setdefault(uid, a)
agree = collections.Counter()
for k, v in by_id.items():
    if k in dat_age:
        agree["match" if all(x == dat_age[k] for x in v.values()) else "differ"] += 1
    else:
        agree["id not in .dat age lists"] += 1
w("  .dat age node unit lists: %s" % {k: len(v) for k, v in sorted(AGE_UNITS.items())})
w("  JSON RequiredAge vs .dat earliest-age membership: %s" % dict(agree))
w("  NOTE the .dat TechTree is GLOBAL (one table for all civs) -> it cannot express per-civ age")

# ---------- 4. user-side copies of these filenames ----------
w("")
w("=" * 78)
w("4. does the USER tree contain any of these JSONs (game-written settings)?")
w("=" * 78)
targets = ["hotkeys.json", "selection_group_def.json", "chronicles_selection_group_def.json",
           "civilizations.json", "linkedTechs.json", "linkedUnits.json", "unitlines.json",
           "dropsites.json", "sharedbuildings.json", "objreplacement.json", "unitcategories.json",
           "maps.json", "sounds.json", "buttons.json", "eras.json", "AIConsts.json",
           "airesourcetypes.json", "futuravailableunits.json", "civTechTrees.json",
           "adapterblacklist.json", "morematerials.json", "materials.json"]
found = collections.defaultdict(list)
for root, dirs, files in os.walk(USER):
    for fn in files:
        if fn.lower() in targets or fn.lower().startswith(("hotkeys", "selection_group")):
            found[fn].append(os.path.join(root, fn))
for k in sorted(found):
    for fp in found[k]:
        w("  %-36s %9d  %s" % (k, os.path.getsize(fp), fp))
w("  (%d distinct names)" % len(found))
open(os.path.join(OUT, "s39_decisive.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
