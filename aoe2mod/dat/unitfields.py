# -*- coding: utf-8 -*-
"""Every field of every unit, with its absolute byte offset in the .dat.

WHY THIS EXISTS
---------------
`aoe2mod/dat/parser.py` walks the whole 93 MB file to leftover 0, but keeps only
the handful of values the intent layer asks for and throws the rest away.
`aoe2mod/dat/newunit.py` then patches *specific* offsets it recomputes by hand.
That is enough for "set a villager's HP", and it is why the page could only offer
a dozen stats: everything else had no address, so nothing else could be edited.

AGE (AdvancedGenieEditor) does not have that problem -- it knows where every
field starts, so it can show all ~85 of them.  This module gives the same
addressability without a second parser: it replays the exact read order of
`parser.read_unit` while recording where every value came from, so the offsets
are produced by the same bytes the proven parse already walks.

THE PROOF IT IS FAITHFUL
------------------------
`parser.read_unit` is the only read order that has been shown to consume the
real .dat exactly (leftover 0 / final offset 93,273,004).  This module does not
restate the layout from the schema; it copies that function literally, line for
line, unrolling the `r.i16()` calls that `parser.py` discards into named ones.
When the two disagree, `scan()` fails on its leftover check instead of returning
plausible-looking wrong offsets -- which is the failure mode that matters here,
because a wrong offset writes into a neighbouring field and the game reads it as
a silent nerf rather than an error.

FIELD NAMES
-----------
Names follow genieutils `src/dat/Unit.cpp` (`HitPoints`, `LineOfSight`,
`Type50.DisplayedAttack`, ...): that is what AGE's labels key on and what
`AGE3-全量数据/schema/schema.json` uses.  Repeated fields get `.0`/`.1` suffixes
so a flat dict keeps one name per address.
"""

from __future__ import annotations

from . import parser as P

__all__ = ["scan", "by_civ", "KINDS"]

# The only scalar shapes a unit record contains.  `str` is handled separately
# because its width is in the two bytes in front of it.
KINDS = {"u8": 1, "i16": 2, "u16": 2, "i32": 4, "u32": 4, "f32": 4}


class Rec(P.Reader):  # type: ignore[misc]
    """A `parser.Reader` that remembers where every value it read came from.

    Every accessor keeps `parser.Reader`'s exact signature *plus* an optional
    name.  Called without a name -- which is what the other nine stages of
    `Parser.parse()` do -- it behaves as the base reader and records nothing.
    That is deliberate: nine of the ten stages are not this module's business,
    and a recorder that insisted on names would make `scan()` unusable as a
    drop-in.
    """

    __slots__ = ("fields",)

    def __init__(self, data, gv):
        P.Reader.__init__(self, data, gv)
        self.fields = []

    def _note(self, name, pos, kind, value):
        if name is not None:
            self.fields.append((name, pos, kind, value))

    # -- scalars, each with the name the caller gave it ---------------------
    def u8(self, name=None):                 # noqa: D102
        p = self.pos
        v = P.Reader.u8(self)
        self._note(name, p, "u8", v)
        return v

    def i16(self, name=None):                # noqa: D102
        p = self.pos
        v = P.Reader.i16(self)
        self._note(name, p, "i16", v)
        return v

    def i32(self, name=None):                # noqa: D102
        p = self.pos
        v = P.Reader.i32(self)
        self._note(name, p, "i32", v)
        return v

    def u32(self, name=None):                # noqa: D102
        p = self.pos
        v = P.Reader.u32(self)
        self._note(name, p, "u32", v)
        return v

    def f32(self, name=None):                # noqa: D102
        p = self.pos
        v = P.Reader.f32(self)
        self._note(name, p, "f32", v)
        return v

    def i16_n(self, name, n):
        """`i16_array` with one name per element; n==1 gets no suffix."""
        p = self.pos
        vals = P.Reader.i16_array(self, n)
        if n == 1:
            self.fields.append((name, p, "i16", vals[0]))
        else:
            for i, v in enumerate(vals):
                self.fields.append(("%s.%d" % (name, i), p + 2 * i, "i16", v))
        return vals

    def s(self, name):
        """`debug_string`: uint16 marker, uint16 stored length, then bytes.

        Three addresses, not one, because they are three different edits: the
        length is what a writer must bump if a name grows, and the marker
        (`0x0A60`) is what `parser.debug_string` validates before trusting the
        length at all.  Conflating marker and length advances a writer's cursor
        by 2,656 bytes and corrupts everything after -- that is recorded in
        `parser.Reader.debug_string`'s own docstring as a bug that already
        happened once.
        """
        p = self.pos
        marker, text = self.debug_string()
        stored = self.last_string_len
        self.fields.append((name + ".marker", p, "u16", marker))
        self.fields.append((name + ".len", p + 2, "u16", stored))
        self.fields.append((name, p + 4, "str", text))
        return text


