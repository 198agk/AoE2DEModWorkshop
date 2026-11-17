import _gamepaths as GP
"""Nail down attack/armor semantics against well-known AoE2 stats.

parse_dat.read_type50() throws the Attack/Armor lists away, so this re-walks them
and prints them using the GAME'S OWN authoritative class table
(Tools_Builds/AGE3NamesV0007.ini [AoE2DEArmorNames]), then checks a set of
unambiguous, externally-known unit stats so we know the interpretation is right
rather than plausible.

Known AoE2 (DE) values used as ground truth:
  Archer      id 4   : pierce attack 4, melee 0 ; armour 0 melee / 0 pierce, range 4, LOS 6
  Skirmisher  id 7   : pierce attack 3, +4 vs Archers(class 15) ; armour 0/3
  Knight      id 38  : melee attack 10, armour 2 melee / 2 pierce
  Villager    id 83  : melee attack 3, armour 0/0
  Spearman    id 93  : melee attack 3, +15 vs Cavalry(class 8)
  Man-at-Arms id 75  : melee attack 6, +2 vs Eagle(class 29), armour 0/1
"""
import os, sys, io, json, struct, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P

BASE = GP.DAT
INI = os.path.join(GP.GAME, "Tools_Builds", "AGE3NamesV0007.ini")

# ---- authoritative class table straight from the game's own ini --------------
def load_ini_section(path, section):
    out = {}
    cur = None
    with open(path, "r", encoding="latin-1") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if line.startswith("[") and line.endswith("]"):
                cur = line[1:-1]
                continue
            if cur != section or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out

ARMOR = load_ini_section(INI, "AoE2DEArmorNames")
print("loaded %d armor class names from the game's own ini" % len(ARMOR))
# the ini numbers armour classes 0..36; the dat stores those numbers directly


def cn(c):
    return ARMOR.get(str(c), "Class %s" % c)


class Rec(object):
    def __init__(self, b, base, gv=P.GV_C32):
        self.b = b; self.o = base
        # version awareness: P.read_* branch on r.gv
        self.gv = gv

    def u8(self):
        v = self.b[self.o]; self.o += 1; return v
    def i16(self):
        v = struct.unpack_from("<h", self.b, self.o)[0]; self.o += 2; return v
    def i32(self):
        v = struct.unpack_from("<i", self.b, self.o)[0]; self.o += 4; return v
    def u32(self):
        v = struct.unpack_from("<I", self.b, self.o)[0]; self.o += 4; return v
    def f32(self):
        v = struct.unpack_from("<f", self.b, self.o)[0]; self.o += 4; return v
    def i16_array(self, n):
        return [self.i16() for _ in range(n)]
    def i32_array(self, n):
        return [self.i32() for _ in range(n)]
    def f32_array(self, n):
        return [self.f32() for _ in range(n)]
    def skip(self, n):
        self.o += n
    def debug_string(self):
        m = struct.unpack_from("<H", self.b, self.o)[0]; self.o += 2
        n = struct.unpack_from("<H", self.b, self.o)[0]; self.o += 2
        raw = self.b[self.o:self.o + n]; self.o += n
        return (m, n, raw.decode("latin-1"))
    def sized_string(self, n):
        raw = self.b[self.o:self.o + n]; self.o += n
        return raw.decode("latin-1")


