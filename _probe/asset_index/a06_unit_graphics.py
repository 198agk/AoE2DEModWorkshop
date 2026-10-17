#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
a06_unit_graphics.py -- re-parse the .dat with an INSTRUMENTED read_unit that
captures every graphic reference the stock parser throws away.

Method: import parse_dat as P, then monkey-patch the module-level helpers
P.read_type50 / P.read_creatable / P.read_building / P.read_unit / P.read_civ
with byte-for-byte identical re-implementations that ALSO record the graphic ids.
parse_dat.py itself is NOT modified.

Output: units_raw.json  -- one record per (civ, unit) with all graphic refs.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "datparse")))
import parse_dat as P  # noqa: E402

DAT = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"

UNIT_TYPE_FLAG = 20
UNIT_TYPE_DEAD_FISH = 30
UNIT_TYPE_BIRD = 40
UNIT_TYPE_COMBATANT = 50
UNIT_TYPE_PROJECTILE = 60
UNIT_TYPE_CREATABLE = 70
UNIT_TYPE_BUILDING = 80
UNIT_TYPE_AOE_TREES = 90

# Every field that can hold a graphic id, grouped by role.
GFX_FIELDS = [
    "standing_1", "standing_2", "dying", "undead",
    "attack_graphic", "attack_graphic2",
    "garrison_graphic", "spawning_graphic", "upgrade_graphic",
    "hero_glow_graphic", "idle_attack_graphic", "special_graphic",
    "construction_graphic", "snow_graphic", "destruction_graphic",
    "destruction_rubble_graphic", "researching_graphic", "research_completed_graphic",
]


def _read_type50(r, u):
    r.i16()                                               # BaseArmor
    n = r.i16()
    for _ in range(n):
        r.i16(); r.i16()
    n = r.i16()
    for _ in range(n):
        r.i16(); r.i16()
    r.i16(); r.f32(); r.f32(); r.f32(); r.f32()
    r.i16(); r.i16(); r.u8(); r.i16()
    r.f32(); r.f32(); r.f32()
    r.u8(); r.f32(); r.f32()
    u["attack_graphic"] = r.i16()                         # AttackGraphic
    r.i16(); r.i16(); r.f32(); r.f32()
    r.f32(); r.f32(); r.f32()
    r.i16(); r.f32()
    u["attack_graphic2"] = r.i16()                        # AttackGraphic2 (>= C27)


def _read_creatable(r, u):
    for _ in range(3):
        r.i16(); r.i16(); r.i16()
    n = r.i16()
    for _ in range(n):
        r.i16(); r.i16(); r.u8(); r.i32()
    r.f32(); r.f32(); r.u8(); r.u8()
    u["garrison_graphic"] = r.i32()
    u["spawning_graphic"] = r.i16()
    u["upgrade_graphic"] = r.i16()
    u["hero_glow_graphic"] = r.i16()
    u["idle_attack_graphic"] = r.i16()
    r.f32(); r.f32()
    r.i16(); r.i16(); r.i16()
    r.i32(); r.u8(); r.f32()
    r.i16(); r.i32(); r.i32(); r.i16()
    r.f32(); r.f32(); r.f32()
    r.f32(); r.u8()
    r.f32(); r.f32(); r.f32()
    r.i32()
    u["special_graphic"] = r.i32()
    r.u8(); r.i16()


def _read_building(r, u):
    u["construction_graphic"] = r.i16()
    u["snow_graphic"] = r.i16()
    u["destruction_graphic"] = r.i16()
    u["destruction_rubble_graphic"] = r.i16()
    u["researching_graphic"] = r.i16()
    u["research_completed_graphic"] = r.i16()
    r.u8(); r.i16(); r.u8()
    r.i16(); r.i16(); r.i16(); r.i16()
    r.u8()
    for _ in range(4):
        r.i16(); r.f32(); r.f32()
    r.i16(); r.i16(); r.i16(); r.i16()
    r.u32(); r.u32()
    r.u8(); r.f32(); r.f32(); r.i16()
    r.skip(6)


