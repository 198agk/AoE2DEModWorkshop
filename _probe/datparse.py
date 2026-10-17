# -*- coding: utf-8 -*-
"""
Pure-Python reader/writer for empires2_x2_p1.dat  (VER 8.9  =>  genie GV_C32).

Transliterated field-by-field from the genieutils sources that the game itself
ships (Tools_Builds/docs/Source.7z -> genieutils/), so it is authoritative
rather than community-reverse-engineered.

Why this exists: AGE (AdvancedGenieEditor3.exe) is the only existing editor and
it has no headless/batch mode -- it can only "open one dat path in a GUI".  Our
tool needs a real library-level API, so we must own the parser.

Design notes / hard-won gotchas, all verified against the real 12 MB file:
  * GameVersion ordering IS the logic.  GV_C32 (VER 8.9) is numerically SMALLER
    than GV_SWGB, so every `gv >= GV_SWGB` branch is DEAD and every "legacy
    fixed-size string" branch (the huge `gv > GV_LatestTap && gv < GV_C2 || ...`
    expression) is FALSE -- meaning all strings go through serializeDebugString
    (uint16 marker 0x0A60 + uint16 length + bytes).  Forgetting this desyncs.
  * `serializeSubWithPointers` writes NOTHING for a zero pointer, so the
    Graphics/Units arrays are sparse and a slot with pointer==0 consumes 0 bytes.
  * GraphicAngleSound holds THREE FrameNum/SoundID pairs, not one (24 bytes at
    this version).  Guessing "one pair" desyncs after ~366 graphics.
  * TerrainRestriction::setTerrainCount(TerrainsUsed1) is a GLOBAL that also
    controls how many Terrains the TerrainBlock contains (134 here, not 200).
  * Unit's trailing sections are Type-gated; Type must be retained, never skipped.
  * The whole .dat is a raw deflate stream (no zlib header).
  * zlib cannot reproduce the original compressed bytes byte-for-byte, so an
    edit is validated by re-parsing, not by comparing compressed output.

Authoritative sources under _probe/source/genieutils:
  src/dat/*.cpp, src/dat/unit/*.cpp, include/genie/dat/*.h,
  include/genie/file/ISerializable.h, include/genie/Types.h
"""
import struct, sys, zlib, json

# ---------------------------------------------------------------------------
# GameVersion -- ORDER IS SEMANTIC (include/genie/Types.h).  Do not reorder.
# ---------------------------------------------------------------------------
GV_NAMES = [
    "GV_None", "GV_TEST", "GV_MIK", "GV_DAVE", "GV_MATT", "GV_AoEB", "GV_AoE",
    "GV_RoR", "GV_Tapsa", "GV_T2", "GV_T3", "GV_T4", "GV_T5", "GV_T6", "GV_T7",
    "GV_T8", "GV_AoKE3", "GV_AoKA", "GV_AoKB", "GV_AoK", "GV_TC", "GV_TCV",
    "GV_Cysion", "GV_C2", "GV_C3", "GV_C4", "GV_CK", "GV_C5", "GV_C6", "GV_C7",
    "GV_C8", "GV_C9", "GV_C10", "GV_C11", "GV_C12", "GV_C13", "GV_C14",
    "GV_C15", "GV_C16", "GV_C17", "GV_C18", "GV_C19", "GV_C20", "GV_C21",
    "GV_C22", "GV_C23", "GV_C24", "GV_C25", "GV_C26", "GV_C27", "GV_C28",
    "GV_C29", "GV_C30", "GV_C31", "GV_C32",
    "GV_SWGB", "GV_CC", "GV_CCV", "GV_CCV2",
]
assert len(GV_NAMES) == 59, len(GV_NAMES)
globals().update({n: i for i, n in enumerate(GV_NAMES)})

GV_ANCIENT = set([GV_None, GV_TEST, GV_MIK, GV_DAVE, GV_MATT])

GV_LatestTap = GV_T8
GV_LatestDE2 = GV_C32
GV = GV_C32                       # the version of the file we read

FILE_VERSION_SIZE = 8
DBG_MARKER = 0x0A60

TILE_TYPE_COUNT = 19
TERRAIN_UNITS_SIZE = 30
BUILDING_ANNEXES_SIZE = 4
LOOTABLE_RES_COUNT = 4
TECHTREE_AGES = 5

