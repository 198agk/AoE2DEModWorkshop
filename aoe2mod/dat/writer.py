"""write_dat.py -- re-serializer for AoE2 DE ``.dat`` files.

VENDORED VERBATIM from _probe/serializer/write_dat.py by
tools/sync_engine.py.  Do not edit here; edit the research copy and
re-run the sync, or the verification lineage is lost.
"""

import io
import os
import struct
import zlib

# Version constants and the FileVersion -> GameVersion mapping live in
# parse_dat.py; importing them keeps exactly one authoritative copy.  The
# writer needs them because several record layouts branch on the game version
# (Task.Enabled, Tech ResearchLocations, Creatable train locations, ...).
from . import parser as _pd

GV_C4 = _pd.GV_C4
GV_C13 = _pd.GV_C13
GV_C15 = _pd.GV_C15
GV_C16 = _pd.GV_C16
GV_C17 = _pd.GV_C17
GV_C18 = _pd.GV_C18
GV_C19 = _pd.GV_C19
GV_C20 = _pd.GV_C20
GV_C22 = _pd.GV_C22
GV_C23 = _pd.GV_C23
GV_C24 = _pd.GV_C24
GV_C25 = _pd.GV_C25
GV_C26 = _pd.GV_C26
GV_C27 = _pd.GV_C27
GV_C28 = _pd.GV_C28
GV_C29 = _pd.GV_C29
GV_C30 = _pd.GV_C30
GV_C31 = _pd.GV_C31
GV_C32 = _pd.GV_C32
GV_CCV2 = _pd.GV_CCV2
GV_MATT = _pd.GV_MATT
GV_LatestDE2 = _pd.GV_LatestDE2

DEBUG_STRING_MARKER = 0x0A60

# One effect command on disk: u8 type + i16 a + i16 b + i16 c + f32 d = 11 B.
# Kept as a constant because `write_effect` needs it to walk the raw cursor over
# a list whose length the model changed (see `Writer.replay_raw`).
EFFECT_COMMAND_BYTES = 11


# ---------------------------------------------------------------------------
# low level deflate container (same convention as load_dat in parse_dat.py)
# ---------------------------------------------------------------------------
def load_dat(path):
    """Return (decompressed_bytes, how).  Mirrors parse_dat.load_dat()."""
    with open(path, "rb") as fh:
        blob = fh.read()
    if blob[:4] == b"VER ":
        return blob, "already-decompressed"
    d = zlib.decompressobj(-15)
    data = d.decompress(blob) + d.flush()
    return data, "raw-deflate(window_bits=-15)"