# Replays of the sub-structures.  Each one mirrors its `parser.py` twin.

def _resource_storage(r, i):
    r.i16("ResourceStorages.%d.Type" % i)
    r.f32("ResourceStorages.%d.Amount" % i)
    r.u8("ResourceStorages.%d.Mode" % i)


def _damage_graphic(r, i):
    r.i16("DamageGraphics.%d.Percent" % i)
    r.i16("DamageGraphics.%d.Graphic" % i)
    r.u8("DamageGraphics.%d.ApplyMode" % i)


def _attack_or_armor(r, prefix, i):
    r.i16("%s.%d.Class" % (prefix, i))
    r.i16("%s.%d.Amount" % (prefix, i))


def _type50(r):
    r.i16("Type50.BaseArmor")
    n = r.i16("Type50.AttacksCount")
    for i in range(n):
        _attack_or_armor(r, "Type50.Attacks", i)
    n = r.i16("Type50.ArmoursCount")
    for i in range(n):
        _attack_or_armor(r, "Type50.Armours", i)
    r.i16("Type50.DefenseTerrainBonus")
    r.f32("Type50.BonusDamageResistance")
    r.f32("Type50.MaxRange")
    r.f32("Type50.BlastWidth")
    r.f32("Type50.ReloadTime")
    r.i16("Type50.ProjectileUnitID")
    r.i16("Type50.AccuracyPercent")
    r.u8("Type50.BreakOffCombat")
    r.i16("Type50.FrameDelay")
    r.f32("Type50.GraphicDisplacement.0")
    r.f32("Type50.GraphicDisplacement.1")
    r.f32("Type50.GraphicDisplacement.2")
    r.u8("Type50.BlastAttackLevel")
    r.f32("Type50.MinRange")
    r.f32("Type50.AccuracyDispersion")
    r.i16("Type50.AttackGraphic")
    r.i16("Type50.DisplayedMeleeArmour")
    r.i16("Type50.DisplayedAttack")
    r.f32("Type50.DisplayedRange")
    r.f32("Type50.DisplayedReloadTime")
    if P.GV_C20 <= r.gv <= P.GV_LatestDE2:
        r.f32("Type50.BlastDamage")
    if P.GV_C22 <= r.gv <= P.GV_LatestDE2:
        r.f32("Type50.DamageReflection")
        r.f32("Type50.FriendlyFireDamage")
    if P.GV_C27 <= r.gv <= P.GV_LatestDE2:
        r.i16("Type50.InterruptFrame")
        r.f32("Type50.GarrisonFirepower")
        r.i16("Type50.AttackGraphic2")


def _projectile(r):
    r.u8("Projectile.0")
    r.u8("Projectile.1")
    r.u8("Projectile.2")
    r.u8("Projectile.3")
    r.u8("Projectile.4")
    r.f32("Projectile.ProjectileArc")