# UnitType thresholds (include/genie/dat/Unit.h)
UT_EyeCandy = 10
UT_Trees = 15
UT_Flag = 20
UT_25 = 25
UT_Dead_Fish = 30
UT_Bird = 40
UT_Combatant = 50
UT_Projectile = 60
UT_Creatable = 70
UT_Building = 80
UT_AoeTrees = 90

# GameVersion -> dat version string (genie/Types.h SupportedDatVersionsToGameVersion)
DAT_VERSION_MAP = {
    "VER 8.9": GV_C32, "VER 8.8": GV_C31, "VER 8.7": GV_C30,
    "VER 8.6": GV_C29, "VER 8.5": GV_C28, "VER 8.4": GV_C27,
    "VER 8.3": GV_C26, "VER 8.2": GV_C25, "VER 8.1": GV_C24,
}


def is_legacy_string(gv):
    """The giant `gv > GV_LatestTap && gv < GV_C2 || gv < GV_Tapsa || gv > GV_LatestDE2`
    expression repeated all over genieutils.  False for GV_C32 -> always dbgstr."""
    return (gv > GV_LatestTap and gv < GV_C2) or (gv < GV_Tapsa) or (gv > GV_LatestDE2)


class DatError(Exception):
    pass


class Cursor(object):
    """Read/write cursor over a bytearray.  One class, two directions, because
    the field layout must stay identical between parse and save."""

    def __init__(self, buf, gv=GV):
        self.b = bytearray(buf) if not isinstance(buf, bytearray) else buf
        self.o = 0
        self.gv = gv
        self.marks = {}
        self.writing = False

    # -- primitives --------------------------------------------------------
    _FMT = {"b": "b", "B": "B", "h": "h", "H": "H", "i": "i", "I": "I",
            "q": "q", "Q": "Q", "f": "f", "d": "d"}
    _SZ = {"b": 1, "B": 1, "h": 2, "H": 2, "i": 4, "I": 4, "q": 8, "Q": 8,
           "f": 4, "d": 8}

    def u(self, ch):
        """Read one scalar."""
        n = self._SZ[ch]
        v = struct.unpack_from("<" + self._FMT[ch], self.b, self.o)[0]
        self.o += n
        return v

    def ua(self, ch, n):
        """Read n scalars as a list."""
        n = int(n)
        if n <= 0:
            return []
        v = list(struct.unpack_from("<%d%s" % (n, self._FMT[ch]), self.b, self.o))
        self.o += self._SZ[ch] * n
        return v

    def put(self, ch, v):
        self.b[self.o:self.o + self._SZ[ch]] = struct.pack("<" + self._FMT[ch], v)
        self.o += self._SZ[ch]

    def puta(self, ch, vs):
        if len(vs):
            self.b[self.o:self.o + self._SZ[ch] * len(vs)] = \
                struct.pack("<%d%s" % (len(vs), self._FMT[ch]), *vs)
            self.o += self._SZ[ch] * len(vs)

    def skip(self, n):
        self.o += int(n)

    def zeros(self, n):
        self.b[self.o:self.o + int(n)] = b"\x00" * int(n)
        self.o += int(n)

    def raw(self, n):
        s = bytes(self.b[self.o:self.o + n])
        self.o += n
        return s

    def putraw(self, s):
        self.b[self.o:self.o + len(s)] = s
        self.o += len(s)

    # -- strings -----------------------------------------------------------
    def dbgstr(self):
        """serializeDebugString: uint16 0x0A60 marker, uint16 size, size bytes.
        size includes a trailing NUL when the string is non-empty."""
        if self.writing:
            raise DatError("dbgstr write not supported here")
        m = self.u("H")
        if m != DBG_MARKER:
            raise DatError("debug-string marker 0x%04x != 0x0A60 at 0x%x"
                           % (m, self.o - 4))
        n = self.u("H")
        if n == 0:
            return ""
        return self.raw(n).rstrip(b"\x00").decode("utf-8", "replace")

    def fixedstr(self, n):
        return self.raw(n).rstrip(b"\x00").decode("utf-8", "replace")

    def mark(self, label):
        self.marks[label] = self.o


