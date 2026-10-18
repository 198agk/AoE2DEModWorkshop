"""locate.py -- find and mark the byte offsets of unit records.

VENDORED from _probe/datparse/intent_patch.py by tools/sync_engine.py
(the demo main() and its __main__ guard are trimmed).  Do not edit here;
edit the research copy and re-run the sync, or the verification lineage
is lost.

``locate(data)`` returns ``(civs, civs_start, gv, tail)`` and
``find_units(civs, unit_id)`` returns every per-civ physical record.
"""

import os, sys, io, json, struct, zlib, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from . import parser as P

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
OUT = os.path.join(HERE, "out_intent")
SEM = os.path.join(os.path.dirname(HERE), "semantic", "unit_names.json")

# ---------------------------------------------------------------------------
# THE INTENT.  This is the entire "user interface" of this demo.
# ---------------------------------------------------------------------------
INTENT = {
    "say":      "弓箭手攻击力 +2",
    "match_en": "Archer",
    "unit_id":  4,
    "field":    "attack",
    "delta":    +2,
}


class Orec(object):
    """Byte reader that also records the offset of every field we care about."""

    def __init__(self, b, base, gv=P.GV_C32):
        self.b = b
        self.o = base
        self.marks = {}
        # version awareness: read_creatable/read_tech/... branch on r.gv.
        # Default keeps the DE/C32 fast path; callers parsing a legacy stream
        # must pass the gv the real parser resolved.
        self.gv = gv

    def at(self, k):
        self.marks[k] = self.o
        return self.o

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
        # Contract: MUST match parse_dat.Reader.debug_string() -- a 2-tuple
        # (marker, text).  The authoritative read_* functions do
        # `r.debug_string()[1]` and are routinely handed this reader (walk_unit
        # calls P.read_bird/P.read_creatable), so a different arity here
        # silently returns the length integer instead of the name.
        m = struct.unpack_from("<H", self.b, self.o)[0]; self.o += 2
        n = struct.unpack_from("<H", self.b, self.o)[0]; self.o += 2
        # Same duck-type contract as parse_dat.Reader: read_graphic() reads the
        # stored width from here so a writer can re-emit the string at a
        # different length.  Omitting it makes that read raise AttributeError.
        self.last_string_len = n
        raw = self.b[self.o:self.o + n]; self.o += n
        z = raw.find(b"\x00")
        if z >= 0:
            raw = raw[:z]
        return (m, raw.decode("latin-1"))
    def sized_string(self, n):
        raw = self.b[self.o:self.o + n]; self.o += n
        return raw.decode("latin-1")


