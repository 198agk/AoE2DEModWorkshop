//! Stage 8: civilizations and their unit records, plus stage 9-10.
//!
//! This is where the file actually lives: 63 civs, 2,693 unit records each,
//! 89 MB of Civs section out of a 93 MB file.  Almost every one of the guards
//! in here exists because a real dataset needed it, so the branches are
//! transcribed from `aoe2mod/dat/parser.py` rather than reconstructed.

use crate::Reader;
use std::io;

pub const AGES: usize = 5;
pub const BUILDING_ANNEXES_SIZE: usize = 4;
pub const LOOTABLE_RES_COUNT: usize = 6;

// Unit type thresholds.  A record's `type` byte decides which sub-blocks follow
// it, so these are control flow, not labels.
pub const UNIT_TYPE_FLAG: u8 = 20;
pub const UNIT_TYPE_DEAD_FISH: u8 = 30;
pub const UNIT_TYPE_BIRD: u8 = 40;
pub const UNIT_TYPE_COMBATANT: u8 = 50;
pub const UNIT_TYPE_PROJECTILE: u8 = 60;
pub const UNIT_TYPE_CREATABLE: u8 = 70;
pub const UNIT_TYPE_BUILDING: u8 = 80;
pub const UNIT_TYPE_AOE_TREES: u8 = 90;

// GameVersion ordinals used by the guards in this file.
const GV_MATT: u32 = 4;
const GV_AoEB: u32 = 5;
const GV_AoKE3: u32 = 16;
const GV_AoKB: u32 = 18;
const GV_C13: u32 = 35;
const GV_C15: u32 = 37;
const GV_C16: u32 = 38;
const GV_C17: u32 = 39;
const GV_C18: u32 = 40;
const GV_C19: u32 = 41;
const GV_C20: u32 = 42;
const GV_C22: u32 = 44;
const GV_C23: u32 = 45;
const GV_C24: u32 = 46;
const GV_C25: u32 = 47;
const GV_C26: u32 = 48;
const GV_C27: u32 = 49;
const GV_C28: u32 = 50;
const GV_C29: u32 = 51;
const GV_C30: u32 = 52;
const GV_C31: u32 = 53;
const GV_C32: u32 = 54;
const GV_CCV2: u32 = 58;
const GV_LATEST_DE2: u32 = 54;

fn in_de2(gv: u32, lo: u32) -> bool {
    lo <= gv && gv <= GV_LATEST_DE2
}

/// The fields of a unit record that this crate models.
///
/// Everything else is skipped: the parser's job for now is to reach the right
/// offsets and expose what the family layer and the writers need (`id`, `type`,
/// `hit_points`, `name`, `task_swap_group`).  A field that is only skipped
/// cannot be wrong.
#[derive(Debug, Clone, Default)]
pub struct Unit {
    pub unit_type: u8,
    pub id: i16,
    pub class: i16,
    pub hit_points: i16,
    pub name: String,
    /// `Bird.TaskSwapGroup`.  The engine swaps an object's record pointer to
    /// another unit in the same group when a villager is retasked, so this is
    /// what makes a villager reskin keep applying after the player assigns a
    /// job.  Zero for every record with no bird block.
    pub task_swap_group: u8,
}

fn read_resource_storage(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(2 + 4 + 1)
}

fn read_damage_graphic(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(2 + 2 + 1)
}

fn read_dead_fish(r: &mut Reader<'_>) -> io::Result<()> {
    // 41 bytes in total, and the `u8` between the last f32 field and the float
    // block is easy to drop: the Python original reads
    //   i16, i16, f32, u8, i16, u8, f32, u8, then f32 x5, then f32
    // and omitting that one byte shifts every following field in the record.
    // Measured 2026-10-27: this single byte made unit 0 read 630 bytes instead
    // of 484, and because the next sub-block is count-driven it then consumed
    // 242 bytes instead of 86 -- one missing byte, three wrong numbers.
    r.skip(2 + 2 + 4 + 1 + 2 + 1)?; // i16,i16,f32,u8,i16,u8
    r.skip(4)?; // f32
    r.skip(1)?; // u8
    r.skip(4 * 5)?; // TurnRadius .. Stationary
    r.skip(4) // MinCollisionSizeMultiplier
}

fn read_bird(r: &mut Reader<'_>, gv: u32) -> io::Result<u8> {
    r.skip(2 + 4 + 4)?;
    let n = r.i16()?;
    r.skip(2 * n.max(0) as usize)?; // DropSites
    let tsg = r.u8()?; // TaskSwapGroup
    r.skip(2 + 2)?; // AttackSound, MoveSound
    r.skip(4 + 4)?; // Wwise attack/move
    r.skip(1)?; // RunPattern
    let tn = r.i16()?;
    for _ in 0..tn.max(0) {
        crate::stages37::read_task(r, gv)?;
    }
    Ok(tsg)
}