def walk_unit(r):
    u = {}
    u["type"] = r.u8()
    u["id"] = r.i16()
    r.i32(); r.i32()                      # LanguageDLLName, Creation
    u["class"] = r.i16()
    r.i16_array(2)                        # StandingGraphic
    r.i16(); r.i16(); r.u8()              # Dying, Undead, UndeadMode
    u["hit_points"] = r.i16()
    u["line_of_sight"] = r.f32()
    r.u8()                                # GarrisonCapacity
    r.f32(); r.f32(); r.f32()             # CollisionSize
    r.i16(); r.i16(); r.i16(); r.i16()    # Train/Damage/Dead/Blood
    r.u8(); r.u8()                        # SortNumber, CanBeBuiltOn
    u["icon_id"] = r.i16()
    r.u8(); r.i16(); r.u8(); r.u8()       # HideInEditor, OldPortraitPict, Enabled, Disabled
    r.i16_array(2); r.i16_array(2)        # PlacementSideTerrain, PlacementTerrain
    r.f32(); r.f32()                      # ClearanceSize
    r.u8(); r.u8(); r.i16(); r.u8()       # HillMode, FogVisibility, TerrainRestriction, FlyMode
    r.i16(); r.f32()                      # ResourceCapacity, ResourceDecay
    r.u8(); r.u8(); r.u8(); r.u8(); r.u8()
    r.f32(); r.u8()                       # MultipleAttributeMode, MinimapColor
    r.i32(); r.i32()                      # LanguageDLLHelp, HotKeyText
    r.u8(); r.u8(); r.u8(); r.u8()
    r.u8(); r.u8(); r.u8()
    r.u8(); r.u8(); r.i16()
    r.u8(); r.u8()
    r.f32(); r.f32(); r.f32()             # OutlineSize
    r.i32(); r.i32()                      # scenario data
    for _ in range(3):
        P.read_resource_storage(r)
    for _ in range(r.u8()):
        P.read_damage_graphic(r)
    r.i16(); r.i16()                      # SelectionSound, DyingSound
    r.u32(); r.u32(); r.u32(); r.u32()    # Wwise
    r.u8(); r.u8()                        # OldAttackReaction, ConvertTerrain
    u["name"] = r.debug_string()[2]
    r.i16(); r.i16()                      # CopyID, BaseID

    t = u["type"]
    if t == P.UNIT_TYPE_AOE_TREES:
        return u
    if t >= P.UNIT_TYPE_FLAG:
        u["speed"] = r.f32()
    else:
        return u
    if t >= P.UNIT_TYPE_DEAD_FISH:
        P.read_dead_fish(r)
    if t >= P.UNIT_TYPE_BIRD:
        P.read_bird(r)
    if t >= P.UNIT_TYPE_COMBATANT:
        u["type50"] = {}
        t50 = u["type50"]
        t50["base_armor"] = r.i16()
        n = r.i16()
        t50["attacks"] = [{"class": r.i16(), "amount": r.i16()} for _ in range(n)]
        n = r.i16()
        t50["armors"] = [{"class": r.i16(), "amount": r.i16()} for _ in range(n)]
        r.i16()                              # DefenseTerrainBonus
        r.f32()                              # BonusDamageResistance
        t50["max_range"] = r.f32()
        r.f32()                              # BlastWidth
        t50["reload_time"] = r.f32()
        t50["projectile_unit_id"] = r.i16()
        t50["accuracy"] = r.i16()
        r.u8()                               # BreakOffCombat
        t50["frame_delay"] = r.i16()
        r.f32(); r.f32(); r.f32()            # GraphicDisplacement
        r.u8()                               # BlastAttackLevel
        t50["min_range"] = r.f32()
        r.f32()                              # AccuracyDispersion
        t50["attack_graphic"] = r.i16()
        t50["displayed_melee_armour"] = r.i16()
        t50["displayed_attack"] = r.i16()
        t50["displayed_range"] = r.f32()
        t50["displayed_reload_time"] = r.f32()
        r.f32(); r.f32(); r.f32()            # BlastDamage, DamageReflection, FriendlyFire
        r.i16(); r.f32(); r.i16()            # InterruptFrame, GarrisonFirepower, AttackGraphic2
    if t == P.UNIT_TYPE_PROJECTILE:
        P.read_projectile(r)
    if t >= P.UNIT_TYPE_CREATABLE:
        P.read_creatable(r)
    if t == P.UNIT_TYPE_BUILDING:
        P.read_building(r)
    return u


data, _ = P.load_dat(BASE)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
s = p.stats
stage8 = next(t for t in p.stage_offsets if t[0].startswith("8 Civs"))
CIVS_START = stage8[1] + 2

r = Rec(data, CIVS_START, gv=p.r.gv)
r.u8(); r.debug_string()          # player_type, name
nres = r.i16(); r.i16(); r.i16()  # resource count, ttid, tbid
r.f32_array(nres); r.u8()         # resources, icon_set
m = r.i16(); ptrs = r.i32_array(m)
byid = {}
for i in range(m):
    if ptrs[i]:
        u = walk_unit(r)
        byid[u["id"]] = u
print("walked civ[0] (%s): %d units, tail offset 0x%X" % (
    s["civs"][0]["name"], len(byid), r.o))