# ---------------------------------------------------------------------------
class Dat(object):
    """Parses the whole .dat.  Keeps only what the higher layers need, plus
    enough per-slot detail to dump/round-trip."""

    def __init__(self, raw_bytes, gv=GV, verbose=False):
        self.gv = gv
        self.verbose = verbose
        self.c = Cursor(raw_bytes, gv)
        # filled by parse()
        self.doc = {}

    # == helpers ==========================================================
    def _c(self):
        return self.c

    # == entry point ======================================================
    def parse(self):
        c = self.c
        doc = self.doc

        fv = c.fixedstr(FILE_VERSION_SIZE)
        doc["FileVersion"] = fv
        if fv not in DAT_VERSION_MAP:
            raise DatError("unsupported dat version %r" % fv)
        doc["GameVersion"] = GV_NAMES[DAT_VERSION_MAP[fv]]
        gv = self.gv = DAT_VERSION_MAP[fv]
        c.gv = gv

        # `if (gv >= GV_SWGB)` block (Civs count + 4 unknown int32) is DEAD here.
        if gv >= GV_SWGB:
            raise DatError("GV_SWGB layout not implemented")

        # ---- TerrainRestrictions ---------------------------------------
        n_tr = c.u("h")
        terrains_used = c.u("h")
        doc["numTerrainRestrictions"] = n_tr
        doc["terrainsUsed"] = terrains_used
        c.ua("i", n_tr)                       # FloatPtrTerrainTables
        if gv >= GV_AoKA:
            c.ua("i", n_tr)                   # TerrainPassGraphicPointers
        c.mark("terrainRestrictions")
        for _ in range(n_tr):
            c.ua("f", terrains_used)          # PassableBuildableDmgMultiplier
            c.skip(terrains_used * 16)        # TerrainPassGraphic: 4 x int32
        c.mark("playerColours")

        # ---- PlayerColours ---------------------------------------------
        n_pc = c.u("h")
        doc["numPlayerColours"] = n_pc
        c.skip(n_pc * 9 * 4)
        c.mark("sounds")

        # ---- Sounds -----------------------------------------------------
        n_snd = c.u("h")
        doc["numSounds"] = n_snd
        for _ in range(n_snd):
            c.skip(6)                         # ID, PlayDelay, file_count
            fc = c.u("h")
            c.skip(6)                         # CacheTime(i32) + TotalProbability(i16)
            for _ in range(fc):
                c.dbgstr()                    # FileName
                c.skip(10)                    # ResourceID, Prob, Civ, IconSet
        c.mark("graphics")

        # ---- Graphics ---------------------------------------------------
        n_g = c.u("h")
        doc["numGraphics"] = n_g
        gptrs = c.ua("i", n_g)
        n_gz = sum(1 for p in gptrs if p)
        doc["numGraphicsNonZero"] = n_gz
        c.mark("graphicsBody")
        self.graphics = []
        for i, p in enumerate(gptrs):
            if p:
                self.graphics.append(self._graphic())
            else:
                self.graphics.append(None)
        c.mark("terrainBlock")

        # ---- TerrainBlock ----------------------------------------------
        self._terrain_block(terrains_used)
        c.mark("randomMaps")

        # ---- RandomMaps -------------------------------------------------
        self._random_maps()
        c.mark("effects")

        # ---- Effects ----------------------------------------------------
        n_eff = c.u("i")
        doc["numEffects"] = n_eff
        for _ in range(n_eff):
            c.dbgstr()                        # Name
            ncmd = c.u("h")
            c.skip(ncmd * 11)                 # EffectCommand: u8 + 3 x i16 + f
        c.mark("unitHeaders")

        # ---- UnitHeaders (gv >= GV_AoK) ---------------------------------
        n_uh = c.u("i")
        doc["numUnitHeaders"] = n_uh
        for _ in range(n_uh):
            if c.u("B"):                      # Exists
                ntask = c.u("h")
                c.skip(ntask * self._TASK_SIZE)
        c.mark("civs")

        # ---- Civs -------------------------------------------------------
        n_civ = c.u("h")
        doc["numCivs"] = n_civ
        c.mark("units")
        self.civs = []
        for _ in range(n_civ):
            self.civs.append(self._civ())
        c.mark("techs")

        # ---- Techs ------------------------------------------------------
        n_tech = c.u("h")
        doc["numTechs"] = n_tech
        for _ in range(n_tech):
            self._tech()
        c.mark("tail")

        # ---- tail ------------------------------------------------------
        doc["tail"] = c.ua("i", 7)
        self._techtree()
        c.mark("eof")

        doc["parsedBytes"] = c.o
        doc["fileBytes"] = len(c.b)
        doc["leftover"] = len(c.b) - c.o
        return doc

    # -- graphic ----------------------------------------------------------
    def _graphic(self):
        c = self.c
        gv = self.gv
        g = {}
        if is_legacy_string(gv):
            raise DatError("legacy graphic string layout")
        g["Name"] = c.dbgstr()
        g["FileName"] = c.dbgstr()
        if gv >= GV_C5 and gv <= GV_LatestDE2:
            g["ParticleEffectName"] = c.dbgstr()
        g["SLP"] = c.u("i")
        c.skip(3)                             # IsLoaded, OldColorFlag, Layer
        g["PlayerColor"] = c.u("h")
        c.skip(1)                             # TransparentSelection
        g["Coordinates"] = c.ua("h", 4)
        nd = c.u("h")
        g["SoundID"] = c.u("h")
        if gv >= GV_C4 and gv <= GV_LatestDE2:
            c.skip(4)                         # WwiseSoundID
        ang = c.u("B")
        g["FrameCount"] = c.u("h")
        g["AngleCount"] = c.u("h")
        c.skip(4 + 4 + 4)                     # SpeedMultiplier, FrameDuration, ReplayDelay
        c.skip(1)                             # SequenceType
        g["ID"] = c.u("h")
        c.skip(1)                             # MirroringMode
        if gv >= GV_AoKB:
            c.skip(1)                         # EditorFlag
        c.skip(nd * 16)                       # GraphicDelta, 16 bytes each
        if ang != 0:
            c.skip(g["AngleCount"] * self._ANGLE_SOUND_SIZE)
        return g

    #: GraphicAngleSound at this version: (i16,i16,u32) x 3 = 24
    _ANGLE_SOUND_SIZE = (2 + 2 + 4) * 3

    # -- terrain block ----------------------------------------------------
    def _terrain_block(self, terrain_count):
        c = self.c
        gv = self.gv
        c.skip(4 * 6)                         # vfptr, MapPointer, 4 x i32 dims
        c.skip(TILE_TYPE_COUNT * 6)           # TileSize: i16 W,H,DeltaY
        if gv >= GV_AoE:
            c.skip(2)                         # PaddingTS
        for _ in range(terrain_count):
            self._terrain()
        # gv < GV_AoEB -> no AoEAlphaUnknown
        # (gv < GV_C9 || gv > GV_LatestDE2) is FALSE -> no TerrainBorders/MapRowOffset
        if gv >= GV_AoKA:
            c.skip(4 * 4)
            if gv >= GV_AoK:
                c.skip(4 * 2)
        c.skip(2)                             # TerrainsUsed2
        # (gv < GV_AoEB) -> no RemovedBlocksUsed
        c.skip(2 * 13)                        # BordersUsed..BlockEndCol
        if gv >= GV_AoKE3:
            c.skip(4 + 4 + 1)                 # SearchMapPtr, SearchMapRowsPtr, AnyFrameChange
        c.skip(2)                             # MapVisibleFlag, FogFlag

    def _terrain(self):
        c = self.c
        gv = self.gv
        c.skip(2)                             # Enabled, Random
        # (gv >= T2 && gv < C2) is FALSE; (gv >= C8 && <= LatestDE2) is TRUE
        c.skip(6)                             # IsWater, HideInEditor, StringID
        c.dbgstr()                            # Name
        c.dbgstr()                            # Name2
        c.skip(4)                             # SLP
        c.skip(8)                             # ShapePtr, SoundID
        c.skip(4 + 4)                         # WwiseSoundID, WwiseSoundStopID
        c.skip(8)                             # BlendPriority, BlendType
        c.dbgstr()                            # OverlayMaskName
        c.skip(3)                             # Colors[3]
        c.skip(2)                             # CliffColors pair<u8>
        c.skip(2)                             # PassableTerrain, ImpassableTerrain
        c.skip(1)                             # IsAnimated
        c.skip(2 + 2)                         # AnimationFrames, PauseFames
        c.skip(4 + 4)                         # Interval, PauseBetweenLoops
        c.skip(2 + 2)                         # Frame, DrawFrame
        c.skip(4)                             # AnimateLast
        c.skip(2)                             # FrameChanged, Drawn
        c.skip(TILE_TYPE_COUNT * 6)           # ElevationGraphics: 19 x FrameData
        c.skip(2)                             # TerrainToDraw
        c.skip(4)                             # TerrainDimensions pair<i16>
        # (gv >= C8 && <= LatestDE2) TRUE -> MaskedDensity, NOT Borders
        c.skip(2 * TERRAIN_UNITS_SIZE)        # TerrainUnitMaskedDensity
        c.skip(2 * TERRAIN_UNITS_SIZE)        # TerrainUnitID
        c.skip(2 * TERRAIN_UNITS_SIZE)        # TerrainUnitDensity
        c.skip(1 * TERRAIN_UNITS_SIZE)        # TerrainUnitCentering
        c.skip(2)                             # NumberOfTerrainUnitsUsed
        if gv < GV_SWGB:                      # TRUE at GV_C32
            c.skip(2)                         # Phantom

    # -- random maps ------------------------------------------------------
    def _random_maps(self):
        c = self.c
        gv = self.gv
        n = c.u("I")
        self.doc["numRandomMaps"] = n
        c.skip(4)                             # RandomMapsPtr
        for second_pass in (False, True):
            for _ in range(n):
                if not second_pass:
                    c.skip(4)                 # MapID
                c.skip(4 * 9)                 # 4 borders, usage, water, base, cover, unused
                for grp in range(4):
                    cnt = c.u("I")
                    c.skip(4)                 # ptr
                    if second_pass:
                        sz = (48, 24, 44, 24)[grp]
                        c.skip(cnt * sz)

    # -- civ / unit -------------------------------------------------------
    _TASK_SIZE = (2 + 2 + 1 + 2 + 2 + 2 + 2 + 2 + 2 + 2 + 2
                  + 4 * 3 + 1 + 4 + 1 + 1 + 2 + 2 + 1 + 1 + 1
                  + 2 * 5 + 2 + 2 + 4 * 2 + 2)

    def _civ(self):
        c = self.c
        gv = self.gv
        civ = {}
        civ["PlayerType"] = c.u("B")
        civ["Name"] = c.dbgstr()
        nres = c.u("h")
        if gv >= GV_MIK:
            civ["TechTreeID"] = c.u("h")
            if gv >= GV_AoKB:
                civ["TeamBonusID"] = c.u("h")
                # gv >= GV_SWGB is FALSE -> no Name2 / UniqueUnitsTechs
        civ["Resources"] = c.ua("f", nres)
        civ["IconSet"] = c.u("B")
        nunit = c.u("h")
        ptrs = c.ua("i", nunit)
        civ["numUnits"] = nunit
        civ["numUnitsNonZero"] = sum(1 for p in ptrs if p)
        civ["Units"] = []
        for p in ptrs:
            if p:
                civ["Units"].append(self._unit())
            else:
                civ["Units"].append(None)
        return civ

    def _unit(self):
        c = self.c
        gv = self.gv
        u = {}
        utype = c.u("B")
        u["Type"] = utype
        if is_legacy_string(gv):
            raise DatError("legacy unit string layout")
        u["ID"] = c.u("h")
        if gv <= GV_LatestDE2 and gv >= GV_C15:
            u["LanguageDLLName"] = c.u("i")
            u["LanguageDLLCreation"] = c.u("i")
        u["Class"] = c.u("h")
        u["StandingGraphic"] = c.ua("h", 2)      # gv>=GV_AoKB -> both written
        c.skip(2 + 2 + 1)                        # DyingGraphic, UndeadGraphic, UndeadMode
        u["HitPoints"] = c.u("h")
        u["LineOfSight"] = c.u("f")
        c.skip(1)                                # GarrisonCapacity
        c.skip(4 * 3)                            # CollisionSize xyz
        c.skip(2)                                # TrainSound
        if gv >= GV_AoKE3:
            c.skip(2)                            # DamageSound
        c.skip(2)                                # DeadUnitID
        if gv >= GV_C7 and gv <= GV_LatestDE2:
            c.skip(2)                            # BloodUnitID
        c.skip(1 + 1 + 2)                        # SortNumber, CanBeBuiltOn, IconID
        c.skip(1 + 2 + 1)                        # HideInEditor, OldPortraitPict, Enabled
        if gv >= GV_AoK:
            c.skip(1)                            # Disabled
        if gv >= GV_MIK:
            c.skip(4)                            # PlacementSideTerrain
        c.skip(4)                                # PlacementTerrain
        c.skip(8)                                # ClearanceSize pair<float>
        c.skip(1 + 1 + 2 + 1)                    # HillMode, FogVisibility, TerrainRestriction, FlyMode
        c.skip(2 + 4)                            # ResourceCapacity, ResourceDecay
        c.skip(1 + 1 + 1 + 1 + 1)                # BlastDefenseLevel..InterfaceKind
        c.skip(4 + 1)                            # MultipleAttributeMode, MinimapColor
        if gv >= GV_AoEB:
            c.skip(4 + 4)                        # LanguageDLLHelp, HotKeyText
            # gv < GV_C30 is FALSE -> the legacy int32 hotkey is NOT present
            c.skip(1 + 1 + 1 + 1)                # Recyclable..ResourceGatherGroup
            if gv >= GV_AoKE3:
                c.skip(1)                        # OcclusionMode
                if gv >= GV_AoKA:
                    c.skip(1 + 1)                # ObstructionType, ObstructionClass
                    if gv >= GV_TC:
                        c.skip(1 + 1 + 2)        # Trait, Civilization, Nothing
            c.skip(1 + 1)                        # SelectionEffect, EditorSelectionColour
            c.skip(4 * 3)                        # OutlineSize xyz
            if gv >= GV_CK and gv <= GV_LatestDE2:
                c.skip(4 + 4)                    # scenario trigger data
        c.skip(3 * 7)                            # ResourceStorage x3
        ndg = c.u("B")
        c.skip(ndg * 5)                          # DamageGraphic
        c.skip(2 + 2)                            # SelectionSound, DyingSound
        if gv >= GV_C4 and gv <= GV_LatestDE2:
            c.skip(4 * 4)                        # 4 wwise sound ids
        c.skip(1 + 1)                            # OldAttackReaction, ConvertTerrain
        u["Name"] = c.dbgstr()
        if gv >= GV_AoE:
            c.skip(2)                            # CopyID
        if gv >= GV_AoKA:
            c.skip(2)                            # BaseID
        # ---- Type-gated tail (Type is now known!) ----
        if utype == UT_AoeTrees:
            return u
        if utype >= UT_Flag:
            u["Speed"] = c.u("f")
        else:
            return u
        if utype >= UT_Dead_Fish:
            self._dead_fish()
        if utype >= UT_Bird:
            self._bird()
        if utype >= UT_Combatant:
            self._type50()
        if utype == UT_Projectile:
            c.skip(9)                            # Projectile
        if utype >= UT_Creatable:
            self._creatable()
        if utype == UT_Building:
            self._building()
        return u

    def _dead_fish(self):
        c = self.c
        gv = self.gv
        c.skip(2 + 2 + 4 + 1 + 2 + 1 + 4 + 1)    # WalkingGraphic..OldMoveAlgorithm
        if gv >= GV_AoKB:
            c.skip(4 * 5)
            if gv >= GV_C14:
                c.skip(4)                        # MinCollisionSizeMultiplier

    def _bird(self):
        c = self.c
        gv = self.gv
        c.skip(2 + 4 + 4)                        # DefaultTaskID, SearchRadius, WorkRate
        cnt = c.u("h")
        c.skip(cnt * 2)                          # DropSites
        c.skip(1 + 2)                            # TaskSwapGroup, AttackSound
        if gv >= GV_AoEB:
            c.skip(2)                            # MoveSound
        c.skip(4 + 4)                            # Wwise attack/move
        c.skip(1)                                # RunPattern
        ntask = c.u("h")
        c.skip(ntask * self._TASK_SIZE)

    def _type50(self):
        c = self.c
        gv = self.gv
        c.skip(2)                                # BaseArmor (int16 at this version)
        n = c.u("h")
        c.skip(n * 4)                            # Attacks
        n = c.u("h")
        c.skip(n * 4)                            # Armours
        c.skip(2)                                # DefenseTerrainBonus
        if gv >= GV_C16:
            c.skip(4)                            # BonusDamageResistance
        c.skip(4 + 4 + 4)                        # MaxRange, BlastWidth, ReloadTime
        c.skip(2 + 2 + 1)                        # ProjectileUnitID, AccuracyPercent, BreakOffCombat
        c.skip(2 + 4 * 3 + 1 + 4)                # FrameDelay, GraphicDisplacement, BlastAttackLevel, MinRange
        if gv >= GV_AoKB:
            c.skip(4)                            # AccuracyDispersion
        c.skip(2)                                # AttackGraphic
        if gv >= GV_AoEB:
            c.skip(2 + 2 + 4 + 4)                # DisplayedMeleeArmour, DisplayedAttack, DisplayedRange, DisplayedReloadTime
            if gv >= GV_C20:
                c.skip(4)                        # BlastDamage
            if gv >= GV_C22:
                c.skip(4 + 4)                    # DamageReflection, FriendlyFireDamage
            if gv >= GV_C27:
                c.skip(2 + 4 + 2)                # InterruptFrame, GarrisonFirepower, AttackGraphic2

    def _creatable(self):
        c = self.c
        gv = self.gv
        c.skip(3 * 7)                            # ResourceCosts x3
        # gv >= GV_C29 -> counted TrainLocations
        ntl = c.u("h")
        c.skip(ntl * 9)                          # TrainLocation: i16,i16,u8,i32
        if gv >= GV_AoEB:
            if gv >= GV_AoKE3:
                c.skip(4 + 4 + 1)                # RearAttackModifier, FlankAttackModifier, CreatableType
                if gv >= GV_AoKB:
                    c.skip(1 + 4)                # HeroMode, GarrisonGraphic
                    if gv >= GV_C13:
                        c.skip(2 + 2)            # SpawningGraphic, UpgradeGraphic
                        if gv >= GV_C16:
                            if gv >= GV_C17:
                                c.skip(2)        # HeroGlowGraphic
                            if gv >= GV_C26:
                                c.skip(2)        # IdleAttackGraphic
                            c.skip(4 + 4 + 2 + 2)    # MaxCharge, RechargeRate, ChargeEvent, ChargeType
                            if gv >= GV_C23:
                                c.skip(2)        # ChargeTarget
                            if gv >= GV_C25:
                                c.skip(4 + 1 + 4)  # ChargeProjectileUnit, AttackPriority, InvulnerabilityLevel
                            if gv >= GV_C24:
                                c.skip(2 + 4 + 4 + 2)  # ButtonIconID, Short/Extended tooltip, HotkeyAction
                            if gv >= GV_C19:
                                c.skip(4 * 3)    # Min/MaxConversionTimeMod, ConversionChanceMod
                c.skip(4 + 1 + 4 * 3)            # TotalProjectiles, MaxTotalProjectiles, ProjectileSpawningArea
                c.skip(4 + 4 + 1)                # SecondaryProjectileUnit, SpecialGraphic, SpecialAbility
            c.skip(2)                            # DisplayedPierceArmour

    def _building(self):
        c = self.c
        gv = self.gv
        c.skip(2)                                # ConstructionGraphicID
        if gv >= GV_TC:
            c.skip(2)                            # SnowGraphicID
            if gv >= GV_C10:
                c.skip(2)                        # DestructionGraphicID
                if gv >= GV_C12:
                    c.skip(2)                    # DestructionRubbleGraphicID
                    if gv >= GV_C13:
                        c.skip(2 + 2)            # ResearchingGraphic, ResearchCompletedGraphic
        c.skip(1 + 2 + 1)                        # AdjacentMode, GraphicsAngle, DisappearsWhenBuilt
        c.skip(2 * 4)                            # StackUnitID, FoundationTerrainID, OldOverlayID, TechID
        if gv >= GV_AoKE3:
            c.skip(1)                            # CanBurn
            c.skip(BUILDING_ANNEXES_SIZE * 10)   # BuildingAnnex: i16 + 2 x float
            if gv >= GV_AoKA:
                c.skip(2)                        # HeadUnit
            c.skip(2 + 2)                        # TransformUnit, TransformSound
        c.skip(2)                                # ConstructionSound
        if gv >= GV_AoKE3:
            if gv >= GV_C4:
                c.skip(4 + 4)                    # WwiseTransformSoundID, WwiseConstructionSoundID
            c.skip(1 + 4 + 4)                    # GarrisonType, GarrisonHealRate, GarrisonRepairRate
            c.skip(2)                            # PileUnit
            c.skip(LOOTABLE_RES_COUNT)           # LootingTable

    # -- tech -------------------------------------------------------------
    def _tech(self):
        c = self.c
        gv = self.gv
        c.skip(2 * 6)                            # RequiredTechs[6]
        c.skip(3 * 5)                            # ResearchResourceCost x3 (i16,i16,u8)
        c.skip(2)                                # RequiredTechCount
        if gv >= GV_AoKB:
            c.skip(2 + 2)                        # Civ, FullTechMode
        # gv < GV_C31 FALSE -> no inline ResearchLocation
        if gv >= GV_MATT:
            c.skip(4 + 4)                        # LanguageDLLName, LanguageDLLDescription
        # gv < GV_C31 FALSE -> no inline ResearchTime
        c.skip(2 + 2 + 2)                        # EffectID, Type, IconID
        # gv < GV_C31 FALSE -> no ButtonID
        if gv >= GV_AoEB:
            c.skip(4 + 4)                        # LanguageDLLHelp, LanguageDLLTechTree
        c.dbgstr()                               # Name
        if gv >= GV_C15:
            c.skip(1)                            # Repeatable
        if gv >= GV_C31:
            n = c.u("h")
            c.skip(n * 9)                        # ResearchLocation: i16,i16,u8,i32

    # -- tech tree --------------------------------------------------------
    def _techtree(self):
        c = self.c
        gv = self.gv
        age_count = c.u("B")
        bld_count = c.u("B")
        if gv >= GV_C32:
            unit_count = c.u("h")                # int16 at 8.9 (u8 before)
        else:
            unit_count = c.u("B")
        res_count = c.u("B")
        c.skip(4)                                # TotalUnitTechGroups
        slots = 10 if gv >= GV_AoKB else 5
        zones = 10 if gv >= GV_AoKB else 3
        self.doc["techtreeCounts"] = dict(ages=age_count, buildings=bld_count,
                                          units=unit_count, research=res_count,
                                          slots=slots, zones=zones)
        for _ in range(age_count):
            c.skip(4 + 1)                        # ID, Status
            n = c.u("B"); c.skip(n * 4)          # Buildings
            n = c.u("B"); c.skip(n * 4)          # Units
            n = c.u("B"); c.skip(n * 4)          # Techs
            c.skip(4 + slots * 4 + slots * 4)    # Common
            c.skip(1 + zones + zones)            # NumBuildingLevels, per-zone arrays
            c.skip(1 + 4)                        # MaxAgeLength, LineMode
        for _ in range(bld_count):
            c.skip(4 + 1)
            for _3 in range(3):
                n = c.u("B"); c.skip(n * 4)
            c.skip(4 + slots * 4 + slots * 4)    # Common
            c.skip(1 + TECHTREE_AGES + TECHTREE_AGES)
            c.skip(4 + 4)                        # LineMode, EnablingResearch
        for _ in range(unit_count):
            c.skip(4 + 1 + 4)                    # ID, Status, UpperBuilding
            c.skip(4 + slots * 4 + slots * 4)    # Common
            c.skip(4)                            # VerticalLine
            n = c.u("B"); c.skip(n * 4)          # Units
            c.skip(4 * 4)                        # LocationInAge, RequiredResearch, LineMode, EnablingResearch
        for _ in range(res_count):
            c.skip(4 + 1 + 4)
            for _3 in range(3):
                n = c.u("B"); c.skip(n * 4)
            c.skip(4 + slots * 4 + slots * 4)    # Common
            c.skip(4 * 3)                        # VerticalLine, LocationInAge, LineMode


