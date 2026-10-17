# AoE2DE Scenario / Campaign Format — Survey

Scope: what it takes to build a beginner-friendly scenario/campaign mod tool for
Age of Empires II: Definitive Edition, such that the user never sees field names,
file paths, or raw formats.

Machine surveyed: game `D:\Games\Steam\steamapps\common\AoE2DE`, version `101.103.54800.0`
(Steam appid 813780, buildid 25464371); user profile `C:\Users\26913\Games\Age of Empires 2 DE`.
All inspection was READ-ONLY on both roots. Every script and output in this survey is under
`D:\Software\DeepSeek Harness\工作区2\_probe\survey_scenario\`.

Evidence labels used below: **[V]** verified by my own inspection on this machine ·
**[D]** found in documentation or published metadata · **[I]** inferred / not directly verified.

---

## 1. Bottom line

- **Viable, and the read/edit path is much cheaper than expected.** Scenario files are
  **not encrypted** — a 4-byte ASCII version string followed by a plain **raw-deflate**
  stream (zlib `wbits=-15`), and **campaigns are not compressed at all**: they are plain
  containers holding complete, standalone scenario files back-to-back. **[V]**
- **Do not write a parser. One mature library already dominates the space.**
  `KSneijders/AoE2ScenarioParser` (Python, GPL-3.0) shipped **0.9.4**, was **pushed
  2026-10-03**, and does full read **and write** for scenario versions **1.36–1.59**,
  shipping a machine-readable JSON schema **per version** that already names every
  trigger field and its type. **[V]/[D]** The gap to fill is the *friendly layer*, not
  the format layer.
- **Biggest blocker: scenario-version coverage.** Of the **53** standalone scenario files
  on this machine, **21 read and 32 fail** under the library, and **100 % of the failures
  are one class** — `UnknownScenarioStructureError: The version DE:<v> is not supported`
  for versions **1.21, 1.33 and 1.35** (the pre-2019 structure). All 32 failures are old
  shipped/random-map content; the user's own two files (1.53, 1.54) are fine. When the same
  test is run over the **229 scenarios embedded in campaigns, 222 (96.9 %) read OK in
  isolated processes** — the corpus that actually matters is well covered, and the gap is
  confined to legacy files. **[V]**
- **The library's real hazard is cross-version state leakage, not correctness on a single
  file.** Loading two *different* scenario versions in one Python process corrupts the
  second load, and writing older versions after newer ones raises. This is a **known,
  hard-coded TODO in the library**, not a bug I can configure away. Rule: **one scenario
  version per process.** **[V]**
- **Licensing is the strategic decision, not the technology.** The library is **GPL-3.0**
  (its PyPI metadata wrongly claims MIT — unresolved conflict), and the one existing GUI
  competitor (`MegaDusknoir/AoE2TriggerCraft2`, Python, GPL-3.0, actively maintained) is
  already built on it. A new tool either (a) links the GPL library and lives with copyleft,
  (b) vendors a clean-room writer, or (c) ships as a GPL-3.0 product. **[V]/[D]/[I]**

---

## 2. Real files found

Counts by extension, whole tree, both roots **[V]**:

| Extension | Count | Where |
|---|---|---|
| `.aoe2campaign` | **42** | `D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign\` (all of them) |
| `.scx` | **50** | `...\resources\_common\drs\gamedata_x2\` (49) + `...\campaign\0_E3_Scenario` sibling |
| `.aoe2scenario` | **3** | game root 1, user profile 2 |
| `.scn` | **0** | none on this machine |
| `.rms` / `.rms2` | 208 / 16 | `...\resources\_common\random-map-scripts\` — separate, **plaintext** format |

Smallest/largest campaign: 297 282 B (`acam1.aoe2campaign`) … 3 688 713 B
(`dcam0.aoe2campaign`). Campaign list: `acam1-4`, `cam2-5`, `coop3,6,9,10,17,22,25`,
`dcam0`, `eecam1-3`, `fcam1-7`, `incam1-3`, `kcam1-3`, `rcam1-4`, `wecam1-3`, `xcam1-3`.

The three `.aoe2scenario` files:

| Path | Size | Version **[V]** |
|---|---|---|
| `D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign\0_E3_Scenario.aoe2scenario` | 57 070 B | 1.35 |
| `C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario` | 209 143 B | 1.53 |
| `C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\7V1变态山谷-炮塔盛宴-变态难.aoe2scenario` | 179 824 B | 1.54 |

Full machine-readable inventory: `_probe\survey_scenario\file_survey.tsv`.

**Mod delivery path [V]:** subscribed mods live at
`C:\Users\26913\Games\Age of Empires 2 DE\<steamid>\mods\subscribed\<pubid>_<name>\` and
**mirror the game's relative tree** (e.g. `...\resources\_common\dat\empires2_x2_p1.dat`).
A scenario mod is therefore "write a `.aoe2scenario` at the mirrored path + an `info.json`" —
the tool can hide paths entirely behind an "Install as mod" action. Note the mod string-table
filename convention `key-value-modded-strings-utf8.txt` differs from the base file's
`key-value-strings-utf8.txt`. **[V]**

---

## 3. Format findings

### 3.1 Container — **[V]**

- **First 4 bytes are a version string, not a magic number.** Observed across all 95
  scenario/campaign files: `1.21`×25, `1.33`×1, `1.35`×6, `1.36`×15, `1.48`×1, `1.51`×1,
  `1.53`×1, `1.54`×3, `2.00`×42. **All 42 campaigns start `2.00`; all `.scx`/`.aoe2scenario`
  start `1.xx`.**
- **Body is RAW DEFLATE** (`zlib.decompressobj(-15)`, no zlib header, no Adler-32).
  Verified at the true stream offset: `wbits=-15` reaches `d.eof == True` with
  `len(d.unused_data) == 0` exactly at EOF; `wbits` 15/31/47 all raise. **No CMF/FLG
  candidates in the first 256 bytes. Compressed but NOT encrypted.**
- **Plaintext header precedes the stream.** For `0_E3_Scenario` (1.35) the header is
  85 bytes, stream offset 85, 56 985 → 316 584 B (5.56×): `0 "1.35"` + `00000000`;
  `+8` `05 00 00 00` (header/save version = 5); `+12` unix ts ~1562419097 (2019-07-06);
  `+16` `01 00 00 00`; `+24` `00 08 00 00` = **2048 (map size in tiles)**; `+28` `00 e8 03 00`
  = 256 000; `+32..` player indices 2–7; `+64` length-prefixed ASCII author `"Freeman1302"`.
- Stream offset varies with header length: 1.21 `.scx` → 28/49/53; later `.scx` →
  65…117; `The Siege` (1.53) → 83; the Chinese 1.54 file → **1185** (many player-name
  strings). **A reader cannot assume a fixed offset — it must find the stream.**
- Inflated body of `0_E3_Scenario`: first `u32` 15648, then `float 1.35`, then player
  civ/name strings at **~256-byte fixed strides** (`Japanese`, `Byzantines`, `Franks`,
  `Aztecs`, `Malians`, `Saracens`, `Burmese`), objective paragraphs, per-player AI
  filenames (`Promisory`, `E3-p2.ai`, `Fe Immobile AI.ai`×6), and then **embedded AI
  script text verbatim** (`(load "Promisory\const")`, `#load-if-not-defined DIFFICULTY-EASIEST`,
  `(defrule ;military`, `(set-strategic-number sn-…)`). 571 ASCII strings ≥ 6 chars in that
  one 1.35 file. **[V]**