def deflate(data, level=6):
    """Raw deflate (window_bits=-15) exactly as the game container uses."""
    c = zlib.compressobj(level, zlib.DEFLATED, -15)
    return c.compress(data) + c.flush()


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------
class Writer(object):
    """Accumulates the decompressed stream.

    ``raw`` (optional) is the original decompressed stream.  A cursor walks it
    in lock-step with the output: modeled fields advance it by their own width,
    and unmodeled runs are copied from it.  Because the cursor is advanced by
    *structure* rather than by output offset, appended records (which do not
    exist in ``raw``) do not disturb it.
    """

    __slots__ = ("out", "raw", "pos", "rpos", "model_bytes",
                 "opaque_bytes", "mismatches", "first_mismatch", "strict",
                 "opaque_sites", "compare_limit", "marks", "cur", "log",
                 "trace", "suppress", "mismatch_list", "gv")

    def __init__(self, raw=None, strict=True, trace=False, gv=None):
        self.out = bytearray()
        self.raw = raw
        self.pos = 0       # OUTPUT offset (grows with appended records)
        self.rpos = 0      # RAW-stream cursor (advances by STRUCTURE only)
        self.model_bytes = 0
        self.opaque_bytes = 0
        self.mismatches = 0
        self.first_mismatch = None
        self.mismatch_list = []
        self.opaque_sites = 0
        self.strict = strict
        # comparisons are only meaningful up to the original EOF
        self.compare_limit = len(raw) if raw is not None else 0
        self.marks = []
        self.cur = "?"
        self.trace = trace
        self.log = []
        self.suppress = 0
        # Game version the records are laid out for.  Record widths branch on
        # it (see parse_dat.py for the authoritative guard list), so the writer
        # must be told which layout to emit; None keeps the DE/C32 default so
        # existing callers are unaffected.
        self.gv = GV_C32 if gv is None else gv

    def new_record(self):
        """Emit a record that has no counterpart in ``raw``.

        Inside this context the raw cursor is frozen (``op``/modeled fields do
        not advance it, and comparisons are muted), and on exit it is restored
        so the verbatim replay of the pre-existing structure resumes at exactly
        the same raw offset.  Without this, appending one record would shift
        every later ``op()`` read and corrupt the whole tail.
        """
        return _NewRecord(self)

    def mark(self, name):
        """Record the current output offset under ``name`` (stage debugging)."""
        self.marks.append((name, self.pos))

    def advance_raw(self, n):
        """Move the raw cursor by ``n`` bytes without emitting anything.

        Use this when the model writes a list whose ELEMENT COUNT changed: the
        element writes above already advanced the cursor by the NEW count, so
        ``n`` is the width the raw stream stored for the whole list.

        Measured reason it exists (2026-10-22): appending two `type 102`
        commands to a shipped effect emitted 22 extra bytes and left the cursor
        drifting, so every later field was read from the wrong offset -- the
        93 MB stream serialised to 96,331,764 B (+3,061,612) and a re-parse died
        in ``read_bird``.  The first attempt at a fix advanced the cursor a
        SECOND time by the old width and lost 27 MB, which is what a repair
        that is not read back looks like.
        """
        n = int(n)
        if not n:
            return
        if not self.suppress:
            self.rpos = max(0, self.rpos + n)

    # -- core ---------------------------------------------------------------
    def _emit(self, b, kind, raw_len=None):
        """Append ``b`` and advance the raw cursor by ``raw_len``.

        ``raw_len`` defaults to ``len(b)``, which is what every in-place patch
        wants: the field we write is the same width as the field it replaces.
        A LENGTH-CHANGING edit (rewriting a graphics record's ``file`` string to
        name a different picture) must pass the width the raw stream actually
        stored, or ``rpos`` lands inside the next raw field and every later
        ``op()`` copies shifted bytes.  Measured before this argument existed: a
        single +3 byte string produced 991,273 mismatches and a 3 MB file.
        """
        b = bytes(b)
        n = len(b)
        if raw_len is None:
            raw_len = n
        # A length-changing edit cannot be compared byte-for-byte against the
        # stream it replaces, so it is not a "mismatch" (that counter means the
        # model DISAGREES with the raw stream, which must stay 0).  Widths that
        # do match are compared over the raw width, which is the same thing.
        if (self.strict and not self.suppress and self.raw is not None
                and raw_len == n
                and self.rpos + n <= self.compare_limit):
            seg = self.raw[self.rpos:self.rpos + n]
            if seg != b:
                self.mismatches += 1
                if len(self.mismatch_list) < 64:
                    self.mismatch_list.append((self.rpos, n, kind, b, seg,
                                               self.cur))
                if self.first_mismatch is None:
                    self.first_mismatch = (self.rpos, n, kind, b, seg,
                                           self.cur, list(self.log[-24:]))
        self.out += b
        self.pos += n
        if not self.suppress:
            self.rpos += raw_len
        if self.trace:
            self.log.append((self.pos, kind, n, self.cur))
            if len(self.log) > 64:
                del self.log[0]
        if kind == "opaque":
            self.opaque_bytes += n
        else:
            self.model_bytes += n

    # -- verbatim channel ---------------------------------------------------
    def op(self, n):
        """Emit ``n`` bytes verbatim from the raw stream (unmodeled run).

        Inside a :meth:`new_record` context there is no raw counterpart, so
        zeros are emitted instead (and the raw cursor is left untouched).
        """
        if n <= 0:
            return
        self.opaque_sites += 1
        if self.raw is None or self.suppress:
            self._emit(b"\x00" * n, "opaque")
        else:
            self._emit(self.raw[self.rpos:self.rpos + n], "opaque")

    def _peek(self, fmt, n):
        if self.raw is None or self.suppress or self.rpos + n > len(self.raw):
            return 0
        return struct.unpack_from(fmt, self.raw, self.rpos)[0]

    def opu8(self):
        v = self._peek("<B", 1); self.op(1); return v

    def opi16(self):
        v = self._peek("<h", 2); self.op(2); return v

    def opu16(self):
        v = self._peek("<H", 2); self.op(2); return v

    def opi32(self):
        v = self._peek("<i", 4); self.op(4); return v

    def opu32(self):
        v = self._peek("<I", 4); self.op(4); return v

    # -- modeled primitives -------------------------------------------------
    def u8(self, v):
        self._emit(struct.pack("<B", v & 0xFF), "model")

    def u16(self, v):
        self._emit(struct.pack("<H", v & 0xFFFF), "model")

    def i16(self, v):
        self._emit(struct.pack("<h", v), "model")

    def u32(self, v):
        self._emit(struct.pack("<I", v & 0xFFFFFFFF), "model")

    def i32(self, v):
        self._emit(struct.pack("<i", v), "model")

    def f32(self, v):
        self._emit(struct.pack("<f", v), "model")

    def fixed_string(self, s, n):
        """``Reader.fixed_string(n)`` inverse: latin-1 bytes, zero padded."""
        b = s.encode("latin-1")[:n]
        self._emit(b + b"\x00" * (n - len(b)), "model")

    def debug_string(self, s, raw_len=None):
        """``serializeDebugString``: u16 marker, u16 EXACT byte count, bytes.

        genieutils uses ``serializeSize<uint16_t>(size, str.size())`` -- there
        is NO ``+1`` for a NUL terminator.  ``Reader.debug_string`` cuts the
        text at the first NUL, so writing ``len(bytes)`` reproduces the file
        value only because the stored strings contain no embedded NUL.

        ``raw_len`` is the width the raw stream used for THIS string, needed
        only when the new text is a different length (a reskin retargeting a
        graphics record at another picture).  It is passed to ``_emit`` so the
        raw cursor keeps pointing at the next raw field.
        """
        b = s.encode("latin-1")
        self.u16(DEBUG_STRING_MARKER)
        self.u16(len(b))
        self._emit(b, "model", raw_len=raw_len)
    # -- accounting ---------------------------------------------------------
    def stats(self, size):
        return {
            "output_bytes": size,
            "model_bytes": self.model_bytes,
            "opaque_bytes": self.opaque_bytes,
            "opaque_sites": self.opaque_sites,
            "model_pct": (100.0 * self.model_bytes / size) if size else 0.0,
            "opaque_pct": (100.0 * self.opaque_bytes / size) if size else 0.0,
            "model_vs_original_mismatches": self.mismatches,
            "first_model_mismatch": self.first_mismatch,
            "model_mismatches": list(self.mismatch_list),
            "raw_consumed": self.rpos,
            "raw_size": len(self.raw) if self.raw is not None else 0,
        }


class _NewRecord(object):
    """Context manager returned by :meth:`Writer.new_record`.

    Freezes the raw cursor and mutes model-vs-raw comparison for the duration of
    a synthesised record, then restores both.  Modeled fields are still emitted
    from the model (that is the point), but ``op()`` runs would read raw bytes at
    the wrong place, so inside the context ``op()`` emits zeros instead.
    """

    __slots__ = ("w",)

    def __init__(self, w):
        self.w = w

    def __enter__(self):
        self.w.suppress += 1
        return self.w

    def __exit__(self, exc_type, exc, tb):
        self.w.suppress -= 1
        return False


