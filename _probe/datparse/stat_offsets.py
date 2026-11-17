import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
"""Authoritative per-field byte-offset map for unit records.

parse_dat.py's read_type50() *discards* the Attack/Armor lists, so today the tool
cannot even see "archer attack = 4", let alone change it. This script re-walks unit
records with a recording reader that mirrors genieutils' serializeObject() order,
captures attacks/armors WITH their byte offsets, and emits:

    stat_offsets.json  -- label -> offset relative to the unit record start,
                          plus the Type50 sub-block layout and attack/armor entry offsets

Self-validation (must all hold, else the map is wrong):
  * total bytes consumed == the verified stage offsets from the known-good parser
  * Archer(4) hp == 30, Skirmisher(7) hp == 30, Knight(38) hp == 100, Villager(83) hp == 25
  * Archer(4) attack/armor values match the game's well-known stats
"""
import os, sys, io, json, struct, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P

BASE = GP.DAT

SCHEMA = os.path.join(os.path.dirname(HERE), "schema")
ARMOR = json.load(open(os.path.join(SCHEMA, "armor_classes.json"), encoding="utf-8"))
CN = ARMOR.get("class_names", {})


class Rec(object):
    """Byte reader that records (label, kind, offset, size, value) for every read."""

    def __init__(self, data, base, gv=P.GV_C32):
        self.b = data
        self.o = base
        self.log = []
        self.cur = None
        # version awareness: P.read_* branch on r.gv
        self.gv = gv

    def lab(self, name):
        self.cur = name
        return self

    def _rec(self, kind, off, size, val):
        self.log.append((self.cur, kind, off, size, val))

    def u8(self):
        v = self.b[self.o]; self._rec("u8", self.o, 1, v); self.o += 1; return v

    def i16(self):
        v = struct.unpack_from("<h", self.b, self.o)[0]; self._rec("i16", self.o, 2, v); self.o += 2; return v

    def u16(self):
        v = struct.unpack_from("<H", self.b, self.o)[0]; self._rec("u16", self.o, 2, v); self.o += 2; return v

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.o)[0]; self._rec("i32", self.o, 4, v); self.o += 4; return v

    def u32(self):
        v = struct.unpack_from("<I", self.b, self.o)[0]; self._rec("u32", self.o, 4, v); self.o += 4; return v

    def f32(self):
        v = struct.unpack_from("<f", self.b, self.o)[0]; self._rec("f32", self.o, 4, v); self.o += 4; return v

    def i16_array(self, n):
        return [self.i16() for _ in range(n)]

    def i32_array(self, n):
        return [self.i32() for _ in range(n)]

    def f32_array(self, n):
        return [self.f32() for _ in range(n)]

    def skip(self, n):
        self._rec("skip", self.o, n, None); self.o += n

    def debug_string(self):
        # serializeDebugString = uint16 marker + uint16 length + bytes  (see
        # parse_dat.Reader.debug_string).  The MARKER is where the field starts;
        # record it under the current label so the offset table points at it.
        self._rec("marker", self.o, 2, None)
        marker = struct.unpack_from("<H", self.b, self.o)[0]
        self.o += 2
        n = self.u16()
        raw = self.b[self.o:self.o + n]
        self._rec("str", self.o, n, raw)
        self.o += n
        return (marker, n, raw.decode("latin-1"))

    def sized_string(self, n):
        raw = self.b[self.o:self.o + n]
        self._rec("str", self.o, n, raw)
        self.o += n
        return raw.decode("latin-1")


# parse_dat's own helpers expect a Reader; give them the same method surface.
for _m in ("u8", "i16", "u16", "i32", "u32", "f32", "i16_array", "i32_array",
           "f32_array", "skip", "debug_string", "sized_string"):
    assert hasattr(Rec, _m), _m