### 3.2 Overall structure — **[V]**

Modern scenarios are a sequence of exactly **13 ordered sections**:

```
FileHeader -> DataHeader -> Messages -> Cinematics -> BackgroundImage -> PlayerDataTwo
-> GlobalVictory -> Diplomacy -> Options -> Map -> Units -> Triggers -> Files
```

Field counts per section (v1.54) **[V]**: FileHeader 12 · DataHeader 11 (+1 struct) ·
Messages 12 · Cinematics 3 · BackgroundImage 6 (+1 struct) · PlayerDataTwo 6 (+2 structs) ·
GlobalVictory 11 · Diplomacy 8 (+1 struct) · **Options 61** · Map 18 (+2 structs) ·
Units 5 (+3 structs) · Triggers 11 (+2 structs) · Files 8 (+2 structs).

Public managers on a loaded scenario: `message_manager`, `player_manager`, `map_manager`,
`unit_manager`, `trigger_manager`, `xs_manager`, `option_manager`.

**Terrain is a flat array of tiles**, one `TerrainTile` per square — 20 736 for a 144×144
map (`144²`) — each with `terrain_id`, `elevation`, `layer`, `x`, `y`. Readable and
writable. **[V]**

### 3.3 Campaigns: simpler than expected — **[V]**

- **Uncompressed container.** Scanning the first 4096 offsets of a campaign finds no
  stream starting at the beginning; the members are **complete standalone scenario files
  embedded verbatim and concatenated**.