# ---------------------------------------------------------------------------
# section writers -- each mirrors the same-named reader in parse_dat.py
# ---------------------------------------------------------------------------
def _write_pair_i16(w, pair):
    w.i16(pair[0])
    w.i16(pair[1])


def write_terrain_pass_graphic(w, tpg):
    # TerrainPassGraphic::serializeObject  (GV_C32 -> float WalkSpriteRate)
    w.i32(tpg[0]); w.i32(tpg[1]); w.i32(tpg[2]); w.f32(tpg[3])


def write_terrain_restriction(w, tr):
    for f in tr["mult"]:
        w.f32(f)
    for tpg in tr["pass"]:
        write_terrain_pass_graphic(w, tpg)


def write_player_colour(w, pc):
    for v in pc:
        w.i32(v)


def write_sound_item(w, it):
    w.debug_string(it["file"])
    w.i32(it["resource_id"])
    w.i16(it["probability"])
    w.i16(it["civilization"])
    w.i16(it["iconset"])


def write_sound(w, s):
    w.i16(s["id"])
    w.i16(s["play_delay"])
    w.i16(len(s["items"]))            # serializeSize<int16_t>(file_count, ...)
    w.i32(s["cache_time"])
    w.i16(s["total_probability"])
    for it in s["items"]:
        write_sound_item(w, it)


def write_graphic_delta(w, d):
    # GraphicDelta: i16 GraphicID, i16 Padding1, i32 SpritePtr,
    #                i16 OffsetX, i16 OffsetY, i16 DisplayAngle, i16 Padding2
    w.i16(d[0]); w.i16(d[1]); w.i32(d[2])
    w.i16(d[3]); w.i16(d[4]); w.i16(d[5]); w.i16(d[6])


def write_graphic_angle_sound(w, ans):
    # GraphicAngleSound: 3x { i16 FrameNum, i16 SoundID, u32 WwiseSoundID }
    for frame_num, sound_id, wwise in ans:
        w.i16(frame_num); w.i16(sound_id); w.u32(wwise)


def write_graphic(w, g):
    w.debug_string(g["name"])
    # `_file_len` is the width the raw stream used; passing it lets the writer
    # retarget a record at a picture whose filename has a different length while
    # keeping every later verbatim read aligned.  Absent the key (every record
    # the parser read before this field existed) it defaults to len(file), which
    # is what an in-place write wants anyway.
    w.debug_string(g["file"], raw_len=g.get("_file_len"))
    w.debug_string(g["particle_effect"])
    w.i32(g["slp"])
    w.u8(g["is_loaded"])
    w.u8(g["old_color_flag"])
    w.u8(g["layer"])
    w.i16(g["player_color"])
    w.u8(g["transparent_selection"])
    for v in g["coordinates"]:
        w.i16(v)
    w.i16(len(g["deltas"]))           # serializeSize<int16_t>(delta_count, ...)
    w.i16(g["sound_id"])
    w.u32(g["wwise_sound_id"])
    w.u8(g["angle_sounds_used"])
    w.i16(g["frame_count"])
    w.i16(g["angle_count"])
    # NOT modeled: SpeedMultiplier, FrameDuration, ReplayDelay (3x f32) and
    # SequenceType (u8).  C++ rewrites FrameDuration, so these 13 bytes are
    # taken verbatim -- a reconstructed value could never be trusted.
    w.op(13)
    w.i16(g["id"])
    w.u8(g["mirroring_mode"])
    w.u8(g["editor_flag"])
    for d in g["deltas"]:
        write_graphic_delta(w, d)
    if g["angle_sounds_used"] != 0:
        for ans in g["angle_sounds"]:
            write_graphic_angle_sound(w, ans)


def write_frame_data(w):
    w.op(6)                            # i16 FrameCount, AngleCount, ShapeID


def write_terrain(w, t):
    w.u8(t["enabled"])
    w.u8(t["random"])
    w.u8(t["is_water"])
    w.u8(t["hide_in_editor"])
    w.i32(t["string_id"])
    w.debug_string(t["name"])
    w.debug_string(t["name2"])
    w.i32(t["slp"])
    w.i32(t["shape_ptr"])
    w.i32(t["sound_id"])
    w.u32(t["wwise_sound_id"])
    w.u32(t["wwise_sound_stop_id"])
    w.i32(t["blend_priority"])
    w.i32(t["blend_type"])
    w.debug_string(t["overlay_mask_name"])
    w.op(5)                            # Colors[3] + CliffColors pair
    w.u8(t["passable_terrain"])
    w.u8(t["impassable_terrain"])
    w.u8(t["is_animated"])
    # AnimationFrames, PauseFames, Interval, PauseBetweenLoops, Frame,
    # DrawFrame, AnimateLast, FrameChanged, Drawn  (22 bytes)
    w.op(22)
    for _ in range(19):                # FrameData[19]
        write_frame_data(w)
    # TerrainToDraw(2) + TerrainDimensions(4) + TerrainUnitMaskedDensity(60)
    # + TerrainUnitID(60) + TerrainUnitDensity(60) + TerrainUnitCentering(30)
    # + NumberOfTerrainUnitsUsed(2)
    w.op(218)
    w.i16(t["phantom"])                # gv < GV_SWGB -> Phantom IS present


