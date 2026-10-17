# AoE2DE Random Map Scripts (.rms) and AI Scripts (.per/.per2/.ai/.xs) — Survey

**Target:** Age of Empires II: Definitive Edition, version `101.103.54800.0` (Steam appid 813780, buildid 25464371)
**Game root:** `D:\Games\Steam\steamapps\common\AoE2DE`
**User profile:** `C:\Users\26913\Games\Age of Empires 2 DE`
**Purpose:** inform a beginner-facing mod-making tool in which "the user must never see field names, file paths, or raw formats".
**Method:** direct read-only inspection of every shipped RMS/AI artifact; counts produced by two purpose-built analyzers (`analyze_rms.py`, `analyze_ai.py` in this directory) that strip comments before tokenizing; official legacy documentation extracted from the shipped `.doc` files; error vocabulary extracted from string tables inside `AoE2DE_s.exe`. Evidence grades are marked **[V]** verified by inspection, **[D]** documented, **[I]** inferred.

---

## 1. Bottom line

**RMS (random map scripts) — viable, and the friendlier of the two halves.**
- **[V]** 208 `.rms` + 16 `.rms2` + 87 `.inc` files ship, all pure ASCII, all CRLF, **zero** non-ASCII bytes and zero BOM across 311 analyzed files. The format is a flat, line-oriented command list with seven section headers, 131 distinct commands total, and 4 preprocessor directives. **[V]** Any text editor + a text diff is a complete toolchain; no binary container, no compilation step.
- **[V]** The real working vocabulary is small and heavily skewed: the top 20 of 131 commands cover 229,027 of 320,459 occurrences (71.5%), and the top 50 cover 94.6%. A UI that exposes ~40 abstract "map dials" (land amount, terrain, forest density, cliff count, resource counts/distances, map size) is enough to generate or edit very large classes of maps.
- **[V]** A beginner-facing UI already has a ready-made display vocabulary: `resources\_common\dat\maps.json` holds **194** map entries with `style` (random 143 / "real world" 29 / special 22), plus boolean tags `open` 98, `land` 91, `mixed` 75, `water` 18, `nomad` 18, `closed` 14, `migration` 13, `battle_royale` 5; and `name_string_id`/`rollover_string_id` resolve to localized strings (`10875 "Arabia"` / `10875 "阿拉伯半岛"`). Every one of those 194 correlates 1:1 with a script file that exists on disk (**0 missing**).
- **[V]** The hard part is not the format, it is **spatial correctness**: land → elevation → terrain → cliffs/connections → objects is a fixed one-pass pipeline, and the official guide states outright that "The map generator does not try several iterations until it creates a map that works—if there is not enough space for boar for player 2, then player 2 will not have any boar." A generator that emits valid syntax can still emit a broken map. That risk is invisible to the user and must be absorbed by the tool (templates + parameter bounds, not free-form synthesis).
- **[V]** No RMS editor ships with the game. Community tooling exists but is documents/websites, not an embedded editor: Zetnus' RMS Guide (linked from the AoE2DE UGC Guide's RMS page), `aoe2map.net`. Validation is **client-side only** — the game writes no script diagnostics to disk.

**AI scripts — viable only as a bounded "settings" surface, not as a general authoring surface.**
- **[V]** `.ai` is a **0-byte marker**, always. All 3 shipped `.ai` files are empty, and each one is paired with a same-named `.per`/`.per2` (`AI (HD version).ai` → `AI (HD version).per` 1,170,991 B; `E3-p2.ai` → `E3-p2.per` 2,139 B; `randomgame.ai` → `randomgame.per2` 1,174 B). The official guide states this verbatim: "An empty text file with an .AI extension … should be created to make an entry appear in the list of computer players and in the scenario editor. … **You must have both a .PER and an .AI file with the same name for your script to function!**" **[D]** So "create an AI" is trivially two files, one of them empty — perfectly hideable.
- **[V]** `.per` and `.per2` are **the same language**: a Lisp-like s-expression rule language — `;` comments, `(defconst name value)`, `(defrule (condition…) => (action…) …)`, `(disable-self)`, and the preprocessor `#load-if-defined SYMBOL / #load-if-not-defined / #else / #end-if`. `.per2` is not a new format; it is the PromiDE-era file set under `gamedata_x2` with a different extension. 91 `.per` + 30 `.per2` files, 15,554 `defrule` and 30,174 `defconst` occurrences, 120 distinct directives in real use.
- **[V]** `.xs` is a genuine C-like scripting language (`//` comments, `void f() { xsEffectAmount(4,900,9,-735,8); }`, `extern const int cAttributeFood = 0;`), auto-includes `Constants.xs` (1,175 `extern const` declarations), and is **the only one of the three that is actually programming** rather than configuration.
- **[V]** Beginner intent splits cleanly. "Make the AI more aggressive / build more walls / train more archers / don't rush" are, in practice, **strategic-number assignments** — one-line constant tweaks in a `(defrule (true) => (set-strategic-number …) (disable-self))` shell. The shipped AiBuilder does exactly this for its whole aggression block. A UI that only ever emits `set-strategic-number`, `set-goal`, and `defconst` lines inside a fixed rule skeleton never has to show a field name, a condition, or a rule arrow. Anything beyond that (custom build orders, scouting logic, target selection) is real programming in a 120-directive language with a 139-name strategic-number namespace.
- **[V]** Failure reporting is thin and not machine-readable: the AI parser emits `AI file Error: '%s' Line %d` as an **in-game modal dialog** with documented codes ERR2001–ERR9001; the RMS parser emits `(RandomMapSync) ERROR: %s, unrecognized command ignored`-style messages plus an internal `RMS_ERROR_POPUP` flag. **[V]** `MainLog.txt` records only `Initializing Random Map File Type` / `Initializing Error Handler` and their terminating counterparts — **zero** parse errors in any session log. A tool therefore cannot read back what the game thought; it must validate before the game ever runs.

**What differs from other mod types.** Both RMS and AI are *plain text, self-contained, hot-swappable, and log-silent*. There is no asset pipeline, no DAT editing, no sprite/sound work — unlike the shipped `Tools_Builds\AdvancedGenieEditor3.exe`, whose own readme mentions no `.rms`/`.per`/`.ai`/`.xs` content at all. But they differ from each other in one decisive way: **RMS is declarative data with no control flow beyond `if`/`start_random`**, so a parameter-space UI is a faithful model; **AI is an imperative rule engine**, so a parameter-space UI is only faithful for the constant-tuning subset. RMS is the natural first target.

---

## 2. RMS: inventory

### 2.1 Counts by extension (game root, recursive) — [V]

| Ext | Files | Total bytes | Min | Max | Zero-byte |
|---|---|---|---|---|---|
| `.rms` | 208 | 11,399,881 | 80 | 936,628 | 0 |
| `.rms2` | 16 | 1,378,851 | 7,238 | 513,539 | 0 |
| `.inc` | 87 | 1,072,770 | 4 | 165,791 | 0 |
| `.def` | 1 | 48,803 | — | — | 0 |

### 2.2 Where they live — [V]

| Root | `.rms` | `.rms2` | `.inc` | note |
|---|---|---|---|---|
| `resources\_common\drs\gamedata_x2` | 180 | 16 | 81 | the main official map set |
| `modes\Pompeii\resources\_common\drs\gamedata_x2` | 28 | 0 | 6 | Return-of-Rome-scoped overlay |
| **Total** | **208** | **16** | **87** | |

Subfolders: `resources\_common\drs\gamedata_x2\includes\` holds **54** `.inc` fragments (the shared library); the remaining `.inc` files sit flat in `gamedata_x2`.

**Critical correction to the brief.** **[V]** `D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\random-map-scripts\` **exists but is empty** (`os.listdir` → `[]`). The path is still present as a string in the executable (offset 52398138, alongside `resources\_common\terrain\`, `resources\_common\textures\`, …), and the legacy guide says scripts "must be placed in the RANDOM directory" **[D]**. In the shipped DE build, however, every map comes from the DRS overlay path above. A tool that writes to `random-map-scripts\` writes to a directory the shipped game does not read from.

### 2.3 Size / complexity extremes — [V]

- Smallest real maps after the stubs: `Blind_Random.rms` 1,269 B.
- Largest: `Arena.rms` 936,628 B; `Stranded.rms` 606,793 B; `MountainRange.rms` 508,239 B; `The_Passage.rms` 238,142 B; `Sandrift.rms` 238,131 B.
- Most lines: `Megarandom.rms2` 27,907 lines / 513,539 B; `MountainRange.rms` 23,556; `PMegarandom.rms` 18,166 / 341,137; `The_Passage.rms` 9,571; `Sandrift.rms` 9,402.
- `.rms2` set (16, all in `gamedata_x2`): `acropolis` 14,559; `budapest` 8,520; `cenotes` 26,349; `cityoflakes` 7,493; `CtR Monsoon` 172,823; `CtR Pyramid Descent` 171,882; `CtR Random` 173,652; `CtR Spiral` 171,668; `goldenpit` 19,171; `hamburger` 14,586; `hideout` 8,988; `hillfort` 18,432; `lombardia` 7,238; `Megarandom` 513,539; `steppe` 39,317; `valley` 10,634.

### 2.4 Authoritative index — `maps.json` — [V]

`resources\_common\dat\maps.json` (128,394 B), `map_list` = **194** entries. `script_filename` resolves to **178 `.rms` + 16 `.rms2`**, and **0 are missing on disk** relative to `gamedata_x2`. Per-key coverage:

`data_name`/`name_string_id`/`rollover_string_id`/`icon_reference`/`map_icon_filename`/`script_filename`/`storage_id`/`style` = 194 each; `random_map` 186; `regicide` 185; `death_match` 176; `empire_wars` 176; `wonder_race` 161; `const_name` 160; `sudden_death` 160; `king_of_the_hill` 111; `capture_the_relic` 107; `defend_the_wonder` 100; `open` 98; `land` 91; `mixed` 75; `scenario_filename` 50; `water` 18; `nomad` 18; `closed` 14; `migration` 13; `mappool_icon_filename` 7; `battle_royale` 5; `prohibited_game_mode` 1.

Example (`arabia`), verbatim keys: `{"const_name":"arabia","data_name":"ARABIA-MAP","name_string_id":10875,"rollover_string_id":30110,"icon_reference":"IconArabia","map_icon_filename":"rm_arabia","script_filename":"Arabia.rms","storage_id":9,"style":"random","land":true,"open":true,"random_map":true,"death_match":true,"regicide":true,"king_of_the_hill":true,"capture_the_relic":true,"sudden_death":true,"defend_the_wonder":true,"wonder_race":true,"empire_wars":true}`

`style` distribution: `random` 143, `real world` 29, `special` 22. `scenario_filename` (50 entries, e.g. `real-world-spain`, `real-world-england`) marks entries that are scenarios, not RMS.

### 2.5 The shared include library — [V]

`gamedata_x2\includes\` (54 files). Largest: `themes.inc` 117,961; `forest.inc` 92,163; `constants.inc` 57,235; `starting_resources.inc` 52,171; `herdable_starting.inc` 36,353; `huntable.inc` 20,458; `mainland.inc` 20,160; `water_blending.inc` 19,032; `helpers.inc` 18,542. Notable small ones: `town_centres.inc` 328; `empire_wars.inc` 242; `starting_objects.inc` **4 B** (blank); `thebr_setup.inc` 46 B.

Scattering of `#include_drs` across the corpus — [V]: `includes/predators.inc` included by **47** files; `huntable.inc` by 54; `starting_resources.inc` by 55; `forest.inc` by 13. `land_resources.inc` and `std_resources.inc` are included by 0 files (top-level fragments).