- Header: `[0:4] = '2.00'`; `[4:8] u32 = 6`; `[8:36]` seven u32 `= (2,3,4,5,6,7,<unix ts>)`;
  `[32:40]` internal ASCII slug (campaign name, e.g. `xcam1`, `dcam0`); then a variable
  prologue listing member filenames (`C1_Attila_1.aoe2scenario` …) and an opaque blob.
- **There IS an index-like structure in the prologue carrying each member's filename and
  its `(span, offset)` — but its layout is NOT uniform across campaigns, and I only decoded
  it for a subset. [V]** For 8 of 42 campaigns (`xcam1`, `eecam3`, `fcam1`, `fcam2`, `fcam4`,
  `incam1`, `kcam2`, `kcam3`) the entries sit at a **64-byte stride ending exactly at the end
  of the prologue**, as `len(prologue) − 64·n`, each entry being
  `<u32 span><u32 offset><u32 const><char name[24]>` with the name then repeated; those 8
  campaigns account for all **54/229** `(span,offset)` pairs that matched my physical scan.
  For the other 34 campaigns that assumption lands mid-string and yields **garbage `const`
  values** (e.g. `coop10` `[540368739, 826671134, …]`, `dcam0` `[3479570, 1634624867, …]`)
  and **0/58** recoverable names. Additionally, **searching the prologue for a `(span,offset)`
  byte pair is unreliable** — a coincidental match exists. **So do not parse the campaign
  prologue; scan for member blobs physically.**
- **Member scan recipe — this is the method that works on 100 % of campaigns [V]:**
  repeatedly find `rb"1\.\d\d\x00\x00\x00\x00"` at or after `pos`, then scan header length `h`
  in `24..400` for a deflate stream with `d.eof == True` and > 1000 B output; member span =
  `h + consumed`; continue at `off + span`.
- **All 42 campaigns scanned → 229 embedded scenarios.** Per-campaign member counts: `fcam7`
  16, `dcam0` 4, most others 5–6; `coop3` and `coop6` were originally under-counted because
  their prologues themselves contain a deflate stream. Embedded versions span **1.36 – 1.59**.
- **222 of the 229 extracted members (96.9 %) then read cleanly under `AoE2ScenarioParser`,
  each in an isolated process. [V]** Readable by version: `1.36` 6, `1.37` 2, `1.40` 1,
  `1.41` 3, `1.42` 1, `1.43` 3, `1.45` 1, `1.46` 4, `1.47` 20, `1.48` 4, `1.49` 10, `1.51` 17,
  `1.53` 4, `1.54` 23, `1.55` 89, `1.56` 6, `1.57` 10, `1.58` 16, `1.59` 2. The **7 failures are
  my extraction boundaries being slightly off, not library gaps** — 6 are
  `EndOfFileError: End of file reached.` (a byte count read past the span) and only one
  (`DE:1.52`) is genuine `UnknownScenarioStructureError`; `1.52` is absent from the library's
  version folders. **[V]**