def write_terrain_block(w, tb):
    w.u32(tb["virtual_function_ptr"])
    w.u32(tb["map_pointer"])
    w.i32(tb["map_width"])
    w.i32(tb["map_height"])
    w.i32(tb["world_width"])
    w.i32(tb["world_height"])
    for ts in tb["tile_sizes"]:
        for v in ts:
            w.i16(v)
    w.op(2)                            # PaddingTS
    for t in tb["terrains"]:
        write_terrain(w, t)
    w.f32(tb["map_min_x"]); w.f32(tb["map_min_y"])
    w.f32(tb["map_max_x"]); w.f32(tb["map_max_y"])
    w.f32(tb["map_max_x_plus1"]); w.f32(tb["map_max_y_plus1"])
    w.i16(tb["terrains_used2"])
    w.i16(tb["borders_used"])
    w.i16(tb["max_terrain"])
    w.i16(tb["tile_width"])
    w.i16(tb["tile_height"])
    w.i16(tb["tile_half_height"])
    w.i16(tb["tile_half_width"])
    w.i16(tb["elev_height"])
    w.i16(tb["cur_row"])
    w.i16(tb["cur_col"])
    w.i16(tb["block_beg_row"])
    w.i16(tb["block_end_row"])
    w.i16(tb["block_beg_col"])
    w.i16(tb["block_end_col"])
    w.u32(tb["search_map_ptr"])
    w.u32(tb["search_map_rows_ptr"])
    w.u8(tb["any_frame_change"])
    w.u8(tb["map_visible_flag"])
    w.u8(tb["fog_flag"])


def _write_map_land(w):
    w.op(16); w.op(4); w.op(8); w.op(4); w.op(12)


def _write_map_terrain(w):
    w.op(24)


def _write_map_unit(w):
    # RandomMap.cpp:214-229 -- i32 Unit | i32 HostTerrain | u8 GroupPlacing
    # | u8 ScaleFlag | i16 Padding1 | i32 x8  ==  4+4+1+1+2+32 == 44 B.
    # (was op(10)+op(32) == 42 B, which silently desynced the raw cursor)
    w.op(12); w.op(32)


def _write_map_elevation(w):
    w.op(24)


_MAP_WRITERS = (("lands", _write_map_land),
                ("terrains", _write_map_terrain),
                ("units", _write_map_unit),
                ("elevations", _write_map_elevation))


def write_random_maps(w, rm):
    w.u32(rm["count"])
    w.i32(rm["random_maps_ptr"])
    # RandomMap.cpp:62-63 runs serializeSub<MapInfo> TWICE over the same vector.
    # ``io_all_`` is a per-MapInfo member (RandomMap.h:147, non-static), so on
    # pass 0 every map is header+counts only and on pass 1 every map carries its
    # bodies.  A single shared flag that toggles *inside* the map loop instead
    # alternates between maps, which only happens to coincide when count <= 1.
    maps = rm["maps"]
    for _pass in range(2):
        io_all = (_pass == 1)
        for _m in maps:
            if not io_all:
                w.opi32()              # MapID
            w.op(36)                   # 9 x int32 header
            for _key, _fn in _MAP_WRITERS:
                c = w.opu32()
                w.opi32()              # *Ptr
                if io_all:
                    for _ in range(c):
                        _fn(w)


def write_effect_command(w, c):
    w.u8(c[0]); w.i16(c[1]); w.i16(c[2]); w.i16(c[3]); w.f32(c[4])


def write_effect(w, e):
    if e.get("_new"):
        # synthesised record: no counterpart in `raw`, so freeze the raw cursor
        # and mute model-vs-raw comparison for its duration.
        with w.new_record():
            w.debug_string(e["name"])
            w.i16(len(e["commands"]))
            for c in e["commands"]:
                write_effect_command(w, c)
        return
    w.debug_string(e["name"])
    old_n = w._peek("<h", 2) if w.raw is not None and w.rpos + 2 <= len(w.raw) else len(e["commands"])
    w.i16(len(e["commands"]))
    # The command list is a variable-length run: writing it from the model
    # advances the raw cursor by NEW_COUNT * 11, but the raw stream stored
    # OLD_COUNT * 11.  Correct the cursor by the DIFFERENCE so the next field is
    # read where it really starts.
    #
    # Measured 2026-10-22: without this, appending two `type 102` commands
    # produced a 96,331,764 B stream (+3,061,612) whose re-parse died in
    # `read_bird` -- every field after this record came from the wrong offset.
    # The first attempt advanced by the whole old width on top of the new one
    # and lost 27 MB; a repair is only a repair if the round-trip is read back.
    for c in e["commands"]:
        write_effect_command(w, c)
    if old_n is not None and old_n != len(e["commands"]):
        w.advance_raw(EFFECT_COMMAND_BYTES * (old_n - len(e["commands"])))


def write_task(w, t):
    """Mirrors ``read_task``: only ``task_type`` and ``id`` survive the parse.

    The remaining 65 bytes (IsDefault .. Enabled, gv >= GV_C28 for that last
    int16) are unmodeled and replayed verbatim.  Total record = 69 bytes,
    matching parse_dat.py:446-460 exactly.
    """
    w.i16(t["task_type"])
    w.i16(t["id"])
    task_tail(w)


def task_tail(w):
    w.op(1)    # IsDefault                        (u8)
    w.op(8)    # ActionType..TerrainID            (4 x i16)
    w.op(8)    # ResourceIn..UnusedResource       (4 x i16)
    w.op(12)   # WorkValue1, WorkValue2, WorkRange(3 x f32)
    w.op(1)    # AutoSearchTargets                (u8)
    w.op(4)    # SearchWaitTime                   (f32)
    w.op(2)    # EnableTargeting, CombatLevelFlag (2 x u8)
    w.op(4)    # GatherType, WorkFlag2            (2 x i16)
    w.op(3)    # TargetDiplomacy, CarryCheck, PickForConstruction (3 x u8)
    w.op(8)    # Moving/Proceeding/Working/Carrying               (4 x i16)
    w.op(4)    # ResourceGathering, DepositSoundID                (2 x i16)
    if GV_C4 <= w.gv <= GV_LatestDE2:                       # UnitCommand.cpp:76
        w.op(8)    # Wwise gathering/deposit ID                   (2 x u32)
    if w.gv >= GV_C28:                                      # UnitCommand.cpp:81
        w.op(2)    # Enabled                                     (i16)