def _train_location(r, i):
    r.i16("Creatable.TrainLocations.%d.TrainTime" % i)
    r.i16("Creatable.TrainLocations.%d.UnitID" % i)
    r.u8("Creatable.TrainLocations.%d.ButtonID" % i)
    if P.GV_C30 <= r.gv <= P.GV_LatestDE2:
        r.i32("Creatable.TrainLocations.%d.HotKeyID" % i)


def _resource_cost(r, i):
    r.i16("Creatable.ResourceCosts.%d.Type" % i)
    r.i16("Creatable.ResourceCosts.%d.Amount" % i)
    r.i16("Creatable.ResourceCosts.%d.Flag" % i)


def _creatable(r):
    for i in range(3):
        _resource_cost(r, i)
    if P.GV_C29 <= r.gv <= P.GV_LatestDE2:
        n = r.i16("Creatable.TrainLocationsCount")
        for i in range(n):
            _train_location(r, i)
    else:
        _train_location(r, 0)
    r.f32("Creatable.RearAttackModifier")
    r.f32("Creatable.FlankAttackModifier")
    r.u8("Creatable.CreatableType")
    r.u8("Creatable.HeroMode")
    r.i32("Creatable.GarrisonGraphic")
    if P.GV_C13 <= r.gv <= P.GV_LatestDE2:
        r.i16("Creatable.SpawningGraphic")
        r.i16("Creatable.UpgradeGraphic")
        if r.gv >= P.GV_C16:
            if r.gv >= P.GV_C17:
                r.i16("Creatable.HeroGlowGraphic")
            if r.gv >= P.GV_C26:
                r.i16("Creatable.IdleAttackGraphic")
            r.f32("Creatable.MaxCharge")
            r.f32("Creatable.RechargeRate")
            r.i16("Creatable.ChargeEvent")
            r.i16("Creatable.ChargeType")
            if r.gv >= P.GV_C23:
                r.i16("Creatable.ChargeTarget")
            if r.gv >= P.GV_C25:
                r.i32("Creatable.ChargeProjectileUnit")
                r.u8("Creatable.AttackPriority")
                r.f32("Creatable.InvulnerabilityLevel")
            if r.gv >= P.GV_C24:
                r.i16("Creatable.ButtonIconID")
                r.i32("Creatable.ButtonShortTooltipID")
                r.i32("Creatable.ButtonExtendedTooltipID")
                r.i16("Creatable.ButtonHotkeyAction")
            if r.gv >= P.GV_C19:
                r.f32("Creatable.MinConversionTimeMod")
                r.f32("Creatable.MaxConversionTimeMod")
                r.f32("Creatable.ConversionChanceMod")
    r.f32("Creatable.TotalProjectiles")
    r.u8("Creatable.MaxTotalProjectiles")
    r.f32("Creatable.ProjectileSpawningArea.0")
    r.f32("Creatable.ProjectileSpawningArea.1")
    r.f32("Creatable.ProjectileSpawningArea.2")
    r.i32("Creatable.SecondaryProjectileUnit")
    r.i32("Creatable.SpecialGraphic")
    r.u8("Creatable.SpecialAbility")
    r.i16("Creatable.DisplayedPierceArmour")