- **The official content on this machine is large [V]:** across the 222 readable embedded
  members there are **17 552 triggers, 19 782 conditions, 59 701 effects and 1 499 968 placed
  units** — i.e. a tool is facing a real corpus, not toy files.
- **Cross-check confirming the container model:** the user's own
  `The Siege.aoe2scenario` (209 143 B) is byte-for-byte `dcam0`'s 4th member (extracted at
  offset 3 479 570 with span 209 143) — an embedded campaign scenario and a standalone
  saved scenario are the same object. **[V]**
- **In-place editing preserves file size, and the edit survives re-reading: verified.**
  Adding a trigger to `xcam1` member 0 produced 84 739 B against an original 91 684 B span;
  writing `b[:off] + modified + b'\x00'*(span-len(modified)) + b[off+span:]` yields
  `roundtrip\xcam1.padded.aoe2campaign` at exactly **636 022 B = the original size**. Scanning
  that file back finds all 6 members at **identical offsets** `[676, 92360, 213883, 263927,
  356046, 533058]`, member 0 re-reads as **135 triggers with the last one named
  `'PROBE ADDED TRIGGER'`**, and **every other member is byte-identical to the original**.
  So the container's size and offset fields never need patching, and padding with zeros is
  safe. **[V]**
- **`ASP`'s own writer is ~7–8 % smaller** (it drops editor padding): `xcam1`'s 6 members
  re-serialized 635 346 → 585 238 B = **92.11 %**, all 6 OK. **[V]**
- **Output is byte-reproducible once the output filename is fixed** — but `ASP` **sets the
  scenario's internal name from the output filename on write** (`The Siege` → `gen3`), which
  is also the in-game scenario name. Real gotcha for any tool. **[V]**

### 3.4 Trigger vocabulary lives in the game's string table, not in widgetui — **[V]**

- Authoritative name/id list:
  `D:\Games\Steam\steamapps\common\AoE2DE\resources\en\strings\key-value\key-value-strings-utf8.txt`
  (2 012 476 B, 19 679 `id "string"` pairs). One parallel file per language with **identical
  ids**, so the table is language-independent.
- **Mapping to the library's enum index is exactly linear [V]:**
  **conditions `game_id = 10500 + n`**, **effects `game_id = 11550 + n`**.
  Conditions: 35/41 names match exactly; the 6 exceptions are cosmetic renames plus `[None]`
  (e.g. idx 29 `OR` vs `"Condition Separator"`). Effects: 98/103 match; exceptions are
  `[None]` at idx 0 and four renames (`DISABLE_UNIT_TARGETING` vs `"Disable Unit Targetable
  State"`). Effect ids run 11550–11659; condition ids 10500–10580, with 10531–10553 genuinely
  unused holes. **No guessed mapping is needed — a tool can show the game's own localized
  trigger wording.**
- **The in-game editor UI does NOT carry the vocabulary.** `widgetui\editorbottomtriggerspanel.json`
  is the single largest UI file in the game at **1 241 730 B**, but it contains **zero**
  `StringId` keys and no trigger/condition/effect ids — pure layout/atlas data. **[V]**
- Help text is in the same table at higher ids (e.g. id 30691
  `"Select the player ID to change ownership to."`), so per-field explanatory strings are
  **already localized and available**. **[V]**

---

## 4. User-meaningful concepts

Everything below was confirmed present on real official scenarios. **[V]**