def write_unit_header(w, uh):
    w.u8(uh["exists"])
    if uh["exists"]:
        w.i16(len(uh["tasks"]))
        for t in uh["tasks"]:
            write_task(w, t)


def write_resource_storage(w):
    w.op(7)                            # i16, f32, u8


def write_damage_graphic(w):
    w.op(5)                            # i16, i16, u8


def write_dead_fish(w):
    w.op(2); w.op(2); w.op(4); w.op(1); w.op(2); w.op(1); w.op(4)
    w.op(1); w.op(4); w.op(4); w.op(4); w.op(4); w.op(4); w.op(4)


def write_bird(w):
    w.op(2); w.op(4); w.op(4)
    n = w.opi16()
    w.op(2 * n)                        # DropSites
    w.op(1)                            # TaskSwapGroup
    w.op(2)                            # AttackSound
    w.op(2)                            # MoveSound
    w.op(4); w.op(4)                   # Wwise attack/move
    w.op(1)                            # RunPattern
    tn = w.opi16()
    # read_bird discards the Task objects it reads (parse_dat.py:497-499), so
    # there is nothing in the model to re-emit -- replay each 4+65-byte record.
    for _ in range(tn):
        w.op(4)                        # task_type, id
        task_tail(w)


def write_attack_or_armor(w):
    w.op(4)


def write_type50(w):
    w.op(2)                            # BaseArmor
    n = w.opi16()
    for _ in range(n):
        write_attack_or_armor(w)
    n = w.opi16()
    for _ in range(n):
        write_attack_or_armor(w)
    w.op(2); w.op(4); w.op(4); w.op(4); w.op(4)
    w.op(2); w.op(2); w.op(1); w.op(2)
    w.op(4); w.op(4); w.op(4); w.op(1)
    w.op(4); w.op(4); w.op(2); w.op(2); w.op(2)
    w.op(4); w.op(4)                   # DisplayedRange, DisplayedReloadTime
    if GV_C20 <= w.gv <= GV_LatestDE2:                  # Type50.cpp:94
        w.op(4)                        # BlastDamage
    if GV_C22 <= w.gv <= GV_LatestDE2:                  # Type50.cpp:99
        w.op(4); w.op(4)               # DamageReflection, FriendlyFireDamage
    if GV_C27 <= w.gv <= GV_LatestDE2:                  # Type50.cpp:105
        w.op(2); w.op(4); w.op(2)      # InterruptFrame, GarrisonFirepower, AttackGraphic2


def write_projectile(w):
    w.op(5); w.op(4)


def write_train_location(w):
    w.op(2); w.op(2); w.op(1)
    if GV_C30 <= w.gv <= GV_LatestDE2:                  # TrainLocation.cpp:28
        w.op(4)                                         # HotKeyID


def write_resource_cost(w):
    w.op(6)


def write_creatable(w):
    for _ in range(3):
        write_resource_cost(w)
    if GV_C29 <= w.gv <= GV_LatestDE2:                  # Creatable.cpp:58
        n = w.opi16()
        for _ in range(n):
            write_train_location(w)
    else:
        write_train_location(w)                         # Creatable.cpp:66 -- exactly 1
    w.op(4); w.op(4); w.op(1); w.op(1); w.op(4)         # Rear/FlankAttackModifier, CreatableType,
                                                        # HeroMode, GarrisonGraphic
    if GV_C13 <= w.gv <= GV_LatestDE2:                  # Creatable.cpp:91
        w.op(2); w.op(2)                                # SpawningGraphic, UpgradeGraphic
        if w.gv >= GV_C16:
            if w.gv >= GV_C17:
                w.op(2)                                 # HeroGlowGraphic
            if w.gv >= GV_C26:                          # Creatable.cpp:102
                w.op(2)                                 # IdleAttackGraphic
            w.op(4); w.op(4)                            # MaxCharge, RechargeRate
            w.op(2); w.op(2)                            # ChargeEvent, ChargeType
            if w.gv >= GV_C23:                          # Creatable.cpp:111
                w.op(2)                                 # ChargeTarget
            if w.gv >= GV_C25:                          # Creatable.cpp:116
                w.op(4); w.op(1); w.op(4)               # ChargeProjectileUnit, AttackPriority,
                                                        # InvulnerabilityLevel
            if w.gv >= GV_C24:                          # Creatable.cpp:123
                w.op(2); w.op(4); w.op(4); w.op(2)      # ButtonIconID, ButtonShort/ExtendedTooltipID,
                                                        # ButtonHotkeyAction
            if w.gv >= GV_C19:                          # Creatable.cpp:131
                w.op(4); w.op(4); w.op(4)               # Min/MaxConversionTimeMod, ConversionChanceMod
    w.op(4)                             # TotalProjectiles
    w.op(1)                             # MaxTotalProjectiles
    w.op(12)                            # ProjectileSpawningArea[3]
    w.op(4)                             # SecondaryProjectileUnit
    w.op(4)                             # SpecialGraphic
    w.op(1)                             # SpecialAbility
    w.op(2)                             # DisplayedPierceArmour


def write_building(w):
    w.op(2); w.op(2); w.op(2); w.op(2); w.op(2); w.op(2)
    w.op(1); w.op(2); w.op(1); w.op(2); w.op(2); w.op(2); w.op(2); w.op(1)
    for _ in range(4):                 # Annexes[4]: i16 + pair<float> = 10 B
        w.op(10)
    w.op(2); w.op(2); w.op(2); w.op(2)
    w.op(4); w.op(4); w.op(1); w.op(4); w.op(4); w.op(2); w.op(6)


