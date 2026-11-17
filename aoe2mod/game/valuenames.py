# -*- coding: utf-8 -*-
"""Which id space a stored integer belongs to, so the editor can print a name.

WHY THIS EXISTS: the census in ui/server.py ships the values a column really
holds, and fieldlabels.value_name can only spell six task columns.  Measured
2026-11-16 on units 4/74/83/82/103: 2,038 columns had a picker and 1,786 of them
offered nothing but a bare number -- reported as 「很多这种下拉的选项全是id，很难
看懂是什么东西，没有解释」.  AGE3 answers the same question by printing
`87 - 靶场`; this table is what lets the page do that.

HONESTY RULE: every entry below is a whitelist and not a guess.  A wrong name
is worse than a number, because the player edits the value that the name says.
A tail that appears in no table here prints its number.  Nothing is inferred
from the field label (「图形」 in a label does not prove the column is a graphic
index) -- only tails whose meaning is checked against the data.
"""

import re

# Columns that store an index into the unit table.  Checked against the data:
# Creatable.TrainLocations.0.UnitID 87 is 靶场, 103 is 铁匠铺, 118 是城镇中心;
# Building.StackUnitID / Building.HeadUnit / Bird.DropSites all name real units
# (a 城堡 stacks units, a bird drops onto 食物 / 伐木场 ids).
_UNIT_TAILS = frozenset([
    "UnitID", "DeadUnitID", "BloodUnitID", "StackUnitID", "HeadUnit",
    "PileUnit", "TransformUnit", "ProjectileUnitID", "SecondaryProjectileUnit",
    "ChargeProjectileUnit", "DropSites",
])

# Columns that store an index into the graphics table.  StandingGraphic.0 is
# graphic 1751 for a 民兵, and the table really does hold 20,883 records with
# names like ArcheryRange EAST Age2 (Rubble).
_GRAPHIC_TAILS = frozenset([
    "Graphic", "StandingGraphic", "MovingGraphic", "WorkingGraphic",
    "ProceedingGraphic", "CarryingGraphic", "DyingGraphic", "AttackGraphic",
    "ConstructionGraphicID", "DestructionGraphicID",
    "DestructionRubbleGraphicID", "SnowGraphicID", "SpecialGraphic",
    "SpawningGraphic", "GarrisonGraphic", "HeroGlowGraphic",
    "IdleAttackGraphic", "ResearchingGraphic", "ResearchCompletedGraphic",
    "UpgradeGraphic", "UndeadGraphic",
])

# Sound indexes into the 930-record sound table (BLAC.wav, komodof1.wav).  The
# Wwise columns are NOT here on purpose: those store a 32-bit hash that indexes
# nothing a human can read, so they stay numbers.
_SOUND_TAILS = frozenset([
    "DyingSound", "AttackSound", "MoveSound", "SelectionSound", "TrainSound",
    "ConstructionSound", "TransformSound", "DamageSound",
])

# Terrain ids.  Checked against the table (200 records): 1 Water, Shallow,
# 2 Beach, 7 Farm1, 28 Water, Bridge, 35 Ice.  `-1` means "no terrain" and has
# no name, which is the same luck the other spaces have.
_TERRAIN_TAILS = frozenset([
    "TerrainID", "FoundationTerrainID", "PlacementTerrain",
    "PlacementSideTerrain",
])

# The class id space: 27 城墙, 39 城门, 52 塔, 6 步兵.  `Class` on a unit is its
# own class; Tasks.N.ClassID is the class a task may act on.
_CLASS_TAILS = frozenset(["Class", "ClassID"])

_TECH_TAILS = frozenset(["TechID"])

# Hotkey ids: 16131 is 「铁匠铺  S」, 16000 is 「没设热键」.  Resolved through
# `aoe2mod/game/hotkeys.py`, which reads the install's own hotkeys.json.  The
# 8.4 name for the same space is `HotKeyFromUnit` -- `mod/portgen.py` measured
# them as one numbering space when the field moved onto the train location.
#
# DELIBERATELY ABSENT: `LanguageDLLHotKeyText` (0 of its 96 shipped values are
# in hotkeys.json; it equals HotKeyID + 139000 on 207 of 400 sampled units and
# disagrees on the rest, so the offset is a habit, not a rule) and
# `ButtonHotkeyAction` (values -1 / 153 / 154 are button actions).
_HOTKEY_TAILS = frozenset(["HotKeyID", "HotKey", "HotKeyFromUnit"])

# Plain 0/1 columns.  Only these spell themselves: a value of 5 in
# CombatLevelFlag or 2 in HideInEditor is not 「yes」, and a name that says it is
# would teach the player to write 1 where the file expects 5.
_BOOL_TAILS = frozenset([
    "Enabled", "IsDefault", "CanBurn", "CanBeBuiltOn", "DisappearsWhenBuilt",
    "EnableTargeting", "AutoSearchTargets", "PickForConstruction",
    "Recyclable",
])

_ZH = {
    "unit": "单位编号",
    "graphic": "图形编号",
    "sound": "音效编号",
    "terrain": "地形编号",
    "class": "类别编号",
    "tech": "科技编号",
    "hotkey": "热键编号",
    "bool": "开关",
}

# Numbered families whose members are NOT all the same kind of number.  The
# corpse block is the reason this exists: DeadFish.0/4/8 are graphics, .1/5/9 are
# seconds, .2/6/10 are how much can be gathered and .3/7/11 are action ids.
# Naming all twelve as graphics would rename a duration as a picture.
_FAMILIES = (
    (re.compile(r"^(?:\w+\.)*DeadFish\.(\d+)$"),
     {0: "graphic", 4: "graphic", 8: "graphic"}),
    (re.compile(r"^(?:\w+\.)*StandingGraphic\.\d+$"), "graphic"),
    (re.compile(r"^(?:\w+\.)*AttackGraphic\d+$"), "graphic"),
    (re.compile(r"^(?:\w+\.)*Bird\.DropSites\.\d+$"), "unit"),
    # `PlacementTerrain.0` /`PlacementSideTerrain.1` end in a digit, so the tail
    # lookup below never sees a word; both are terrain ids (measured: 民兵 -1,
    # 建筑 1 Water Shallow / 2 Beach).
    (re.compile(r"^(?:\w+\.)*Placement(?:Side)?Terrain\.\d+$"), "terrain"),
)


def space(full_name):
    """Return the id space of a column, or None when it is just a number.

    Called with the FULL field name rather than its tail, because DeadFish.4
    and DeadFish.5 share a prefix and mean different things.
    """
    if not full_name:
        return None
    for pat, got in _FAMILIES:
        m = pat.match(full_name)
        if m is None:
            continue
        if isinstance(got, str):
            return got
        if m.groups():
            return got.get(int(m.group(1)))
        return None
    tail = full_name.rsplit(".", 1)[-1]
    if tail in _UNIT_TAILS:
        return "unit"
    if tail in _GRAPHIC_TAILS:
        return "graphic"
    if tail in _SOUND_TAILS:
        return "sound"
    if tail in _TERRAIN_TAILS:
        return "terrain"
    if tail in _CLASS_TAILS:
        return "class"
    if tail in _TECH_TAILS:
        return "tech"
    if tail in _HOTKEY_TAILS:
        return "hotkey"
    if tail in _BOOL_TAILS:
        return "bool"
    return None


def space_zh(sp):
    """What to call that space in a tooltip; unknown space gives an empty string."""
    return _ZH.get(sp, "")


def bool_name(v):
    """0 and 1 spell themselves; anything else stays a number (the file has 2 and 5)."""
    if v == 0:
        return "否"
    if v == 1:
        return "是"
    return None