| Beginner concept | Where it really lives | Notes |
|---|---|---|
| **Objectives / mission goals** | NOT a separate table — **triggers** with `display_as_objective=1` | `xcam1_0` has **10** objective triggers, ids 13/102/103/105 etc. Text may be inline (`short_description`) with `<VariableName>` placeholders **or** a string-table id (`short_description_stid`) |
| **Messages / dialogue** | `Display Instructions` (**effect_type 20**) `message` field, + `display_time` (seconds), + `sound_name` | **51** such effects in `xcam1_0`; rich-text markup is inline: `'<PURPLE>Bleda the Hun: …'`, `'<YELLOW>…'`; `'Play_a1a'` |
| **Briefing panels** | `Messages` section: `instructions`, `hints`, `victory`, `loss`, `history`, `scouts`, `instructions_string_table_id` | On the official Attila scenario the first four are **empty** while `hints`/`scouts` hold long prose → the "briefing" a player sees is not where a naive tool would look |
| **Units placed on the map** | `Units` section, 9678 units on `The Siege` (7831 of them GAIA) | Each has `unit_const`, `x`, `y`, `z`, `tile`, `reference_id`, `rotation`, `status`, `name`, `caption_string`, `player`, `garrisoned_in_id` |
| **Players / civs / colors** | `PlayerDataTwo` | `active`, `civilization`, `architecture_set`, `color`, `tribe_name`, `population_cap`, `starting_age`, `food`/`wood`/`stone`/`gold`, `human`, `diplomacy[16]`, `disabled_units/techs/buildings`, `initial_camera_x/y` |
| **Start positions / camera** | player record `initial_camera_x/y`, `initial_player_view_x/y` | On Attila player 1: camera (132, 18), view (128, 43) |
| **Map size** | `Map` section `map_size` (int) | 80 (empty default), 144, 168, 200, 220, 240 observed |
| **Terrain** | `Map` section `terrain`, a flat `UuidList` of `map_size²` tiles (`terrain_id`, `elevation`, `layer`) | 20 736 tiles at 144×144; fully readable/writable |
| **Victory conditions** | `GlobalVictory` section | `conquest_required=1`, `ruins`, `artifacts_required`, `discovery`, `explored_percent_of_map_required`, `gold_required`, `all_custom_conditions_required`, `mode`, `required_score_for_score_victory=14000`, `time_for_timed_game_in_10ths_of_a_year=9000`; plus `Options.victory_condition` (`STANDARD`/`CONQUEST`/`SCORE`/`TIME_LIMIT`/`CUSTOM`/`SECONDARY_GAME_MODE`), `victory_score`, `victory_years=900.0` |
| **AI scripts** | `Files` section: `number_of_ai_files`, `ai_files[]`, `ai_files_present`, `ai_error[]` | **Embedded in the scenario** — no need to touch the game's `ai\` folder. Also seen embedded as raw text in the inflated body |
| **XS scripting** | `xs_manager.xs_trigger` — a normal trigger named `'XS SCRIPT'`, `enabled=False`, holding one `Script Call` effect | XS is smuggled as a single effect inside an auto-generated disabled trigger, **not** a separate file section |
| **Difficulty** | `DifficultyLevel` enum on conditions of type 18 | **Inverted encoding:** `EASIEST=4, STANDARD=3, MODERATE=2, HARD=1, HARDEST=0, EXTREME=-1`. **0 occurrences of a difficulty condition in five real official scenarios** (`xcam1_0`, `xcam1_1`, `acam1_0`, `fcam7_0`, `dcam0_3` — 347 triggers total) — official content varies difficulty via AI scripts (`AoF scenario difficulty.per`), not difficulty conditions |
| **Diplomacy / teams** | `Diplomacy` section + `Options.lock_teams`, `Options.allow_players_choose_teams`, `PlayerManager.set_diplomacy_teams` | |

### The schema a form generator needs already exists in machine-readable form **[V]**

Each supported version ships `conditions.json` and `effects.json` where every entry is
`{"name": …, "attribute_presentation": {<field>: <type-or-enum-name>}}`. The `-1` entry is a
"default attribute value presentation" listing **every possible field and its type** — for
effects: `effect_type, ai_script_goal, armour_attack_quantity, armour_attack_class→DamageClass,
quantity, tribute_list→Attribute, diplomacy→DiplomacyState, object_list_unit_id→UnitInfo,
source_player/target_player→PlayerId, technology→TechInfo, string_id, display_time,
trigger_id→TriggerId, location_x, location_y, location_object_reference→Unit, area_x1..area_y2,
group/type, instruction_panel_position→PanelLocation, attack_stance, time_unit, enabled→bool,
food, wood, stone, gold, item_id, flash_object, force_research_technology, visibility_state,
scroll, operation→Operation, object_list_unit_id_2, button_location→ButtonLocation,
ai_signal_value, object_attributes→ObjectAttribute, variable`.