def write_unit(w, u):
    w.cur = "unit type=%d id=%d" % (u["type"], u["id"])
    if u.get("_img"):
        # A record the model could not rebuild field by field: emit the bytes it
        # was made from.  `serialize_dat` only ever writes a synthesised record
        # through `new_record()`, so the raw cursor is frozen and the verbatim
        # replay of the pre-existing stream resumes at the same offset.
        #
        # Why a byte image at all: a unit record's tail is type-dependent
        # (Type50 / Projectile / Creatable / Building, each with its own version
        # guards), so rebuilding it from zeros would be one guess per field.  A
        # clone of an existing record is exactly right by construction.
        # `new_record()` is not optional: without it `_emit` advances the raw
        # cursor by the record's length, so every later `op()` replays the wrong
        # bytes and the file stops re-parsing (measured: `bad char in struct
        # format` inside read_bird).  Inside the context the cursor is frozen and
        # the verbatim replay resumes where the previous record ended.
        with w.new_record():
            w._emit(bytes(u["_img"]), "new unit record")
        return
    w.u8(u["type"])
    w.i16(u["id"])
    w.op(4); w.op(4)                   # LanguageDLLName, LanguageDLLCreation
    w.i16(u["class"])
    w.op(4)                            # StandingGraphic[2]
    w.op(2); w.op(2); w.op(1)          # DyingGraphic, UndeadGraphic, UndeadMode
    w.i16(u["hit_points"])
    w.op(4); w.op(1)                   # LineOfSight, GarrisonCapacity
    w.op(12)                           # CollisionSize xyz
    w.op(2); w.op(2); w.op(2); w.op(2)  # TrainSound, DamageSound, DeadUnitID, BloodUnitID
    w.op(2)                            # SortNumber, CanBeBuiltOn
    w.op(2); w.op(1); w.op(2); w.op(2)  # IconID, HideInEditor, OldPortraitPict, Enabled+Disabled
    w.op(4); w.op(4)                   # PlacementSideTerrain, PlacementTerrain
    w.op(8)                            # ClearanceSize[2]
    w.op(2)                            # HillMode, FogVisibility
    w.op(2); w.op(1)                   # TerrainRestriction, FlyMode
    w.op(2); w.op(4)                   # ResourceCapacity, ResourceDecay
    w.op(5)                            # BlastDefenseLevel..InterfaceKind
    w.op(4)                            # MultipleAttributeMode
    w.op(1)                            # MinimapColor
    w.op(8)                            # LanguageDLLHelp, LanguageDLLHotKeyText
    # Unit.cpp:128 -- pre-C30 carries an extra hotkey int32 (READ path only; the
    # engine folds it into Creatable.HotKeyFromUnit).  Present on disk for e.g.
    # VER 7.8, so it must round-trip here too.
    if w.gv < GV_C30:
        w.op(4)                        # hotkeyValue
    w.op(4); w.op(3); w.op(4)          # Recyclable..GatherGroup, Occlusion..Class, Trait+Civ+Nothing
    w.op(2)                            # SelectionEffect, EditorSelectionColour
    w.op(12)                           # OutlineSize xyz
    w.op(8)                            # 2 x int32 scenario trigger data
    for _ in range(3):
        write_resource_storage(w)
    dgc = w.opu8()
    for _ in range(dgc):
        write_damage_graphic(w)
    w.op(2); w.op(2)                   # SelectionSound, DyingSound
    w.op(16)                           # 4 x u32 Wwise
    w.op(2)                            # OldAttackReaction, ConvertTerrain
    w.debug_string(u["name"])
    w.op(4)                            # CopyID, BaseID

    t = u["type"]
    if t == 90:                        # UNIT_TYPE_AOE_TREES
        return
    if t >= 20:                        # UNIT_TYPE_FLAG
        w.op(4)                        # Speed
    else:
        return
    if t >= 30:                        # DeadFish
        write_dead_fish(w)
    if t >= 40:                        # Bird
        write_bird(w)
    if t >= 50:                        # Combatant -> Type50
        write_type50(w)
    if t == 60:                        # Projectile
        write_projectile(w)
    if t >= 70:                        # Creatable
        write_creatable(w)
    if t == 80:                        # Building
        write_building(w)


def write_civ(w, c):
    w.u8(c["player_type"])
    w.debug_string(c["name"])
    w.i16(len(c["resources"]))
    w.i16(c["tech_tree_id"])
    w.i16(c["team_bonus_id"])
    for v in c["resources"]:
        w.f32(v)
    w.u8(c["icon_set"])
    ptrs = c.get("_ptrs")
    if ptrs is None:
        w.i16(c["unit_pointers_total"])
        w.op(4 * c["unit_pointers_total"])  # unit pointer array (all-zero/value lost)
    else:
        # Rebuilt from the set of ids this civ actually has.  The array is a
        # PER-ID EXISTENCE FLAG, not a list of offsets: measured on the shipped
        # file, all 2,750 slots exist and every non-zero value is 1 (civ 0 holds
        # 2,693 records, slots 0..2749).  Writing it field by field is what makes
        # adding a record possible at all -- `w.op(4*n)` replays the old bytes,
        # so one extra record shifted the whole tail by 3,009,349 bytes and the
        # result would not re-parse.
        #
        # Slots BEYOND the shipped array have no raw counterpart, so they are
        # emitted without advancing the raw cursor (raw_len=0).  Writing them
        # with i32 would advance rpos past the raw array and shift every later
        # op() by 4 bytes per added slot -- measured: one extra slot produced
        # 3,009,559 extra bytes and a stream that died in read_unit.
        raw_n = c["unit_pointers_total"]
        w.i16(len(ptrs))
        for i, v in enumerate(ptrs):
            if i < raw_n:
                w.i32(v)
            else:
                w._emit(struct.pack("<i", v), "model", raw_len=0)
    for u in c["units"]:
        write_unit(w, u)