def walk_unit(r, ci):
    """Mirror genieutils Unit::serializeObject(), recording field offsets."""
    r.marks = {}
    u = {"civ": ci}
    u["type"] = r.u8()
    u["id"] = r.i16()
    # LanguageDLLName is the display-name string id.  It is NOT a cosmetic field:
    # age variants of one building (Barracks 12/498/132/20) all carry the SAME id
    # here, while two genuinely different units carry different ids.  The
    # age-family rule needs it to tell "another age of this building" apart from
    # "a different building that happens to share a name".
    u["_dll_name"] = r.i32()                  # LanguageDLLName
    r.i32()                                   # Creation
    u["_dll_names"] = {u["_dll_name"]}         # set form, for the family rule
    # Default 0 so an early-returning record type still carries the key; the
    # bird block below overwrites it with the real value.  See the note on
    # parse_dat.read_bird: the engine swaps the live record to another unit with
    # the same TaskSwapGroup when a villager is retasked, so an edit that misses
    # the sibling records silently stops applying.
    u["task_swap_group"] = 0
    u["class"] = r.i16()
    # StandingGraphic: the FIRST int16 indexes the .dat's graphics array BY THE
    # RECORD'S OWN `id` FIELD (measured: 89.8% of units land on a real .sld,
    # vs 57.7% if the array is indexed by position), and the graphics record's
    # `file` string + ".sld" is the file under resources/_common/drs/graphics/.
    # That is the unit -> sprite index the project assumed it had to guess from
    # filename conventions.  Keep the pair so callers can resolve it.
    u["standing_graphic"] = list(r.i16_array(2))     # StandingGraphic
    r.i16(); r.i16(); r.u8()                  # Dying, Undead, UndeadMode
    r.at("hit_points")
    u["hit_points"] = r.i16()
    r.at("line_of_sight")
    u["line_of_sight"] = r.f32()
    r.at("garrison_capacity")
    u["garrison_capacity"] = r.u8()
    r.f32(); r.f32(); r.f32()                 # CollisionSize
    r.i16(); r.i16(); r.i16(); r.i16()        # Train/Damage/Dead/Blood
    r.at("sort_number")
    u["sort_number"] = r.u8()
    r.u8()                                    # CanBeBuiltOn
    u["icon_id"] = r.i16()
    r.u8(); r.i16(); r.u8(); r.u8()
    r.i16_array(2); r.i16_array(2)
    r.f32(); r.f32()
    r.u8(); r.u8(); r.i16(); r.u8()
    r.i16(); r.f32()
    r.u8(); r.u8(); r.u8(); r.u8(); r.u8()
    r.f32(); r.u8()
    r.i32(); r.i32()
    # Unit.cpp:128 -- pre-C30 carriers hold an extra hotkey int32 that the engine
    # copies into Creatable.HotKeyFromUnit.  This guard MUST mirror
    # parse_dat.read_unit() exactly; without it every legacy record (VER 7.8 and
    # older) over-consumes 4 bytes and the whole civ walk desynchronises.
    if r.gv < P.GV_C30:
        r.i32()
    r.u8(); r.u8(); r.u8(); r.u8()
    r.u8(); r.u8(); r.u8()
    r.u8(); r.u8(); r.i16()
    r.u8(); r.u8()
    r.f32(); r.f32(); r.f32()
    r.i32(); r.i32()
    for _ in range(3):
        P.read_resource_storage(r)
    for _ in range(r.u8()):
        P.read_damage_graphic(r)
    r.i16(); r.i16()
    r.u32(); r.u32(); r.u32(); r.u32()
    r.u8(); r.u8()
    u["name"] = r.debug_string()[1]
    r.i16(); r.i16()

    t = u["type"]
    if t == P.UNIT_TYPE_AOE_TREES:
        u["_offs"] = dict(r.marks); return u
    if t >= P.UNIT_TYPE_FLAG:
        r.at("speed")
        u["speed"] = r.f32()
    else:
        u["_offs"] = dict(r.marks); return u
    if t >= P.UNIT_TYPE_DEAD_FISH:
        P.read_dead_fish(r)
    if t >= P.UNIT_TYPE_BIRD:
        u["task_swap_group"] = P.read_bird(r)
    if t >= P.UNIT_TYPE_COMBATANT:
        t50 = {}
        r.at("t50_start")
        r.i16()                               # base_armor (10000 sentinel)
        n = r.i16()
        atk = []
        for _ in range(n):
            a = {"_off_class": r.at("x")}
            c = r.i16()
            a["_off_amount"] = r.at("x")
            v = r.i16()
            a["class"] = c; a["amount"] = v
            atk.append(a)
        t50["attacks"] = atk
        n = r.i16()
        arm = []
        for _ in range(n):
            a = {"_off_class": r.at("x")}
            c = r.i16()
            a["_off_amount"] = r.at("x")
            v = r.i16()
            a["class"] = c; a["amount"] = v
            arm.append(a)
        t50["armors"] = arm
        r.at("defense_terrain_bonus")
        t50["defense_terrain_bonus"] = r.i16()
        r.at("bonus_damage_resistance")
        t50["bonus_damage_resistance"] = r.f32()
        r.at("max_range")
        t50["max_range"] = r.f32()
        r.at("blast_width")
        t50["blast_width"] = r.f32()
        r.at("reload_time")
        t50["reload_time"] = r.f32()
        r.at("projectile_unit_id")
        t50["projectile_unit_id"] = r.i16()
        r.at("accuracy")
        t50["accuracy"] = r.i16()
        r.at("break_off_combat")
        t50["break_off_combat"] = r.u8()
        r.at("frame_delay")
        t50["frame_delay"] = r.i16()
        r.f32(); r.f32(); r.f32()
        r.u8()
        r.at("min_range")
        t50["min_range"] = r.f32()
        r.f32()
        r.at("attack_graphic")
        t50["attack_graphic"] = r.i16()
        r.at("displayed_melee_armour")
        t50["displayed_melee_armour"] = r.i16()
        r.at("displayed_attack")
        t50["displayed_attack"] = r.i16()
        r.at("displayed_range")
        t50["displayed_range"] = r.f32()
        r.at("displayed_reload_time")
        t50["displayed_reload_time"] = r.f32()
        # Type50.cpp:94/99/105 -- three independent version guards.  Mirror
        # parse_dat.read_type50() exactly; reading all three unconditionally
        # over-consumes 16 bytes on every record older than GV_C27.
        if P.GV_C20 <= r.gv <= P.GV_LatestDE2:
            r.f32()                               # BlastDamage
        if P.GV_C22 <= r.gv <= P.GV_LatestDE2:
            r.f32(); r.f32()                      # DamageReflection, FriendlyFireDamage
        if P.GV_C27 <= r.gv <= P.GV_LatestDE2:
            r.i16(); r.f32(); r.i16()             # InterruptFrame, GarrisonFirepower, AttackGraphic2
        u["type50"] = t50
    if t == P.UNIT_TYPE_PROJECTILE:
        P.read_projectile(r)
    if t >= P.UNIT_TYPE_CREATABLE:
        # Creatable.cpp:56 writes 3 x ResourceCost(i16 Type, i16 Amount,
        # i16 Flag) -- ResourceUsage.h:58 -- then the TrainLocation list.
        # Walk it with the UNMODIFIED reader for byte fidelity, then re-read
        # just the few fields the intent schema exposes, from a second cursor
        # parked at the recorded start.  Never hand-inline this layout: the
        # sub-reads stay a pure function of the recorded start offset.
        u["_creatable_start"] = r.o
        P.read_creatable(r)
        u["_creatable_end"] = r.o
        sub = Orec(r.b if hasattr(r, "b") else r.data, u["_creatable_start"], gv=r.gv)
        costs = []
        for _ in range(3):
            c = {"type": sub.i16()}
            c["_off_amount"] = sub.at("x")
            c["amount"] = sub.i16()
            c["flag"] = sub.i16()
            costs.append(c)
        u["costs"] = costs
        tl = []
        if P.GV_C29 <= r.gv <= P.GV_LatestDE2:
            n = sub.i16()
            for _ in range(n):
                d = {"_off_train_time": sub.at("x")}
                d["train_time"] = sub.i16()
                d["unit_id"] = sub.i16()
                d["button_id"] = sub.u8()
                if P.GV_C30 <= r.gv <= P.GV_LatestDE2:
                    sub.i32()                         # HotKeyID
                tl.append(d)
        else:
            d = {"_off_train_time": sub.at("x")}
            d["train_time"] = sub.i16()
            d["unit_id"] = sub.i16()
            d["button_id"] = sub.u8()
            tl.append(d)
        u["train_locations"] = tl
        u["_creatable_head_end"] = sub.o
        # DisplayedPierceArmour is the LAST field of Creatable
        # (Creatable.cpp: serializeSub costs, train locations, then a long tail
        # ending in DisplayedPierceArmour).  Derive it from the authoritative
        # recorded end rather than re-walking the tail.  NOTE: the head sub-walk
        # above deliberately stops after the train-location list, so it does NOT
        # reach _creatable_end -- comparing the two would be a false alarm.
        u["_off_displayed_pierce_armour"] = u["_creatable_end"] - 2
        u["displayed_pierce_armour"] = struct.unpack_from(
            "<h", sub.b, u["_off_displayed_pierce_armour"])[0]
        # DisplayedPierceArmour is the LAST field of Creatable (Creatable.cpp) --
        # derive its offset from the recorded end rather than re-walking.
        u["_off_displayed_pierce_armour"] = u["_creatable_end"] - 2
        u["displayed_pierce_armour"] = struct.unpack_from(
            "<h", sub.b, u["_off_displayed_pierce_armour"])[0]
    if t == P.UNIT_TYPE_BUILDING:
        P.read_building(r)
    u["_offs"] = dict(r.marks)
    return u