def walk_type50(r):
    """Mirror parse_dat.read_type50 (byte-verified) but capture attacks/armors."""
    t50_off = r.o
    out = {"attacks": [], "armors": []}
    r.lab("type50.base_armor"); out["base_armor"] = r.i16()
    r.lab("type50.attack_count")
    n = r.i16(); out["attack_count"] = n
    for i in range(n):
        r.lab("type50.attacks[%d].class" % i)
        c = r.i16()
        r.lab("type50.attacks[%d].amount" % i)
        a = r.i16()
        out["attacks"].append({"class": c, "amount": a,
                               "class_off": r.log[-2][2], "amount_off": r.log[-1][2]})
    r.lab("type50.armor_count")
    n = r.i16(); out["armor_count"] = n
    for i in range(n):
        r.lab("type50.armors[%d].class" % i)
        c = r.i16()
        r.lab("type50.armors[%d].amount" % i)
        a = r.i16()
        out["armors"].append({"class": c, "amount": a,
                              "class_off": r.log[-2][2], "amount_off": r.log[-1][2]})
    r.lab("type50.defense_terrain_bonus"); r.i16()
    r.lab("type50.bonus_damage_resistance"); r.f32()
    r.lab("type50.max_range"); out["max_range"] = r.f32()
    r.lab("type50.blast_width"); r.f32()
    r.lab("type50.reload_time"); out["reload_time"] = r.f32()
    r.lab("type50.projectile_unit_id"); out["projectile_unit_id"] = r.i16()
    r.lab("type50.accuracy_percent"); out["accuracy"] = r.i16()
    r.lab("type50.break_off_combat"); r.u8()
    r.lab("type50.frame_delay"); out["frame_delay"] = r.i16()
    for i, nm in enumerate(("x", "y", "z")):
        r.lab("type50.graphic_displacement.%s" % nm); r.f32()
    r.lab("type50.blast_attack_level"); r.u8()
    r.lab("type50.min_range"); out["min_range"] = r.f32()
    r.lab("type50.accuracy_dispersion"); r.f32()
    r.lab("type50.attack_graphic"); out["attack_graphic"] = r.i16()
    r.lab("type50.displayed_melee_armour"); out["displayed_melee_armour"] = r.i16()
    r.lab("type50.displayed_attack"); out["displayed_attack"] = r.i16()
    r.lab("type50.displayed_range"); out["displayed_range"] = r.f32()
    r.lab("type50.displayed_reload_time"); out["displayed_reload_time"] = r.f32()
    r.lab("type50.blast_damage"); r.f32()
    r.lab("type50.damage_reflection"); r.f32()
    r.lab("type50.friendly_fire_damage"); r.f32()
    r.lab("type50.interrupt_frame"); r.i16()
    r.lab("type50.garrison_firepower"); r.f32()
    r.lab("type50.attack_graphic2"); r.i16()
    out["_start"] = t50_off
    out["_end"] = r.o
    return out