def _read_unit(r, collect=None):
    u = {}
    u["type"] = r.u8()
    u["id"] = r.i16()
    r.i32()
    r.i32()
    u["class"] = r.i16()
    sg = r.i16_array(2)
    u["standing_1"], u["standing_2"] = sg[0], sg[1]
    u["dying"] = r.i16()
    u["undead"] = r.i16()
    r.u8()
    u["hit_points"] = r.i16()
    r.f32(); r.u8()
    r.f32(); r.f32(); r.f32()
    r.i16(); r.i16(); r.i16(); r.i16()
    r.u8(); r.u8()
    u["icon_id"] = r.i16()
    r.u8()
    u["old_portrait_pict"] = r.i16()
    r.u8(); r.u8()
    r.i16_array(2); r.i16_array(2)
    r.f32(); r.f32()
    r.u8(); r.u8(); r.i16(); r.u8(); r.i16(); r.f32()
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
        r.i16(); r.f32(); r.u8()
    dgc = r.u8()
    dmg = []
    for _ in range(dgc):
        gid = r.i16(); pct = r.i16(); mode = r.u8()
        dmg.append([gid, pct, mode])
    u["damage_graphics"] = dmg
    u["damage_graphic_count"] = dgc
    r.i16(); r.i16()
    r.u32(); r.u32(); r.u32(); r.u32()
    r.u8(); r.u8()
    u["name"] = r.debug_string()[1]
    u["copy_id"] = r.i16()
    u["base_id"] = r.i16()

    t = u["type"]
    if t == UNIT_TYPE_AOE_TREES:
        if collect is not None:
            collect(u)
        return u
    if t >= UNIT_TYPE_FLAG:
        r.f32()
    else:
        if collect is not None:
            collect(u)
        return u
    if t >= UNIT_TYPE_DEAD_FISH:
        P.read_dead_fish(r)
    if t >= UNIT_TYPE_BIRD:
        P.read_bird(r)
    if t >= UNIT_TYPE_COMBATANT:
        _read_type50(r, u)
    if t == UNIT_TYPE_PROJECTILE:
        P.read_projectile(r)
    if t >= UNIT_TYPE_CREATABLE:
        _read_creatable(r, u)
    if t == UNIT_TYPE_BUILDING:
        _read_building(r, u)
    if collect is not None:
        collect(u)
    return u


def _read_civ(r, collect=None):
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
    c["unit_pointers_total"] = m
    c["unit_pointers_nonzero"] = sum(1 for p in ptrs if p != 0)
    c["units"] = []
    for i in range(m):
        if ptrs[i] != 0:
            c["units"].append(_read_unit(r, collect))
    return c


def main():
    t0 = time.time()
    data, how = P.load_dat(DAT)
    print("dat %s size=%d" % (how, len(data)))

    # swap in the instrumented readers.  Because Parser.parse() runs the FULL
    # stage chain afterwards (stages 9 and 10 must still land exactly on EOF),
    # a mismatch in any re-implemented reader perturbs the byte cursor and the
    # "leftover" count below becomes nonzero.  That is the self-check.
    P.read_unit = _read_unit
    P.read_civ = _read_civ

    p = P.Parser(data)
    st = p.parse()
    print("parse done %.1fs leftover=%d" % (time.time() - t0, len(data) - p.r.pos))
    print("civs=%d techs=%d" % (st["civ_count"], st["tech_count"]))
    assert len(data) - p.r.pos == 0, "instrumented reader desynced the cursor"

    # re-run just the civ stage so we capture the units, using the same reader
    civ_off = [t for t in p.stage_offsets if t[0].endswith("Civs")][0][1]
    print("Civs stage start = 0x%08X" % civ_off)
    r = P.Reader(data)
    r.pos = civ_off
    civ_count = r.i16()
    assert civ_count == st["civ_count"], "civ count mismatch"

    GFX_KEYS = ["standing_1", "standing_2", "dying", "undead", "attack_graphic",
                "attack_graphic2", "garrison_graphic", "spawning_graphic",
                "upgrade_graphic", "hero_glow_graphic", "idle_attack_graphic",
                "special_graphic", "construction_graphic", "snow_graphic",
                "destruction_graphic", "destruction_rubble_graphic",
                "researching_graphic", "research_completed_graphic"]
    import hashlib

    civs = []
    sigs = []
    for ci in range(civ_count):
        c = {"civ_index": ci}
        c["player_type"] = r.u8()
        c["name"] = r.debug_string()[1]
        n = r.i16()
        c["tech_tree_id"] = r.i16()
        c["team_bonus_id"] = r.i16()
        r.f32_array(n)
        c["icon_set"] = r.u8()
        m = r.i16()
        ptrs = r.i32_array(m)
        units = []
        for i in range(m):
            if ptrs[i] != 0:
                u = _read_unit(r, None)
                units.append(u)
        c["unit_count"] = len(units)

        # signature over the graphic-relevant fields, so we can PROVE that all
        # playable civs agree (or find where they don't) without storing them all
        h = hashlib.sha1()
        for u in units:
            h.update(repr([u.get(k) for k in GFX_KEYS]).encode())
            h.update(repr(u.get("damage_graphics")).encode())
            h.update(repr((u["id"], u["class"], u["type"])).encode())
        c["gfx_sig"] = h.hexdigest()
        sigs.append((ci, c["name"], c["unit_count"], c["gfx_sig"][:12]))
        civs.append(c)
        print("  civ %2d %-14s units=%-5d gfx_sig=%s" % (ci, c["name"], len(units), c["gfx_sig"][:12]))
        c["units"] = units

    print("\ndistinct gfx_sig across civs: %d" % len(set(s[3] for s in sigs)))
    from collections import Counter
    hc = Counter((s[2], s[3]) for s in sigs)
    for (uc, sg), cnt in hc.most_common():
        print("   units=%-5d sig=%s  x%d" % (uc, sg, cnt))

    with open(os.path.join(HERE, "units_raw.json"), "w", encoding="utf-8") as fh:
        json.dump(civs, fh, ensure_ascii=False)
    print("wrote units_raw.json")


if __name__ == "__main__":
    main()
