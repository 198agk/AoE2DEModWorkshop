#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pure-Python parser for the Age of Empires II: Definitive Edition .dat file.

Format spec transcribed from genieutils C++ sources (unpacked from the game's
own ``Tools_Builds/docs/Source.7z`` into ``_probe/source/``):
  <workspace>/_probe/source/genieutils/
     include\\genie\\file\\ISerializable.h   (serialization primitives)
     include\\genie\\Types.h                 (GameVersion enum, VER -> GV map)
     src\\dat\\DatFile.cpp                   (top level read order)
     src\\dat\\*.cpp, src\\dat\\unit\\*.cpp    (per-struct read order)

Target game version: the file starts with "VER 8.9\\0" which maps to
GV_C32 == GV_LatestDE2.  Every `if (gv >= ...)` guard in the C++ is therefore
evaluated once, at parse time, into a hardcoded branch.

Standard library only (zlib, struct, sys, time, json).
"""

import os
import struct
import sys
import time
import zlib

# ---------------------------------------------------------------------------
# Game version guards
# ---------------------------------------------------------------------------
# The C++ uses `gv >= GV_C28` style guards; the numeric value of each GV_* is
# its ordinal in `enum GameVersion` (include/genie/Types.h:33).  The DAT file
# header carries a "VER x.y" string which maps onto one of those ordinals via
# `SupportedDatVersionsToGameVersion` (Types.h:75).
#
# Historically this parser hardcoded GV_C32 (== VER 8.9 == GV_LatestDE2).  That
# silently mis-parsed legacy datasets: a real VER 7.8 (GV_C21) mod dat in the
# local corpus overran by 1,465,059 bytes because `Task.Enabled` (guarded by
# `gv >= GV_C28` in UnitCommand.cpp:81) was read unconditionally.
#
# GV_* ordinals derived mechanically from the enum (see vg_diff_full.py):
GV_TEST = 1
GV_MIK = 2
GV_DAVE = 3
GV_MATT = 4
GV_AoEB = 5
GV_AoE = 6
GV_RoR = 7
GV_Tapsa = 8
GV_T2 = 9
GV_T3 = 10
GV_T4 = 11
GV_T5 = 12
GV_T6 = 13
GV_T7 = 14
GV_T8 = 15
GV_AoKE3 = 16
GV_AoKA = 17
GV_AoKB = 18
GV_AoK = 19
GV_TC = 20
GV_TCV = 21
GV_Cysion = 22
GV_C2 = 23
GV_C3 = 24
GV_C4 = 25
GV_CK = 26
GV_C5 = 27
GV_C6 = 28
GV_C7 = 29
GV_C8 = 30
GV_C9 = 31
GV_C10 = 32
GV_C11 = 33
GV_C12 = 34
GV_C13 = 35
GV_C14 = 36
GV_C15 = 37
GV_C16 = 38
GV_C17 = 39
GV_C18 = 40
GV_C19 = 41
GV_C20 = 42
GV_C21 = 43
GV_C22 = 44
GV_C23 = 45
GV_C24 = 46
GV_C25 = 47
GV_C26 = 48
GV_C27 = 49
GV_C28 = 50
GV_C29 = 51
GV_C30 = 52
GV_C31 = 53
GV_C32 = 54
GV_SWGB = 55
GV_CC = 56
GV_CCV = 57
GV_CCV2 = 58

GV_LatestTap = GV_T8
GV_LatestDE2 = GV_C32

# Types.h:75 `SupportedDatVersionsToGameVersion`
VER_TO_GV = {
    "VER 7.1": GV_C14, "VER 7.2": GV_C15, "VER 7.3": GV_C16,
    "VER 7.4": GV_C17, "VER 7.5": GV_C18, "VER 7.6": GV_C19,
    "VER 7.7": GV_C20, "VER 7.8": GV_C21, "VER 7.9": GV_C22,
    "VER 8.0": GV_C23, "VER 8.1": GV_C24, "VER 8.2": GV_C25,
    "VER 8.3": GV_C26, "VER 8.4": GV_C27, "VER 8.5": GV_C28,
    "VER 8.6": GV_C29, "VER 8.7": GV_C30, "VER 8.8": GV_C31,
    "VER 8.9": GV_C32,
}

# Default for code paths that are still version-agnostic.
GV = GV_C32


class UnsupportedVersionError(Exception):
    """Raised when the DAT carries a FileVersion we cannot interpret."""


def gv_from_version_string(ver):
    """Map a raw 8-byte FileVersion field onto a GameVersion ordinal.

    `ver` is what `Reader.fixed_string(8)` returns (usually 'VER 8.9'); it may
    carry trailing NULs or other padding, so normalise first.
    """
    if isinstance(ver, bytes):
        ver = ver.decode("latin-1")
    ver = ver.split("\x00")[0].strip()
    if ver not in VER_TO_GV:
        raise UnsupportedVersionError(
            "unsupported DAT FileVersion %r (known: %s)"
            % (ver, ", ".join(sorted(VER_TO_GV))))
    return VER_TO_GV[ver]

FILE_VERSION_SIZE = 8
TILE_TYPE_COUNT = 19          # SharedTerrain::TILE_TYPE_COUNT   (TerrainCommon.h:46)
TERRAIN_UNITS_SIZE = 30       # Terrain::TERRAIN_UNITS_SIZE      (Terrain.h:73)
AGES = 5                      # TechTree.h
BUILDING_ANNEXES_SIZE = 4     # unit::Building     (Building.cpp)
LOOTABLE_RES_COUNT = 6        # unit::Building

# Terrain::getTerrainCount(GV_C32):
#   Terrain::terrain_count_ is a *different* static from
#   TerrainRestriction::terrain_count_; DatFile only ever calls
#   TerrainRestriction::setTerrainCount(), so Terrain::terrain_count_ stays 0
#   and the GV_C8..GV_LatestDE2 branch returns 200.
TERRAIN_COUNT_FOR_TERRAINBLOCK = 200

# TerrainRestriction::terrain_count_ is set by DatFile from TerrainsUsed1.
# (54 restrictions; each sized by TerrainsUsed1.)

UNIT_TYPE_EYECANDY = 10
UNIT_TYPE_TREES = 15
UNIT_TYPE_FLAG = 20
UNIT_TYPE_25 = 25
UNIT_TYPE_DEAD_FISH = 30
UNIT_TYPE_BIRD = 40
UNIT_TYPE_COMBATANT = 50
UNIT_TYPE_PROJECTILE = 60
UNIT_TYPE_CREATABLE = 70
UNIT_TYPE_BUILDING = 80
UNIT_TYPE_AOE_TREES = 90

DEBUG_STRING_MARKER = 0x0A60


# ---------------------------------------------------------------------------
# Byte reader
# ---------------------------------------------------------------------------
class Reader(object):
    """Byte reader.

    Duck-type contract for the `read_*` functions in this module: any reader
    object passed to them MUST expose a `gv` attribute holding the active
    GameVersion ordinal (they branch on it ~27 times).  `Parser` sets it from
    the FileVersion field.  Probe scripts that roll their own lightweight
    reader (recording offsets, etc.) must copy it too -- see
    `intent_patch.Orec`, `attack_semantics.Rec`, `stat_offsets.Rec`, all of
    which take a `gv=` argument.  Omitting it fails loudly with
    AttributeError, which is deliberate: a silently wrong version would
    corrupt every subsequent offset.
    """

    __slots__ = ("data", "pos", "size", "gv", "last_string_len")

    def __init__(self, data, gv=GV_C32):
        self.data = data
        self.pos = 0
        self.size = len(data)
        # Active GameVersion ordinal; the Parser sets this once the FileVersion
        # field has been read.  Defaults to GV_C32 so version-agnostic callers
        # (and the writer) keep working unchanged.
        self.gv = gv
        # Stored width of the most recent `debug_string`, for callers that must
        # re-emit it at a different length (see `read_graphic`).
        self.last_string_len = 0

    # -- bounds check ------------------------------------------------------
    def _need(self, n):
        if self.pos + n > self.size:
            raise EOFError(
                "read of %d byte(s) at offset %d would pass end of file (%d)"
                % (n, self.pos, self.size)
            )

    # -- scalars -----------------------------------------------------------
    def u8(self):
        p = self.pos
        self._need(1)
        self.pos = p + 1
        return self.data[p]

    def u16(self):
        p = self.pos
        self._need(2)
        self.pos = p + 2
        return struct.unpack_from("<H", self.data, p)[0]

    def i16(self):
        p = self.pos
        self._need(2)
        self.pos = p + 2
        return struct.unpack_from("<h", self.data, p)[0]

    def u32(self):
        p = self.pos
        self._need(4)
        self.pos = p + 4
        return struct.unpack_from("<I", self.data, p)[0]

    def i32(self):
        p = self.pos
        self._need(4)
        self.pos = p + 4
        return struct.unpack_from("<i", self.data, p)[0]

    def f32(self):
        p = self.pos
        self._need(4)
        self.pos = p + 4
        return struct.unpack_from("<f", self.data, p)[0]

    # -- bulk --------------------------------------------------------------
    def raw(self, n):
        if n < 0:
            raise ValueError("negative read length %d at offset %d" % (n, self.pos))
        p = self.pos
        self._need(n)
        self.pos = p + n
        return self.data[p:p + n]

    def skip(self, n):
        self._need(n)
        self.pos += n

    def i16_array(self, n):
        p = self.pos
        self._need(2 * n)
        self.pos = p + 2 * n
        return struct.unpack_from("<%dh" % n, self.data, p)

    def i32_array(self, n):
        p = self.pos
        self._need(4 * n)
        self.pos = p + 4 * n
        return struct.unpack_from("<%di" % n, self.data, p)

    def f32_array(self, n):
        p = self.pos
        self._need(4 * n)
        self.pos = p + 4 * n
        return struct.unpack_from("<%df" % n, self.data, p)

    # -- strings -----------------------------------------------------------
    def fixed_string(self, n):
        b = self.raw(n)
        z = b.find(b"\x00")
        if z >= 0:
            b = b[:z]
        return b.decode("latin-1")

    def sized_string(self, n):
        """serialize(std::string&, len): read len bytes, cut at first NUL."""
        if n <= 0:
            return ""
        return self.fixed_string(n)

    def debug_string(self):
        """serializeDebugString: uint16 marker, uint16 length, bytes.

        Also leaves the STORED byte count in ``self.last_string_len``.  The
        return value carries the marker, not the length, so a caller that needs
        to re-emit the string at a different width (retargeting a graphics
        record) must read it from here; using the marker by mistake advances a
        writer's raw cursor by 2,656 bytes and corrupts everything after it.
        """
        marker = self.u16()
        ln = self.u16()
        self.last_string_len = ln
        b = self.raw(ln)
        z = b.find(b"\x00")
        if z >= 0:
            b = b[:z]
        return (marker, b.decode("latin-1"))


# ---------------------------------------------------------------------------
# Decompression
# ---------------------------------------------------------------------------
def load_dat(path):
    """Return the raw (decompressed) .dat bytes.

    The retail .dat is raw deflate (zlib window_bits=-15) after the fact; the
    decompressed payload itself begins with b'VER '.  Accept either form.
    """
    with open(path, "rb") as fh:
        blob = fh.read()

    if blob[:4] == b"VER ":
        return blob, "already-decompressed"

    d = zlib.decompressobj(-15)
    out = d.decompress(blob)
    out += d.flush()
    return out, "raw-deflate(window_bits=-15)"


# ---------------------------------------------------------------------------
# Sub-structures
# ---------------------------------------------------------------------------
def read_terrain_pass_graphic(r):
    return (r.i32(), r.i32(), r.i32(), r.f32())          # 16 bytes


def read_terrain_restriction(r, terrain_count):
    floats = r.f32_array(terrain_count)
    tpg = [read_terrain_pass_graphic(r) for _ in range(terrain_count)]
    return {"mult": floats, "pass": tpg}


def read_player_colour(r):
    return r.i32_array(9)                                 # 9 x int32


def read_sound_item(r):
    marker, fname = r.debug_string()
    return {
        "file": fname,
        "resource_id": r.i32(),
        "probability": r.i16(),
        "civilization": r.i16(),
        "iconset": r.i16(),
    }


def read_sound(r):
    snd = {"id": r.i16(), "play_delay": r.i16()}
    file_count = r.i16()
    snd["cache_time"] = r.i32()
    snd["total_probability"] = r.i16()
    snd["items"] = [read_sound_item(r) for _ in range(file_count)]
    return snd


def read_graphic_delta(r):
    return (r.i16(), r.i16(), r.i32(), r.i16(), r.i16(), r.i16(), r.i16())  # 16 B


def read_graphic_angle_sound(r):
    out = []
    for _ in range(3):
        out.append((r.i16(), r.i16(), r.u32()))           # 8 B
    return out                                            # 24 B


def read_graphic(r):
    m1, name = r.debug_string()
    n1 = r.last_string_len
    m2, fname = r.debug_string()
    n2 = r.last_string_len
    m3, pfx = r.debug_string()
    n3 = r.last_string_len
    g = {
        "name": name,
        "file": fname,
        "particle_effect": pfx,
        # Stored byte counts of the three strings, NOT of the decoded text.  A
        # reskin can point a record at another picture by re-emitting `file` at
        # a different LENGTH, and then the writer must advance its raw cursor by
        # the width the stream actually used or every later verbatim read is
        # shifted (measured: one +3 byte string, 991,273 mismatches).
        "_name_len": n1,
        "_file_len": n2,
        "_particle_len": n3,
        "slp": r.i32(),
        "is_loaded": r.u8(),
        "old_color_flag": r.u8(),
        "layer": r.u8(),
        "player_color": r.i16(),
        "transparent_selection": r.u8(),
        "coordinates": r.i16_array(4),
        "sound_id": None,
        "wwise_sound_id": None,
        "angle_sounds_used": None,
        "frame_count": None,
        "angle_count": None,
        "id": None,
        "mirroring_mode": None,
        "editor_flag": None,
        "deltas": [],
        "angle_sounds": [],
    }
    delta_count = r.i16()
    g["sound_id"] = r.i16()
    g["wwise_sound_id"] = r.u32()
    g["angle_sounds_used"] = r.u8()
    g["frame_count"] = r.i16()
    angle_count = r.i16()
    g["angle_count"] = angle_count
    r.f32()                    # SpeedMultiplier
    r.f32()                    # FrameDuration
    r.f32()                    # ReplayDelay
    r.u8()                     # SequenceType
    g["id"] = r.i16()
    g["mirroring_mode"] = r.u8()
    g["editor_flag"] = r.u8()
    g["deltas"] = [read_graphic_delta(r) for _ in range(delta_count)]
    if g["angle_sounds_used"] != 0:
        g["angle_sounds"] = [read_graphic_angle_sound(r) for _ in range(angle_count)]
    return g


def read_frame_data(r):
    return (r.i16(), r.i16(), r.i16())                    # 6 B


def read_terrain(r):
    t = {}
    t["enabled"] = r.u8()
    t["random"] = r.u8()
    t["is_water"] = r.u8()
    t["hide_in_editor"] = r.u8()
    t["string_id"] = r.i32()
    t["name"] = r.debug_string()[1]
    t["name2"] = r.debug_string()[1]
    t["slp"] = r.i32()
    t["shape_ptr"] = r.i32()
    t["sound_id"] = r.i32()
    t["wwise_sound_id"] = r.u32()
    t["wwise_sound_stop_id"] = r.u32()
    t["blend_priority"] = r.i32()
    t["blend_type"] = r.i32()
    t["overlay_mask_name"] = r.debug_string()[1]
    r.skip(3)                                             # Colors[3]
    r.skip(2)                                             # CliffColors pair
    t["passable_terrain"] = r.u8()
    t["impassable_terrain"] = r.u8()
    t["is_animated"] = r.u8()
    r.i16()                                               # AnimationFrames
    r.i16()                                               # PauseFames
    r.f32()                                               # Interval
    r.f32()                                               # PauseBetweenLoops
    r.i16()                                               # Frame
    r.i16()                                               # DrawFrame
    r.f32()                                               # AnimateLast
    r.u8()                                                # FrameChanged
    r.u8()                                                # Drawn
    for _ in range(TILE_TYPE_COUNT):
        read_frame_data(r)
    r.i16()                                               # TerrainToDraw
    r.i16_array(2)                                        # TerrainDimensions
    r.i16_array(TERRAIN_UNITS_SIZE)                       # TerrainUnitMaskedDensity
    r.i16_array(TERRAIN_UNITS_SIZE)                       # TerrainUnitID
    r.i16_array(TERRAIN_UNITS_SIZE)                       # TerrainUnitDensity
    r.skip(TERRAIN_UNITS_SIZE)                            # TerrainUnitCentering (u8)
    r.i16()                                               # NumberOfTerrainUnitsUsed
    # Terrain.cpp:196 `if (gv < GV_SWGB) serialize<int16_t>(Phantom);`
    # GV_C32 (54) < GV_SWGB (55) is TRUE, so Phantom IS present in DE dats.
    t["phantom"] = r.i16()
    return t


def read_terrain_block(r):
    tb = {}
    tb["virtual_function_ptr"] = r.u32()
    tb["map_pointer"] = r.u32()
    tb["map_width"] = r.i32()
    tb["map_height"] = r.i32()
    tb["world_width"] = r.i32()
    tb["world_height"] = r.i32()
    tb["tile_sizes"] = [r.i16_array(3) for _ in range(TILE_TYPE_COUNT)]  # 6 B each
    r.i16()                                               # PaddingTS
    tb["terrains"] = [read_terrain(r) for _ in range(TERRAIN_COUNT_FOR_TERRAINBLOCK)]
    # gv >= GV_C9 && gv <= GV_LatestDE2  ->  TerrainBorders + MapRowOffset SKIPPED
    tb["map_min_x"] = r.f32()
    tb["map_min_y"] = r.f32()
    tb["map_max_x"] = r.f32()
    tb["map_max_y"] = r.f32()
    tb["map_max_x_plus1"] = r.f32()
    tb["map_max_y_plus1"] = r.f32()
    tb["terrains_used2"] = r.i16()
    tb["borders_used"] = r.i16()
    tb["max_terrain"] = r.i16()
    tb["tile_width"] = r.i16()
    tb["tile_height"] = r.i16()
    tb["tile_half_height"] = r.i16()
    tb["tile_half_width"] = r.i16()
    tb["elev_height"] = r.i16()
    tb["cur_row"] = r.i16()
    tb["cur_col"] = r.i16()
    tb["block_beg_row"] = r.i16()
    tb["block_end_row"] = r.i16()
    tb["block_beg_col"] = r.i16()
    tb["block_end_col"] = r.i16()
    tb["search_map_ptr"] = r.u32()
    tb["search_map_rows_ptr"] = r.u32()
    tb["any_frame_change"] = r.u8()
    tb["map_visible_flag"] = r.u8()
    tb["fog_flag"] = r.u8()
    return tb


def read_map_land(r):
    # RandomMap.cpp:151-168 -- i32 LandID | u32 Terrain | i32 LandSpacing
    # | i32 BaseSize | u8 Zone | u8 PlacementType | i16 Padding1 | i32 BaseX
    # | i32 BaseY | u8 LandProportion | u8 ByPlayerFlag | i16 Padding2
    # | i32 StartAreaRadius | i32 TerrainEdgeFade | i32 Clumpiness  ==  44 B
    r.i32(); r.u32(); r.i32(); r.i32()
    r.u8(); r.u8(); r.i16()
    r.i32(); r.i32()
    r.u8(); r.u8(); r.i16()
    r.i32(); r.i32(); r.i32()                             # 44 B


def read_map_terrain(r):
    r.i32_array(6)                                        # 24 B


def read_map_unit(r):
    # RandomMap.cpp:214-229 -- i32 Unit | i32 HostTerrain | u8 GroupPlacing
    # | u8 ScaleFlag | i16 Padding1 | i32 x8  ==  4+4+1+1+2+32  ==  44 B
    r.i32(); r.i32(); r.u8(); r.u8(); r.i16()
    r.i32_array(8)                                        # 44 B


def read_map_elevation(r):
    r.i32_array(6)                                        # 24 B


def read_random_maps(r):
    count = r.u32()
    rm_ptr = r.i32()
    maps = [{"io_all": False} for _ in range(count)]
    # RandomMap.cpp:62-63 calls serializeSub<MapInfo> TWICE over the same vector.
    for _pass in range(2):
        for m in maps:
            if not m["io_all"]:
                m["map_id"] = r.i32()
            for _ in range(9):                            # 9 x int32 header
                r.i32()
            for key, fn in (("lands", read_map_land),
                            ("terrains", read_map_terrain),
                            ("units", read_map_unit),
                            ("elevations", read_map_elevation)):
                c = r.u32()
                r.i32()                                   # *Ptr
                if m["io_all"]:
                    for _ in range(c):
                        fn(r)
            m["io_all"] = not m["io_all"]
    return {"count": count, "random_maps_ptr": rm_ptr, "maps": maps}


def read_effect_command(r):
    return (r.u8(), r.i16(), r.i16(), r.i16(), r.f32())   # 11 B


def read_effect(r):
    name = r.debug_string()[1]
    n = r.i16()
    return {"name": name, "commands": [read_effect_command(r) for _ in range(n)]}


def read_unit_line(r):
    ul = {"id": r.i16()}
    n = r.i16()
    ul["name"] = r.sized_string(n)
    m = r.i16()
    ul["unit_ids"] = r.i16_array(m)
    return ul


def read_task(r):
    t = {}
    t["task_type"] = r.i16()
    t["id"] = r.i16()
    r.u8()                                                # IsDefault
    r.i16(); r.i16(); r.i16(); r.i16()                    # ActionType..TerrainID
    r.i16(); r.i16(); r.i16(); r.i16()                    # ResourceIn..UnusedResource
    r.f32(); r.f32(); r.f32()                             # WorkValue1/2, WorkRange
    r.u8()                                                # AutoSearchTargets
    r.f32()                                               # SearchWaitTime
    r.u8(); r.u8()                                        # EnableTargeting, CombatLevelFlag
    r.i16(); r.i16()                                      # GatherType, WorkFlag2
    r.u8(); r.u8(); r.u8()                                # TargetDiplomacy, CarryCheck, PickForConstruction
    r.i16(); r.i16(); r.i16(); r.i16()                    # Moving/Proceeding/Working/Carrying
    r.i16(); r.i16()                                      # ResourceGathering/DepositSoundID
    if GV_C4 <= r.gv <= GV_LatestDE2:                     # UnitCommand.cpp:76
        r.u32(); r.u32()                                  # Wwise* ID
    if r.gv >= GV_C28:                                    # UnitCommand.cpp:81
        r.i16()                                           # Enabled
    return t


def read_unit_header(r):
    exists = r.u8()
    uh = {"exists": exists, "tasks": []}
    if exists:
        n = r.i16()
        uh["tasks"] = [read_task(r) for _ in range(n)]
    return uh


# --- unit sub-structures ---------------------------------------------------
def read_resource_storage(r):                             # int16, float, uint8
    r.i16(); r.f32(); r.u8()


def read_damage_graphic(r):
    r.i16(); r.i16(); r.u8()                              # 5 B


def read_dead_fish(r):
    r.i16(); r.i16(); r.f32(); r.u8(); r.i16(); r.u8(); r.f32(); r.u8()
    r.f32(); r.f32(); r.f32(); r.f32(); r.f32()           # TurnRadius..Stationary
    r.f32()                                               # MinCollisionSizeMultiplier


def read_bird(r):
    """Bird/creatable task block.  RETURNS ``TaskSwapGroup``.

    TaskSwapGroup is not decoration.  The engine swaps the live object's record
    pointer to another unit with the same group when a villager is retasked
    ("Villager" -> "Builder"), so an edit that only touches the record a name
    resolved to stops applying the instant the player assigns a job -- silently,
    exactly like an age variant.  The value must therefore be exposed to the
    family layer instead of being skipped.

    Writing this out (rather than the previous bare ``r.u8()``) does NOT perturb
    byte-exact round-trips: ``_probe/serializer/write_dat.py``'s ``write_bird``
    replays this field with ``w.op(1)`` from the ORIGINAL bytes and never reads
    the parsed model.
    """
    r.i16(); r.f32(); r.f32()
    n = r.i16()
    r.i16_array(n)                                        # DropSites
    tsg = r.u8()                                          # TaskSwapGroup
    r.i16()                                               # AttackSound
    r.i16()                                               # MoveSound
    r.u32(); r.u32()                                      # Wwise attack/move
    r.u8()                                                # RunPattern
    tn = r.i16()
    for _ in range(tn):
        read_task(r)
    return tsg


def read_attack_or_armor(r):
    r.i16(); r.i16()                                      # 4 B


def read_type50(r):
    r.i16()                                               # BaseArmor
    n = r.i16()
    for _ in range(n):
        read_attack_or_armor(r)
    n = r.i16()
    for _ in range(n):
        read_attack_or_armor(r)
    r.i16()                                               # DefenseTerrainBonus
    r.f32()                                               # BonusDamageResistance
    r.f32(); r.f32(); r.f32()                             # MaxRange, BlastWidth, ReloadTime
    r.i16(); r.i16()                                      # ProjectileUnitID, AccuracyPercent
    r.u8()                                                # BreakOffCombat
    r.i16()                                               # FrameDelay
    r.f32(); r.f32(); r.f32()                             # GraphicDisplacement[3]
    r.u8()                                                # BlastAttackLevel
    r.f32()                                               # MinRange
    r.f32()                                               # AccuracyDispersion
    r.i16()                                               # AttackGraphic
    r.i16(); r.i16()                                      # DisplayedMeleeArmour, DisplayedAttack
    r.f32(); r.f32()                                      # DisplayedRange, DisplayedReloadTime
    if GV_C20 <= r.gv <= GV_LatestDE2:                    # Type50.cpp:94
        r.f32()                                           # BlastDamage
    if GV_C22 <= r.gv <= GV_LatestDE2:                    # Type50.cpp:99
        r.f32(); r.f32()                                  # DamageReflection, FriendlyFireDamage
    if GV_C27 <= r.gv <= GV_LatestDE2:                    # Type50.cpp:105
        r.i16(); r.f32(); r.i16()                         # InterruptFrame, GarrisonFirepower, AttackGraphic2


def read_projectile(r):
    r.u8(); r.u8(); r.u8(); r.u8(); r.u8()               # 5 x uint8
    r.f32()                                               # ProjectileArc


def read_train_location(r):
    r.i16(); r.i16(); r.u8()                              # TrainTime, UnitID, ButtonID
    if GV_C30 <= r.gv <= GV_LatestDE2:                    # TrainLocation.cpp:28
        r.i32()                                           # HotKeyID


def read_resource_cost(r):                                # int16, int16, int16
    r.i16(); r.i16(); r.i16()


def read_creatable(r):
    for _ in range(3):
        read_resource_cost(r)
    # Creatable.cpp:58 -- DE stores an explicit count; older versions write
    # exactly one entry with no count field in front of it.
    if GV_C29 <= r.gv <= GV_LatestDE2:
        n = r.i16()
        for _ in range(n):
            read_train_location(r)
    else:
        read_train_location(r)                            # Creatable.cpp:66 -- exactly 1
    # gv >= GV_AoEB, gv >= GV_AoKE3, gv >= GV_AoKB
    r.f32(); r.f32()                                      # RearAttackModifier, FlankAttackModifier
    r.u8()                                                # CreatableType
    r.u8()                                                # HeroMode
    r.i32()                                               # GarrisonGraphic
    if GV_C13 <= r.gv <= GV_LatestDE2:                    # Creatable.cpp:91
        r.i16(); r.i16()                                  # SpawningGraphic, UpgradeGraphic
        if r.gv >= GV_C16:
            if r.gv >= GV_C17:
                r.i16()                                   # HeroGlowGraphic
            if r.gv >= GV_C26:                            # Creatable.cpp:102
                r.i16()                                   # IdleAttackGraphic
            r.f32(); r.f32()                              # MaxCharge, RechargeRate
            r.i16(); r.i16()                              # ChargeEvent, ChargeType
            if r.gv >= GV_C23:                            # Creatable.cpp:111
                r.i16()                                   # ChargeTarget
            if r.gv >= GV_C25:                            # Creatable.cpp:116
                r.i32(); r.u8(); r.f32()                  # ChargeProjectileUnit, AttackPriority, InvulnerabilityLevel
            if r.gv >= GV_C24:                            # Creatable.cpp:123
                r.i16(); r.i32(); r.i32(); r.i16()        # ButtonIconID, ButtonShort/ExtendedTooltipID, ButtonHotkeyAction
            if r.gv >= GV_C19:                            # Creatable.cpp:131
                r.f32(); r.f32(); r.f32()                 # Min/MaxConversionTimeMod, ConversionChanceMod
    r.f32()                                               # TotalProjectiles
    r.u8()                                                # MaxTotalProjectiles
    r.f32(); r.f32(); r.f32()                             # ProjectileSpawningArea[3]
    r.i32()                                               # SecondaryProjectileUnit
    r.i32()                                               # SpecialGraphic
    r.u8()                                                # SpecialAbility
    r.i16()                                               # DisplayedPierceArmour


def read_building(r):
    r.i16()                                               # ConstructionGraphicID
    r.i16()                                               # SnowGraphicID (>= TC)
    r.i16()                                               # DestructionGraphicID (>= C10)
    r.i16()                                               # DestructionRubbleGraphicID (>= C12)
    r.i16(); r.i16()                                      # ResearchingGraphic, ResearchCompletedGraphic (>= C13)
    r.u8()                                                # AdjacentMode
    r.i16()                                               # GraphicsAngle
    r.u8()                                                # DisappearsWhenBuilt
    r.i16(); r.i16(); r.i16(); r.i16()                    # StackUnitID, FoundationTerrainID, OldOverlayID, TechID
    r.u8()                                                # CanBurn
    # Annexes[4]: int16 UnitID + pair<float> Misplacement = 10 bytes each
    for _ in range(BUILDING_ANNEXES_SIZE):
        r.i16(); r.f32(); r.f32()
    r.i16()                                               # HeadUnit
    r.i16(); r.i16()                                      # TransformUnit, TransformSound
    r.i16()                                               # ConstructionSound
    r.u32(); r.u32()                                      # WwiseTransform/ConstructionSoundID
    r.u8()                                                # GarrisonType
    r.f32(); r.f32()                                      # GarrisonHealRate, GarrisonRepairRate
    r.i16()                                               # PileUnit
    r.skip(LOOTABLE_RES_COUNT)                            # LootingTable[6]


def read_unit(r, collect=None):
    u = {}
    u["type"] = r.u8()
    u["id"] = r.i16()
    r.i32()                                               # LanguageDLLName
    r.i32()                                               # LanguageDLLCreation
    u["class"] = r.i16()
    r.i16_array(2)                                        # StandingGraphic
    r.i16()                                               # DyingGraphic
    r.i16()                                               # UndeadGraphic
    r.u8()                                                # UndeadMode
    u["hit_points"] = r.i16()
    r.f32()                                               # LineOfSight
    r.u8()                                                # GarrisonCapacity
    r.f32(); r.f32(); r.f32()                             # CollisionSize xyz
    r.i16()                                               # TrainSound
    r.i16()                                               # DamageSound
    r.i16()                                               # DeadUnitID
    r.i16()                                               # BloodUnitID
    r.u8(); r.u8()                                        # SortNumber, CanBeBuiltOn
    r.i16()                                               # IconID
    r.u8()                                                # HideInEditor
    r.i16()                                               # OldPortraitPict
    r.u8()                                                # Enabled
    r.u8()                                                # Disabled
    r.i16_array(2)                                        # PlacementSideTerrain
    r.i16_array(2)                                        # PlacementTerrain
    r.f32(); r.f32()                                      # ClearanceSize
    r.u8()                                                # HillMode
    r.u8()                                                # FogVisibility
    r.i16()                                               # TerrainRestriction
    r.u8()                                                # FlyMode
    r.i16()                                               # ResourceCapacity
    r.f32()                                               # ResourceDecay
    r.u8(); r.u8(); r.u8(); r.u8(); r.u8()                # BlastDefenseLevel..InterfaceKind
    r.f32()                                               # MultipleAttributeMode
    r.u8()                                                # MinimapColor
    r.i32(); r.i32()                                      # LanguageDLLHelp, LanguageDLLHotKeyText
    # Unit.cpp:128 -- pre-C30 read path carries an extra hotkey int32 that the
    # engine copies into Creatable.HotKeyFromUnit instead of a TrainLocation.
    if r.gv < GV_C30:
        r.i32()                                           # hotkeyValue (READ path only)
    r.u8(); r.u8(); r.u8(); r.u8()                        # Recyclable, EnableAutoGather, CreateDoppelganger, ResourceGatherGroup
    r.u8(); r.u8(); r.u8()                                # OcclusionMode, ObstructionType, ObstructionClass
    r.u8(); r.u8(); r.i16()                               # Trait, Civilization, Nothing
    r.u8(); r.u8()                                        # SelectionEffect, EditorSelectionColour
    r.f32(); r.f32(); r.f32()                             # OutlineSize xyz
    r.i32(); r.i32()                                      # 2 x int32 (scenario trigger data)
    for _ in range(3):
        read_resource_storage(r)
    dgc = r.u8()
    for _ in range(dgc):
        read_damage_graphic(r)
    r.i16(); r.i16()                                      # SelectionSound, DyingSound
    r.u32(); r.u32(); r.u32(); r.u32()                    # Wwise train/damage/selection/dying
    r.u8(); r.u8()                                        # OldAttackReaction, ConvertTerrain
    u["name"] = r.debug_string()[1]
    r.i16()                                               # CopyID
    r.i16()                                               # BaseID

    t = u["type"]
    # TaskSwapGroup is 0 for every record that has no bird/task block, and the
    # only nonzero values in VER 8.9 are the villager/fishing-ship swapping
    # baskets.  Defaulting the key here keeps the model uniform so callers never
    # have to distinguish "no task block" from "group 0".
    u["task_swap_group"] = 0
    if t == UNIT_TYPE_AOE_TREES:
        if collect is not None:
            collect(u)
        return u
    if t >= UNIT_TYPE_FLAG:
        r.f32()                                           # Speed
    else:
        if collect is not None:
            collect(u)
        return u
    if t >= UNIT_TYPE_DEAD_FISH:
        read_dead_fish(r)
    if t >= UNIT_TYPE_BIRD:
        u["task_swap_group"] = read_bird(r)
    if t >= UNIT_TYPE_COMBATANT:
        read_type50(r)
    if t == UNIT_TYPE_PROJECTILE:
        read_projectile(r)
    if t >= UNIT_TYPE_CREATABLE:
        read_creatable(r)
    if t == UNIT_TYPE_BUILDING:
        read_building(r)
    if collect is not None:
        collect(u)
    return u


def read_civ(r, collect=None):
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
            c["units"].append(read_unit(r, collect))
    return c


def read_research_resource_cost(r):                       # int16, int16, uint8
    r.i16(); r.i16(); r.u8()


def read_research_location(r):
    return (r.i16(), r.i16(), r.u8(), r.i32())            # 9 B


def read_tech(r):
    t = {}
    r.i16_array(6)                                        # RequiredTechs (>= AoKA => 6)
    for _ in range(3):
        read_research_resource_cost(r)
    r.i16()                                               # RequiredTechCount
    t["civ"] = r.i16()                                    # (gv >= AoKB)
    r.i16()                                               # FullTechMode
    # Research.cpp:70 -- moved into ResearchLocations for gv >= GV_C31
    if r.gv < GV_C31:
        r.i16()                                           # ResearchLocation
    # Research.cpp:73-87 -- i32 for DE (gv >= GV_C18), else u16 pair
    if r.gv >= GV_MATT:
        if GV_C18 <= r.gv <= GV_LatestDE2:
            r.i32()                                       # LanguageDLLName
            r.i32()                                       # LanguageDLLDescription
        else:
            r.i16(); r.i16()                              # LanguageDLLNameU16/DescU16
    # Research.cpp:89 -- moved into ResearchLocations for gv >= GV_C31
    if r.gv < GV_C31:
        r.i16()                                           # ResearchTime
    t["effect_id"] = r.i16()
    t["type"] = r.i16()
    t["icon_id"] = r.i16()
    # Research.cpp:96 -- moved into ResearchLocations for gv >= GV_C31
    if r.gv < GV_C31:
        r.u8()                                            # ButtonID
    r.i32()                                               # LanguageDLLHelp
    r.i32()                                               # LanguageDLLTechTree
    # Research.cpp:105 -- deprecated once ResearchLocations exists
    if r.gv < GV_C31:
        r.i32()                                           # HotKey
    t["name"] = r.debug_string()[1]
    if GV_C15 <= r.gv <= GV_LatestDE2:
        r.u8()                                            # Repeatable
    # Research.cpp:131 -- DE carries an explicit array; older versions
    # synthesise one entry from the scalars (no bytes on the wire).
    if GV_C31 <= r.gv <= GV_LatestDE2:
        n = r.i16()
        t["research_locations"] = [read_research_location(r) for _ in range(n)]
    else:
        t["research_locations"] = None
    return t


# --- tech tree -------------------------------------------------------------
def read_common(r):                                       # techtree::Common
    r.i32()                                               # SlotsUsed
    r.i32_array(10)                                       # UnitResearch
    r.i32_array(10)                                       # Mode
    # = 84 bytes


def _group(r):
    n = r.u8()
    if n:
        r.i32_array(n)


def read_tech_tree_age(r):
    r.i32()                                               # ID
    r.u8()                                                # Status
    _group(r); _group(r); _group(r)                       # Buildings, Units, Techs
    read_common(r)
    r.u8()                                                # NumBuildingLevels
    r.skip(10)                                            # BuildingsPerZone
    r.skip(10)                                            # GroupLengthPerZone
    r.u8()                                                # MaxAgeLength
    r.i32()                                               # LineMode


def read_building_connection(r):
    r.i32()
    r.u8()
    _group(r); _group(r); _group(r)
    read_common(r)
    r.u8()                                                # LocationInAge
    r.skip(AGES)                                          # UnitsTechsTotal
    r.skip(AGES)                                          # UnitsTechsFirst
    r.i32()                                               # LineMode
    r.i32()                                               # EnablingResearch


def read_unit_connection(r):
    r.i32()
    r.u8()
    r.i32()                                               # UpperBuilding
    read_common(r)
    r.i32()                                               # VerticalLine
    _group(r)
    r.i32()                                               # LocationInAge
    r.i32()                                               # RequiredResearch
    r.i32()                                               # LineMode
    r.i32()                                               # EnablingResearch


def read_research_connection(r):
    r.i32()
    r.u8()
    r.i32()                                               # UpperBuilding
    _group(r); _group(r); _group(r)
    read_common(r)
    r.i32()                                               # VerticalLine
    r.i32()                                               # LocationInAge
    r.i32()                                               # LineMode


def read_tech_tree(r):
    tt = {}
    age_count = r.u8()
    building_count = r.u8()
    # TechTree.cpp:68 -- TechTree is the one place that guards with an inline
    # getGameVersion() call rather than a cached `gv` local, so the unit count
    # is int16 only from C32 onward and a single byte before that. Reading the
    # wrong width here misaligns the whole remaining tail.
    if r.gv >= GV_C32:
        unit_count = r.i16()
    else:
        unit_count = r.u8()
    # TechTree.cpp:77 -- int16 only for the CCV2 build, uint8 everywhere else.
    if r.gv == GV_CCV2:
        research_count = r.i16()
    else:
        research_count = r.u8()
    tt["total_unit_tech_groups"] = r.i32()
    tt["ages"] = age_count
    tt["buildings"] = building_count
    tt["units"] = unit_count
    tt["research"] = research_count
    for _ in range(age_count):
        read_tech_tree_age(r)
    for _ in range(building_count):
        read_building_connection(r)
    for _ in range(unit_count):
        read_unit_connection(r)
    for _ in range(research_count):
        read_research_connection(r)
    return tt


# ---------------------------------------------------------------------------
# Top-level driver
# ---------------------------------------------------------------------------
class Parser(object):
    def __init__(self, data):
        self.r = Reader(data)
        self.stats = {}
        self.stage_offsets = []
        self.first_units = []
        self.notes = []

    def _collect_unit(self, u):
        if len(self.first_units) < 5:
            self.first_units.append({"name": u["name"], "hit_points": u["hit_points"],
                                     "type": u["type"], "id": u["id"]})

    def _stage(self, name, fn, stop_after=None):
        start = self.r.pos
        fn()
        end = self.r.pos
        self.stage_offsets.append((name, start, end))
        print("stage %-34s start 0x%08X  end 0x%08X  (%d bytes)"
              % (name, start, end, end - start))
        if stop_after:
            print("stopped after stage '%s' at offset %d" % (name, end))
            raise SystemExit(0)

    def parse(self, stop_after=None):
        r = self.r
        s = self.stats

        # ---- stage 1 ------------------------------------------------------
        def stage1():
            s["file_version"] = r.fixed_string(FILE_VERSION_SIZE)
            # Every later record layout branches on the game version, so the
            # reader must carry it before a single record is decoded.
            s["game_version"] = gv_from_version_string(s["file_version"])
            r.gv = s["game_version"]
            s["terrain_restriction_count"] = r.i16()
            s["terrains_used1"] = r.i16()
            s["float_ptr_terrain_tables"] = r.i32_array(s["terrain_restriction_count"])
            s["terrain_pass_graphic_pointers"] = r.i32_array(s["terrain_restriction_count"])
            s["terrain_restrictions"] = [
                read_terrain_restriction(r, s["terrains_used1"])
                for _ in range(s["terrain_restriction_count"])
            ]
            s["player_colour_count"] = r.i16()
            s["player_colours"] = [read_player_colour(r) for _ in range(s["player_colour_count"])]
        self._stage("1 FileVersion+TerrainRestr+Colours", stage1,
                    stop_after == 1)

        # ---- stage 2 ------------------------------------------------------
        def stage2():
            s["sound_count"] = r.i16()
            s["sounds"] = [read_sound(r) for _ in range(s["sound_count"])]
        self._stage("2 Sounds", stage2, stop_after == 2)

        # ---- stage 3 ------------------------------------------------------
        def stage3():
            s["graphic_count"] = r.i16()
            ptrs = r.i32_array(s["graphic_count"])
            s["graphic_pointers_nonzero"] = sum(1 for p in ptrs if p != 0)
            s["graphics"] = [read_graphic(r) for p in ptrs if p != 0]
        self._stage("3 Graphics", stage3, stop_after == 3)

        # ---- stage 4 ------------------------------------------------------
        def stage4():
            s["terrain_block"] = read_terrain_block(r)
            s["random_maps"] = read_random_maps(r)
        self._stage("4 TerrainBlock+RandomMaps", stage4, stop_after == 4)

        # ---- stage 5 ------------------------------------------------------
        def stage5():
            s["effect_count"] = r.i32()
            s["effects"] = [read_effect(r) for _ in range(s["effect_count"])]
        self._stage("5 Effects", stage5, stop_after == 5)

        # ---- stage 6: UnitLines ------------------------------------------
        # DatFile.cpp:214  if (gv >= GV_SWGB)  --  GV_C32 < GV_SWGB, so this
        # block is NOT executed for a DE "VER 8.9" file.  We do not read it.
        s["unit_lines"] = None
        self.notes.append(
            "Stage 6 (UnitLines) SKIPPED: DatFile.cpp:214 guards UnitLines with "
            "`if (gv >= GV_SWGB)`; GV_C32 < GV_SWGB, so a VER 8.9 file contains "
            "no UnitLines array here. The task brief listed it as a stage; the "
            "source contradicts that, and reading it would corrupt everything after."
        )
        print("stage 6 UnitLines                          SKIPPED (gv >= GV_SWGB is false)")

        # ---- stage 7 ------------------------------------------------------
        def stage7():
            s["unit_header_count"] = r.i32()
            s["unit_headers"] = [read_unit_header(r) for _ in range(s["unit_header_count"])]
        self._stage("7 UnitHeaders", stage7, stop_after == 7)

        # ---- stage 8 ------------------------------------------------------
        def stage8():
            s["civ_count"] = r.i16()
            s["civs"] = [read_civ(r, self._collect_unit) for _ in range(s["civ_count"])]
        self._stage("8 Civs", stage8, stop_after == 8)

        # ---- stage 9 ------------------------------------------------------
        def stage9():
            s["tech_count"] = r.i16()
            s["techs"] = [read_tech(r) for _ in range(s["tech_count"])]
        self._stage("9 Techs", stage9, stop_after == 9)

        # ---- stage 10 -----------------------------------------------------
        def stage10():
            s["time_slice"] = r.i32()
            s["unit_kill_rate"] = r.i32()
            s["unit_kill_total"] = r.i32()
            s["unit_hit_point_rate"] = r.i32()
            s["unit_hit_point_total"] = r.i32()
            s["razing_kill_rate"] = r.i32()
            s["razing_kill_total"] = r.i32()
            s["tech_tree"] = read_tech_tree(r)
        self._stage("10 Tail+TechTree", stage10, stop_after == 10)

        return s


def main():
    argv = sys.argv[1:]
    stop_after = None
    path = None
    for a in argv:
        if a.startswith("--stop-after="):
            stop_after = int(a.split("=", 1)[1])
        else:
            path = a

    if path is None:
        path = (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
                r"\empires2_x2_p1.dat")

    t0 = time.time()
    data, how = load_dat(path)
    t1 = time.time()
    print("source        : %s" % path)
    print("decompression : %s" % how)
    print("raw size      : %d bytes  (%.2f s)" % (len(data), t1 - t0))
    print("first 8 bytes : %r" % data[:8])
    print("")

    p = Parser(data)
    try:
        st = p.parse(stop_after=stop_after)
    except EOFError as e:
        off = p.r.pos
        print("")
        print("!!! PARSE FAILED: %s" % e)
        ctx = data[max(0, off - 16):off + 16]
        print("    offset %d (0x%X)" % (off, off))
        print("    bytes around offset: %s" % " ".join("%02x" % b for b in ctx))
        raise SystemExit(1)

    t2 = time.time()
    final = p.r.pos
    total = len(data)

    print("")
    print("=" * 72)
    print("RESULT")
    print("=" * 72)
    print("final offset        : %d" % final)
    print("data size           : %d" % total)
    print("exact match         : %s" % ("YES" if final == total else "NO"))
    print("leftover bytes      : %d" % (total - final))
    print("parse time          : %.2f s" % (t2 - t1))
    print("")
    print("FileVersion         : %r" % st.get("file_version"))
    print("terrain restrictions: %d" % st["terrain_restriction_count"])
    print("TerrainsUsed1       : %d" % st["terrains_used1"])
    print("player colours      : %d" % st["player_colour_count"])
    print("sounds              : %d" % st["sound_count"])
    print("graphics (total)    : %d" % st["graphic_count"])
    print("graphics (nonzero)  : %d" % st["graphic_pointers_nonzero"])
    print("effects             : %d" % st["effect_count"])
    print("unit lines          : %s" % (st["unit_lines"] if st["unit_lines"] is not None else "not present for GV_C32"))
    print("unit headers        : %d" % st["unit_header_count"])
    print("civs                : %d" % st["civ_count"])
    print("techs               : %d" % st["tech_count"])
    tt = st["tech_tree"]
    print("techtree ages/buildings/units/research: %d/%d/%d/%d"
          % (tt["ages"], tt["buildings"], tt["units"], tt["research"]))
    print("")
    print("first units decoded inside Civs (name, hit points):")
    for u in p.first_units:
        print("    %-40r type=%-3d id=%-4d hp=%d"
              % (u["name"], u["type"], u["id"], u["hit_points"]))

    total_units = sum(len(c["units"]) for c in st["civs"])
    print("")
    print("total unit objects decoded across all civs: %d"
          % total_units)

    print("")
    print("stage offsets:")
    for name, a, b in p.stage_offsets:
        print("    %-34s 0x%08X -> 0x%08X  (%d)" % (name, a, b, b - a))

    print("")
    print("notes / uncertainties:")
    if not p.notes:
        print("    (none)")
    for n in p.notes:
        print("    - %s" % n)

    if final != total:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