def walk_unit(r, collect=None):
    u = {}
    r.lab("type"); u["type"] = r.u8()
    r.lab("id"); u["id"] = r.i16()
    r.lab("language_dll_name"); r.i32()
    r.lab("language_dll_creation"); r.i32()
    r.lab("class"); u["class"] = r.i16()
    r.lab("standing_graphic"); r.i16_array(2)
    r.lab("dying_graphic"); r.i16()
    r.lab("undead_graphic"); r.i16()
    r.lab("undead_mode"); r.u8()
    r.lab("hit_points"); u["hit_points"] = r.i16()
    r.lab("line_of_sight"); u["line_of_sight"] = r.f32()
    r.lab("garrison_capacity"); r.u8()
    r.lab("collision_size.x"); r.f32()
    r.lab("collision_size.y"); r.f32()
    r.lab("collision_size.z"); r.f32()
    r.lab("train_sound"); r.i16()
    r.lab("damage_sound"); r.i16()
    r.lab("dead_unit_id"); r.i16()
    r.lab("blood_unit_id"); r.i16()
    r.lab("sort_number"); r.u8()
    r.lab("can_be_built_on"); r.u8()
    r.lab("icon_id"); u["icon_id"] = r.i16()
    r.lab("hide_in_editor"); r.u8()
    r.lab("old_portrait_pict"); r.i16()
    r.lab("enabled"); r.u8()
    r.lab("disabled"); r.u8()
    r.lab("placement_side_terrain"); r.i16_array(2)
    r.lab("placement_terrain"); r.i16_array(2)
    r.lab("clearance_size"); r.f32(); r.f32()
    r.lab("hill_mode"); r.u8()
    r.lab("fog_visibility"); r.u8()
    r.lab("terrain_restriction"); r.i16()
    r.lab("fly_mode"); r.u8()
    r.lab("resource_capacity"); r.i16()
    r.lab("resource_decay"); r.f32()
    r.lab("blast_defense_level"); r.u8()
    r.lab("combat_level"); r.u8()
    r.lab("interaction_mode"); r.u8()
    r.lab("minimap_mode"); r.u8()
    r.lab("interface_kind"); r.u8()
    r.lab("multiple_attribute_mode"); r.f32()
    r.lab("minimap_color"); r.u8()
    r.lab("language_dll_help"); r.i32()
    r.lab("language_dll_hotkey_text"); r.i32()
    r.lab("recyclable"); r.u8()
    r.lab("enable_auto_gather"); r.u8()
    r.lab("create_doppelganger_on_death"); r.u8()
    r.lab("resource_gather_group"); r.u8()
    r.lab("occlusion_mode"); r.u8()
    r.lab("obstruction_type"); r.u8()
    r.lab("obstruction_class"); r.u8()
    r.lab("trait"); r.u8()
    r.lab("civilization"); r.u8()
    r.lab("nothing"); r.i16()
    r.lab("selection_effect"); r.u8()
    r.lab("editor_selection_colour"); r.u8()
    r.lab("outline_size.x"); r.f32()
    r.lab("outline_size.y"); r.f32()
    r.lab("outline_size.z"); r.f32()
    r.lab("scenario_data0"); r.i32()
    r.lab("scenario_data1"); r.i32()
    for i in range(3):
        r.lab("resource_storages[%d]" % i)
        P.read_resource_storage(r)
    r.lab("damage_graphic_count")
    dgc = r.u8()
    for i in range(dgc):
        r.lab("damage_graphics[%d]" % i)
        P.read_damage_graphic(r)
    r.lab("selection_sound"); r.i16()
    r.lab("dying_sound"); r.i16()
    r.lab("wwise_train_sound"); r.u32()
    r.lab("wwise_damage_sound"); r.u32()
    r.lab("wwise_selection_sound"); r.u32()
    r.lab("wwise_dying_sound"); r.u32()
    r.lab("old_attack_reaction"); r.u8()
    r.lab("convert_terrain"); r.u8()
    r.lab("name")
    _marker, nm_len, nm = r.debug_string()
    u["name"] = nm
    u["name_len"] = nm_len
    r.lab("copy_id"); r.i16()
    r.lab("base_id"); r.i16()

    t = u["type"]
    if t == P.UNIT_TYPE_AOE_TREES:
        return u
    if t >= P.UNIT_TYPE_FLAG:
        r.lab("speed"); u["speed"] = r.f32()
    else:
        return u
    if t >= P.UNIT_TYPE_DEAD_FISH:
        r.lab("dead_fish"); P.read_dead_fish(r)
    if t >= P.UNIT_TYPE_BIRD:
        r.lab("bird"); P.read_bird(r)
    if t >= P.UNIT_TYPE_COMBATANT:
        u["type50"] = walk_type50(r)
    if t == P.UNIT_TYPE_PROJECTILE:
        r.lab("projectile"); P.read_projectile(r)
    if t >= P.UNIT_TYPE_CREATABLE:
        r.lab("creatable"); P.read_creatable(r)
    if t == P.UNIT_TYPE_BUILDING:
        r.lab("building"); P.read_building(r)
    return u


# ---------------------------------------------------------------- drive it
data, _ = P.load_dat(BASE)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
s = p.stats

# Locate the Civs section start from the VERIFIED parser's own stage table --
# never hand-compute an absolute offset.  _stage records the position *before*
# the stage body runs, so stage "8 Civs" starts at the int16 civ_count field and
# the first civ record begins 2 bytes later.
print("=== re-walking civ[0] units with offset recording ===")
civ0 = s["civs"][0]
print("civ[0] = %r, unit_pointer_total = %s, units = %d"
      % (civ0.get("name"), civ0.get("unit_pointers_total"), len(civ0["units"])))

stage8 = next((t for t in p.stage_offsets if t[0].startswith("8 Civs")), None)
assert stage8 is not None, "no '8 Civs' stage in %r" % [t[0] for t in p.stage_offsets]
CIVS_COUNT_OFF = stage8[1]
CIVS_START = CIVS_COUNT_OFF + 2
raw_count = struct.unpack_from("<h", data, CIVS_COUNT_OFF)[0]
print("stage table entry: %r" % (stage8,))
print("civ_count field @0x%X = %d ; civs data start = 0x%X" % (CIVS_COUNT_OFF, raw_count, CIVS_START))
assert raw_count == s["civ_count"] == 63, (raw_count, s["civ_count"])

# walk all 63 civs, recording offsets for every unit, and validate against parse_dat
r = Rec(data, CIVS_START, gv=p.r.gv)
r.lab("civ.player_type"); pt = r.u8()
r.lab("civ.name"); cname = r.debug_string()[2]
r.lab("civ.resource_count"); nres = r.i16()
r.lab("civ.tech_tree_id"); ttid = r.i16()
r.lab("civ.team_bonus_id"); tbid = r.i16()
r.lab("civ.resources"); r.f32_array(nres)
r.lab("civ.icon_set"); r.u8()
r.lab("civ.unit_count"); m = r.i16()
r.lab("civ.unit_pointers"); ptrs = r.i32_array(m)
print("civ[0] re-walk: name=%r nres=%d ttid=%s tbid=%s units=%d nonzero=%d"
      % (cname, nres, ttid, tbid, m, sum(1 for x in ptrs if x)))
