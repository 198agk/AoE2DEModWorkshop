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
    /// The bytes this record occupied in the input.  A unit's tail is
    /// type-dependent (Type50 / Projectile / Creatable / Building, each with its
    /// own version guards), so re-emitting it field by field would be one guess
    /// per field.  Emitting the captured span is exactly right by construction.
    pub image: Option<Vec<u8>>,
    pub unit_type: u8,
    pub id: i16,
    pub class: i16,
    pub hit_points: i16,
    /// `IconID`: which picture represents this unit. Reported, not skipped --
    /// the browse grid needs it to say `has_icon` honestly, and many units carry
    /// none at all (a grid that silently rendered holes would look broken).
    pub icon_id: Option<i16>,
    /// Byte offset of `hit_points` inside `image`.  An edit is expressed as a
    /// write at a named offset into the captured span, which is precise: the
    /// parser measured the offset, nothing here guesses it.
    pub hit_points_offset: usize,
    pub name: String,
    /// `Bird.TaskSwapGroup`.  The engine swaps an object's record pointer to
    /// another unit in the same group when a villager is retasked, so this is
    /// what makes a villager reskin keep applying after the player assigns a
    /// job.  Zero for every record with no bird block.
    pub task_swap_group: u8,
    /// The three `ResourceCost` slots of the `Creatable` block, with the offset
    /// of each amount.  A cost edit is a write at one of these offsets: which
    /// slot answers "木材成本" is a lookup (`type_ == 1`), not a guess.
    pub costs: Vec<CostSlot>,
    /// Type50's attack and armour lists.  Every entry carries its own class, so
    /// "对平民攻击加2" resolves to the entry whose class is the schema's first
    /// candidate that this unit actually carries -- not to a fixed slot.
    pub type50: Option<Type50>,
    /// `Creatable.DisplayedPierceArmour` lives at the end of the Creatable tail,
    /// two bytes before the block ends (`locate.py:297` derives it the same way).
    /// It is a panel field that mirrors an armour entry, so it needs its own
    /// mark to stay in step.
    pub displayed_pierce_armour: Option<Mark<i16>>,
}

/// One `ResourceCost` slot: `i16 type, i16 amount, i16 flag`.
#[derive(Debug, Clone, Copy, Default)]
pub struct CostSlot {
    pub type_: i16,
    pub amount: i16,
    /// Absolute file offset of `amount`.  Absolute, not record-relative, because
    /// that is what every write path in `aoe2mod-serve` speaks.
    pub amount_offset: usize,
}

/// One entry of Type50's attack or armour list: `i16 class, i16 amount`.
#[derive(Debug, Clone, Copy, Default)]
pub struct DamageEntry {
    pub class: i16,
    pub amount: i16,
    pub amount_offset: usize,
}

/// A field the game renders on the unit panel, plus where it lives.  AoE2 keeps
/// several of these twice -- the displayed number and the raw entry the damage
/// maths actually reads -- so an edit has to move both or the panel starts
/// lying.  `stat_mirrors.json` records which pairs exist.
#[derive(Debug, Clone, Copy, Default)]
pub struct Mark<T> {
    pub value: T,
    pub offset: usize,
}