def walk_civ(r, ci):
    c = {"index": ci}
    c["player_type"] = r.u8()
    c["name"] = r.debug_string()[1]
    n = r.i16()
    c["tech_tree_id"] = r.i16()
    c["team_bonus_id"] = r.i16()
    r.f32_array(n)
    r.u8()                                    # icon_set
    m = r.i16()
    ptrs = r.i32_array(m)
    c["unit_pointers_total"] = m
    units = []
    for i in range(m):
        if ptrs[i] != 0:
            units.append(walk_unit(r, ci))
    c["units"] = units
    return c


def walk_tech(r):
    """Mirror genieutils Research::serializeObject(), recording field offsets.

    A tech is GLOBAL -- there is one physical record per tech id, not one per
    civilization -- so unlike ``walk_unit`` this is called once each.
    """
    r.marks = {}
    t = {}
    # ★★ RequiredTechs is the AGE GATE of a technology, and it was being read
    # and thrown away.  A tech is applied once every entry here is satisfied:
    # tech 104 'Dark Age' is satisfied at 0:00 (it is the starting age), while
    # 102 'Feudal Age', 103 'Imperial Age' and 266 'Castle built' are not.
    # Measured on the British anchors, which is why v5/v6 failed: tech 383
    # 'C-Bonus, +25% Shepherd' has [] and takes effect at 0:00; tech 263
    # 'Longbow (make avail)' has [102, 266] and therefore cannot fire before a
    # Castle exists -- so a unit grant hung on 263 produced a Barracks button
    # only AFTER the user built one.  `tech 1350 'Champi Scout (Make avail)'`,
    # the anchor the game itself uses, has [104] and likewise fires at 0:00.
    # Keeping the field is what lets a caller pick an anchor that fires at game
    # start instead of inferring it from the tech's name or its location.
    t["required_techs"] = [x for x in r.i16_array(6) if x != -1]
    # Research.cpp:61 -- ALWAYS exactly 3 ResourceUsage<int16,int16,uint8>
    # records (Tech::Tech() does ResourceCosts(3)); each is 5 bytes, Type first.
    # These are the first thing in the record, so a cost edit needs no walk of
    # the rest.  Recorded per slot: an empty slot is a real, load-bearing thing
    # -- (-1,0,0) is the sentinel and a (0,0,0)/(0,0,1) placeholder is legal --
    # so the compiler gets the raw triple and decides, instead of this walker
    # guessing which slot "is" the cost.
    t["costs"] = []
    for _i in range(3):
        c = {"type": r.i16()}
        c["_off_amount"] = r.at("cost[%d].amount" % _i)
        c["amount"] = r.i16()
        c["flag"] = r.u8()                    # 1 = paid, 0 = only needed, 2 = seen
        t["costs"].append(c)
    r.i16()                                   # RequiredTechCount
    t["civ"] = r.i16()
    r.i16()                                   # FullTechMode
    # Research.cpp:70 -- folded into ResearchLocations for gv >= GV_C31
    if r.gv < P.GV_C31:
        r.i16()                               # ResearchLocation
    # Research.cpp:73-87 -- i32 pair for DE (gv >= GV_C18), else u16 pair
    if r.gv >= P.GV_MATT:
        if P.GV_C18 <= r.gv <= P.GV_LatestDE2:
            r.i32(); r.i32()                  # LanguageDLLName, Description
        else:
            r.i16(); r.i16()
    # Research time has TWO storage shapes and the binding must tolerate both:
    #   * gv <  GV_C31 -- one scalar in the record (the legacy shape)
    #   * gv >= GV_C31 -- an explicit ResearchLocations array; every entry
    #     carries its own copy and they must all be updated together or the
    #     copies end up disagreeing.
    t["_off_research_time"] = None
    t["research_time"] = None
    if r.gv < P.GV_C31:
        t["_off_research_time"] = r.at("research_time")
        t["research_time"] = r.i16()
    t["effect_id"] = r.i16()
    t["type"] = r.i16()
    t["icon_id"] = r.i16()
    if r.gv < P.GV_C31:
        r.u8()                                # ButtonID
    r.i32()                                   # LanguageDLLHelp
    r.i32()                                   # LanguageDLLTechTree
    if r.gv < P.GV_C31:
        r.i32()                               # HotKey (deprecated by the array)
    t["name"] = r.debug_string()[1]
    if P.GV_C15 <= r.gv <= P.GV_LatestDE2:
        r.u8()                                # Repeatable
    if P.GV_C31 <= r.gv <= P.GV_LatestDE2:
        n = r.i16()
        locs = []
        for _ in range(n):
            d = {}
            d["location_id"] = r.i16()
            d["_off_research_time"] = r.at("x")
            d["research_time"] = r.i16()
            d["button_id"] = r.u8()
            d["hotkey_id"] = r.i32()
            locs.append(d)
        t["research_locations"] = locs
    else:
        # Research.cpp:137-148 -- pre-C31 keeps the scalars; the engine
        # re-packs them into one ResearchLocation at read time with no bytes
        # on the wire, so there is nothing here to offset.
        t["research_locations"] = None
    return t