A generated form can therefore label and type every field **without hardcoding anything**.
Caveat that matters for UI: **unused fields read as `-1`, not `0`** — a blank field is `-1`. **[V]**

### Trigger object surface **[V]**

Real triggers expose `name`, `description`, `short_description`, `header`, `enabled`,
`looping`, `display_as_objective`, `display_on_screen`, `mute_objectives`, `execute_on_load`,
`trigger_id`, `description_stid`, `short_description_stid`, `conditions`, `effects`,
`condition_order`, `effect_order` (both lists), `description_order` (**an int, not a list**),
and `new_condition`/`new_effect`/`remove_condition`/`remove_effect`.

**Two real editing hazards [V]:**
1. **Display order ≠ storage order.** `trigger_display_order` on `xcam1_0` is
   `[97, 22, 78, 94, 98, 12, 2, 3, 7, 0, 1, …]` — a true permutation of `range(134)` but not
   identity. On `The Siege` it is `[0..21, 24, 22, 23, 25..29, 32, 30, 33, 31, …]`. A tool
   that presents triggers in storage order shows the player an order the game does not use.
2. **Trigger count and complexity are real, not toy.** `xcam1_0`: **134 triggers, 158
   conditions, 329 effects, 5431 units, map 144**. `The Siege`: 89 triggers, 244 effects,
   **9678 units**. Effect usage skews hard: type 8 (Activate Trigger) 86×, 20 (Display
   Instructions) 36×, 12 (Unload) 33×, 9 (Kill Object) 33×. Only **15 distinct condition
   types and 24 distinct effect types** are used across 134 triggers — a UI that surfaces
   the top ~25 of each would cover real content.

### Enum vocabulary already available for a UI **[V]**

`ActionType, Age, AttackPriority, AttackStance, Attribute (**601** members), BlastLevel,
BlockageClass, ButtonLocation, CaptureFlag, ChargeEvent, ChargeType, ColorMood, CombatAbility,
Comparison, DamageClass, DecisionOption, DifficultyLevel, DiplomacyState, DisableUnitFlag,
FogVisibility, GarrisonType, HeroStatusFlag, Hotkey, Literal, LocalTechnology, ObjectAttribute,
ObjectClass (64), ObjectModifyAttributeState, ObjectState (9), ObjectType (4), ObstructionType,
OcclusionMode, Operation, PanelLocation, ProjectileHitMode, ProjectileSmartMode,
ProjectileVanishMode, SecondaryGameMode, SelectionEffect, TechnologyState (6),
TerrainRestrictions, TimeUnit, UnitAIAction (25), UnitTrait, VictoryCondition (6),
VictoryTimerType, VisibilityState` — plus `TerrainId` with **131** members.

---

## 5. Existing tooling