### 2.6 Constant library — `random_map.def` — [V]

`gamedata_x2\random_map.def`, 48,803 B / 1,557 lines / **1,431 `#const`**. This is the machine-readable name→ID table the `.rms` text depends on. Family prefixes: `ATTR` 235, `DLC` 180, `CIVILIZATION` 66, `AMOUNT` 34, `REAL` 29, `TREE` 26, `VILLAGER` 25, `ELITE` 24, `SPECIAL` 22, `WD` 21, `CC` 19, `GAIA` 14, `WILD` 12, `MOUNTAIN` 10, `TOWN` 9, `STRING` 9, `YURT` 8, `EM` 7. Useful resolved values: `WOLF 126`, `WOLF_HILL 126`, `DIRE_WOLF 89`, `RABID_WOLF 202`, `HUNTING_WOLF 700`, `BOAR 48`, `WILD_BOAR 48`, `IRON_BOAR 810`, `DEER 65`, `SHEEP 594`, `FORAGE 59`, `GOLD 66`, `GOLD_MINE 66`, `STONE 102`, `TOWN_CENTER 109`, `VILLAGER 83`, `CASTLE 82`, `RELIC 285`, `FOREST_TREE 411`, `OAKTREE 349`, `PINETREE 350`, `PALMTREE 351`, `BAMBOO_TREE 348`, `SHORE_FISH 69`, `FISH_PERCH 53`, `FISH_SALMON 456`, `FISH_DORADO 455`. Note the file also carries **commented-out duplicates** (`/* #const DEER 65 */`, `/* #const WOLF 126 */`) — a parser must strip block comments or it will double-register.

---

## 3. RMS: syntax

### 3.1 Shape of the language — [V] verified from corpus, [D] where the guide agrees

A `.rms` file is **line-oriented plain text, case-sensitive**, in this order:

1. Optional preamble of `#const` / `#define` / `#include_drs` / `if…endif` (theme selection, scaling).
2. Seven **section headers**, each on its own line, in angle brackets, in this generation order — **[D]** "A Random Map starts with Land first, then Elevation, then Terrain, and finally Cliffs and Connections. The order is important."
   `<PLAYER_SETUP>` → `<LAND_GENERATION>` → `<ELEVATION_GENERATION>` → `<CLIFF_GENERATION>` → `<TERRAIN_GENERATION>` → `<OBJECTS_GENERATION>` → `<CONNECTION_GENERATION>`