fn read_attack_or_armor(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(4)
}

fn read_type50(r: &mut Reader<'_>, gv: u32) -> io::Result<()> {
    r.skip(2)?; // BaseArmor
    let n = r.i16()?;
    for _ in 0..n.max(0) {
        read_attack_or_armor(r)?;
    }
    let n = r.i16()?;
    for _ in 0..n.max(0) {
        read_attack_or_armor(r)?;
    }
    r.skip(2)?; // DefenseTerrainBonus
    r.skip(4)?; // BonusDamageResistance
    r.skip(4 * 3)?; // MaxRange, BlastWidth, ReloadTime
    r.skip(2 + 2)?; // ProjectileUnitID, AccuracyPercent
    r.skip(1)?; // BreakOffCombat
    r.skip(2)?; // FrameDelay
    r.skip(4 * 3)?; // GraphicDisplacement[3]
    r.skip(1)?; // BlastAttackLevel
    r.skip(4)?; // MinRange
    r.skip(4)?; // AccuracyDispersion
    r.skip(2)?; // AttackGraphic
    r.skip(2 + 2)?; // DisplayedMeleeArmour, DisplayedAttack
    r.skip(4 + 4)?; // DisplayedRange, DisplayedReloadTime
    if in_de2(gv, GV_C20) {
        r.skip(4)?; // BlastDamage
    }
    if in_de2(gv, GV_C22) {
        r.skip(4 + 4)?; // DamageReflection, FriendlyFireDamage
    }
    if in_de2(gv, GV_C27) {
        r.skip(2 + 4 + 2)?; // InterruptFrame, GarrisonFirepower, AttackGraphic2
    }
    Ok(())
}

fn read_projectile(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(5)?; // 5 x u8
    r.skip(4) // ProjectileArc
}

fn read_train_location(r: &mut Reader<'_>, gv: u32) -> io::Result<()> {
    r.skip(2 + 2 + 1)?; // TrainTime, UnitID, ButtonID
    if in_de2(gv, GV_C30) {
        r.skip(4)?; // HotKeyID
    }
    Ok(())
}

fn read_resource_cost(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(2 + 2 + 2)
}

fn read_creatable(r: &mut Reader<'_>, gv: u32) -> io::Result<()> {
    for _ in 0..3 {
        read_resource_cost(r)?;
    }
    // Creatable.cpp:58 -- DE stores an explicit count; before C29 exactly one
    // entry is written with no count in front of it.
    if in_de2(gv, GV_C29) {
        let n = r.i16()?;
        for _ in 0..n.max(0) {
            read_train_location(r, gv)?;
        }
    } else {
        read_train_location(r, gv)?;
    }
    r.skip(4 + 4)?; // Rear/FlankAttackModifier
    r.skip(1 + 1)?; // CreatableType, HeroMode
    r.skip(4)?; // GarrisonGraphic
    if in_de2(gv, GV_C13) {
        r.skip(2 + 2)?; // SpawningGraphic, UpgradeGraphic
        if gv >= GV_C16 {
            if gv >= GV_C17 {
                r.skip(2)?; // HeroGlowGraphic
            }
            if gv >= GV_C26 {
                r.skip(2)?; // IdleAttackGraphic
            }
            r.skip(4 + 4)?; // MaxCharge, RechargeRate
            r.skip(2 + 2)?; // ChargeEvent, ChargeType
            if gv >= GV_C23 {
                r.skip(2)?; // ChargeTarget
            }
            if gv >= GV_C25 {
                r.skip(4 + 1 + 4)?; // ChargeProjectileUnit, AttackPriority, Invuln
            }
            if gv >= GV_C24 {
                r.skip(2 + 4 + 4 + 2)?; // ButtonIconID, tooltips, hotkey action
            }
            if gv >= GV_C19 {
                r.skip(4 * 3)?; // Min/MaxConversionTimeMod, ConversionChanceMod
            }
        }
    }
    r.skip(4)?; // TotalProjectiles
    r.skip(1)?; // MaxTotalProjectiles
    r.skip(4 * 3)?; // ProjectileSpawningArea[3]
    r.skip(4)?; // SecondaryProjectileUnit
    r.skip(4)?; // SpecialGraphic
    r.skip(1)?; // SpecialAbility
    r.skip(2) // DisplayedPierceArmour
}