def _building(r):
    r.i16("Building.ConstructionGraphicID")
    r.i16("Building.SnowGraphicID")
    r.i16("Building.DestructionGraphicID")
    r.i16("Building.DestructionRubbleGraphicID")
    r.i16("Building.ResearchingGraphic")
    r.i16("Building.ResearchCompletedGraphic")
    r.u8("Building.AdjacentMode")
    r.i16("Building.GraphicsAngle")
    r.u8("Building.DisappearsWhenBuilt")
    r.i16("Building.StackUnitID")
    r.i16("Building.FoundationTerrainID")
    r.i16("Building.OldOverlayID")
    r.i16("Building.TechID")
    r.u8("Building.CanBurn")
    for i in range(P.BUILDING_ANNEXES_SIZE):
        r.i16("Building.Annexes.%d.UnitID" % i)
        r.f32("Building.Annexes.%d.Misplacement.0" % i)
        r.f32("Building.Annexes.%d.Misplacement.1" % i)
    r.i16("Building.HeadUnit")
    r.i16("Building.TransformUnit")
    r.i16("Building.TransformSound")
    r.i16("Building.ConstructionSound")
    r.u32("Building.WwiseTransformSoundID")
    r.u32("Building.WwiseConstructionSoundID")
    r.u8("Building.GarrisonType")
    r.f32("Building.GarrisonHealRate")
    r.f32("Building.GarrisonRepairRate")
    r.i16("Building.PileUnit")
    # LootingTable: genieutils `Building.cpp:105` serializes it as
    # `serialize<uint8_t>(LootingTable, LOOTABLE_RES_COUNT)` -- six independent
    # u8 switches, one per resource, NOT a packed struct.  AGE exposes them as
    # six separate number controls (`AGE_Frame/Units.cpp:4928-4935`: Stone /
    # Wood / Ore / Gold / Food / Goods Loot Switch), so one opaque "raw" row
    # left the last six bytes of every building record both invisible and
    # uneditable.  Measured on the shipped .dat: 30,809 building records carry
    # only three distinct tables -- [0,0,0,0,0,0] x 28,730, [1,1,0,1,1,0] x
    # 1,890, [0,0,0,1,0,0] x 189 -- which is exactly what six on/off bytes look
    # like, and is why they read as u8 rather than as a 6-byte blob.
    for i in range(P.LOOTABLE_RES_COUNT):
        r.u8("Building.LootingTable.%d" % i)


def _dead_fish(r):
    r.i16("DeadFish.0")
    r.i16("DeadFish.1")
    r.f32("DeadFish.2")
    r.u8("DeadFish.3")
    r.i16("DeadFish.4")
    r.u8("DeadFish.5")
    r.f32("DeadFish.6")
    r.u8("DeadFish.7")
    r.f32("DeadFish.TurnRadius")
    r.f32("DeadFish.8")
    r.f32("DeadFish.9")
    r.f32("DeadFish.10")
    r.f32("DeadFish.11")
    r.f32("DeadFish.MinCollisionSizeMultiplier")


def _bird(r):
    """`parser.read_bird` -> returns TaskSwapGroup.

    TaskSwapGroup is not decoration: the engine swaps the live object's record
    pointer to another unit with the same group when a villager is retasked
    ("Villager" -> "Builder"), so an edit that only touches the record a name
    resolved to stops applying the instant the player assigns a job.
    """
    r.i16("Bird.0")
    r.f32("Bird.1")
    r.f32("Bird.2")
    n = r.i16("Bird.DropSitesCount")
    r.i16_n("Bird.DropSites", n)
    tsg = r.u8("Bird.TaskSwapGroup")
    r.i16("Bird.AttackSound")
    r.i16("Bird.MoveSound")
    r.u32("Bird.WwiseAttackSoundID")
    r.u32("Bird.WwiseMoveSoundID")
    r.u8("Bird.RunPattern")
    tn = r.i16("Bird.TaskCount")
    for i in range(tn):
        p = "Bird.Tasks.%d." % i
        r.i16(p + "TaskType")
        r.i16(p + "ID")
        r.u8(p + "IsDefault")
        # `read_task` reads `r.i16()` four times here (ActionType .. TerrainID)
        # and four times again for ResourceIn .. UnusedResource.  Writing five
        # in the first group shifts the whole task by 2 bytes and every later
        # record with it.  Names come from genieutils `src/dat/UnitCommand.cpp`.
        r.i16(p + "ActionType")
        r.i16(p + "ClassID")
        r.i16(p + "UnitID")
        r.i16(p + "TerrainID")
        r.i16(p + "ResourceIn")
        r.i16(p + "ResourceMultiplier")
        r.i16(p + "ResourceOut")
        r.i16(p + "UnusedResource")
        r.f32(p + "WorkValue1")
        r.f32(p + "WorkValue2")
        r.f32(p + "WorkRange")
        r.u8(p + "AutoSearchTargets")
        r.f32(p + "SearchWaitTime")
        r.u8(p + "EnableTargeting")
        r.u8(p + "CombatLevelFlag")
        r.i16(p + "GatherType")
        r.i16(p + "WorkFlag2")
        r.u8(p + "TargetDiplomacy")
        r.u8(p + "CarryCheck")
        r.u8(p + "PickForConstruction")
        r.i16(p + "MovingGraphic")
        r.i16(p + "ProceedingGraphic")
        r.i16(p + "WorkingGraphic")
        r.i16(p + "CarryingGraphic")
        r.i16(p + "ResourceGatheringSoundID")
        r.i16(p + "DepositSoundID")
        if P.GV_C4 <= r.gv <= P.GV_LatestDE2:
            r.u32(p + "WwiseGatherSoundID")
            r.u32(p + "WwiseDepositSoundID")
        if r.gv >= P.GV_C28:
            r.i16(p + "Enabled")
    return tsg