# ---------------------------------------------------------------------------
def load_dat(path):
    """Read a .dat: raw-deflate (no zlib header) after an uncompressed prefix?
    No -- the entire file is one raw deflate stream."""
    raw = open(path, "rb").read()
    return decompress(raw), raw


def decompress(raw):
    d = zlib.decompressobj(-15)
    out = d.decompress(raw) + d.flush()
    if d.unused_data:
        raise DatError("%d trailing bytes after deflate stream" % len(d.unused_data))
    return out


def compress(data, level=6):
    co = zlib.compressobj(level, zlib.DEFLATED, -15)
    return co.compress(data) + co.flush()


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else \
        r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
    data, raw = load_dat(src)
    d = Dat(data)
    doc = d.parse()
    print("file        : %s" % src)
    print("compressed  : %d bytes" % len(raw))
    print("decompressed: %d bytes" % len(data))
    print("version     : %s (%s)" % (doc["FileVersion"], doc["GameVersion"]))
    print("leftover    : %d bytes" % doc["leftover"])
    print()
    print("counts:")
    for k in sorted(doc):
        if k.startswith("num") or k in ("terrainsUsed", "leftover", "parsedBytes"):
            print("   %-24s %s" % (k, doc[k]))
    print()
    print("section offsets:")
    for k, v in d.c.marks.items():
        print("   %-24s 0x%08x" % (k, v))