fn read_building(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(2)?; // ConstructionGraphicID
    r.skip(2)?; // SnowGraphicID
    r.skip(2)?; // DestructionGraphicID
    r.skip(2)?; // DestructionRubbleGraphicID
    r.skip(2 + 2)?; // ResearchingGraphic, ResearchCompletedGraphic
    r.skip(1)?; // AdjacentMode
    r.skip(2)?; // GraphicsAngle
    r.skip(1)?; // DisappearsWhenBuilt
    r.skip(2 * 4)?; // StackUnitID, FoundationTerrainID, OldOverlayID, TechID
    r.skip(1)?; // CanBurn
    for _ in 0..BUILDING_ANNEXES_SIZE {
        r.skip(2 + 4 + 4)?; // Annex: UnitID + pair<float>
    }
    r.skip(2)?; // HeadUnit
    r.skip(2 + 2)?; // TransformUnit, TransformSound
    r.skip(2)?; // ConstructionSound
    r.skip(4 + 4)?; // WwiseTransform/ConstructionSoundID
    r.skip(1)?; // GarrisonType
    r.skip(4 + 4)?; // GarrisonHealRate, GarrisonRepairRate
    r.skip(2)?; // PileUnit
    r.skip(LOOTABLE_RES_COUNT) // LootingTable[6]
}

pub fn read_unit(r: &mut Reader<'_>, gv: u32) -> io::Result<Unit> {
    let mut u = Unit::default();
    u.unit_type = r.u8()?;
    u.id = r.i16()?;
    r.skip(4)?; // LanguageDLLName
    r.skip(4)?; // LanguageDLLCreation
    u.class = r.i16()?;
    r.skip(2 * 2)?; // StandingGraphic
    r.skip(2)?; // DyingGraphic
    r.skip(2)?; // UndeadGraphic
    r.skip(1)?; // UndeadMode
    u.hit_points = r.i16()?;
    trace(r, "after hp");
    r.skip(4)?; // LineOfSight
    r.skip(1)?; // GarrisonCapacity
    r.skip(4 * 3)?; // CollisionSize xyz
    r.skip(2)?; // TrainSound
    r.skip(2)?; // DamageSound
    r.skip(2)?; // DeadUnitID
    r.skip(2)?; // BloodUnitID
    r.skip(1 + 1)?; // SortNumber, CanBeBuiltOn
    r.skip(2)?; // IconID
    r.skip(1)?; // HideInEditor
    r.skip(2)?; // OldPortraitPict
    r.skip(1)?; // Enabled
    r.skip(1)?; // Disabled
    r.skip(2 * 2)?; // PlacementSideTerrain
    r.skip(2 * 2)?; // PlacementTerrain
    r.skip(4 + 4)?; // ClearanceSize
    r.skip(1)?; // HillMode
    r.skip(1)?; // FogVisibility
    r.skip(2)?; // TerrainRestriction
    r.skip(1)?; // FlyMode
    r.skip(2)?; // ResourceCapacity
    r.skip(4)?; // ResourceDecay
    r.skip(5)?; // BlastDefenseLevel..InterfaceKind
    r.skip(4)?; // MultipleAttributeMode
    r.skip(1)?; // MinimapColor
    r.skip(4 + 4)?; // LanguageDLLHelp, LanguageDLLHotKeyText
    // Unit.cpp:128 -- the pre-C30 read path carries an extra hotkey int32 that
    // the engine copies into Creatable.HotKeyFromUnit instead of a TrainLocation.
    if gv < GV_C30 {
        r.skip(4)?;
    }
    r.skip(4)?; // Recyclable, EnableAutoGather, CreateDoppelganger, GatherGroup
    r.skip(3)?; // OcclusionMode, ObstructionType, ObstructionClass
    r.skip(1 + 1 + 2)?; // Trait, Civilization, Nothing
    r.skip(1 + 1)?; // SelectionEffect, EditorSelectionColour
    r.skip(4 * 3)?; // OutlineSize xyz
    r.skip(4 + 4)?; // 2 x int32 scenario trigger data
    for _ in 0..3 {
        read_resource_storage(r)?;
    }
    trace(r, "after common");
    let dgc = r.u8()?;
    for _ in 0..dgc {
        read_damage_graphic(r)?;
    }
    r.skip(2 + 2)?; // SelectionSound, DyingSound
    r.skip(4 * 4)?; // Wwise train/damage/selection/dying
    r.skip(1 + 1)?; // OldAttackReaction, ConvertTerrain
    u.name = r.debug_string()?.1;
    r.skip(2)?; // CopyID
    r.skip(2)?; // BaseID
    trace(r, "after name");

    let t = u.unit_type;
    if t == UNIT_TYPE_AOE_TREES {
        return Ok(u);
    }
    if t >= UNIT_TYPE_FLAG {
        r.skip(4)?; // Speed
    } else {
        return Ok(u);
    }
    if t >= UNIT_TYPE_DEAD_FISH {
        read_dead_fish(r)?;
    }
    trace(r, "after dead_fish");
    if t >= UNIT_TYPE_BIRD {
        u.task_swap_group = read_bird(r, gv)?;
    }
    trace(r, "after bird");
    if t >= UNIT_TYPE_COMBATANT {
        read_type50(r, gv)?;
    }
    trace(r, "after type50");
    if t == UNIT_TYPE_PROJECTILE {
        read_projectile(r)?;
    }
    if t >= UNIT_TYPE_CREATABLE {
        read_creatable(r, gv)?;
    }
    trace(r, "after creatable");
    if t == UNIT_TYPE_BUILDING {
        read_building(r)?;
    }
    Ok(u)
}