def write_research_location(w, loc):
    # A location is (location_id, research_time, button_id, hotkey_id) on disk.
    # The model carries it as a dict (that is what `locate_techs` returns and
    # what the reader hands back), while hand-written callers pass a tuple.
    # Both used to be "the same thing" until 2026-10-22, when the first real
    # `_new` tech with a modelled donor location died on `KeyError: 0` -- the
    # shipped branch replays these with `w.op()` and never came through here.
    if isinstance(loc, dict):
        w.i16(loc["location_id"]); w.i16(loc["research_time"])
        w.u8(loc["button_id"]); w.i32(loc["hotkey_id"])
        return
    w.i16(loc[0]); w.i16(loc[1]); w.u8(loc[2]); w.i32(loc[3])


def write_tech(w, t):
    if t.get("_new"):
        # synthesised record: no counterpart in `raw` -- freeze the raw cursor so
        # the verbatim replay of the tail (stage 10) still starts at the right
        # raw offset.
        #
        # The four display-string ids are NOT zeros any more.  They used to be,
        # and that quietly made every synthesised tech unnameable: string id 0
        # is defined in 0 of the 17 locale tables (measured 2026-10-22, max
        # shipped id 30030001), so the record could exist and never say what it
        # is.  A caller now has to supply `lang_name`; the rest default to 0
        # because "no description" is a real state the shipped file also uses.
        with w.new_record():
            for _ in range(6):
                w.i16(0)                   # RequiredTechs[6]
            for _ in range(3):
                w.i16(0); w.i16(0); w.u8(0)  # ResearchResourceCost[3]
            w.i16(0)                       # RequiredTechCount
            w.i16(t["civ"])
            w.i16(0)                       # FullTechMode
            if w.gv < GV_C31:
                w.i16(0)                   # ResearchLocation (Research.cpp:70)
            w.i32(int(t.get("lang_name") or 0))
            w.i32(int(t.get("lang_description") or 0))
            if w.gv < GV_C31:
                w.i16(0)                   # ResearchTime (Research.cpp:89)
            w.i16(t["effect_id"])
            w.i16(t["type"])
            w.i16(t["icon_id"])
            if w.gv < GV_C31:
                w.u8(0)                    # ButtonID (Research.cpp:96)
            w.i32(int(t.get("lang_help") or 0))
            w.i32(int(t.get("lang_tech_tree") or 0))
            if w.gv < GV_C31:
                w.i32(0)                   # HotKey (Research.cpp:105)
            w.debug_string(t["name"])
            if GV_C15 <= w.gv <= GV_LatestDE2:
                w.u8(0)                    # Repeatable (Research.cpp:126)
            if GV_C31 <= w.gv <= GV_LatestDE2:      # Research.cpp:131
                w.i16(len(t["research_locations"] or []))
                for loc in (t["research_locations"] or []):
                    write_research_location(w, loc)
        return
    w.op(12)                           # RequiredTechs[6]
    w.op(15)                           # ResearchResourceCost[3]
    w.op(2)                            # RequiredTechCount
    w.i16(t["civ"])
    w.op(2)                            # FullTechMode
    if w.gv < GV_C31:
        w.op(2)                        # ResearchLocation (Research.cpp:70)
    w.op(4); w.op(4)                   # LanguageDLLName, LanguageDLLDescription
    if w.gv < GV_C31:
        w.op(2)                        # ResearchTime (Research.cpp:89)
    w.i16(t["effect_id"])
    w.i16(t["type"])
    w.i16(t["icon_id"])
    if w.gv < GV_C31:
        w.op(1)                        # ButtonID (Research.cpp:96)
    w.op(4); w.op(4)                   # LanguageDLLHelp, LanguageDLLTechTree
    if w.gv < GV_C31:
        w.op(4)                        # HotKey (Research.cpp:105)
    w.debug_string(t["name"])
    if GV_C15 <= w.gv <= GV_LatestDE2:
        w.op(1)                        # Repeatable (Research.cpp:126)
    if GV_C31 <= w.gv <= GV_LatestDE2:          # Research.cpp:131
        w.i16(len(t["research_locations"] or []))
        for loc in (t["research_locations"] or []):
            write_research_location(w, loc)


# -- tech tree (entirely unmodeled beyond its header counts) ----------------
def _write_common(w):
    w.op(84)                           # SlotsUsed + UnitResearch[10] + Mode[10]


def _write_group(w):
    n = w.opu8()
    if n:
        w.op(4 * n)


def write_tech_tree_age(w):
    w.opi32()                          # ID
    w.opu8()                           # Status
    _write_group(w); _write_group(w); _write_group(w)
    _write_common(w)
    w.opu8()                           # NumBuildingLevels
    w.op(10); w.op(10)                 # BuildingsPerZone, GroupLengthPerZone
    w.opu8()                           # MaxAgeLength
    w.opi32()                          # LineMode


def write_building_connection(w):
    w.opi32()
    w.opu8()
    _write_group(w); _write_group(w); _write_group(w)
    _write_common(w)
    w.opu8()                           # LocationInAge
    w.op(5); w.op(5)                   # UnitsTechsTotal, UnitsTechsFirst
    w.opi32()                          # LineMode
    w.opi32()                          # EnablingResearch


def write_unit_connection(w):
    w.opi32()
    w.opu8()
    w.opi32()                          # UpperBuilding
    _write_common(w)
    w.opi32()                          # VerticalLine
    _write_group(w)
    w.opi32()                          # LocationInAge
    w.opi32()                          # RequiredResearch
    w.opi32()                          # LineMode
    w.opi32()                          # EnablingResearch


def write_research_connection(w):
    w.opi32()
    w.opu8()
    w.opi32()                          # UpperBuilding
    _write_group(w); _write_group(w); _write_group(w)
    _write_common(w)
    w.opi32()                          # VerticalLine
    w.opi32()                          # LocationInAge
    w.opi32()                          # LineMode