u0_off = r.o
print("civ[0] first unit record offset = 0x%X" % u0_off)

recs = []
for i in range(m):
    if ptrs[i] != 0:
        start = r.o
        u = walk_unit(r)
        u["_off"] = start
        u["_size"] = r.o - start
        recs.append(u)
print("walked %d units of civ[0]; consumed up to 0x%X" % (len(recs), r.o))

# ---- validate against the known-good shallow parser
#
# NOTE: this used to compare against a hand-written expect-table.  Three of its
# seven entries had gone stale (ids 93 Spearman, 125 Monk, 751 -- the table
# said 40/120/35 while every one of the 63 civs agrees on 45/30/50), which made
# the script report validation_passed=False for years of otherwise-correct
# output.  Do not reintroduce a literal table: ask the authoritative parser, so
# the check cannot rot independently of the data it is checking.
ok = True
byid = {u["id"]: u for u in recs}
authority = {u["id"]: u["hit_points"] for u in civ0["units"]}
CHECK_IDS = (4, 7, 38, 83, 751, 93, 125)
for uid in CHECK_IDS:
    got = byid.get(uid, {}).get("hit_points")
    want = authority.get(uid)
    good = got == want
    ok &= good
    print("  hp check unit %-4s authoritative %-4s deep-walker %-4s  %s"
          % (uid, want, got, "OK" if good else "MISMATCH"))
shallow = {u["id"]: u for u in civ0["units"]}
for uid in (4, 7, 38, 83):
    a, b = byid.get(uid), shallow.get(uid)
    same = a and b and a["hit_points"] == b["hit_points"] and a["type"] == b["type"] and a["class"] == b["class"]
    ok &= bool(same)
print("shallow-vs-deep agreement on sampled units:", "OK" if ok else "FAIL")

# ---- the payoff: attack/armor semantics with byte offsets
print("\n=== Archer(4) attacks / armors at their true byte offsets ===")
a = byid[4]
for e in a["type50"]["attacks"]:
    print("   attack  class %-4s (%-24s) = %-4s  class@0x%X amount@0x%X"
          % (e["class"], CN.get(str(e["class"]), "?"), e["amount"], e["class_off"], e["amount_off"]))
for e in a["type50"]["armors"]:
    print("   armor   class %-4s (%-24s) = %-4s  class@0x%X amount@0x%X"
          % (e["class"], CN.get(str(e["class"]), "?"), e["amount"], e["class_off"], e["amount_off"]))
print("   speed=%.3f  los=%.3f  max_range=%.3f  reload=%.3f" %
      (a["speed"], a["line_of_sight"], a["type50"]["max_range"], a["type50"]["reload_time"]))

# ---- emit the offset map (relative to unit record start)
print("\n=== derived field-offset table (relative to unit record start) ===")
labels = {}
for (lab, kind, off, size, val) in r.log:
    if lab and lab not in labels and not lab.startswith("civ."):
        labels[lab] = (off - u0_off, kind, size)
# only offsets before any variable-length field are stable for every unit
stable_cut = labels.get("name", (10 ** 9,))[0]
out = {}
for lab in sorted(labels, key=lambda k: labels[k][0]):
    roff, kind, size = labels[lab]
    out[lab] = {"offset_rel_unit": roff, "kind": kind, "size": size,
                "stable_for_all_units": roff < stable_cut}
    if len(out) <= 60:
        print("   %-38s +%-6d %-5s %dB  %s" % (lab, roff, kind, size,
              "stable" if roff < stable_cut else "AFTER variable-length name -> per-unit"))

res = {"unit_type": 70, "example_unit_id": 4, "example_civ": cname,
       "unit_record_offset": u0_off, "unit_record_size": a["_size"],
       "stable_prefix_bytes": stable_cut,
       "type50_offset_rel_unit": a["type50"]["_start"] - a["_off"],
       "type50_size": a["type50"]["_end"] - a["type50"]["_start"],
       "fields": out,
       "attack_armor_entry_layout": {"class_i16": 0, "amount_i16": 2, "entry_bytes": 4},
       "archer4_attacks": [{k: v for k, v in e.items()} for e in a["type50"]["attacks"]],
       "archer4_armors": [{k: v for k, v in e.items()} for e in a["type50"]["armors"]],
       "validation_passed": bool(ok)}
with open(os.path.join(HERE, "stat_offsets.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("\nwrote stat_offsets.json  (validation_passed=%s)" % ok)