/// Debug aid: prints the cursor after a named block.  Silent unless
/// `AOE2MOD_TRACE=1`, so a normal run pays nothing.
fn trace(r: &Reader<'_>, what: &str) {
    if std::env::var("AOE2MOD_TRACE").is_ok() {
        eprintln!("  {:<18} -> {}", what, r.pos);
    }
}

#[derive(Debug, Clone, Default)]
pub struct Civ {
    pub player_type: u8,
    pub name: String,
    pub tech_tree_id: i16,
    pub team_bonus_id: i16,
    pub icon_set: u8,
    pub unit_pointers_total: i16,
    pub unit_pointers_nonzero: usize,
    pub units: Vec<Unit>,
}

pub fn read_civ(r: &mut Reader<'_>, gv: u32) -> io::Result<Civ> {
    let mut c = Civ::default();
    c.player_type = r.u8()?;
    c.name = r.debug_string()?.1;
    let n = r.i16()?;
    c.tech_tree_id = r.i16()?;
    c.team_bonus_id = r.i16()?;
    r.skip(4 * n.max(0) as usize)?; // resources: f32[n]
    c.icon_set = r.u8()?;
    let m = r.i16()?;
    let mut ptrs = Vec::with_capacity(m.max(0) as usize);
    for _ in 0..m.max(0) {
        ptrs.push(r.i32()?);
    }
    c.unit_pointers_total = m;
    c.unit_pointers_nonzero = ptrs.iter().filter(|&&p| p != 0).count();
    for p in ptrs {
        if p != 0 {
            c.units.push(read_unit(r, gv)?);
        }
    }
    Ok(c)
}

// ---------------------------------------------------------------------------
// Stage 9: technologies
// ---------------------------------------------------------------------------
#[derive(Debug, Clone, Default)]
pub struct Tech {
    pub civ: i16,
    pub effect_id: i16,
    pub tech_type: i16,
    pub icon_id: i16,
    pub name: String,
    pub research_location_count: Option<usize>,
}

fn read_research_resource_cost(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(2 + 2 + 1)
}

fn read_research_location(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(2 + 2 + 1 + 4)
}

pub fn read_tech(r: &mut Reader<'_>, gv: u32) -> io::Result<Tech> {
    let mut t = Tech::default();
    r.skip(2 * 6)?; // RequiredTechs
    for _ in 0..3 {
        read_research_resource_cost(r)?;
    }
    r.skip(2)?; // RequiredTechCount
    t.civ = r.i16()?;
    r.skip(2)?; // FullTechMode
    if gv < GV_C31 {
        r.skip(2)?; // ResearchLocation
    }
    if gv >= GV_MATT {
        if in_de2(gv, GV_C18) {
            r.skip(4 + 4)?; // LanguageDLLName / Description
        } else {
            r.skip(2 + 2)?;
        }
    }
    if gv < GV_C31 {
        r.skip(2)?; // ResearchTime
    }
    t.effect_id = r.i16()?;
    t.tech_type = r.i16()?;
    t.icon_id = r.i16()?;
    if gv < GV_C31 {
        r.skip(1)?; // ButtonID
    }
    r.skip(4 + 4)?; // LanguageDLLHelp, LanguageDLLTechTree
    if gv < GV_C31 {
        r.skip(4)?; // HotKey
    }
    t.name = r.debug_string()?.1;
    if in_de2(gv, GV_C15) {
        r.skip(1)?; // Repeatable
    }
    if in_de2(gv, GV_C31) {
        let n = r.i16()?;
        t.research_location_count = Some(n.max(0) as usize);
        for _ in 0..n.max(0) {
            read_research_location(r)?;
        }
    }
    Ok(t)
}

