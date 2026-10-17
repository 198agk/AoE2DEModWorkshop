# Semantic Layer Report — AoE2DE dat ID → human-readable name

**Deliverables**
| File | Contents |
|---|---|
| `_probe\semantic\unit_names.json` | 2,693 distinct dat unit IDs → `{internal, en, zh, tw, name_string_id, ...}` |
| `_probe\semantic\tech_names.json` | 1,510 techs → same shape + description/help/tech_tree string families |
| `_probe\semantic\SEMANTIC_REPORT.md` | this document |

**Scripts** (all in `_probe\semantic\`, stdlib only, Python 3):
`strings_db.py` (key-value parser/merger) · `extract_ids.py` (dat string-id capture) ·
`analyze_units.py` · `check_divergence.py` · `build_semantic.py` · `finalize.py` ·
`inventory_json.py` · `check_armor_classes.py` · `diag_techs.py` · `diag_techs2.py` ·
`join_test.py` · `validate.py` · `check_techtree_conflict.py` · `probe_strings.py`

Nothing under the game directory was modified — read-only access only.

---

## 1. The resolution chain (verified)

```
dat unit record  ──LanguageDLLName (int32 @ record+3)──▶  string id  ──┐
dat tech record  ──LanguageDLLName (int32 @ record+33)─▶  string id  ──┤
                                                                       ▼
        resources\<lang>\strings\key-value\key-value-strings-utf8.txt
        + 12 sibling key-value files (campaigns / paphos / PDLC)
             numeric key ──▶  localised display string
```

The dat field named `LanguageDLLName` is **not** a DLL reference. It is an
integer index into the key-value string files. The name is historical: in the
original Age of Kings the strings lived in `language.dll` / `language_x1_p1.dll`
Win32 resource tables. **No `language*.dll` exists anywhere in the AoE2DE tree**
(whole-tree recursive search returned zero matches; the only DLLs are
`BugSplat64.dll`, `BugSplatRc64.dll`, `Juij_Steam.dll`, `libHttpClient.Win32.dll`,
`PartyWin.dll`, `steam_api64.dll`, `version.dll`, `winmm.dll`). The DLL mechanism
is **dead**; the field name survives as a legacy label. Localisation is 100%
key-value text files under `resources\<lang>\strings\key-value\`.

### Getting the field out of the dat

`_probe\datparse\parse_dat.py` reads and **discards** these fields
(`r.i32()  # LanguageDLLName` at `parse_dat.py:602` and `:718-724`). Rather than
re-derive the record layout and risk a desync, `extract_ids.py` **monkey-patches**
`parse_dat.read_unit` / `parse_dat.read_tech`: it records `start = r.pos` before
delegating, then samples the int32s out of the same byte buffer with
`struct.unpack_from`. The verified parser remains the single source of truth for
record boundaries; only 4 bytes inside each record are sampled.

**Correctness check after instrumentation** — identical to the pristine parser:

```
dat size 93,268,152 · final offset 93,268,152 · exact match YES
leftover 0 · parse 4.73 s · civs 63 · techs 1,510 · unit records 136,861
all 10 stage start/end offsets byte-identical to the unpatched parser
```

Verified record offsets from record start:
* **unit** — `+0` u8 type, `+1` i16 id, `+3` **i32 LanguageDLLName**, `+7` i32 LanguageDLLCreation
* **tech** — `+33` **i32 LanguageDLLName**, `+37` **i32 LanguageDLLDescription**,
  `+47` **i32 LanguageDLLHelp**, `+51` **i32 LanguageDLLTechTree**

Cross-checked against the vendored C++ spec:
`_probe\source\genieutils\include\genie\dat\Unit.h:95` `int32_t LanguageDLLName = 5000;`
and `Research.h:67` `int32_t LanguageDLLName = 7000;`, `:73` `LanguageDLLDescription = 8000;`,
`:93` `LanguageDLLHelp = 107000;`, `:95` `LanguageDLLTechTree = 150000;`.

---

## 2. String file format (verified)

**Location**
```
resources\<lang>\strings\key-value\key-value-strings-utf8.txt     ← main table
resources\_common\strings\key-value\non-localized-key-value-strings-utf8.txt
```
Languages present: `br de en es fr hi it jp ko ms mx pl ru tr tw vi zh` (17) plus
`_common`, `_launcher`, `_packages`.

**Encoding / syntax**
* UTF-8, **no BOM**, **CRLF** line endings.
* `//` line comments and blank lines are allowed.
* Data line syntax: `<integer-id><TAB or space>"<value>"` — e.g. `98 "1"`,
  `1001 "Age of Empires II"`, `5504 "Outpost"`.
* A trailing `// comment` may follow the quoted value on the same line.
* Some lines use **symbolic** keys (`IDS_OPT_ESC_MENU`, `IDS_CIVTIPS_46_0`,
  `NNNNNN_perth`). These are **not** dat string IDs and are skipped (3,260 such
  lines in the `en` main file).

**Per-language file set** (13 files, all merged by `strings_db.py`):
`key-value-strings-utf8.txt` (19,677 entries), `key-value-paphos-strings-utf8.txt`
(1,709), `key-value-modded-strings-utf8.txt` (0), `paphos-campaign-` (3,224),
`paris-campaign-` (1,129), `PDLC2-campaign-` (1,132), `PDLC3-campaign-` (1,014),
`PDLC4-campaign-` (1,027), `PDLC6-campaign-` (2,213), `peru-campaign-` (1,278),
`portland-campaign-` (1,285), `providence-campaign-` (2,663), `tournament-` (2,
overrides 2 existing ids). **Merged: 36,351 unique numeric IDs, range 98 … 30,030,001.**
`en`, `zh` and `tw` have **identical ID coverage** (36,351 each).

Merged file size: `en` 2,012,476 B; `zh` 1,965,572 B; `tw` 1,969,823 B.

**Verified sample:** id 5504 → `Outpost` / `哨站`.

---

## 3. Coverage

### Units — 2,693 distinct IDs (136,861 per-civ records)

| Category | IDs | Share | Meaning |
|---|---|---|---|
| **resolved** | **1,651** | **61.3 %** | localised name found in en **and** zh |
| unresolved — `LanguageDLLName == 0` | 1,036 | 38.5 % | record carries no name id |
| unresolved — `LanguageDLLName == -1` | 4 | 0.1 % | negative sentinel |
| unresolved — positive id absent from strings | 2 | 0.07 % | genuine string-table gap |

`en`-resolved but `zh`-missing: **0**. Every resolved unit has both languages.

**The 1,036 zero-ID units are internal objects, not player-facing content.**
Types among them: EyeCandy(10) ×354, type 30 ×388, type 60 ×169, Building(80) ×60,
Combatant(70) ×39, Doodad(20) ×25, one type 25. These are scenery, corpses,
"shadow" nodes, annexes and engine plumbing. 354 of them appear *only* as
type 10 EyeCandy (all hp 1), consistent with the parser's earlier finding that all
5,733 empty-internal-name records are EyeCandy.

**The 4 negative-ID units** are all real map objects with no localised string:
`1890 Pasture Annex`, `2078 Pasture Annex Fences`, `2079 Pasture Annex AB`,
`2080 Pasture Annex CD` — internal scenario-support objects.

**The 2 genuine gaps:**
* unit `249` `POREX` → string id **5322** — absent from every key-value file.
* unit `736` `Projectile MLK` → string id **5617** — absent from every key-value file.

### Techs — 1,510 records

| Category | Count | Share | Meaning |
|---|---|---|---|
| **resolved** | **536** | **35.5 %** | localised name in en and zh |
| unresolved — placeholder default id | 743 | 49.2 % | `7000` ×734 / `6000` ×9 |
| unresolved — `0` or `-1` | 201 | 13.3 % | new/internal researches |
| unresolved — positive id absent from strings | 30 | 2.0 % | genuine string-table gap |

`zh` missing among resolved techs: **0**.

**The 743 placeholder-default techs are engine internals by design.** `7000` is
the genieutils `LanguageDLLName` default value (`Research.h:67`) and has no
localised string *on purpose*; the game never displays those techs (they are
"make avail", "C-Bonus, …", "Shadow …", "[SCEN] …", age-transition plumbing).

**A clean, decisive discriminator:** every tech whose `LanguageDLLName > 7399`
resolves — **302 / 302 (100 %)**. All unresolved positive IDs fall in the
`6000..7399` engine-internal block. So a tool can say: *"ids ≤ 7399 that carry
7000/6000 are internal placeholders; ≥ 7400 are real player-visible techs and
always resolve."*

**The 30 genuine tech gaps** (all absent from every key-value file):
`7087 Spearman (make avail)` · `7099 Skirmisher (make avail)` ·
`7106` ×9 (`Shadow Blacksmith/TC/TC Annex/TC Foundation -- Age One`, `Shadow Church`,
`Castle/Feudal/Imperial Age start`, `C-Bonus, Sheep bonus age3 start`) ·
`7107 Shadow Church -- Age One` · `7108 Shadow Dock/Port -- Age One` ·
`7109 Farm -- Age One` · `7153 R TC (make avail)` · `7154 Scout (make avail)` ·
`7162 Wall 2 (make avail)` · `7167 Cog`, `Enable Merchant Ship` ·
`7213 Barracks/Palisade Wall (make avail)` · `7214 Church (make avail)` ·
`7215 Farms (make avail)` · `7367` ×6 (Heavy/Light Cavalry HP bonuses) ·
`7385 Fish Trap (make avail)`.

### Tech string-ID family
The four tech strings are **one family derived from the Name id**:
`Description = Name + 1000`, `Help = Name + 100000`, `TechTree = Name + 150000`.
This holds exactly for **915 / 1,309** positive-Name techs; the remainder use
hand-authored ids (e.g. `(7000, 8288, 107288, 157288)`). `tech_names.json` records
all four resolved independently rather than relying on the pattern.

**Secondary string fields are much sparser than the Name field.** Among the 536
resolved techs, only **449** also have a resolvable description, **28** a resolvable
help string and **1** a resolvable techtree string. `tech_names.json` still records
each of the three with its own `name_string_id` + `en`/`zh`/`tw` (null where the id
is not in any string file) so the tool can show what exists and omit the rest —
the tooltip text for most techs is simply not present in the shipped string files.

---

## 4. Internal code name vs localised display name

The dat's short `Name` (`ARCHR`, `KNGHT`, `LEGION`) is an **engine-side code name**,
not a display string and not a stable key.

* Of 1,651 resolved unit IDs, **1,143** have a 3–8 char ALLCAPS-style code.
* Only **310 / 1,651** have an internal code equal to the localised name
  (case-insensitive) — e.g. `KNGHT` → "Knight", `EAGLE` → "Eagle Scout" is *not* a match.
* **1,526 distinct internal codes** cover 1,651 resolved IDs — so codes are not unique.
* **51 internal codes map to multiple localised names.** Examples:
  `TREBU` → {Trebuchet, Warwolf Trebuchet}; `RTWC2` → {Town Center, Defensive/
  Economic/Military Town Center}; `THSWD` → {Long Swordsman, Eastern Swordsman,
  Norse Warrior}; `ARTCT` → {Relic Cart, Treasure Chest}; `MPCAV` →
  {Flamethrower, War Elephant}; `WCTW3` → {Fire Tower, Keep}.

**Conclusion:** the internal code is *not* a reliable path to a display name.
It is useful only as a debugging label and as a loose grouping hint. The
authoritative and reliable path is `LanguageDLLName` → key-value string.
`unit_names.json` therefore carries `internal` for reference and `en`/`zh` for display.

---

## 5. Civ divergence — one lookup table is **not** sufficient

The dat stores units per civ (63 civs). For **118 unit IDs** `LanguageDLLName` is
**NOT identical across civs**, so the parent's assumption that one table suffices
does not hold.

The divergence is a **strict, clean civ partition**: 57 civs use the standard id,
and exactly **6 civs — Achaemenids, Athenians, Macedonians, Puru, Spartans,
Thracians** (the "Chronicles" / antiquity set) — use an alternate `405xxx` id. All
118 IDs share this exact same 6-civ split; no other pattern exists.

Crucially the alternates are **genuinely different units**, not aliases:

| Unit ID | internal | 57 civs (standard) | 6 Chronicles civs |
|---|---|---|---|
| 4 | `ARCHR` | 5083 Archer / 步弓手 | 405052 **Bowman** / 弓兵 |
| 38 | `KNGHT` | 5068 Knight / 骑士 | 405049 **Lancer** / 长矛骑兵 |
| 74 | `SPRMN` | 5079 Militia / 民兵 | 405039 **Levy** / 征兵 |
| 75 | `SWDMN` | 5080 Man-at-Arms / 武士 | 405040 **Maceman** / 链锤兵 |
| 77 | `THSWD` | 5081 Long Swordsman / 长剑士 | 405041 **Swordsman** / 剑士 |
| 36 | `BCANN` | 5093 Bombard Cannon / 手推炮 | 405163 **Siege Ballista** / 攻城弩炮 |
| 30 | `CRCH2` | 5138 Monastery / 修道院 | 405066 **Temple** / 圣殿 |
| 82 | `CSTL` | 5142 Castle / 城堡 | 405065 **Fort** / 堡垒 |

Additionally **6 unit IDs carry a different internal `Name` across civs**.

**Handling in the deliverable:** the majority variant (57 civs) is emitted as the
canonical `en`/`zh`/`name_string_id`, plus an explicit `civ_variants` map giving
every variant with its civ list and an `is_canonical` flag. A tool that only needs
a "common" name can read the top level; a tool that wants civ-correct naming reads
`civ_variants`.

All 118 alternates and all 118 majority ids resolve in both `en` and `zh`
(0 unresolved on either side).

---

## 6. Resolution of the CivTechTrees-vs-strings conflict

While validating against `resources\_common\dat\CivTechTrees\<CIV>.json` (62 files,
10,742 nodes) we found **44 disagreements** — e.g. `ACHAEMENIDS.json` node 4 has
`Name: "Archer"` but `Name String ID: 405052`. Our pipeline reports **"Bowman"**.
Checking the raw string file settles it:

```
key-value-paphos-strings-utf8.txt   405052 "Bowman"        ← authoritative
ACHAEMENIDS.json                    Name = "Archer"       ← stale base-game label
```

**In all 44 cases the raw string file agrees with our value and 0 cases support the
JSON's `Name` field.** All 44 are Chronicles civs. Conclusion: the key-value string
files are authoritative; the `Name` field inside CivTechTrees JSON is a base-game
display label that was not updated when Chronicles re-skinned those units. The
`Name String ID` in those files is correct and matches our `civ_variants` keys.

Other joins: 276 nodes agree outright; 122 nodes land on our canonical id and 198
on one of our variant ids. 10,360 nodes use string ids not reachable from the unit
map (they are techs/buildings/help ids in a different namespace) and 62 nodes have
Node IDs that are not dat unit ids.

---

## 7. JSON semantic sources — structure and join quality

All under `resources\_common\dat\`.

| File | Top structure | Join to dat IDs |
|---|---|---|
| `futuravailableunits.json` (1.3 MB) | `{civ: {Buildings: [{ID, Name, Techs[], Units:[{ID, Name, RequiredAge, PrereqTech, ...}]}]}}`, 58 civs | **99.3 %** (283/285 distinct IDs are dat unit ids); the 2 strays are `20000`, `20001` (engine pseudo-ids). Carries its own human-readable `Name` — useful cross-check |
| `CivTechTrees\<CIV>.json` (62) | `{civ_id, civ_techs_buildings[], civ_techs_units[]}`; node = `{Name, Node Type, Name String ID, Help String ID, Age ID, Building ID, Node ID, Picture Index, Node Status}` | Node ID → dat unit id for 518/519 distinct Node IDs. **`Name` is unreliable** (§6); use `Name String ID` |
| `civilizations.json` | `{civilization_list: [{internal_name, tech_tree_name, data_name, hud_style, name_string_id, era, ...}]}`, 63 entries | `name_string_id` resolves 63/63 in `en`. **Naming differs from the dat**: file uses `Britons`/`Franks`, the dat uses `British`/`French`. Join on *order* or `data_name`, not the raw string |
| `eras.json` | `[{Name: "base"\|"antiquity", Ages:[{NameId, TechTreeIconMaterialName, ShieldMaterialName}]}]` | `NameId` 4201–4205 (base) and `407084…` (antiquity) — resolves via strings |
| `unitlines.json` | `{Hint, UnitLines:[{Name, Identifier, Building, LineID, IDChain[]}]}` | `IDChain` holds dat unit ids (e.g. `[117,155]`); `LineID` −400…−199 |
| `unitcategories.json` | `{Cavalry:[], CavalryArchers:[], SiegeWeapons:[7], Archers:[], Infantry:[], Warboats:[], Monks:[2]}` | Mostly **empty**; not a usable category source |
| `linkedTechs.json` | `{LinkedTechs:[{NameId, Comment, Local, Type, Techs[]}]}`, 20 | `Techs[]` are dat **tech indices**; `NameId` 424001+ is a **separate** string id **not** in the dat |
| `linkedUnits.json` | `{Data:[{Name, Units[]}]}`, 8 | `Units[]` are dat unit ids (e.g. `Lü Bu` → `[2032, 2061]`). Human `Name` is not localised |
| `dropsites.json` | `{drop_site_list:[{name, building_id, worker_object_group, accepts_livestock, target_list[], update_ai_resource_types}]}`, 30 | `building_id` is a dat unit id |
| `sharedbuildings.json` | `{Data:[{Name, Units:[{FirstUnitID, FirstBuildingID, SecondUnitID, SecondBuildingID}]}]}`, 11 | All ids are dat unit ids |
| `objreplacement.json` | `{objects:[{name, object_id, object_override:{replacement_object, chance}\|{replacement_attribute}}]}`, 8 | `object_id` is a dat unit id (83 ↹ 293 Villager M/F 50 %) |
| `buttons.json` | `{command_button_list:[{name, button_action_id, sequence_id, icon_id, help_string_id, more_help_string_id}]}`, 14 | `help_string_id` etc. are **string ids** — resolve via the same key-value table |
| `sounds.json` | `{sound_list:[{key, name}]}`, 53 | Symbolic key → Wwise event name; **no** dat id join |
| `maps.json` | `{default_map_type, ..., map_list}` | Map definitions; no unit-id join |
| `selection_group_def.json` (23,890 B) / `chronicles_selection_group_def.json` (24,210 B) | `{selection_group:[{name, group_list, item_list:[{id, label}]}], radial_data}` | `id`/`label` are **object-group** ids (`OBJECT_GROUP_ARCHER`), not dat unit ids |
| `paphos_campaign.json`, `peru_campaign.json`, `providence_campaign.json` | Campaign metadata (file paths, map dims, preloaded images) | No dat unit-id join |
| `paphosfutureavailableunits.json` (259,799 B) | Same shape as `futuravailableunits.json`, 12 civs — the **Chronicles** counterpart | Same 99 % join; use for the 6 Chronicles civs |
| `airesourcetypes.json` | `{ResourceTypes:[{Resource, Types:[{Name, ID}]}]}` | `ID` are dat unit ids of resource sources (Forage Bush 59, Fish 53, …) |
| `hotkeys.json` (490 KB) | `{shared_hotkey_group_list[], hotkey_group_list[]}` | `name_string_id`/`data_name` — string ids, no unit join |
| `AIConsts.json`, `adapterblacklist.json` | AI constants / GPU blacklist | No semantic join |

**Key takeaway for the tool:** `futuravailableunits.json` + `paphosfutureavailableunits.json`
already carry a human-readable `Name` and a clean 99 % join to dat unit ids — they
are the best *independent cross-check* for the unit map. `CivTechTrees\*.json` is
the best source of *which civ has which node* but its `Name` field must be ignored
in favour of `Name String ID`. `civilizations.json` supplies civ display names but
uses different civ spellings than the dat.

---

## 8. AGE ini tables — `Tools_Builds\AGE3NamesV0007.ini`

10,662 bytes / 576 lines, four sections. `[Counts]`: `NumAoE2DEArmors=37`,
`NumAoE2DETerrainTables=32`, `NumAoE2DECivResources=500`.

* **`[AoE2DEArmorNames]`** — 37 entries, ids **0..36**. Attack/armor classes.
  Named entries: 1 Infantry, 2 Turtle Ships, 3 Base Pierce, 4 Base Melee,
  5 War Elephants, 8 Cavalry, 11 All Buildings (except Port),
  13 Stone Walls & Gates & Towers, 14 Predator Animals, 15 Archers,
  16 Ships & Saboteur, 17 Rams & Trebuchet & Siege Towers, 18 Trees,
  19 Unique Units (except Turtle Ship), 20 Siege Weapons, 21 Standard Buildings,
  22 Walls & Gates, 23 Gunpowder Units, 24 Hunted Predator Animals, 25 Monks,
  26 Castle, 27 Spearmen, 28 Cavalry Archers, 29 Eagle Warriors, 30 Camels,
  31 Leitis Attack, 32 Condottiero, 34 Fishing Ship, 35 Mamelukes, 36 Heroes;
  0/6/7/9/10/12/33 are `Unused`.
* **`[AoE2DETerrainTableNames]`** — 32 entries, ids 0..31, complete
  (0 All, 1 Land + shallows, 2 Beach, …, 31 All - water, wheel track).
  Annotates **terrain restriction** tables (the dat's `TerrainRestrictions` block, 54 entries).
* **`[AoE2DECivResourceNames]`** — 500 entries, ids 0..499, complete but sparse in
  meaning: many are literally `Unused`. Real ones include 0 Food Storage,
  4 Population Headroom, 6 Current Age, 77 Conversion Resistance, 91 Starting Food,
  205–208 Feitoria productivities, 262 Civilization Name Override,
  263 Starting Scout ID, 234 Spawn Cap, 235 Flemish Militia Population.
  Annotates the **civ resource** array in civ records.

### Confirmation: dat attack/armor `Class` indexes `[AoE2DEArmorNames]` — **CONFIRMED**

The parser discarded these arrays (`parse_dat.py:502` `read_attack_or_armor`,
`read_type50` at `:506`), so `check_armor_classes.py` wrapped `read_type50` and
re-read the arrays from the same byte stream (layout: `+0` i16 BaseArmor, `+2` i16
n_armor, then `n_armor × (i16 class, i16 amount)`, then the same for attacks).
**90,190 type-50 records captured; final offset still 93,268,152 (no desync).**

* ARMOR: 34 distinct classes, ids **1..60**
* ATTACK: 37 distinct classes, ids **−1..60**

Every class in **0..36 maps 1:1 onto `[AoE2DEArmorNames]`** with semantically
correct frequency — e.g. armor class 4 "Base Melee" ×31,984, class 21 "Standard
Buildings" ×24,507, class 15 "Archers" ×22,113, class 30 "Camels" ×16,577, and
attack class 3 "Base Pierce" ×69,123 / class 4 "Base Melee" ×69,123 on every
damaging unit. **The mapping is confirmed.**

**However the ini is incomplete for the current game.** Classes **37, 38, 39, 40,
41, 60** appear in the dat but are **absent from `AoE2DEArmorNames`** (the file is
v0007 and predates later DE content), as does the attack sentinel `−1`:

| Class | Seen in | Total refs | In ini? |
|---|---|---|---|
| 37 | armor + attack | 1,638 | no |
| 38 | armor + attack | 15,561 | no |
| 39 | armor + attack | 17,010 | no |
| 40 | attack only | 441 | no |
| 41 | armor + attack | 504 | no |
| 60 | armor + attack | 3,087 | no |
| −1 | attack only | 63 | no |

So a tool must **not** present the ini as exhaustive: it should render unknown
classes as e.g. `"Class 38"` rather than crashing or inventing a name, and ideally
carry a small supplemental table. The **units** deliverable is unaffected — no
`unit_names.json` value depends on the ini.

---

## 9. Honest list of everything unresolved

**Units — 1,042 of 2,693 IDs unresolved (38.7 %)**

* **1,036 IDs with `LanguageDLLName == 0`** — reason: the record carries no name
  string id at all. These are engine-internal objects: EyeCandy scenery (354),
  type-30/60 placeholders, and "shadow"/annex/plumbing objects. They are not
  player-facing content and have no localised name to find. **Not a gap in our
  method — there is no name in the data.**
* **4 IDs with `LanguageDLLName == -1`** — reason: negative sentinel meaning
  "no string". `1890 Pasture Annex`, `2078 Pasture Annex Fences`,
  `2079 Pasture Annex AB`, `2080 Pasture Annex CD`.
* **2 IDs with a positive id absent from every string file** — reason: genuine
  string-table gap. `249 POREX` (id 5322), `736 Projectile MLK` (id 5617).

**Techs — 974 of 1,510 unresolved (64.5 %)**

* **743 with the genieutils placeholder default** (`7000` ×734, `6000` ×9) —
  reason: by design these internal techs ("make avail", "C-Bonus …", "Shadow …",
  "[SCEN] …", age transitions) are never displayed, so no string was authored.
* **201 with `0` or `-1`** — reason: unnamed "New Research" placeholder records,
  e.g. "Auto upgrade Scout Feudal Age".
* **30 with a positive id absent from every string file** — reason: genuine gap,
  all in the `7087..7385` range (full list in §3).

Every unresolved entry in both JSON files carries an explicit
`"resolved": false`, a `"category"`, and a human-readable `"unresolved_reason"`
naming *which* of the above situations applies. **No value was invented or
left silently blank.**

---

## 10. Reproducing

```
python extract_ids.py          # dat -> _raw_ids.json  (~5 s)
python build_semantic.py       # -> unit_names.json, tech_names.json
python finalize.py             # adds `category`, writes _final_stats.json
python validate.py             # end-to-end validation (11/11 ground truth)
python check_armor_classes.py  # -> _armor_classes.json
python inventory_json.py       # JSON source inventory
python join_test.py            # join quality against each JSON source
```
Set `PYTHONIOENCODING=utf-8` or the scripts' own
`sys.stdout.reconfigure(encoding="utf-8")` (already applied) before printing
Chinese text, otherwise Windows `gbk` stdout raises `UnicodeEncodeError`.