| Name | URL | License | Last activity | Read/Write | Completeness | Maintenance risk |
|---|---|---|---|---|---|---|
| **AoE2ScenarioParser** | https://github.com/KSneijders/AoE2ScenarioParser | **GPL-3.0** (PyPI metadata wrongly says MIT — conflict unresolved) | **pushed 2026-10-03**, commits 2026-10-02, 105★, 15 forks, 4 open issues | **Both**; read verified on real files; write verified (round-trip 92.11 % and byte-stable from gen 2) | **High.** All 13 sections; triggers/conditions/effects/units inspect+add+edit+remove; map/campaign; 24 version folders 1.36–1.59; per-version JSON schema; 229 campaign members readable once extracted | **Low.** Actively maintained by the original author since 2019, with a second maintainer for datasets. **No GitHub Releases** — distribution is PyPI + git tags |
| AoE2TriggerCraft2 | https://github.com/MegaDusknoir/AoE2TriggerCraft2 | GPL-3.0 | pushed 2026-10-09, 7★, 1 fork | Both (via the library) | "A packed GUI python tool for edit AoE2DE scenario, based on AoE2ScenarioParser" — **the nearest existing competitor; a GUI on the same parser** | Medium — one maintainer, young (created 2025-07) |
| AoE2TriggerCraft (C++) | https://github.com/MegaDusknoir/AoE2TriggerCraft | GPL-3.0 | pushed 2025-08-03, 6★ | Both | Older C++ editor | **Dead — archived** |
| aoe2-probe | https://github.com/ptazithos/aoe2-probe | MIT | pushed 2024-05-31, 4★ | Read/write (Rust) | Rust scenario library | Stale |
| aoe2scenario (Rust) | https://github.com/juliamauri/aoe2scenario | AGPL-3.0 | pushed 2026-10-01, 0★ | Both | New, 118 KB, 1 open issue | Immature |
| ZetaTwo/AoE2ScenarioParser | https://github.com/ZetaTwo/AoE2ScenarioParser | none stated | pushed 2022-03-15, 1★ | Spec only (Kaitai Struct) | Format description, not a tool | **Dead — archived** |
| AoE2ScenarioEditor | https://github.com/newtonerdai/AoE2ScenarioEditor | GPL-3.0 | pushed 2021-05-24, 0★ | Both | One week of life, 39 KB | **Abandoned** |
| AoE2ScenarioObfuscator | https://github.com/TrickyDeath/AoE2ScenarioObfuscator | MIT | pushed 2026-10-06, 1★ | Write only | Obfuscates trigger text only | Low relevance |
| Official in-game **Scenario Editor** | ships with the game | proprietary | current | Both | Full editor: `widgetui\editorbottom*panel.json` (triggers panel alone is 1.24 MB), `dialogscenarioeditormenu.json`, campaign editor, slideshow editor | N/A — but it is a power-user tool that exposes raw field names, and is exactly what a beginner-friendly tool has to beat on *approachability*, not features |
| `Scenarioforge` | — | — | — | — | — | **Does not exist for AoE2**; every GitHub hit is an unrelated project (Salesforce/finance/cyber-range). Earlier notes referencing it should be disregarded |

**What a new tool would actually add.** The format work is done and the write path is
proven, so a new tool competes on **UX**, not on parsing: hiding the 13-section model, the
13 000-field enum space, the `-1`-means-empty convention, the display-vs-storage order
permutation, and the inverted difficulty encoding. The in-game editor already does
everything a power user needs, and `AoE2TriggerCraft2` is a GUI over the same library — but
neither is written for a first-time modder. **[I]**

---

## 6. Difficulty ratings

| Task | Rating | Justification |
|---|---|---|
| **Read an existing scenario** | **Low** | Nothing is encrypted: raw deflate behind a short plaintext header. `AoE2ScenarioParser` reads real files in a median **1.38 s**, and its per-version JSON schema describes every field. **222 of 229 embedded campaign members parse once extracted.** The only reason this is not trivial: 32 of 53 standalone files on disk (v1.21/1.33/1.35) are **outside the library's supported range** and would need either a legacy reader or a graceful "this scenario is too old to edit" path — note 6 of 7 campaign-member failures were my own extraction-boundary error, not the library. **[V]** |
| **Edit an existing scenario** | **Low–Medium** | The write path works and is deterministic: re-serialization is byte-stable from generation 2, and **in-place edits to a campaign member preserve the whole file's size exactly** (636 022 B in, 636 022 B out) so none of the container's size/index fields need patching. The Medium comes from *semantics*, not bytes: display order ≠ storage order, `-1` means empty, and difficulty is inverted. And one hard operational rule: **one scenario version per process** — the library monkey-patches classes per version and never restores them, so mixing versions corrupts later loads and writes. **[V]** |
| **Create a new scenario from scratch** | **Medium** | Seeding works from a bundled template, but **only for v1.54+** (`from_default` succeeds for 1.54/1.57/1.58/1.59 and raises `UnknownStructureError: A default scenario file could not be found for version: DE:<v>` for 1.36/1.40/1.46/1.48/1.53) — a hard floor on any "new scenario" feature that targets old versions. After seeding, a scenario is trivially valid (map 80, 0 triggers). The real work is **terrain**: a from-scratch map means authoring `map_size²` tiles (6 400 at 80×80, 57 600 at 240×240) unless the tool starts from a real template scenario. **[V]** |