def read_unit_fields(r):
    """One unit record, named and addressed.  Returns (start, end, type)."""
    start = r.pos
    t = r.u8("Type")
    r.i16("ID")
    r.i32("LanguageDLLName")
    r.i32("LanguageDLLCreation")
    r.i16("Class")
    r.i16_n("StandingGraphic", 2)
    r.i16("DyingGraphic")
    r.i16("UndeadGraphic")
    r.u8("UndeadMode")
    r.i16("HitPoints")
    r.f32("LineOfSight")
    r.u8("GarrisonCapacity")
    r.f32("CollisionSize.0")
    r.f32("CollisionSize.1")
    r.f32("CollisionSize.2")
    r.i16("TrainSound")
    r.i16("DamageSound")
    r.i16("DeadUnitID")
    r.i16("BloodUnitID")
    r.u8("SortNumber")
    r.u8("CanBeBuiltOn")
    r.i16("IconID")
    r.u8("HideInEditor")
    r.i16("OldPortraitPict")
    r.u8("Enabled")
    r.u8("Disabled")
    r.i16_n("PlacementSideTerrain", 2)
    r.i16_n("PlacementTerrain", 2)
    r.f32("ClearanceSize.0")
    r.f32("ClearanceSize.1")
    r.u8("HillMode")
    r.u8("FogVisibility")
    r.i16("TerrainRestriction")
    r.u8("FlyMode")
    r.i16("ResourceCapacity")
    r.f32("ResourceDecay")
    r.u8("BlastDefenseLevel")
    r.u8("CombatLevel")
    r.u8("InteractionMode")
    r.u8("MinimapMode")
    r.u8("InterfaceKind")
    r.f32("MultipleAttributeMode")
    r.u8("MinimapColor")
    r.i32("LanguageDLLHelp")
    r.i32("LanguageDLLHotKeyText")
    # Unit.cpp:128 -- the pre-C30 read path carries an extra hotkey int32 that
    # the engine copies into Creatable.HotKeyFromUnit instead of a TrainLocation.
    if r.gv < P.GV_C30:
        r.i32("Creatable.HotKeyFromUnit")
    r.u8("Recyclable")
    r.u8("EnableAutoGather")
    r.u8("CreateDoppelgangerOnDeath")
    r.u8("ResourceGatherGroup")
    r.u8("OcclusionMode")
    r.u8("ObstructionType")
    r.u8("ObstructionClass")
    r.u8("Trait")
    r.u8("Civilization")
    r.i16("Nothing")
    r.u8("SelectionEffect")
    r.u8("EditorSelectionColour")
    r.f32("OutlineSize.0")
    r.f32("OutlineSize.1")
    r.f32("OutlineSize.2")
    r.i32("ScenarioTrigger1")
    r.i32("ScenarioTrigger2")
    for i in range(3):
        _resource_storage(r, i)
    dgc = r.u8("DamageGraphicsCount")
    for i in range(dgc):
        _damage_graphic(r, i)
    r.i16("SelectionSound")
    r.i16("DyingSound")
    r.u32("WwiseTrainSoundID")
    r.u32("WwiseDamageSoundID")
    r.u32("WwiseSelectionSoundID")
    r.u32("WwiseDyingSoundID")
    r.u8("OldAttackReaction")
    r.u8("ConvertTerrain")
    r.s("Name")
    r.i16("CopyID")
    r.i16("BaseID")

    # `parser.read_unit` has TWO early returns here, and both must be copied or
    # every record after the first tree / first type<20 object shifts:
    #   * type 90 (forest) stops BEFORE Speed -- it has no Speed field at all.
    #   * type < 20 (eyecandy, 10) has no Speed either and stops there.
    if t == P.UNIT_TYPE_AOE_TREES:
        return start, r.pos, t
    if t < P.UNIT_TYPE_FLAG:
        return start, r.pos, t
    r.f32("Speed")
    if t >= P.UNIT_TYPE_DEAD_FISH:
        _dead_fish(r)
    if t >= P.UNIT_TYPE_BIRD:
        _bird(r)
    if t >= P.UNIT_TYPE_COMBATANT:
        _type50(r)
    if t == P.UNIT_TYPE_PROJECTILE:
        _projectile(r)
    if t >= P.UNIT_TYPE_CREATABLE:
        _creatable(r)
    if t == P.UNIT_TYPE_BUILDING:
        _building(r)
    return start, r.pos, t