3. Inside sections: `command value…` lines, optionally followed by a `{ … }` brace block of sub-commands.
4. `{` and `}` **must be on their own line** — **[D]** verbatim: "Braces {} enclose commands under specific instruction. Opening and closing braces must be on their own line." (The guide's own annotated example violates this cosmetically by putting `{` after `create_player_lands `, so treat the statement as descriptive of intent, not as a parser rule — **[V]** the corpus always puts braces on their own line.)

### 3.2 Section usage across the corpus — [V]

| Section | Occurrences | Files using it |
|---|---|---|
| `<TERRAIN_GENERATION>` | 382 | 216 |
| `<PLAYER_SETUP>` | 380 | 216 |
| `<LAND_GENERATION>` | 330 | 166 |
| `<ELEVATION_GENERATION>` | 280 | 192 |
| `<OBJECTS_GENERATION>` | 216 | 216 |
| `<CONNECTION_GENERATION>` | 125 | 78 |
| `<CLIFF_GENERATION>` | 89 | 85 |

216 files contain at least one section; 95 files contain **zero** sections — these are the `.inc` fragments plus the one-line `EM *.rms` stubs. Section counts per file: 6 sections = 90 files, 4 = 46, 5 = 36, 7 = 27, 3 = 9, 8 = 1, 10 = 1. (Counts of 65 and 202 occur 4 and 2 times respectively: files that re-open sections, e.g. `if/else` branches that each restate `<TERRAIN_GENERATION>`.)

### 3.3 Directives — [V]

| Directive | Occurrences | Files |
|---|---|---|
| `#const` | 50,052 | 230 |
| `#define` | 13,281 | 236 |
| `#include_drs` | 3,319 | 198 |
| `#undefine` | 1 | 1 |

`#const NAME value` defines a numeric/symbol constant (value may be an expression: `#const MAPSCALE_SIDE (MAPSIZE_SIDE / MAPSIDE_BASE)`, `#const CONFINED_INCREASE 1.2`). `#define NAME` defines a boolean flag; the corpus reuses it for random map themes. `#include_drs path/to/file.inc` inlines a fragment, **forward slashes**, optionally followed by a numeric DRS id (`#include_drs Arabia.rms 54201`). `#undefine` appears exactly once.

### 3.4 Full frequency-ranked command table (131 commands, 320,459 occurrences) — [V]

| # | Command | Count | # | Command | Count | # | Command | Count |
|---|---|---|---|---|---|---|---|---|
| 1 | `avoid_actor_area` | 28922 | 45 | `left_border` | 1335 | 89 | `building_architecture` | 72 |
| 2 | `elseif` | 19145 | 46 | `group_placement_radius` | 1243 | 90 | `cliff_type` | 70 |
| 3 | `endif` | 17698 | 47 | `other_zone_avoidance_distance` | 1202 | 91 | `enable_waves` | 68 |
| 4 | `if` | 17697 | 48 | `terrain_cost` | 1167 | 92 | `layer_to_place_on` | 67 |
| 5 | `create_terrain` | 14299 | 49 | `replace_terrain` | 1155 | 93 | `group_variance` | 60 |
| 6 | `number_of_clumps` | 13394 | 50 | `border_fuzziness` | 1130 | 94 | `resource_delta` | 58 |
| 7 | `percent_chance` | 13118 | 51 | `min_distance_to_map_edge` | 1045 | 95 | `water_definition` | 57 |
| 8 | `base_terrain` | 12079 | 52 | `clumping_factor` | 1039 | 96 | `require_path` | 54 |
| 9 | `land_percent` | 11981 | 53 | `circle_radius` | 1024 | 97 | `set_facet` | 50 |
| 10 | `create_object` | 10262 | 54 | `height_limits` | 976 | 98 | `find_closest_to_map_center` | 47 |
| 11 | `number_of_objects` | 9491 | 55 | `assign_to` | 965 | 99 | `create_connect_teams_lands` | 43 |
| 12 | `create_land` | 8728 | 56 | `set_scaling_to_map_size` | 862 | 100 | `set_circular_base` | 37 |
| 13 | `else` | 8501 | 57 | `set_scale_by_size` | 796 | 101 | `min_length_of_cliff` | 33 |
| 14 | `actor_area_radius` | 7509 | 58 | `terrain_size` | 774 | 102 | `max_length_of_cliff` | 33 |
| 15 | `number_of_tiles` | 7403 | 59 | `land_id` | 754 | 103 | `behavior_version` | 31 |
| 16 | `actor_area` | 6840 | 60 | `set_tight_grouping` | 732 | 104 | `min_distance_cliffs` | 30 |
| 17 | `set_gaia_object_only` | 5852 | 61 | `zone` | 679 | 105 | `direct_placement` | 30 |
| 18 | `effect_amount` | 5722 | 62 | `ai_info_map_type` | 540 | 106 | `add_object` | 28 |
| 19 | `set_place_for_every_player` | 5486 | 63 | `create_elevation` | 462 | 107 | `override_actor_radius_if_required` | 26 |
| 20 | `base_size` | 4900 | 64 | `set_loose` | 457 | 108 | `cliff_curliness` | 24 |
| 21 | `min_distance_to_players` | 4593 | 65 | `set_loose_grouping` | 421 | 109 | `set_scaling_to_player_number` | 22 |
| 22 | `spacing_to_other_terrain_types` | 4548 | 66 | `random_placement` | 395 | 110 | `avoid_other_land_zones` | 22 |
| 23 | `temp_min_distance_group_placement` | 4435 | 67 | `beach_terrain` | 380 | 111 | `create_connect_all_lands` | 21 |
| 24 | `min_distance_group_placement` | 4008 | 68 | `create_player_lands` | 368 | 112 | `override_map_size` | 18 |
| 25 | `set_scale_by_groups` | 3717 | 69 | `color_correction` | 339 | 113 | `find_closest_to_map_edge` | 17 |
| 26 | `end_random` | 3414 | 70 | `set_circular_placement` | 317 | 114 | `create_connect_to_nonplayer_land` | 14 |
| 27 | `start_random` | 3413 | 71 | `place_on_forest_zone` | 285 | 115 | `land_conformity` | 14 |
| 28 | `max_distance_to_players` | 3366 | 72 | `place_on_specific_land_id` | 268 | 116 | `make_indestructible` | 10 |
| 29 | `terrain_type` | 3133 | 73 | `set_flat_terrain_only` | 245 | 117 | `create_object_group` | 10 |
| 30 | `actor_area_to_place_in` | 2986 | 74 | `spacing` | 213 | 118 | `create_connect_land_zones` | 9 |
| 31 | `land_position` | 2963 | 75 | `nomad_resources` | 199 | 119 | `generate_mode` | 8 |
| 32 | `number_of_groups` | 2941 | 76 | `spacing_to_specific_terrain` | 163 | 120 | `min_placement_distance` | 8 |
| 33 | `base_elevation` | 2842 | 77 | `enable_balanced_elevation` | 162 | 121 | `set_zone_randomly` | 7 |
| 34 | `terrain_mask` | 2708 | 78 | `effect_percent` | 161 | 122 | `set_gaia_civilization` | 7 |
| 35 | `terrain_to_place_on` | 2389 | 79 | `force_nomad_treaty` | 135 | 123 | `generate_for_first_land_only` | 3 |
| 36 | `avoid_forest_zone` | 2203 | 80 | `create_connect_all_players_land` | 115 | 124 | `distance_to_other_terrain_types` | 2 |
| 37 | `max_distance_to_other_zones` | 2187 | 81 | `ignore_terrain_restrictions` | 111 | 125 | `accumulate_connections` | 2 |
| 38 | `find_closest` | 2163 | 82 | `set_gaia_unconvertible` | 109 | 126 | `set_building_capturable` | 2 |
| 39 | `avoid_cliff_zone` | 1737 | 83 | `min_number_of_cliffs` | 107 | 127 | `avoid_actor` | 1 |
| 40 | `second_object` | 1631 | 84 | `max_number_of_cliffs` | 107 | 128 | `avoid_all_actor_areas` | 1 |
| 41 | `set_avoid_player_start_areas` | 1564 | 85 | `set_zone_by_team` | 94 | 129 | `assign_to_player` | 1 |
| 42 | `top_border` | 1376 | 86 | `enable_tile_shuffling` | 93 | 130 | `min_terrain_distance` | 1 |
| 43 | `right_border` | 1366 | 87 | `grouped_by_team` | 83 | 131 | `temp_min_distance_to_players` | 1 |
| 44 | `bottom_border` | 1347 | 88 | `force_placement` | 76 | | | |

**Concentration:** top 20 = 229,027 occurrences (71.5%); top 50 = 303,289 (94.6%); the bottom 50 commands together account for 1,788 occurrences (0.56%).

**Pseudo-section `<top-level>`** (commands appearing outside any section, i.e. inside `.inc` fragments): `elseif` 5858, `if` 4486, `endif` 4476, `percent_chance` 4237, `avoid_actor_area` 2565, `number_of_objects` 1205, `end_random` 1087, `start_random` 1086. This confirms `.inc` fragments are ordinary RMS text spliced in, not a separate mini-language.

### 3.5 Per-section vocabulary leads — [V]

- `<PLAYER_SETUP>`: `effect_amount` 5207, `if` 1014, `endif` 1014, `else` 578, `ai_info_map_type` 533, `percent_chance` 396, `random_placement` 395, `nomad_resources` 198, `start_random` 182, `end_random` 182, `force_nomad_treaty` 134, `grouped_by_team` 83, `elseif` 77, `water_definition` 56, `direct_placement` 30, `behavior_version` 30, `effect_percent` 15, `set_gaia_civilization` 7, `override_map_size` 3.
- `<LAND_GENERATION>`: `create_land` 8690, `base_size` 4652, `percent_chance` 4090, `elseif` 3730, `number_of_tiles` 3506, `terrain_type` 3093, `base_elevation` 2839, `land_position` 2830, `land_percent` 1511, `top/right/bottom/left_border` ~1350 each, `other_zone_avoidance_distance` 1188, `border_fuzziness` 1096, `circle_radius` 1022, `assign_to` 965.
- `<TERRAIN_GENERATION>`: `create_terrain` 13553, `number_of_clumps` 11665, `base_terrain` 10957, `land_percent` 10227, `spacing_to_other_terrain_types` 4318, `set_scale_by_groups` 3564, `terrain_mask` 2640, `number_of_tiles` 1591, `set_avoid_player_start_areas` 1516, `height_limits` 968, `set_scale_by_size` 618, `clumping_factor` 406, `else` 1034, `beach_terrain` 369, `color_correction` 323, `set_flat_terrain_only` 237.
- `<OBJECTS_GENERATION>`: `avoid_actor_area` 26357, `create_object` 9463, `number_of_objects` 8286, `actor_area_radius` 7030, `if` 6502, `endif` 6501, `actor_area` 6459, `elseif` 6344, `set_gaia_object_only` 5434, `set_place_for_every_player` 4958, `temp_min_distance_group_placement` 3978, `min_distance_group_placement` 3755, `min_distance_to_players` 3662, `else` 3660, `actor_area_to_place_in` 2807, `max_distance_to_players` 2695.
- `<ELEVATION_GENERATION>`: `number_of_tiles` 2094, `if` 1441, `number_of_clumps` 1312, `create_elevation` 450, `base_terrain` 444, `spacing` 213, `enable_balanced_elevation` 160.
- `<CLIFF_GENERATION>`: `min_number_of_cliffs` 104, `max_number_of_cliffs` 104, `cliff_type` 70, `min_length_of_cliff` 33, `max_length_of_cliff` 33, `min_distance_cliffs` 29, `cliff_curliness` 23.
- `<CONNECTION_GENERATION>`: `terrain_cost` 1167, `replace_terrain` 1155, `terrain_size` 774, `create_connect_all_players_land` 115, `create_connect_teams_lands` 43, `create_connect_all_lands` 21, `create_connect_to_nonplayer_land` 14, `create_connect_land_zones` 9, `accumulate_connections` 2.

### 3.6 Verified excerpts

**Conditionals and `#define` inside a section** — `Arabia.rms:25-33` [V]:
```
start_random
  percent_chance 80
  #define PALAEARCTIC_EUROPE_MEDITERRANEAN
  percent_chance 20
  #define THEME_SELECTION
end_random
else
  #define THEME_SELECTION
endif
```
`else` / `elseif` / `endif` work exactly like `if`, and `#define` may sit inside a `percent_chance` branch.

**Random values and expressions as arguments** — `Arabia.rms:836-839` [V]:
```
	circle_radius rnd(32,34) 6
else
	circle_radius 34 1
endif
```
`rnd(a,b)` is a valid argument; arithmetic expressions are valid (`land_percent (6 * CONFINED_INCREASE)`, `max_distance_to_players (MAPSIZE_SIDE * 0.20)`); `#const` symbols are valid arguments.

**Command + brace block with nested conditionals** — `Arabia.rms:952-960` [V]:
```
create_terrain FOREST_PLACEHOLDER
{
	base_terrain BASE_TERRAIN
	if RND_GLOBAL_FOREST_SIZE_SMALL
		land_percent (6 * CONFINED_INCREASE)
	elseif RND_GLOBAL_FOREST_SIZE_MEDIUM
		land_percent (8 * CONFINED_INCREASE)
	elseif RND_GLOBAL_FOREST_SIZE_LARGE
	...
```

**A complete, canonical object block** — `includes\town_centres.inc`, whole file [V]:
```
if OFFSET_TOWN_CENTER
	create_object PLACEHOLDER_AMPHIBIOUS
else
	create_object PLACEHOLDER_AMPHIBIOUS_TILE
endif
{
	second_object TOWN_CENTER
	set_place_for_every_player

	if NOMAD_START
		number_of_objects 0
	endif

	min_distance_to_players 0
	max_distance_to_players 0

	actor_area 10
	actor_area_radius 1
}
```
Note the construct that trips naive parsers: the `if/else/endif` selects which `create_object` is used, and the `{ … }` block belongs to whichever one won.

**Attribute effects** — `Acclivity.rms:1948` and `:2010-2017` [V]:
```
effect_amount MOD_RESOURCE AMOUNT_STARTING_WOOD ATTR_SET -30
effect_amount GAIA_SET_ATTRIBUTE ANIMAL_BLOOD_SMALL ATTR_STORAGE_VALUE 30000
```

**Connection generation** — `Acclivity.rms:4334` [V]:
```
create_connect_all_players_land
{
	replace_terrain EDGE_FOREST RELIC_TERRAIN ;
	terrain_size EDGE_FOREST 1 0
}
create_connect_all_lands
{
	terrain_size BASE_TERRAIN 1000 0
	...
	replace_terrain BEACH BEACH_TERRAIN ;
	terrain_cost BEACH 1
}
```
The trailing `;` inside a brace block is accepted (and also used in `object_setup.inc`), i.e. `;` is a tolerated no-op statement separator inside braces even though the guide documents only `/* */` comments.

**Map-size override** — `includes\EnlargeMap.inc` (14 lines, whole file conceptually) [V]: nested map-size conditionals emitting `override_map_size 144`, `168`, `200`, `220`, `240`, `255`. `includes\scaling.inc` (88 lines) derives `MAPSIZE_SIDE` / `MAPSIZE_AREA` for 14 size names (`MAPSIZE_MINI` … `MAPSIZE_LUDICROUS`) and ends with `override_map_size MAPSIZE_SIDE`. `includes\preliminaries.inc:3` is `behavior_version 2`.

**Minimal valid map (stub pattern)** — `EM Arabia.rms`, 82 B, whole file [V]:
```
#define ESCALATION_MODE
ai_info_map_type EM_ARABIA 0 0

#include_drs Arabia.rms
```
So a "new map" can legitimately be three lines that redirect to an existing one.

**New commands introduced by `.rms2`** — [V]: `enable_waves` (68), `layer_to_place_on` (67), `set_facet` (50), `land_conformity` (14), `min_placement_distance` (8), `generate_mode` (8), `accumulate_connections` (2), `terrain_type LAYER_C`. Everything else in `.rms2` is the same language as `.rms`.

### 3.7 The official guide's own documentation gaps — [D]

`Docs\All\TC Random Map Scripting Guide.doc` was extracted to text (73,131 B / 70,692 chars). It documents only the **classic AoK/TC-era** surface: it states the map-size table (`tiny_map 72x72/5,184/0.5` … `gigantic_map 255x255/62,025/6.2`), the seven headers, `#define`, `if/elseif/else/endif`, `start_random`/`percent_chance`/`end_random`, and one command per concept. It contains **no** mention of `#const` (0 hits), `#include_drs` (0), `#undefine` (0), `behavior_version` (0), `ai_info_map_type` (0), `effect_amount` (0), `water_definition` (0), `nomad_resources` (0), `ATTR_*` (0) — yet those are the dominant modern constructs (50,052 `#const`, 5,722 `effect_amount`, 540 `ai_info_map_type`). It also claims "`random_placement … This is the only valid entry under <PLAYER_SETUP>`", which the shipped corpus flatly contradicts. **The official guide is 20+ years stale and must not be used as the schema for a tool.**

The guide's most useful content is the intent/behaviour prose: standard starting resources (6 berries; 1 group of 7 gold; 2 groups of 4 gold; 1 group of 5 stone; 1 group of 4 stone; 1 group of 4 sheep; 2 groups of 2 sheep; 1 group of 4 deer; 2 boar; 2 wolves; 1 group of 3 straggler trees; 1 group of 2 straggler trees); the zoning recipe (`start_random` / `percent_chance 20 set_zone_by_team` / `20 zone 1` / `20 set_zone_randomly` / `end_random`, remainder defaulting); the object-scattering rule ("If number_of_groups is not specified, then each object is treated as its own group… Standard Ensemble Studios maps scatter fish, but keep gold and stone mines in tight groups"); the failure mode ("if there is not enough space for boar for player 2, then player 2 will not have any boar"); the debugging tip (temporarily set base terrain to grass and player lands to desert to reveal start areas); and the object/terrain/map name vocabulary.

---

## 4. RMS: encodings and quirks

**[V] All 311 analyzed files (208 `.rms` + 16 `.rms2` + 87 `.inc`):**

| Property | Result |
|---|---|
| Encoding | `utf-8` **with no BOM** — 311/311 |
| Non-ASCII bytes | **0** across all files |
| BOM | **0** files |
| Line endings | **CRLF-only** — 311/311 |
| Bare LF | 0 |
| Bare CR | 0 |
| Mixed | 0 |

The corpus is uniformly machine-generated-clean ASCII/CRLF. There are **no encoding anomalies to handle**, so a tool may safely write UTF-8-no-BOM + CRLF and never branch. (`.per`/`.per2`/`.ai`/`.xs` are likewise pure ASCII with 0 BOM and 0 non-ASCII bytes.)

**[V] 13 files flagged by the size heuristic, none malformed:**

| File | Bytes | Verdict |
|---|---|---|
| `EM Arabia.rms` | 82 | 1-line `#include_drs` redirect — valid |
| `EM Arena.rms` | 80 | same |
| `EM Black Forest.rms` | 94 | same |
| `EM Fortified Clearing.rms` | 106 | same |
| `EM Glade.rms` | 80 | same |
| `EM Nomad.rms` | 80 | same |
| `EM Runestones.rms` | 90 | same |
| `F_Distances_A.inc` | 58 | fragment: two `min/max_distance_to_players` lines, **no section header** |
| `F_Distances_B.inc` | 198 | fragment: `start_random`/`percent_chance` distance block, no header |
| `F_Distances_B2.inc` | 198 | same |
| `F_StartingVills.inc` | 158 | `if EMPIRE_WARS / else / create_object VILLAGER { … } / endif` |
| `includes\starting_objects.inc` | 4 | `"\n\n"` — deliberately blank placeholder |
| `thebr_setup.inc` | 46 | `if BATTLE_ROYALE` / `/* nomad_resources */` / `endif` |

**Real quirks a tool must respect** — [V]:
1. Block comments are load-bearing: `/* #define DEBUG_MODE */` and `/* #const DEER 65 */` are used to *disable* active statements. Any tool that reads values without stripping `/* */` will see phantom constants and phantom commands. (An early version of this survey's analyzer produced 400 bogus "commands" — map names like `arabia` — exactly this way; the corrected analyzer strips comments first and yields 131.)
2. Comments may sit **inline** after a value (`avoid_actor_area 1100 /* Predators */`) and may span many lines.
3. `#include_drs` paths use **forward slashes** even on Windows, and may carry a numeric DRS id as a second argument.
4. Directives and commands may share a line: `percent_chance 20 #define X`.
5. `rnd(a,b)` and arithmetic parenthesised expressions are valid arguments wherever a number is expected.
6. A `{ … }` block may follow an `if/else/endif` group rather than a literal `create_*` line (`town_centres.inc`).
7. `.inc` fragments are written **without** section headers and are spliced into a section by the includer.
8. `;` inside a brace block is tolerated as a separator (`object_setup.inc`, `Acclivity.rms:4334`) even though the guide never documents it.
9. Two `.per` files are 0 bytes (`Promisory\merge3.per`, `Promisory\merge3b.per`) — placeholder artifacts in the shipped corpus, evidence that zero-byte files are tolerated.

---

## 5. RMS: intent mapping (beginner intent → concrete construct)

The left column is what a beginner says; the right column is what a tool would have to emit. All right-column constructs are verified present in the shipped corpus.

| Beginner intent | Concrete construct | Evidence |
|---|---|---|
| "Make a map like Arabia / Islands / Arena" | Copy/`#include_drs` the corresponding script; 194 map entries in `maps.json` give the name, icon, description and script filename | [V] |
| "More gold on the map" | `create_object GOLD` (or `GOLD_MINE`, id 66) `{ number_of_objects N number_of_groups G group_placement_radius R }`; also `number_of_tiles`/`number_of_clumps` on the containing terrain | [V] `create_object` 10,262; `number_of_objects` 9,491 |
| "More starting berries" | `create_object FORAGE_PLANT { second_object PLANT_DEAD set_place_for_every_player set_gaia_object_only number_of_objects 6 set_tight_grouping group_placement_radius 1 min_distance_to_players 12 … }` | [V] `includes\starting_resources.inc` head |
| "Make the map bigger / smaller" | `override_map_size <tiles>` (144/168/200/220/240/255 in `EnlargeMap.inc`), or `override_map_size MAPSIZE_SIDE` from `scaling.inc`; the *game* map size is a lobby setting, not an RMS one | [V] `override_map_size` 18/4 files |
| "Fewer/more wolves" | Wolf ids are constants: `WOLF 126`, `WOLF_HILL 126`, `DIRE_WOLF 89`, `RABID_WOLF 202` in `random_map.def`; the corpus controls them via `#const PREDATOR_A 126` + `create_object PREDATOR_A { number_of_objects PREDATOR_COUNT … }` | [V] `includes\predators.inc`; `Acclivity.rms` inline `#const PREDATOR_A 126 /* Wolf */`, `PREDATOR_B 486 /* Bear */` |
| "No wolves at all" | Set `number_of_objects 0` in the `PREDATOR_A` block, or drop `#include_drs includes/predators.inc` (included by 47 maps) | [V] |
| "More deer / boar / sheep" | `create_object DEER` (65) / `BOAR` (48) / `SHEEP` (594) with `number_of_objects`, `number_of_groups`, `min_distance_to_players`, `max_distance_to_players` | [V] `DEER` 97 hits/43 files; `BOAR 48`; `SHEEP 594` |
| "Islands" | `<LAND_GENERATION> base_terrain WATER` + `create_player_lands { land_percent 52 … }` + `create_land { … }` per island; or reuse `Islands.rms`/`Archipelago.rms` | [V] guide's annotated Coastal script shows the pattern |
| "Snow / desert / forest theme" | `terrain_type SNOW` inside `create_player_lands`, and/or `create_terrain SNOW { base_terrain … land_percent … number_of_clumps … }`; the official maps do it with a `start_random`/`percent_chance` theme block | [V] `Arabia.rms:25-33`, `:952`; `Acropolis.rms2` `#define PH_MEDISOUTH` |
| "Hilly map" | `<ELEVATION_GENERATION> create_elevation { number_of_tiles N number_of_clumps C spacing S }`, `base_elevation`, `enable_balanced_elevation` | [V] `create_elevation` 462; `enable_balanced_elevation` 162 |
| "More cliffs" | `<CLIFF_GENERATION> min_number_of_cliffs N max_number_of_cliffs M cliff_type X cliff_curliness C` | [V] counts in §3.5 |
| "Start with a castle / extra villagers" | `create_object CASTLE` (82) / `create_object VILLAGER` (83) with `set_place_for_every_player` and `min/max_distance_to_players`; or `effect_amount MOD_RESOURCE AMOUNT_STARTING_<RES> ATTR_SET <delta>` | [V] `F_StartingVills.inc`; `Acclivity.rms:1948` |
| "More/less starting wood, food, gold" | `effect_amount MOD_RESOURCE AMOUNT_STARTING_WOOD ATTR_SET -30` (negative reduces) | [V] `Acclivity.rms:1948` |
| "Bigger forests" | `create_terrain FOREST_PLACEHOLDER { base_terrain BASE_TERRAIN … land_percent (6 * CONFINED_INCREASE) … }` / `number_of_clumps` | [V] `Arabia.rms:952`; `number_of_clumps` 13,394 |
| "Don't let resources spawn in weird places" | `min_distance_to_players`, `max_distance_to_players`, `set_avoid_player_start_areas`, `avoid_actor_area`, `other_zone_avoidance_distance`, `max_distance_to_other_zones` | [V] each present at scale |
| "Nomad start" | `nomad_resources` in `<PLAYER_SETUP>`, plus `if NOMAD_START number_of_objects 0 endif` in the town-centre block | [V] `nomad_resources` 199; `town_centres.inc` |
| "Reveal the whole map / different game modes" | RMS does not do this — it is a lobby setting; the RMS-side analogue is `ai_info_map_type NAME 0 0` so the AI knows the map | [V] `ai_info_map_type` 540 |
| "Make the AI play the map well" | Ship a companion `.per` and set `ai_info_map_type` | [D] guide: "unless you compose a new .AI file for that map, the Computer Player may not play with optimal efficiency" |

**Load-bearing caveat for the tool** — [D]: the generator is **single-pass and non-retrying**. "Land is placed all at once but terrain is placed in the order you specify, and then objects are placed on top of terrain. … The map generator does not try several iterations until it creates a map that works—if there is not enough space for boar for player 2, then player 2 will not have any boar." Therefore the tool should generate from a **validated template plus bounded parameter deltas** rather than synthesize commands freely, and should keep the object budget of the base map intact.

---

## 6. AI: inventory

### 6.1 Counts by extension — [V]

| Ext | Files (game root) | Bytes | Zero-byte | Files (user profile) |
|---|---|---|---|---|
| `.per` | 90 | 6,378,490 | 2 | 1 (`…\0\mods\local\AGE本地测试\resources\_common\ai\E3-p2 副本.per`, 2,083 B) |
| `.per2` | 30 | 589,292 | 0 | 0 |
| `.ai` | 3 | **0** | **3** | 0 |
| `.xs` | 7 | 126,841 | 0 | 1 (`…\76561198406248391\resources\_common\xs\default0.xs`, 1,792 B) |

### 6.2 Location map — [V]

| Root | `.per` | `.per2` | `.ai` | `.xs` |
|---|---|---|---|---|
| `resources\_common\ai` | 52 | 0 | 2 | 0 |
| `resources\_common\drs\gamedata_x2` | 1 | 30 | 1 | 0 |
| `resources\_common\xs` | 0 | 0 | 0 | 7 |
| `modes\Pompeii\resources\_common\ai` | 35 | 0 | 0 | 0 |
| `modes\Pompeii\resources\_common\drs\gamedata_x2` | 2 | 0 | 0 | 0 |

### 6.3 The `.ai` files (all 0 bytes) and their pairing — [V]

| `.ai` marker | Paired file | Size |
|---|---|---|
| `resources\_common\ai\AI (HD version).ai` | `AI (HD version).per` | 1,170,991 B |
| `resources\_common\ai\E3-p2.ai` | `E3-p2.per` | 2,139 B |
| `resources\_common\drs\gamedata_x2\randomgame.ai` | `randomgame.per2` | 1,174 B |

The executable's personality-marker table (offset ≈52598896) holds the literal strings `E3-p2.ai`, `AI (HD version)`, `HD_AI_TAG`, `PromiDE`, `RandomGame` — i.e. the engine enumerates these by name. No `.per` on disk references `".ai"`.

### 6.4 The `.per` sets — [V]

**`resources\_common\ai\` (5 loose + 2 subdirs)**

Loose: `AI (HD version).per` 1,170,991; `AiBuilder.per` 55,417; `E3-p2.per` 2,139; `AoF scenario difficulty.per` 1,709; `AoF scenario upgrades.per` 26,264. Plus `ai.txt` 8 B (content `AI.txt`).
`AiBuilder\` (9): `constantsUP.per` 31,250; `construction.per` 11,822; `economy.per` 2,407; `general.per` 2,498; `market.per` 4,363; `militaryBehavior.per` 2,745; `militaryUnits.per` 6,443; `phaseUpdate.per` 78,659; `technologies.per` 41,740.
`Promisory\` (38): `units.per` 463,297 (1,144 `defrule`); `tsa.per` 439,866 (1,023); `buildings.per` 437,220 (1,084); `init.per` 357,549; `general.per` 254,563; `customConstants.per` 242,766 (6,769 `defconst`); `const.per` 180,224 (4,806); `ImprovementBucketsConst.per` 134,558 (3,614); `escrow.per` 118,395; `gatherers.per` 199,545; `researches.per` 228,188; `orb.per` 153,780; `defaultConstants.per` 33,758; `threats.per` 76,083; `trade.per` 42,917; `watercontrol.per` 58,794; `dawn.per` 15,423; … plus `merge3.per` and `merge3b.per`, both **0 B**.

**`modes\Pompeii\resources\_common\ai\` (2 loose + 3 subdirs)**
Loose: `AiBuilder_p.per` 44,367; `Fe Immobile AI.per` 1,468.
`AiBuilder_p\` (12): `AiBuilder.per` 56,059; `constantsUP.per` 31,258; `technologies.per` 44,727; `phaseUpdate.per` 78,574; `obseleteConstants.per` 12,305; `construction.per` 11,907; `militaryUnits.per` 6,655; `alternateConstants.per` 5,570; `market.per` 4,363; `militaryBehavior.per` 2,745; `general.per` 2,498; `economy.per` 2,473.
`default\` (20): `tsa.per` 186,880; `buildings.per` 99,295; `units.per` 72,053; `dawn.per` 57,580; `init.per` 51,590; `interaction.per` 40,462; `customConstants.per` 37,451; `defaultConstants.per` 33,758; `escrow.per` 2,678; …
`Trajan\additional\`: `old_dawn.per` 15,373 and **`population defconsts generator.py`** 1,156 B — a Jupyter-exported Python generator that writes `constantprintout.per` from `population_list = [25, 50, 75, 100, 125, 150, 175, 200]`, emitting `#load-if-defined POPULATION-CAP-<cap>` / `(defconst p<percent> max(1,floor(percent*cap/200)))` / `#end-if`. **[V] This is direct proof that the shipped `.per` corpus is machine-generated text.**

### 6.5 The `.per2` set (30, all in `gamedata_x2`) — [V]

`elite ai petersen rules.per2` 33,274; `elite petersen constants.per2` 34,481; `elite petersen civ loads.per2` 64,147; `elite petersen deathmatch.per2` 72,590; `elite petersen dip boomer.per2` 475; `elite petersen bully.per2` 30,008; `elite petersen feeder.per2` 5,062; `elite petersen insult.per2` 4,272; `elite petersen liar.per2` 3,544; `elite petersen rush.per2` 2,842; `elite petersen tower.per2` 5,298; `elite petersen upgrades.per2` 72,467; `elite petersen wonder.per2` 3,651; `elite wonder kill.per2` 52,823; `elite wonder rush.per2` 56,231; `diplomacy.per2` 21,285; `difficulty loads.per2` 5,032; `map loads.per2` 14,093; `fishboat.per2` 4,463; `full tech.per2` 23,610; `gather.per2` 12,359; `groups.per2` 12,666; `market.per2` 12,623; `resign.per2` 2,647; `supplement.per2` 29,952; `warboat island.per2` 3,129; `warboat.per2` 2,874; `wonder.per2` 3,651; `PromiDE.per2` 969; `randomgame.per2` 1,174.

**These are not a different format.** They are ordinary AI scripts / load-lists from the PromiDE era, just carrying `.per2`. The engine recognizes `.ai2`, `.per`, `.per2`, `.ai` as AI extensions (extension table in `aiexpert.cpp` string block).

### 6.6 The `.xs` set — [V]

`resources\_common\xs\`: `Constants.xs` 61,369; `Effects.xs` 53,983; `ailib\Geometry.xs` 5,705; `ailib\GoalArrayOps.xs` 2,787; `ailib\MilitaryEvaluation.xs` 2,349; `x256tech.xs` 281; `x9tech.xs` 367; plus `xs.txt` 6 B (content `xs.txt`).
User side: `C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\xs\default0.xs` 1,792 B (auto-generated scenario helper — see §7.3).

### 6.7 Nothing in the user profile's mods ships scripts — [V]

`C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\` holds 6 mods (`182654_Age of Anime (Chibi Edition)`, `423821_…军团长天赋模组`, `423822_…军团长天赋文本`, `550009_2026 Civilization Alliance 文明联盟 文本UI(v19)`, `550412_透明主题整合自用`, `550749_{2026}10倍资源文明联盟2倍科技 北欧dlc可用 v48`). **None** ships any `.rms`/`.rms2`/`.per`/`.per2`/`.ai`/`.xs`. The one local mod, `0\mods\local\AGE本地测试\`, contains only `resources\_common\ai\E3-p2 副本.per` (2,083 B) and an `info.json` reading `{"Author":"AGE可视化编辑器 By RemonBo","CacheStatus":0,"Description":"由 AGE 可视化编辑器 By RemonBo 生成的本地测试模组","Title":"AGE本地测试"}` — i.e. it is an AGE-generated test artifact, not a shipped AI.

---

## 7. AI: format per extension

### 7.1 `.ai` — an empty marker file, nothing more — [V]/[D]

Verbatim from `Docs\All\TC CP Strategy Builder.doc` (extracted):

> "AI Files are text files that have their extension changed to '.per' (for example, 'Henry Tudor.per'). … **An empty text file with an .AI extension (for example, 'Marko.ai') should be created to make an entry appear in the list of computer players and in the scenario editor.** The game will try to find a file with a matching .per extension that will be started when you pick that player. In your game's AI directory, you would then have 2 files … `MyAI.ai` (This is an empty file that makes an entry in the game's list) / `MyAI.per` (This file contains your custom AI script of rules and facts). **You must have both a .PER and an .AI file with the same name for your script to function!**"

Confirmed by disk: 3 `.ai` files, all 0 bytes, each paired with a same-named `.per`/`.per2`. The engine's `aiexpert.cpp` also carries the error `%s AI file must have at least one rule`.

**Tool implication:** "new AI" = write `<Name>.per` + a 0-byte `<Name>.ai`. Nothing user-visible.

### 7.2 `.per` / `.per2` — the s-expression rule language — [V]

Real syntax, verified from `AiBuilder.per` (1,444 lines) and the `.per2` set:

- **Comments**: `;` to end of line (whole-line or trailing).
- **Symbols**: `(defconst name value)`.
- **Rules**: `(defrule (condition…) => (action…) (action…))`. The guide's prose: "Rules are defined in the script with the defrule instruction. If the conditions for the rule are met (True), the instructions in that rule are followed. … Rules continue to be evaluated until they are disabled. This is done with the disable-self command." **[D]**
- **Preprocessor**: `#load-if-defined SYMBOL … #else … #end-if` and `#load-if-not-defined SYMBOL`. Nesting limit 50 (ERR3003). **[D]**
- The keyword table baked into `aiexpert.cpp` is exactly: `load`, `load-random`, `include`, `defrule`, `defconst`, `#load-if-defined`, `#load-if-not-defined`, `#else`, `#end-if`. **[V]**
- Whitespace/newlines are not significant — `(defrule (true) => (set-goal x 1))` on one line is valid.

**Real rules, verbatim (`AiBuilder.per`)** [V]:
```
line 1326  (defrule (true) => (set-strategic-number sn-maximum-food-drop-distance 0) … (sn-maximum-stone-drop-distance 0))
line 1352  (defrule (true) => (set-strategic-number sn-mill-max-distance 30) (up-get-point position-map-size temporary-goal2) (up-modify-goal map-size g:= temporary-goal2) (set-strategic-number sn-enable-boar-hunting 1) (set-goal spread-units 0))
line 1365  (defrule (building-type-count town-center >= 1) => (up-full-reset-search) (up-find-local c: town-center c: 1) (up-set-target-object search-local c: 0) (up-get-point position-object position-self-x))
line 1374  (defrule (true) => (set-strategic-number sn-enable-new-building-system 1) (disable-self))
line 1382  (defrule (true) => (up-get-fact unit-type-count villager villager-count) (up-get-fact game-time 0 gl-game-time) (up-modify-goal land-attack-interval c:max 6) (up-modify-goal naval-attack-interval c:max 6))
           (chat-local-to-self "Entering Phase 1.")
```
Its commented-out examples (lines 1408-1444, each line prefixed `;`) use `(dropsite-min-distance live-boar s:< sn-maximum-hunt-drop-distance)`, `(or (research-completed ri-loom) (dropsite-min-distance live-boar < 15))`, `(set-strategic-number sn-minimum-boar-lure-group-size 1)`, `(up-request-hunters c: 5)`.

**Constants header style (`AiBuilder.per`)** [V]:
```
; AIBuilder v2.0 - CONSTANTS
(defconst phase1-always-enabled 1)
(defconst phase1-aisignal 1)
(defconst phase1-military-explorers 1)
(defconst phase1-food-gatherers 45)
(defconst phase1-wood-gatherers 30)
(defconst phase1-gold-gatherers 15)
(defconst phase1-stone-gatherers 10)
(defconst phase1-villager-cap 25); modify phaseX-villager-cap-easy/moderate/hard instead
```
This is the archetype of a "settings only" file — pure numbers with human names.

**`.per2` verified samples** [V]:
`elite petersen rush.per2`:
```
;error trapping
(defrule (current-age == imperial-age) (not (goal rush-control NO)) => (set-goal rush-control NO))
...
(generate-random-number 12)
(goal rush-control NOTICE)
(difficulty > hard)
(random-number == 1)
(map-type archipelago)
```
`elite petersen dip boomer.per2` (475 B, whole file): comment `;all this file really does for now is ensure more villagers than a "normal" CP`, then rules doing `(set-goal personality 2)`, `(set-goal rush-control BOOMING)`, and `(train villager)` guarded by `(civilian-population < fifty-percent-pop)`.
`elite petersen constants.per2`: `(defconst NO 0)` / `(defconst YES 1)` plus rating scales with trailing `;` comments.

**Real working vocabulary (corpus-wide, comments stripped)** [V] — `ai_analysis.json`: 15,554 `defrule`, 30,174 `defconst`, 120 distinct directives. Top directives by occurrence: `defconst` 30174, `defrule` 15554, `or` 15179, `goal` 12645, `set-goal` 11398, `up-compare-goal` 8719, `strategic-number` 6878, `set-strategic-number` 4652, `building-type-count-total` 4444, `unit-type-count-total` 4413, `up-modify-goal` 3635, `and` 3332, `up-jump-rule` 2256, `game-time` 2204, `unit-type-count` 2032, `up-research-status` 2028, `research` 1908, `release-escrow` 1768, `building-type-count` 1682, `current-age` 1588. Spread across files: `defrule` in 102 files, `or` 83, `goal` 81, `set-goal` 80, `disable-self` 75, `true` 74, `not` 74, `up-compare-goal` 62, `set-strategic-number` 61, `building-type-count` 60, `current-age` 60.

**Documented scale of the surface** — [D] from `TC CP Strategy Builder.txt` (extracted; 141,045 chars): the guide documents **139** distinct `sn-*` strategic-number names (Appendix A "Internal SN parameter documentation", Appendix B "Discontinued SN parameters", Appendix C "SN Parameter Defaults"), plus a combined Facts/Actions/Parameters list (sections at chars 20466, 52799, 66802) — by design a few hundred distinct fact and action keywords. So the language is small in *grammar* (9 keywords) and large in *vocabulary* (hundreds of names). That asymmetry is exactly what makes a parameter-space UI feasible.

### 7.3 `.xs` — the C-like scripting language — [V]

`Constants.xs` header prose: "This is the default XS scripting language constants file. It is automatically included in every instance of the XS scripting language so there is no need to include it in your own .xs files."

Syntax verified from `Constants.xs`:
```
// comments
extern const int cAttributeFood = 0;
extern const int cAttributeWood = 1;
extern const int cAttributeStone = 2;
extern const int cAttributeGold = 3;
extern const int cAttributePopulationCap = 4;
extern const int cAttributeReligion = 5;
extern const int cAttributeCurrentAge = 6;
... 1,175 `extern const int` declarations in total
```
Syntax verified from the user's `default0.xs` (auto-generated by the in-game Script Call feature):
```
//This is an auto-generated XS file. The functions defined in this script are written from the Script Call conditions and effects.
//Make sure this file is NOT used as a main XS file as it is subject to change depending on the scenario.

void direnbaitiansheshou()
{
xsEffectAmount(4,900,9,-735,8);
}
```
**XS is a real programming language**: functions, types, calls, a standard library (`xsEffectAmount`, geometry and goal-array helpers in `ailib\`), and it can be invoked from an AI via `up-*` calls. It is the only one of the four extensions that requires actual programming skill.

---

## 8. AI: intent mapping, and trivial vs. real programming

### 8.1 Where the leverage is: the shipped aggression block — [V]

`AiBuilder.per` lines 1337-1351 are a single `(defrule (true) => … (disable-self))` whose entire body is strategic-number assignments. Verbatim:

```
(set-strategic-number sn-stone-gatherer-percentage 0)
(set-strategic-number sn-cap-civilian-explorers 0)
(set-strategic-number sn-percent-civilian-explorers 100)
(set-strategic-number sn-defense-distance 20)
(set-strategic-number sn-sentry-distance 20)
(set-strategic-number sn-percent-enemy-sighted-response 100)
(set-strategic-number sn-number-explore-groups 0)
(set-strategic-number sn-percent-attack-soldiers 0)
(set-strategic-number sn-task-ungrouped-soldiers 0)
(set-strategic-number sn-number-attack-groups 0)
(set-strategic-number sn-enemy-sighted-response-distance 10)
(set-strategic-number sn-total-number-explorers 0)
(set-strategic-number sn-minimum-town-size 0)
(set-strategic-number sn-maximum-town-size 0)
(disable-self)
```

**This is the template a beginner tool should emit.** One rule, no conditions beyond `(true)`, a list of named dials, `(disable-self)`, done. Nothing in it requires the user to see a field name.

### 8.2 Intent → construct → effort

| Beginner intent | Concrete construct | Effort class |
|---|---|---|
| "AI more aggressive / attacks sooner" | `set-strategic-number sn-number-attack-groups N`, `sn-percent-attack-soldiers`, `sn-minimum-attack-group-size`, `sn-maximum-attack-group-size`, `sn-initial-attack-delay`; or an `(attack-now)` action | **Trivial** — constant writes in a `(true)` rule |
| "AI doesn't rush / booms" | `(set-goal rush-control BOOMING)` vs `NO` | **Trivial** — verified in `elite petersen dip boomer.per2` / `rush.per2` |
| "AI hunts boar / deer" | `(set-strategic-number sn-enable-boar-hunting 1)` (1 = boar+deer, 2 = boar only, 0 = deer only) | **Trivial** — [D]/[V] present in AiBuilder and recommended by airef |
| "AI builds more walls" | `build-wall`, `can-build-wall-with-escrow`, `(set-strategic-number sn-gate-type-for-wall 1)` (palisade vs stone); wall-avoidance/wall-fade in RMS | **Mostly trivial**, but real wall logic (where, in what order) is rules |
| "AI trains more archers / specific units" | `(unit-type-count archer-line >= N)`, `(can-train …)`, `(train archer-line)` | **Small rule** — needs a condition, but a template can hide it |
| "AI gathers differently" | `sn-food-gatherer-percentage`, `sn-wood-gatherer-percentage`, `sn-gold-gatherer-percentage`, `sn-stone-gatherer-percentage`, `sn-maximum-*-drop-distance` | **Trivial** |
| "AI expands its town more" | `sn-minimum-town-size`, `sn-maximum-town-size` | **Trivial** |
| "AI easier / harder" | `(defconst …)`, difficulty-scoped `#load-if-defined DIFFICULTY-*`, the `difficulty` fact, or `sn-do-not-scale-for-difficulty-level`; the shipped pattern is separate `difficulty loads.per2` files and per-difficulty constants (`phaseX-villager-cap-easy/moderate/hard`) | **Trivial→medium** |
| "AI explores more" | `sn-total-number-explorers`, `sn-percent-civilian-explorers`, `sn-number-explore-groups` | **Trivial** |
| "AI plays this water map" | Needs boat rules, dock logic, `warboat.per2`-style content | **Real programming** |
| "AI has a custom build order" | `defrule` chains with `building-type-count` / `unit-type-count` / `current-age` / `can-afford-*` conditions and `enable-timer`/`timer-triggered` pacing | **Real programming** |
| "AI uses goals / scouting / target selection" | `up-*` command family (up-compare-goal, up-modify-goal, up-full-reset-search, up-find-local, up-set-target-object, up-jump-rule, up-get-fact, up-get-point, up-research-status, up-request-hunters, up-set-offense-priority …) + goal arithmetic + `ailib` XS | **Real programming** |
| "Anything in XS" | `void f() { … }` with the XS API | **Real programming** |

**Rule of thumb backed by the corpus** — [V]: of the 120 directives in real use, a small set (`set-strategic-number`, `set-goal`, `defconst`, `disable-self`, `train`, `research`, `build`, `chat-local-to-self`) covers nearly every "make the AI …" request a beginner would phrase. The large remainder (`up-*`, `goal`, comparisons, `and`/`or`/`not`, timers) is what distinguishes a scripter from a settings editor.

**Behavioural SNs worth exposing** — [D] the community reference lists the defaults most often needing change: `sn-cap-civilian-builders` (default 2 → 200), `sn-consecutive-idle-unit-limit` (15 → 1), `sn-do-not-scale-for-difficulty-level` (0 → 1), `sn-enable-boar-hunting` (0 → 1), `sn-enable-offensive-priority` (0 → 1), `sn-enable-patrol-attack` (0 → 1), `sn-initial-exploration-required` (2 → 0), the `sn-maximum-{fish-boat,food,gold,hunt,stone,wood}-drop-distance` family (default −1 = ignored → 20–30), `sn-scale-minimum-attack-group-size` (1 → 0), `sn-task-ungrouped-soldiers` (0 in HD/DE), `sn-zero-priority-distance` (50 → 255), `sn-dropsite-separation-distance` (10 → 3–4), `sn-gate-type-for-wall` (RoR only).

---

## 9. Tooling, validation and error reporting

### 9.1 What the game ships — [V]

- **No RMS or AI editor.** The game root executables are `AoE2DE_s.exe` (72,166,200), `BsSndRpt64.exe`, `BugSplatHD64.exe`, `vc_redist.x64.exe`, `WebClient.exe`. Game root dirs: `BattleServer`, `certificates`, `Docs`, `modes`, `resources`, `Schema`, `SoftwareLicenses`, `Support`, `Tools_Builds`, `webclient`, `widgetui`, `wwise`.
- **`Tools_Builds\` is a DAT/asset toolchain, not a script toolchain.** `AdvancedGenieEditor3.exe`, `AGE3NamesV0007.ini`, `ArtDesk.exe`, `texconv.exe`, `texassemble.exe`, `AOEURLHelper.exe`, `AoEURLInstaller_Steam.exe`, 'Color Blind Mode Colors.txt', `Sprites\`, `docs\` (`AGE_License.txt` 35,821; `AGE_ReadMe.txt` 12,834; `genieutils_License.txt`; `genieutils_ReadMe.txt`; `Source.7z` 341,106). `AGE_ReadMe.txt` contains **no** `.rms`/`.per`/`.ai`/`.xs` content — it edits DAT/Genie data only.
- **`Schema\`** holds only `eCellCategory_services.bond` (81,148 B, protobuf) — unrelated.
- An in-game **AI debugger UI** does exist: `widgetui\aidebugger.json` (43,609 B) defines a collection named `AIDebugger`, and the exe carries `AIDebugger`, `DebugAIScript`, `Age2TabDebugAIScript`, `AIDEBUGGING`. This is a *runtime inspection* view (goals, rule list, local/remote search, unit groups), not an editor and not a validator.
- The only scripting documentation shipped anywhere is `Docs\All\` — `TC Random Map Scripting Guide.doc` (115,712), `TC CP Strategy Builder.doc` (333,312), `AoK CP Strategy Builder.doc` (427,008), plus 11 EULA `.docx`. `Docs\{de,en,es,fr,it,ko,zh}\` carry manuals only. Both CP Strategy Builder docs open "Computer Player Strategy Builder Guide / AI Expert Documentation".

### 9.2 What the game reports at runtime — [V] engine string tables

**RMS parser** (string block near offset ≈53216000, source path baked in as `…\Aoc\Source\Game\RandomMap\RandomMapScriptControllerBase.cpp`):
```
(RandomMapSync) Opening script (%s).
(RandomMapSync) %s(%d): %s
(RandomMapSync) ERROR: Script ended with unclosed comment.
(RandomMapSync) Closing script (%s).
(RandomMapSync) ERROR: %s, unrecognized command ignored
(RandomMapSync) ERROR: label (%s) already defined.
Encountered undefined const %s
Failed to parse filename / Failed to parse string / Failed to parse number / Failed to parse label %s
(RandomMapSync) ERROR: Syntax error. no matching start_random command
(RandomMapSync) ERROR: Syntax error. no matching if command
ERROR: end mCommentLevel without beginning mCommentLevel
(RandomMapSync) ERROR: Command is not valid in this frame of reference.
(RandomMapSync) ERROR: Must use a create command before braces.
(RandomMapSync) NOTE: land_index2=%d has exceeded # lands=%d
(RandomMapSync) ERROR: Cannot set player land start location.
(RandomMapSync) ERROR: %d invalid player number.
(RandomMapSync) NOTE: %d player does not exist, removing land.
(RandomMapSync) ERROR: Cannot set land to a certain player.
(RandomMapSync) Initiating random map script (rms) generation.
Starting random map seed.
Enable error popups for RMS
```
The `%s(%d)` in the second line is `filename(line)`, so the runtime error format for RMS is `<file>(<line>): <message>`. There is an internal flag `RMS_ERROR_POPUP`; a search for a config `.ini` that could toggle it found only `GPUDriverConfig.ini`, so it is a debug-build flag, **not** a user setting. The engine also dumps derived structures (`script_name:`, `elevation_info:`, `terrain_info:`, `mObjectInfo:`, `lands:`, `cliff_info:`, `cross_check_info`, `DLC Enabled:`) — a debug dump, not a validation API.

**AI parser** (string block near offset ≈52589400, source `…\Aoc\Source\Game\ai\aiexpert.cpp`):
```
AI file Error: '%s' Line %d          <- the in-game modal dialog title
%s AI file must have at least one rule
*********************failed to parse directive. Aborting …
failed to find open parenthesis
failed to parse command:
* %s (%d): ERROR #%d: %s *
lexical analysis failed
inclusion stack depth has changed, fail
%s parsing completed successfully
```
Documented error-reporting format — **[D] verbatim from the guide**:
> "Player number / File name / Line number: error code: description. For some errors the line numbers are not relevant and can be omitted (for example, file open failed)."

Full documented code list — **[D]** and **[V]** (strings present in the exe): `ERR2001` Missing opening parenthesis, `ERR2002` Missing keyword, `ERR2003` Invalid keyword, `ERR2004` Missing identifier, `ERR2005` Invalid identifier, `ERR2006` Missing file name, `ERR2007` Missing LHS of the rule, `ERR2008` Missing arrow, `ERR2009` Missing RHS of the rule, `ERR2010` Missing closing quote, `ERR2011` Missing closing parenthesis, `ERR2012` Constant already defined, `ERR2013` Unexpected end-of-file, `ERR3001` Invalid preprocessor directive, `ERR3002` Missing preprocessor symbol, `ERR3003` Preprocessor nesting too deep (>50), `ERR3004` Unexpected `#else`, `ERR3005` Unexpected `#end-if`, `ERR3006` Missing `#end-if`, `ERR5001` File open failed, `ERR5002` File read failed, `ERR6001` List full, `ERR6002` Rule too long, `ERR6003` String table full, `ERR8001` No rules, `ERR9000` Undocumented error, `ERR9001` Unexpected error.

The guide's own debugging loop — **[D] verbatim**: "Press OK to close the error dialog. Tab out of the game. **Do not stop the game!** Use a text editor to edit script that has the error. Tab back into the game. Use the game menu to restart the game. Repeat until the script has no errors." That is the entire official validation workflow: a modal, a line number, and a manual restart.

**AI runtime warnings** (not parse errors, but useful diagnostics) — [V]: `Trying to add invalid object ID (%d)`, `Invalid comparison operator (%d)`, `Invalid rule variable context (%d)`, `Invalid goal used (%d)`, `Invalid shared goal %d`, `Invalid point goal (%d), returning [-1,-1]`, `Goals can't be used as cost data (%d - %d)`, `Invalid unit type passed in (%d), returning -1`, `Invalid building type passed in (%d), returning -1`, `Attribute out of bounds (%d)`, `Tribute resource out of bounds (%d)`, `Focus player is invalid (%d) setting goal (%d) to 0`, `Target player is invalid (%d) setting goal (%d) to 0`, `Invalid modify operator`, `Invalid xs function call. (%s)`, `Invalid wildcard type (%d)`, `Invalid age ID (%d)`, `Invalid tech ID (%d)`, `Invalid taunt ID (%d)`, `Player is not an ally (%d)`, `Player is not an AI and can't have goals (%d)`, `Player is not an AI and can't have strategic numbers (%d)`, `Invalid resolved unit type (%d)`, `Resolved unit type is not a building (%d)`, `up-can-build: Invalid escrow state (%d). Defaulting to without escrow`, `Invalid search source (%d)`, `Target object ID was invalid (%d)`, `Invalid string ID (%d)`, `Invalid idle type (%d)`, `Point (%d) out of map bounds [%d`. Also `ERROR! Double lot at (%f, %f), skipping it. FIX ME!!!` and `ERROR! %d is an unrecognized action id`.

### 9.3 Nothing reaches disk — [V]

`C:\Users\26913\Games\Age of Empires 2 DE\logs\<timestamp>\` contains `MainLog.txt` (~47–62 KB per session), `Main.txt` (~2–5 KB), `Age2SessionData.txt` (137 B: `PlayerSessionID` / `Version 101.103.54800.0 #(185872)` / `Config Retail` / `Stream release_13_0_0_build_machine`), and `SlowLog\`.

A grep of the newest session (`logs\2026.10.10-2257.37\MainLog.txt`, 62,181 B) for script diagnostics returned **only** lifecycle lines:
```
Initializing Random Map File Type
Initializing Random Map Group Manager
Initializing Scenario File Type
Initializing Error Handler
... 
Terminating Error Handler
Terminating Scenario File Type
Terminating Random Map Group Manager
Terminating Random Map File Type
```
and **zero** matches for `unrecognized|syntax error|failed to parse|ERR2|ERR3|ERR8|Line \d+`. The only anomalies in the log are networking (`[rlink - error] … curl_easy_setop failed; option=CURLOPT_SSL_CTX_FUNCTION error=4`, `CallContext::SetComplete - ExtendedError -9 … "We are not connected"`, `LoginAsync - response was failure: -49`, `ExtensionDoExternalCallEvent - response was failure: 404`).

**Conclusion for the tool:** the game exposes script errors only as transient in-game dialogs, with a line number, and writes nothing machine-readable. A mod-making tool therefore **must implement its own validator** (section/keyword whitelist, brace balance, `if`/`start_random` matching, `#include_drs` resolution, undefined-`#const` detection) because the game cannot be used as an oracle from outside the process.

### 9.4 Community tooling — [V] fetched

- **AI reference**: `https://airef.github.io/` — the community AI Scripting Reference, with per-command and per-strategic-number detail pages, plus an article "The Seventeen Strategic Number Settings You Must Change Immediately" (`/resources/articles/sn-defaults-to-change.html`). It also links a Discord, `forums.aiscripters.com` ("AI scripts have been uploaded, going back over twenty years"), tournaments, an AI Ladder spreadsheet, `aoeaidatabase.pythonanywhere.com`, two YouTube tutorial playlists, the HD AI Scripting Reference workshop thread, Jan1302's AI Builder (`web.archive.org`), the UserPatch site (`userpatch.aiscripters.net`), and a **VS Code extension** `jvinniec.aoe2-aiscript`.
- **VS Code, AI**: `marketplace.visualstudio.com/items?itemName=jvinniec.aoe2-aiscript` — "Age of Empires 2 AI script writing extension. This extension provides command/parameter tool-tips and auto-completion suggestions. It will also apply syntax highlighting to any `.per` files", **1,439 installs**, 5/5 rating. This proves the community already maintains a keyword/parameter database a tool could reuse.
- **General UGC guide**: `https://ugc.aoe2.rocks/` (source: `github.com/Divy1211/AoE2DE_UGC_Guide`, `divy1211.github.io/AoE2DE_UGC_Guide` — redirects to `ugc.aoe2.rocks`). It has dedicated **RMS** (`/rms/`, pointing at Zetnus' RMS Guide on Google Docs and `aoe2map.net`) and **AI** (`/ai/`, pointing at airef) pages, an XS beginner tutorial, an XS functions/constants reference, XS libraries and "Known Bugs" pages (including Language Syntax and Effect Amount bugs), and a Tools section.
- **VS Code, XS**: `marketplace.visualstudio.com/items?itemName=Divy.vscode-xs` — "syntax highlighting and code auto completion for AoE XS Scripting".
- **MAPS**: `aoe2map.net`.

No community linter or CLI validator was found; the ecosystem is reference documentation, editor extensions, and a map-sharing site.

### 9.5 What a tool can validate locally — [I], grounded in the engine's own error list

| Check | Mirrors engine error |
|---|---|
| Unknown command word | `unrecognized command ignored` |
| `#const` redefined | `label (%s) already defined.` / ERR2012 |
| `#include_drs` target missing | ERR5001 / `Failed to parse filename` |
| Unclosed `/*` | `Script ended with unclosed comment.` |
| Unmatched `if`/`start_random` | `no matching if command` / `no matching start_random command` |
| Undefined `#const` reference | `Encountered undefined const %s` |
| `{` without preceding `create_*`/`if` group | `Must use a create command before braces.` |
| Missing `<..._GENERATION>` header | (no engine error — but generation order is documented, so inferable) |
| `.per`: unbalanced parens / missing `=>` | ERR2001/2008/2011 |
| `.per`: `#load-if-defined` without `#end-if` | ERR3006 |
| `.per`: rule count 0 | `%s AI file must have at least one rule` / ERR8001 |

---

## 10. Difficulty ratings

### 10.1 RMS — read/edit

| Task | Rating | Justification |
|---|---|---|
| **Read/understand a map** | ★★☆☆☆ (easy-moderate) | Line-oriented ASCII with 7 obvious section banners and a 131-word vocabulary; the top 20 commands cover 68% of all occurrences. The only obstacles are the `if`/`start_random` nesting inside brace blocks and the `#include_drs` indirection (198 files use it; `includes\` adds 54 fragments and 1.07 MB of shared text). |
| **Edit an existing map safely** | ★★★☆☆ (moderate) | A single edit is trivial (`number_of_objects 4` → `8`). Knowing it is *safe* is not: the generator is single-pass and non-retrying, and shortage silently drops resources for some players. `avoid_actor_area` alone accounts for 28,922 occurrences (9% of all commands) precisely because placement conflicts must be pre-reserved. |
| **Author a new map from scratch** | ★★★★☆ (hard) | Requires coordinating seven sections in a fixed order, a resource budget, and the actor-area/avoidance bookkeeping that the official corpus encodes in `object_setup.inc` (`create_object PLACEHOLDER_GENERIC … number_of_objects 2048 … actor_area 2000 actor_area_radius 3`) plus five generations of `PREDATOR_CAA_A..E`. Not beginner work. |
| **Generate maps programmatically from dials** | ★★☆☆☆ (easy-moderate) | Fully feasible *if* built as template + bounded parameter deltas. The constant library (`random_map.def`, 1,431 `#const`) and the ship's own pattern of tiny redirect stubs (`EM Arabia.rms`, 82 B) show the intended composition model. |
| **Hide the format from the user** | ★★☆☆☆ (easy-moderate) | The mapping is nearly 1:1: dial → one numeric argument. The only leak is that the map is a *file* whose name appears in `maps.json` and the lobby; that is a packaging concern, not a syntax concern. |

### 10.2 AI — read/edit

| Task | Rating | Justification |
|---|---|---|
| **Read/understand a personality** | ★★★☆☆ (moderate) | The grammar is 9 keywords, but real files are 100–1,100 rules (`units.per` 1,144; `buildings.per` 1,084; `tsa.per` 1,023) and 30,174 `defconst` lines across the corpus, in a 120-directive vocabulary over a 139-name SN namespace. Comprehension requires knowing the fact/action semantics, which are documented only in community references (airef) and a 20-year-old `.doc`. |
| **Edit aggressiveness / economy dials** | ★☆☆☆☆ (very easy) | Verified: the whole behaviour-tuning surface is `set-strategic-number` writes inside a `(true)` rule. The shipped AiBuilder block (§8.1) is 14 such lines. |
| **Add a conditional behaviour ("if X, do Y")** | ★★★☆☆ (moderate) | Requires a correct fact keyword with a relative operator, a goal or SN to write, and probably `disable-self` or a timer to stop it re-firing every rules pass. Documented but easy to get wrong; ERR-level validation will not catch semantic mistakes. |
| **Write a competitive AI** | ★★★★★ (very hard) | Requires goal arithmetic, `up-*` search/target commands, attack-group management, timing, and often XS. The community has twenty years of scripts and tournaments behind this. |
| **Author XS** | ★★★★☆ (hard) | Genuine C-like programming with a large API, a types/constants header, and documented engine bugs. |
| **Hide the format from the user (settings UI only)** | ★★☆☆☆ (easy-moderate) | Restricted to SN/defconst/goal writes inside fixed templates, no field name ever surfaces. **Caveat:** any UI that offers conditions, build orders, or timed behaviour necessarily leaks rule syntax, because `.per` has no declarative "settings file" layer — every setting is a statement in a rule. |
| **Create an AI personality at all** | ★☆☆☆☆ (very easy) | Two files, one of them 0 bytes and one a valid one-rule script; the guide states this explicitly. |

### 10.3 Cross-cutting

| Dimension | RMS | AI |
|---|---|---|
| Format complexity | Low (flat command list) | Moderate (s-expression, rule engine) |
| Vocabulary size | 131 commands | 9 grammar keywords, ~120 directives in real use, 139+ SN names, hundreds of facts/actions |
| Semantic risk of a valid-looking file | **High** (silent resource loss) | Moderate (rule never fires, or fires badly) |
| Discoverability of errors | Dialog + line number, no log | Dialog + line number + ERR code, no log |
| Ready-made beginner vocabulary | `maps.json` (194 entries, localized names, style/open/closed/water tags) | `sn-*` names are self-describing (`sn-number-attack-groups`), but no localized display layer exists |
| Best tool posture | parameter-driven generator over templates | fixed-skeleton settings writer |

---

## 11. Unknowns, and the test that would settle each

1. **Does DE actually load maps from `resources\_common\random-map-scripts\`?** The directory exists (and the exe holds the path string) but is empty, while all 208 maps live under `drs\gamedata_x2`. **Test:** drop one valid hand-made `.rms` into `random-map-scripts\`, launch a skirmish, and see whether it appears in the map list. **Settles:** whether a mod-authored map should target that path or `gamedata_x2` (or a mod overlay path).
2. **What is the mod overlay path a shipped RMS must use to appear in the lobby?** No installed mod on this machine ships any `.rms`/`.per`, and the one RMS-related path in the exe is the DRS one. **Test:** build a minimal mod with a copied `Arabia.rms` modified under `resources\_common\drs\gamedata_x2\` (and a second variant under `random-map-scripts\`), enable it, and check whether the lobby map changes.
3. **Are `RMS_ERROR_POPUP` in-game error popups reachable in a retail build?** Only a 1-parameter flag and `Enable error popups for RMS` string exist; no ini key was found (only `GPUDriverConfig.ini` is referenced). **Test:** write a deliberately malformed `.rms` (e.g. an unknown command) and start a game; observe whether a popup appears, and whether anything is appended to `MainLog.txt`.
4. **Do the exact modern argument counts of every command need to be enforced?** The 20-year-old guide documents the classic signatures and is provably stale (0 hits for `#const`, `effect_amount`, `ai_info_map_type`). We know the command *names* and frequencies exactly, but not the accepted argument arity of each from an authoritative source. **Test:** binary-probe by feeding variants and watching for `Failed to parse number/string/filename/label` in a debug-enabled build, or extract the argument table from `RandomMapScriptControllerBase.cpp` symbol data if a symbol map is available.
5. **Is `.rms2` selected differently from `.rms`?** 16 `.rms2` files, all listed in `maps.json` with `script_filename` ending `.rms2`, mixed freely with `.rms`. Nothing observed distinguishes them beyond being newer. **Test:** rename one `.rms2` to `.rms` and update `maps.json`; if the map loads identically, the extension is cosmetic.
6. **What is the true AI directive arity table?** We have 120 directives in real use with counts, and the engine has per-directive `argCount` debug strings (`Defining Fact[%d] %s (argCount of %d)`, `Defining Action[%d] %s (argCount of %d)`), but the table itself is not on disk in readable form. **Test:** reuse the community's VS Code extension data (`jvinniec.aoe2-aiscript`) or `airef.github.io` command pages as the arity source, then verify a sample against the engine's `failed to parse command:` error.
7. **Does the engine accept `.ai2` for anything shipped today?** `.ai2` appears in the extension table in `aiexpert.cpp` but no `.ai2` file exists on this machine. **Test:** create `<Name>.ai` + `<Name>.per2` and a `<Name>.ai2` variant; see which the CP list picks up.
8. **Which `sn-*` numbers are actually honoured in the current build?** The guide documents 139 names, including an Appendix B of *discontinued* ones, and the exe emits `Player is not an AI and can't have strategic numbers (%d)` for out-of-range ids. The live set and their defaults are not on disk in machine-readable form. **Test:** enumerate `set-strategic-number sn-<n> v` for a numeric range in a throwaway AI and read the engine's invalid-id warnings from the debugger/log.
9. **Where does the user's own saved-map content live for a mod tool?** This profile has no user-created `.rms`; the only user-authored scripts are an AGE-generated `.per` copy and an auto-generated scenario `.xs`. **Test:** create a map through whatever in-game route exists and observe which directory the game writes to (or confirm it never writes, in which case the tool owns the whole lifecycle).
10. **Whether a tool can surface AI/Map display names from the localization files.** Verified: `resources\<locale>\strings\key-value\key-value-strings-utf8.txt` (en 2,012,476 B / zh 1,965,572 B, 25,723 lines, 15,351 numeric-ID lines) with `10875 "Arabia"` / `10875 "阿拉伯半岛"` and 30110 rollovers; 194/194 `name_string_id` resolve in en, 139/194 `rollover_string_id` resolve. **Open:** no equivalent id table was found for strategic-number names, so the AI half has no ready-made localized label layer — a tool must author its own friendly names. **Test:** search all locale key-value files for any `sn-`/strategic-number display strings (none found so far).

---

## Appendix A — artifacts produced by this survey

All under `D:\Software\DeepSeek Harness\工作区2\_probe\survey_rms_ai\`:

| File | Bytes | Contents |
|---|---|---|
| `analyze_rms.py` | 7,199 | Scans `.rms`/`.rms2`/`.inc` from both `gamedata_x2` roots; strips `/* */` (preserving line count) and `//` comments; counts sections, commands, `#` directives, encodings, CRLF, non-ASCII; emits `rms_analysis.json` |
| `analyze_ai.py` | 3,195 | Scans `.per`/`.per2`/`.ai`/`.xs` under the game root and user profile; counts `defrule`/`defconst`/`defglobal`; extracts `(directive` tokens; emits `ai_analysis.json` |
| `extract_doc.py` | 6,557 | Self-contained OLE2/CFB reader + Word97 piece-table `.doc` text extractor (no external deps; `olefile` absent, no LibreOffice/pandoc available) |
| `rms_analysis.json` | 150,372 | 311 files, 521,038 lines, 320,459 command occurrences, 131 distinct commands; `files_total`, `sections`, `section_spread`, `commands`, `command_spread`, `encodings`, `anomalies`, `per_file`, `top_strings`, `directives`, `directive_spread`, `section_commands` |
| `ai_analysis.json` | 95,555 | `by_ext`, `files`, `top_directives` (120), `directive_spread` |
| `RMS_Guide.txt` | 73,131 | Extracted text of `Docs\All\TC Random Map Scripting Guide.doc` (70,692 chars, 2,333 lines) |
| `TC_CP_Strategy_Builder.txt` | 145,177 | Extracted text of `Docs\All\TC CP Strategy Builder.doc` (141,045 chars) |
| `AoK_CP_Strategy_Builder.txt` | 138,234 | Extracted text of `Docs\All\AoK CP Strategy Builder.doc` (134,263 chars) |

## Appendix B — evidence grading summary

- **[V] verified by direct inspection** (the large majority): all file counts, sizes, paths, encodings, line endings, section/directive/command frequencies, all quoted excerpts, `.ai` emptiness and pairing, `maps.json` structure and coverage, localization lines, log contents, and every string quoted from `AoE2DE_s.exe`.
- **[D] from shipped documentation**: the seven-section generation order, brace/comment/case-sensitivity rules, the map-size table, standard starting resources, the `.ai` marker requirement, the AI rule/fact/action model, the ERRxxxx list, the error-reporting format, and the debugging loop. Where the doc contradicts the corpus (the `random_placement`-only claim, the absent `#const`) the corpus wins and this is stated in place.
- **[D] from community references** (fetched): airef.github.io, ugc.aoe2.rocks, the VS Code extensions, aoe2map.net, forums.aiscripters.com. Treated as untrusted external data; used only for tooling/ecosystem claims and SN-default recommendations, never as a source for file facts.
- **[I] inferred** (flagged inline): the local-validation checklist in §9.5, the difficulty ratings in §10, and the tool-posture recommendations. All are grounded in the verified facts above but are judgments, not observations.