**Single biggest blocker overall: scenario-version coverage in the one library worth reusing.**
It is not a format problem — it is that versions before 1.36 are simply *absent* from the
library (no `v1.21`/`v1.33`/`v1.35` folders, no default templates below 1.54), and that
appears to be a maintenance decision, not an oversight. Every old file on this machine is
unreadable today.

**Is this a good first feature?** **Yes, with one scoping rule.** It is a good first feature
because the format risk is retired: raw deflate, an established GPL library, a verified
write path, and a verified in-place campaign edit. Scope it as **"edit an existing 1.36+
scenario"**, not "build a scenario from nothing" — that dodges the terrain-authoring cost and
the pre-1.54 template floor. Two things must be decided before code: (1) the **GPL-3.0**
question, since linking the library makes the combined work GPL; (2) the **one-version-per-process**
constraint, which dictates the tool's process architecture (worker process per scenario) and
is easy to violate accidentally. **[I]**

---

## 7. Unknowns

| Unknown | What would settle it |
|---|---|
| **Exact semantics of the campaign prologue** beyond the 64-byte index entries — the opaque variable blob between the name list and the index, and the `const` field (`0x00180a60`) that is not a filename length | Dump and diff the prologues of several campaigns with the same member count, and correlate the blob against `resources\_common\campaign\<cam>.json` + `<cam>_layout.json` (plaintext, 20 244 / 22 467 B for `xcam1`) |
| **Whether the game accepts a re-serialized member** — every check so far is *parser*-level, never in-game | Load `roundtrip\xcam1.padded.aoe2campaign` in the game (read-only w.r.t. the game tree: copy it into a local mod folder first) and confirm the added trigger appears and the campaign plays |
| **The 1.21/1.33/1.35 legacy layout** — no structure description exists in the library or in the game's `Docs\` (which holds only manuals/EULAs). `0_E3_Scenario` inflates fine, but its internal layout is mapped only partially (256-byte player strides, embedded AI text) | Extend `probe_header.py`/`header_layout.py` to fully walk a 1.21 `.scx`; the Kaitai spec in the archived `ZetaTwo/AoE2ScenarioParser` is the only external lead and is unverified |
| **The `coop3`/`coop6` prologue streams and `kcam1`'s unexplained 52 612-byte trailing tail** | Inflate those prologues and identify what they contain; check whether the tail is a scene/`ureP`-like blob |
| **The true license** — GitHub `LICENSE` is GPL-3.0 (35 149 B) while PyPI classifiers claim MIT | Ask the maintainer (Discord https://discord.gg/DRUtmugXT3) or open an issue; until then treat as GPL-3.0 |
| **Whether the cross-version bug is fixable from outside** — the library's own TODO at `retriever_object_link.py:81-84` says properties "don't get reset" and neither does resetting them work | A worker-process-per-scenario design sidesteps it; a real fix would need upstream changes |
| **Non-English display of trigger names** — verified the id table is language-independent and 16 language files exist, but I did not confirm that the in-game UI uses these exact strings for the trigger dropdowns | Compare a non-English client's editor labels against `resources\<lang>\strings\key-value\key-value-strings-utf8.txt` ids 10500+/11550+ |
| **Whether `.aoe2campaign` can carry non-scenario assets other than the 1 `.aoe2scenario` and 17 `.gpv` previews** found loose in `resources\_common\campaign\` | Inspect a campaign whose loose assets are missing (e.g. a DLC campaign) and see what the game loads instead |
| **`condition_type == 18` (Difficulty Level) is unused in `xcam1_0`** — I sampled only a few scenarios, so "official content prefers AI-script difficulty" is a small-sample claim | Count condition type 18 across all 229 extracted members |

Every script referenced above is retained under
`D:\Software\DeepSeek Harness\工作区2\_probe\survey_scenario\` for reproducibility.