def locate_techs(data, tail, gv):
    """Walk the tech section.  ``tail`` is the byte just past the last civ.

    The section is an ``i16`` count followed by that many records.  Every
    dataset we have puts the count exactly at ``locate()``'s returned ``tail``,
    so the compiler can reuse the tail it already holds and never needs to
    consult the parser's stage table.
    """
    r = Orec(data, tail, gv=gv)
    n = r.i16()
    return [walk_tech(r) for _ in range(n)]


def find_techs(techs, tech_id):
    """The tech record for ``tech_id`` as ``[(index, tech), ...]``.

    A tech is addressed by its POSITION in the array -- the record carries no
    id field -- so this is a positional lookup.  It returns a list for the same
    reason ``find_units`` does: callers must not have to know that.
    """
    if 0 <= tech_id < len(techs):
        return [(tech_id, techs[tech_id])]
    return []


def diff_regions(a, b, chunk=1 << 16):
    """Contiguous byte ranges that differ, found chunk-wise for speed."""
    n = min(len(a), len(b))
    out = []
    for base in range(0, n, chunk):
        end = min(base + chunk, n)
        if a[base:end] == b[base:end]:
            continue
        i = base
        while i < end:
            if a[i] != b[i]:
                j = i
                while j < end and a[j] != b[j]:
                    j += 1
                out.append((i, j - i))
                i = j
            else:
                i += 1
    return out