def write_tech_tree(w, tt):
    w.u8(tt["ages"])
    w.u8(tt["buildings"])
    # TechTree.cpp:68 -- int16 only from C32; uint8 for every older version.
    if w.gv >= GV_C32:
        w.i16(tt["units"])
    else:
        w.u8(tt["units"])
    # TechTree.cpp:77 -- int16 only for the CCV2 build, uint8 everywhere else.
    if w.gv == GV_CCV2:
        w.i16(tt["research"])
    else:
        w.u8(tt["research"])
    w.i32(tt["total_unit_tech_groups"])
    for _ in range(tt["ages"]):
        write_tech_tree_age(w)
    for _ in range(tt["buildings"]):
        write_building_connection(w)
    for _ in range(tt["units"]):
        write_unit_connection(w)
    for _ in range(tt["research"]):
        write_research_connection(w)


# ---------------------------------------------------------------------------
# top level
# ---------------------------------------------------------------------------
def serialize_dat(stats, raw=None, strict=True, gv=None):
    """Serialise ``stats`` (from ``parse_dat.Parser``) to the .dat byte stream.

    ``raw`` is the original decompressed stream, used verbatim for the runs the
    model does not carry.  Returns ``(bytes, report_dict)``.

    ``gv`` selects the record layouts.  When omitted it is derived from
    ``stats["game_version"]`` (written by the parser's stage 1), which keeps
    legacy files such as VER 7.8 round-tripping without every caller having to
    thread the version through.  Files parsed before this existed simply fall
    back to the DE default.
    """
    if gv is None:
        gv = stats.get("game_version") or GV_C32
    w = Writer(raw, strict=strict, gv=gv)
    s = stats

    # ---- stage 1 ----------------------------------------------------------
    w.fixed_string(s["file_version"], 8)
    w.i16(s["terrain_restriction_count"])
    w.i16(s["terrains_used1"])
    for v in s["float_ptr_terrain_tables"]:
        w.i32(v)
    for v in s["terrain_pass_graphic_pointers"]:
        w.i32(v)
    for tr in s["terrain_restrictions"]:
        write_terrain_restriction(w, tr)
    w.i16(s["player_colour_count"])
    for pc in s["player_colours"]:
        write_player_colour(w, pc)

    # ---- stage 2 ----------------------------------------------------------
    w.i16(s["sound_count"])
    for snd in s["sounds"]:
        write_sound(w, snd)

    # ---- stage 3 ----------------------------------------------------------
    w.i16(s["graphic_count"])
    w.op(4 * s["graphic_count"])       # Graphics pointer array (values lost)
    for g in s["graphics"]:
        write_graphic(w, g)

    # ---- stage 4 ----------------------------------------------------------
    write_terrain_block(w, s["terrain_block"])
    write_random_maps(w, s["random_maps"])

    # ---- stage 5 ----------------------------------------------------------
    w.i32(len(s["effects"]))
    for e in s["effects"]:
        write_effect(w, e)

    # ---- stage 6: UnitLines absent for GV_C32 (DatFile.cpp:214) -----------

    # ---- stage 7 ----------------------------------------------------------
    w.i32(s["unit_header_count"])
    for uh in s["unit_headers"]:
        write_unit_header(w, uh)

    # ---- stage 8 ----------------------------------------------------------
    w.i16(s["civ_count"])
    for c in s["civs"]:
        write_civ(w, c)

    # ---- stage 9 ----------------------------------------------------------
    w.i16(len(s["techs"]))
    for t in s["techs"]:
        write_tech(w, t)

    # ---- stage 10 ---------------------------------------------------------
    w.i32(s["time_slice"])
    w.i32(s["unit_kill_rate"])
    w.i32(s["unit_kill_total"])
    w.i32(s["unit_hit_point_rate"])
    w.i32(s["unit_hit_point_total"])
    w.i32(s["razing_kill_rate"])
    w.i32(s["razing_kill_total"])
    write_tech_tree(w, s["tech_tree"])

    out = bytes(w.out)
    return out, w.stats(len(out))


def write_dat_file(stats, out_path, raw=None, strict=True, level=6, gv=None):
    """Serialise and write a raw-deflate .dat container to ``out_path``."""
    data, rep = serialize_dat(stats, raw=raw, strict=strict, gv=gv)
    blob = deflate(data, level)
    d = os.path.dirname(out_path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(out_path, "wb") as fh:
        fh.write(blob)
    rep["compressed_bytes"] = len(blob)
    rep["decompressed_bytes"] = len(data)
    return rep


def _main(argv):
    base = (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
            r"\empires2_x2_p1.dat")
    import contextlib, sys, time
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "datparse"))
    from aoe2mod.dat import parser as parse_dat

    t0 = time.time()
    raw, how = load_dat(base)
    print("source        : %s" % base)
    print("decompression : %s" % how)
    print("raw size      : %d bytes" % len(raw))
    p = parse_dat.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        st = p.parse()
    print("parsed        : final offset %d  leftover %d"
          % (p.r.pos, len(raw) - p.r.pos))
    data, rep = serialize_dat(st, raw=raw, strict=True)
    print("serialized    : %d bytes" % len(data))
    print("model bytes   : %d (%.2f%%)" % (rep["model_bytes"], rep["model_pct"]))
    print("opaque bytes  : %d (%.2f%%) in %d sites"
          % (rep["opaque_bytes"], rep["opaque_pct"], rep["opaque_sites"]))
    print("model!=raw    : %d field group(s)" % rep["model_vs_original_mismatches"])
    if rep["first_model_mismatch"]:
        off, n, kind, got, want = rep["first_model_mismatch"]
        print("  first at raw offset %d (0x%X) width %d kind %s"
              % (off, off, n, kind))
        print("    model : %s" % got.hex())
        print("    raw   : %s" % want.hex())
    print("identical     : %s" % ("YES" if data == raw else "NO"))
    print("%.2f s" % (time.time() - t0))
    return 0 if data == raw else 2


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