def fields_at(raw, gv, start):
    """Every named field of the ONE record that begins at `start`.

    WHY THIS EXISTS: `scan()` can return a dict-of-dicts per record, and the UI
    briefly kept that for all 136,861 units as its index -- 434 field dicts x
    136,861 records, measured 12.3 GB resident on 2026-10-30.  The panel only
    ever shows one unit at a time, and every byte it needs is still in the file,
    so the index now keeps `start` and the fields are decoded on demand.  One
    record is ~1 KB of reads: microseconds.
    """
    r = Rec(raw, P.GV_C32 if gv is None else gv)
    r.pos = start
    read_unit_fields(r)
    out = {}
    for name, off, kind, value in r.fields:
        out[name] = {"offset": off, "kind": kind, "value": value}
    return out


def scan(raw, gv=None, light=False, on_progress=None):
    """Parse `raw` once; return (units, stats, leftover_bytes).

    Each unit is::

        {"civ_index", "civ", "start", "end", "type",
         "fields": {name: {"offset", "kind", "value"}}}

    `parser.read_unit` is swapped for a recording twin and `parser.read_civ` for
    a thin wrapper, so `Parser.parse()`'s own ten stages drive the walk.  Unit
    boundaries therefore come from the file's own counts and pointer arrays, not
    from arithmetic in this module.

    The civ name is *peeked* through a throwaway reader positioned at the civ's
    start rather than by re-implementing `read_civ`: a second implementation of
    that function would be a second place for the layout to drift, which is the
    exact failure this module exists to avoid.

    `leftover` is the caller's proof of faithfulness -- it must be 0.
    """
    units = []
    state = {"civ_index": -1, "civ": ""}

    # Progress reporting.  The caller asked for it because a cold scan is
    # 10.45 s measured 2026-11-02 and the screen had nothing to draw for it.
    # `reader.pos` is the honest number: stage 8 (Civs) walks the file from
    # 4.2 % to 99.8 %, so bytes walked IS percent walked.  Throttled to ~200
    # callbacks -- one per 0.5 % -- because 136,861 lock acquisitions cost more
    # than the information is worth, and a bar cannot draw faster than that.
    step = max(1, len(raw) // 200)
    marks = {"at": -step}

    def report(reader):
        if on_progress is None:
            return
        if reader.pos - marks["at"] < step:
            return
        marks["at"] = reader.pos
        on_progress(reader.pos)

    def rec_unit(reader, collect=None):
        report(reader)
        start, end, t = read_unit_fields(reader)
        if light:
            # Name and ID only, then throw the field list away.  See
            # `fields_at()` for why the record is not kept decoded.
            uid = -1
            for name, _off, _kind, value in reader.fields:
                if name == "ID":
                    uid = value
                    break
            del reader.fields[:]
            units.append({"start": start, "end": end, "type": t, "id": uid,
                          "civ_index": state["civ_index"], "civ": state["civ"]})
            if collect is not None:
                collect({"name": "", "hit_points": 0, "type": t, "id": uid})
            return {"type": t, "name": None}
        flat = {}
        for name, off, kind, value in reader.fields:
            flat[name] = {"offset": off, "kind": kind, "value": value}
        del reader.fields[:]
        units.append({"start": start, "end": end, "type": t, "fields": flat,
                      "civ_index": state["civ_index"], "civ": state["civ"]})
        if collect is not None:
            # `Parser._collect_unit` reads `name`/`hit_points`/`type`/`id` off
            # the dict the original `read_unit` would have returned.  Feed it
            # those four from the recorded fields instead of throwing the model
            # shape away, so the debug summary of the ten-stage parse still
            # prints real unit names.
            def _v(key, default=None):
                got = flat.get(key)
                return default if got is None else got["value"]
            collect({"name": _v("Name", ""), "hit_points": _v("HitPoints", 0),
                     "type": t, "id": _v("ID", -1)})
        return {"type": t, "name": None}

    def rec_civ(reader, collect=None):
        peek = P.Reader(reader.data, reader.gv)
        peek.pos = reader.pos
        peek.u8()                              # player_type
        state["civ"] = peek.debug_string()[1]
        state["civ_index"] += 1
        # `read_civ` stores the dicts `read_unit` returns, but nothing
        # downstream of `scan()` reads them -- the recorded `units` list is the
        # product.  Letting the original run keeps civ counts, pointer skipping
        # and stage offsets byte-identical to the proven parse.
        got = orig_civ(reader, collect)
        got["units"] = []
        return got

    # The whole patch + parse + restore has to be atomic.  `Parser.parse()` has
    # its own lock, but it releases when it RETURNS -- and the `finally` that
    # undoes the patch runs after that.  Measured 2026-10-29: a second thread
    # could therefore start parsing inside that window, call the recording
    # `read_unit` with a plain `Reader`, and die with
    # `Reader.u8() takes 1 positional argument but 2 were given`; on the write
    # path this hit every single build.  Hold the same RLock across all three.
    with P._PARSE_LOCK:
      # Read the "originals" INSIDE the lock.  Captured outside it, a second
      # thread could snapshot the FIRST thread's recording twin as the original
      # and then "restore" `read_unit` to `rec_unit` for the rest of the process
      # -- measured 2026-10-29, `/api/session-info` showed `rec_unit` before any
      # scan had finished and every later `parse()` died with
      # `Reader.u8() takes 1 positional argument but 2 were given`.
      orig_unit = P.read_unit
      orig_civ = P.read_civ
      P.read_unit = rec_unit
      P.read_civ = rec_civ
      try:
        p = P.Parser(raw)
        # `Parser.parse()` binds `r = self.r` once and every read_* receives
        # that object, so swapping it here is enough for the recorder to see
        # all ten stages.  The subclass keeps `Reader`'s arithmetic untouched;
        # it only adds the named accessors `read_unit_fields` calls.
        p.r = Rec(raw, P.GV_C32 if gv is None else gv)
        stats = p.parse()
      finally:
        P.read_unit = orig_unit
        P.read_civ = orig_civ

    leftover = len(raw) - p.r.pos
    # One last call at the true end, so the bar lands on 100 % from measured
    # bytes instead of from the caller's guess that the scan finished.
    if on_progress is not None:
        on_progress(len(raw) - leftover)
    return units, stats, leftover


def by_civ(units, civ_index):
    """The subset of `units` that belongs to one civilisation."""
    return [u for u in units if u["civ_index"] == civ_index]