// ---------------------------------------------------------------------------
// Stage 10: tail + tech tree
// ---------------------------------------------------------------------------
#[derive(Debug, Clone, Default)]
pub struct TechTree {
    pub ages: u8,
    pub buildings: u8,
    pub units: u32,
    pub research: u8,
    pub total_unit_tech_groups: i32,
}

fn read_common(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(4)?; // SlotsUsed
    r.skip(4 * 10)?; // UnitResearch
    r.skip(4 * 10) // Mode
}

fn skip_group(r: &mut Reader<'_>) -> io::Result<()> {
    let n = r.u8()?;
    if n != 0 {
        r.skip(4 * n as usize)?;
    }
    Ok(())
}

fn read_tech_tree_age(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(4)?; // ID
    r.skip(1)?; // Status
    skip_group(r)?;
    skip_group(r)?;
    skip_group(r)?;
    read_common(r)?;
    r.skip(1)?; // NumBuildingLevels
    r.skip(10)?; // BuildingsPerZone
    r.skip(10)?; // GroupLengthPerZone
    r.skip(1)?; // MaxAgeLength
    r.skip(4) // LineMode
}

fn read_building_connection(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(4)?;
    r.skip(1)?;
    skip_group(r)?;
    skip_group(r)?;
    skip_group(r)?;
    read_common(r)?;
    r.skip(1)?; // LocationInAge
    r.skip(AGES)?; // UnitsTechsTotal
    r.skip(AGES)?; // UnitsTechsFirst
    r.skip(4)?; // LineMode
    r.skip(4) // EnablingResearch
}

fn read_unit_connection(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(4)?;
    r.skip(1)?;
    r.skip(4)?; // UpperBuilding
    read_common(r)?;
    r.skip(4)?; // VerticalLine
    skip_group(r)?;
    r.skip(4)?; // LocationInAge
    r.skip(4)?; // RequiredResearch
    r.skip(4)?; // LineMode
    r.skip(4) // EnablingResearch
}

fn read_research_connection(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(4)?;
    r.skip(1)?;
    r.skip(4)?; // UpperBuilding
    skip_group(r)?;
    skip_group(r)?;
    skip_group(r)?;
    read_common(r)?;
    r.skip(4)?; // VerticalLine
    r.skip(4)?; // LocationInAge
    r.skip(4) // LineMode
}

pub fn read_tech_tree(r: &mut Reader<'_>, gv: u32) -> io::Result<TechTree> {
    let mut tt = TechTree::default();
    tt.ages = r.u8()?;
    tt.buildings = r.u8()?;
    // TechTree.cpp:68 guards the unit count with an inline getGameVersion()
    // call, so it is int16 only from C32 onward and a single byte before that.
    tt.units = if gv >= GV_C32 {
        r.i16()? as u32
    } else {
        r.u8()? as u32
    };
    // TechTree.cpp:77 -- int16 only for the CCV2 build, uint8 everywhere else.
    tt.research = if gv == GV_CCV2 { r.i16()? as u8 } else { r.u8()? };
    tt.total_unit_tech_groups = r.i32()?;
    for _ in 0..tt.ages {
        read_tech_tree_age(r)?;
    }
    for _ in 0..tt.buildings {
        read_building_connection(r)?;
    }
    for _ in 0..tt.units {
        read_unit_connection(r)?;
    }
    for _ in 0..tt.research {
        read_research_connection(r)?;
    }
    Ok(tt)
}

// ---------------------------------------------------------------------------
// Stage 8-10 driver
// ---------------------------------------------------------------------------
pub struct Stages810 {
    pub civs: Vec<Civ>,
    pub techs: Vec<Tech>,
    pub time_slice: i32,
    pub tech_tree: TechTree,
}

pub fn read_stages810(r: &mut Reader<'_>, gv: u32) -> io::Result<Stages810> {
    let civ_count = r.i16()?;
    let mut civs = Vec::with_capacity(civ_count.max(0) as usize);
    for _ in 0..civ_count {
        civs.push(read_civ(r, gv)?);
    }
    let tech_count = r.i16()?;
    let mut techs = Vec::with_capacity(tech_count.max(0) as usize);
    for _ in 0..tech_count {
        techs.push(read_tech(r, gv)?);
    }
    let time_slice = r.i32()?;
    r.skip(4 * 6)?; // unit_kill_rate .. razing_kill_total
    let tech_tree = read_tech_tree(r, gv)?;
    Ok(Stages810 {
        civs,
        techs,
        time_slice,
        tech_tree,
    })
}