def locate(data, parser=None):
    """Locate every civ's unit records in a decompressed .dat stream.

    Returns ``(civs, civs_start, gv, tail)``.  This is the single entry point
    the product uses; ``main()`` below is only the human-facing demo that
    exercises it.  Passing an already-parsed ``parser`` avoids parsing twice.
    """
    p = parser
    if p is None:
        p = P.Parser(data)
        with contextlib.redirect_stdout(io.StringIO()):
            p.parse()
    if p.r.pos != len(data):
        raise SystemExit("parse did not consume the stream: %d/%d, leftover %d"
                         % (p.r.pos, len(data), len(data) - p.r.pos))
    stage8 = next(t for t in p.stage_offsets if t[0].startswith("8 Civs"))
    n_civ = struct.unpack_from("<h", data, stage8[1])[0]
    civs_start = stage8[1] + 2
    r = Orec(data, civs_start, gv=p.r.gv)
    civs = [walk_civ(r, ci) for ci in range(n_civ)]
    return civs, civs_start, p.r.gv, r.o


def find_units(civs, unit_id):
    """Every physical record for ``unit_id``: [(civ_index, civ_name, unit), ...].

    The same logical unit exists once per civilization that owns it -- 63 for
    the Archer, fewer for units some civs lack -- so callers must treat the
    list, not the first hit, as the thing being edited.
    """
    return [(c["index"], c["name"], u)
            for c in civs for u in c["units"] if u["id"] == unit_id]


# ---------------------------------------------------------------------------
# EFFECTS.  A technology's actual gameplay effect lives in this array, NOT in
# the tech record (which only carries `effect_id`).  The parser reads effects
# but records NO offsets for them -- `read_effect` never calls `r.at()` -- so
# until this walker existed there was no byte to write to and "change what a
# tech does" was impossible.  Mirrors parse_dat.read_effect/read_effect_command
# so the two agree byte for byte.
# ---------------------------------------------------------------------------
def walk_effect(r, ei):
    """One Effect: an i16 command count wrapped in a debug string.

    Marks every command field.  The count and the name are NOT marked for
    writing on purpose: changing either changes the record's length, which
    shifts every following effect and invalidates ``effect_id`` everywhere.
    """
    r.marks = {}
    e = {"index": ei}
    e["name"] = r.debug_string()[1]
    n = r.i16()
    e["commands"] = []
    for ci in range(n):
        c = {"_off_type": r.at("type")}
        c["type"] = r.u8()
        c["_off_a"] = r.at("a")
        c["a"] = r.i16()
        c["_off_b"] = r.at("b")
        c["b"] = r.i16()
        c["_off_c"] = r.at("c")
        c["c"] = r.i16()
        c["_off_d"] = r.at("d")
        c["d"] = r.f32()
        e["commands"].append(c)
    return e


def locate_effects(data, parser=None):
    """Walk the Effects section.  Returns ``(effects, start)``.

    Kept SEPARATE from ``locate()`` because that returns a 4-tuple consumed in
    forty places; widening it would touch every caller for a capability only
    this path needs.  The section is an ``i32`` count followed by that many
    records, immediately after stage 4.
    """
    p = parser
    if p is None:
        p = P.Parser(data)
        with contextlib.redirect_stdout(io.StringIO()):
            p.parse()
    stage5 = next(t for t in p.stage_offsets if t[0].startswith("5 Effects"))
    r = Orec(data, stage5[1], gv=p.r.gv)
    n = r.i32()
    return [walk_effect(r, i) for i in range(n)], stage5[1]