/// The Type50 block: damage lists plus the panel fields they mirror.
#[derive(Debug, Clone, Default)]
pub struct Type50 {
    pub attacks: Vec<DamageEntry>,
    pub armors: Vec<DamageEntry>,
    pub displayed_melee_armour: Mark<i16>,
    pub displayed_attack: Mark<i16>,
    pub max_range: Mark<f32>,
    pub reload_time: Mark<f32>,
    pub displayed_range: Mark<f32>,
    pub displayed_reload_time: Mark<f32>,
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

/// Reads one `i16 class, i16 amount` pair, keeping where the amount sits.
///
/// The class is kept because it is the *selector*: a sentence that names a
/// damage class ("对平民") has to find the entry whose class the schema's
/// candidates point at, and a list without classes cannot answer that.
fn read_damage_entry(r: &mut Reader<'_>) -> io::Result<DamageEntry> {
    let class = r.i16()?;
    let amount_offset = r.pos;
    let amount = r.i16()?;
    Ok(DamageEntry {
        class,
        amount,
        amount_offset,
    })
}

fn read_damage_list(r: &mut Reader<'_>) -> io::Result<Vec<DamageEntry>> {
    let n = r.i16()?;
    let mut out = Vec::with_capacity(n.max(0) as usize);
    for _ in 0..n.max(0) {
        out.push(read_damage_entry(r)?);
    }
    Ok(out)
}

fn read_type50(r: &mut Reader<'_>, gv: u32) -> io::Result<Type50> {
    let mut t = Type50::default();
    r.skip(2)?; // BaseArmor
    t.attacks = read_damage_list(r)?;
    t.armors = read_damage_list(r)?;
    r.skip(2)?; // DefenseTerrainBonus
    r.skip(4)?; // BonusDamageResistance
    t.max_range.offset = r.pos;
    t.max_range.value = r.f32()?;
    r.skip(4)?; // BlastWidth
    t.reload_time.offset = r.pos;
    t.reload_time.value = r.f32()?;
    r.skip(2 + 2)?; // ProjectileUnitID, AccuracyPercent
    r.skip(1)?; // BreakOffCombat
    r.skip(2)?; // FrameDelay
    r.skip(4 * 3)?; // GraphicDisplacement[3]
    r.skip(1)?; // BlastAttackLevel
    r.skip(4)?; // MinRange
    r.skip(4)?; // AccuracyDispersion
    r.skip(2)?; // AttackGraphic
    t.displayed_melee_armour.offset = r.pos;
    t.displayed_melee_armour.value = r.i16()?;
    t.displayed_attack.offset = r.pos;
    t.displayed_attack.value = r.i16()?;
    t.displayed_range.offset = r.pos;
    t.displayed_range.value = r.f32()?;
    t.displayed_reload_time.offset = r.pos;
    t.displayed_reload_time.value = r.f32()?;
    if in_de2(gv, GV_C20) {
        r.skip(4)?; // BlastDamage
    }
    if in_de2(gv, GV_C22) {
        r.skip(4 + 4)?; // DamageReflection, FriendlyFireDamage
    }
    if in_de2(gv, GV_C27) {
        r.skip(2 + 4 + 2)?; // InterruptFrame, GarrisonFirepower, AttackGraphic2
    }
    Ok(t)
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

fn read_resource_cost(r: &mut Reader<'_>) -> io::Result<CostSlot> {
    let type_ = r.i16()?;
    let amount_offset = r.pos;
    let amount = r.i16()?;
    r.skip(2)?; // Flag
    Ok(CostSlot {
        type_,
        amount,
        amount_offset,
    })
}

/// Returns the three cost slots and where `DisplayedPierceArmour` sits.
fn read_creatable(r: &mut Reader<'_>, gv: u32) -> io::Result<(Vec<CostSlot>, usize)> {
    let mut costs = Vec::with_capacity(3);
    for _ in 0..3 {
        costs.push(read_resource_cost(r)?);
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
    // Creatable.cpp ends with DisplayedPierceArmour; the tail below is the last
    // field, which is why `locate.py:297` derives it as `_creatable_end - 2`
    // rather than reading a stored offset.  Recording the position directly is
    // the same fact measured instead of reconstructed.
    let dpa = r.pos;
    r.skip(2)?; // DisplayedPierceArmour
    Ok((costs, dpa))
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

fn finish(mut u: Unit, r: &Reader<'_>, start: usize) -> Unit {
    u.image = Some(r.buf[start..r.pos].to_vec());
    u
}

pub fn read_unit(r: &mut Reader<'_>, gv: u32) -> io::Result<Unit> {
    let start = r.pos;
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
    u.hit_points_offset = r.pos - start;
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
    u.icon_id = Some(r.i16()?); // IconID
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
        return Ok(finish(u, r, start));
    }
    if t >= UNIT_TYPE_FLAG {
        r.skip(4)?; // Speed
    } else {
        return Ok(finish(u, r, start));
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
        u.type50 = Some(read_type50(r, gv)?);
    }
    trace(r, "after type50");
    if t == UNIT_TYPE_PROJECTILE {
        read_projectile(r)?;
    }
    if t >= UNIT_TYPE_CREATABLE {
        let (costs, dpa_off) = read_creatable(r, gv)?;
        u.costs = costs;
        u.displayed_pierce_armour = Some(Mark {
            value: i16::from_le_bytes([r.buf[dpa_off], r.buf[dpa_off + 1]]),
            offset: dpa_off,
        });
    }
    trace(r, "after creatable");
    if t == UNIT_TYPE_BUILDING {
        read_building(r)?;
    }
    Ok(finish(u, r, start))
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
    pub name_marker: u16,
    pub name_len: u16,
    pub resources: Vec<f32>,
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
    let (nm, name, nl) = r.debug_string()?;
    c.name = name;
    c.name_marker = nm;
    c.name_len = nl;
    let n = r.i16()?;
    c.tech_tree_id = r.i16()?;
    c.team_bonus_id = r.i16()?;
    for _ in 0..n.max(0) {
        c.resources.push(r.f32()?);
    }
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
    pub image: Option<Vec<u8>>,
    pub civ: i16,
    pub effect_id: i16,
    pub tech_type: i16,
    pub icon_id: i16,
    pub name: String,
    pub research_location_count: Option<usize>,
    /// Byte offset of `effect_id` INSIDE `image`.
    ///
    /// `effect_id` is a modeled mirror of two bytes that live in `image`, and
    /// `write_tech` replays `image` verbatim -- so assigning `t.effect_id`
    /// changes nothing in the output.  Anything that retargets a tech at a
    /// different effect record has to poke these two bytes instead, and this is
    /// how it finds them.  Computed at read time because the position depends
    /// on a chain of version guards (`gv=54`: 6x2 RequiredTechs, 3x5 costs, 2
    /// RequiredTechCount, 2 civ, 2 FullTechMode, 8 LanguageDLL pair for DE2,
    /// then effect_id) -- hard-coding the sum is how it silently lands one
    /// field early the first time a guard changes.
    pub effect_id_offset: Option<usize>,
}

/// Overwrite the `effect_id` field inside `image` so the byte replay points a
/// tech at a different effect record.  Returns false when this tech has no
/// located offset (never parsed, or `image` absent), leaving it untouched.
pub fn set_tech_effect_id(t: &mut Tech, effect_id: i16) -> bool {
    let Some(off) = t.effect_id_offset else {
        return false;
    };
    let Some(img) = t.image.as_mut() else {
        return false;
    };
    if off + 2 > img.len() {
        return false;
    }
    img[off..off + 2].copy_from_slice(&effect_id.to_le_bytes());
    t.effect_id = effect_id;
    true
}

fn read_research_resource_cost(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(2 + 2 + 1)
}

fn read_research_location(r: &mut Reader<'_>) -> io::Result<()> {
    r.skip(2 + 2 + 1 + 4)
}

pub fn read_tech(r: &mut Reader<'_>, gv: u32) -> io::Result<Tech> {
    let start = r.pos;
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
    t.effect_id_offset = Some(r.pos - start);
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
    t.image = Some(r.buf[start..r.pos].to_vec());
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
    pub tech_tree_image: Option<Vec<u8>>,
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
    let tt_start = r.pos;
    let tech_tree = read_tech_tree(r, gv)?;
    Ok(Stages810 {
        civs,
        techs,
        tech_tree_image: Some(r.buf[tt_start..r.pos].to_vec()),
        time_slice,
        tech_tree,
    })
}