# cross-check vs the verified shallow parser
sh = {x["id"]: x for x in s["civs"][0]["units"]}
mism = [(i, byid[i]["hit_points"], sh[i]["hit_points"]) for i in byid if i in sh
        and byid[i]["hit_points"] != sh[i]["hit_points"]]
print("hp mismatches vs verified parser: %d" % len(mism))
assert not mism, mism[:5]

print("\n=== attacks / armors, using the game's own class table ===")
for uid in (4, 7, 38, 83, 93, 75):
    u = byid.get(uid)
    if not u:
        continue
    t = u["type50"]
    print("\n%-4s id=%-4s %-12r hp=%s  los=%.2f speed=%.2f range=%.2f reload=%.2f"
          % ("", uid, u["name"], u["hit_points"], u["line_of_sight"],
             u.get("speed", -1), t["max_range"], t["reload_time"]))
    for e in t["attacks"]:
        print("      ATTACK  class %-3s %-26s = %s" % (e["class"], cn(e["class"]), e["amount"]))
    for e in t["armors"]:
        print("      ARMOUR  class %-3s %-26s = %s" % (e["class"], cn(e["class"]), e["amount"]))

# ---- assertions against externally-known stats ------------------------------
def amt(u, kind, cls):
    return sum(e["amount"] for e in u["type50"][kind] if e["class"] == cls)


print("\n=== the dat's OWN 'displayed_*' fields (what the in-game UI shows) ===")
print("    (these exist because the engine lets a unit's shown attack differ "
      "from its raw list)\n")
for uid in (4, 7, 6, 38, 83, 93, 75, 8, 24):
    u = byid.get(uid)
    if not u:
        continue
    t = u["type50"]
    print("  id %-4s %-12r base_armor=%-3s displayed_attack=%-4s "
          "displayed_melee_armour=%-4s displayed_range=%-6s displayed_reload=%s"
          % (uid, u["name"], t["base_armor"], t["displayed_attack"],
             t["displayed_melee_armour"], t["displayed_range"],
             t["displayed_reload_time"]))

# Class 3 = Base Pierce, class 4 = Base Melee (game's own ini).  The base attack
# of a unit lives in the attack list under one of those two classes; every other
# class in the list is BONUS damage against that class.
print("\n=== class-3/4 rule: does the attack list encode base attack? ===")
for uid in (4, 7, 38, 83, 93, 75):
    u = byid[uid]
    t = u["type50"]
    pierce = amt(u, "attacks", 3)
    melee = amt(u, "attacks", 4)
    shown = t["displayed_attack"]
    base = max(pierce, melee)
    bon = [(e["class"], e["amount"]) for e in t["attacks"]
           if e["class"] not in (3, 4) and e["amount"]]
    print("  %-12r pierce=%-4s melee=%-4s -> base=%-4s | displayed_attack=%-4s | "
          "bonus=%s" % (u["name"], pierce, melee, base, shown, bon))

print("\n=== ground-truth assertions (values I am CERTAIN of) ===")
cases = [
    ("Archer",     4,  "attacks", 3,  4),    # base pierce attack 4
    ("Archer",     4,  "armors",  4,  0),    # 0 melee armour
    ("Archer",     4,  "armors",  3,  0),    # 0 pierce armour
    ("Knight",     38, "attacks", 4,  10),   # base melee attack 10
    ("Knight",     38, "armors",  4,  2),    # 2 melee armour
    ("Knight",     38, "armors",  3,  2),    # 2 pierce armour
    ("Villager",   83, "attacks", 4,  3),    # base melee attack 3
    ("Spearman",   93, "attacks", 4,  3),    # base melee attack 3
    ("Spearman",   93, "attacks", 8,  15),   # +15 vs Cavalry
    ("Spearman",   93, "armors",  3,  0),    # 0 pierce armour
]
hits = 0
for name, uid, kind, cls, want in cases:
    u = byid.get(uid)
    got = amt(u, kind, cls) if u else None
    good = got == want
    hits += good
    print("  %-12s id=%-3s %-7s class %-3s %-26s expect %-4s got %-4s %s"
          % (name, uid, kind, cls, cn(cls), want, got, "OK" if good else "MISMATCH"))
print("\n%d/%d ground-truth attack/armour values reproduced" % (hits, len(cases)))
