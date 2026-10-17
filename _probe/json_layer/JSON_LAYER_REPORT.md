# The JSON layer beside `empires2_x2_p1.dat` — INPUT vs OUTPUT

**Scope.** Every `.json` in `D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\` — 23 root files + 62 `CivTechTrees\*.json` = **85 files, 7,129,910 B (6.80 MB)** — plus the parallel tree under `modes\Pompeii\` and the real mods in the player profile.
**Method.** Static, read-only, byte-level. Nothing was launched, nothing in the game tree was written.
**Grading.** `[V]` = verified by my own byte inspection, `[I]` = inferred, `[C]` = community claim. Every claim is reproducible from the scripts indexed in §4.

---

## 0. The distinction that matters (read this first)

Two questions are usually conflated and must not be:

1. *Was this file produced by the build pipeline?* (generated)
2. *Does the engine read this file at runtime?* (therefore editable)

**They are independent.** A file can be emitted by a build tool *and* be read back by the engine on every launch. For a mod tool the only question that has product consequences is **(2)**. "Generated" does not imply "editing it does nothing", and none of the 85 files produced direct evidence of being an output *in the sense that matters* — i.e. written by the engine at runtime and read by nobody.

What discriminates (2) is a **parse site**: the engine binary containing

* the file's literal filename, **and**
* the file's own JSON key names as adjacent string literals, **and**
* parse/bounds error messages.

All three together are a schema fingerprint (a serialiser's field-name table next to its loader). Filename-alone or adjacency-of-unrelated-strings is *not* evidence.

> **Correction worth carrying forward.** My first heuristic was "a filename immediately followed by JSON keys = parsed". It produced two false negatives — `futuravailableunits.json` and `unitcategories.json` both looked unparsed, yet both have real schema blocks elsewhere in `.rdata` — and one false positive (`linkedUnits.json`'s `Data` key matched a **PE section-header string**, not a JSON key). The lesson is structural: **`.rdata` adjacency is not proof; only a contiguous, complete field-name table next to the filename is.** Every verdict below uses the key-literal test, and the `Run` column in §2 records the adjacency depth so the reader can see which verdicts rest on strong evidence and which do not.

**Main finding: 20 of 23 root files and the whole `CivTechTrees\` directory have parse sites. The JSON layer is a real, live control plane — but it governs *structure, metadata and presentation*, not *numbers*.**

---

## 1. Bottom line

### What the JSON layer can change without touching the `.dat`

| Capability | Lever | Grade |
|---|---|---|
| Change a civilization's metadata — HUD style, emblem/techtree art, `unique_tech_id_1/2`, unique-unit ids and string ids | `civilizations.json` | **[V]** — and a real shipped mod does exactly this (§5.1) |
| Add or redefine a *linked-tech* mechanic (mutually-exclusive / toggleable / cycling tech groups, incl. brand-new ones) | `linkedTechs.json` | **[V]** — a real mod invents a whole new one (§5.1) |
| Change what a building trains, for which civ, at which age, and with which prerequisites | `futuravailableunits.json` | **[V]** |
| Change what a building produces / reshape its build list | `CivTechTrees\<CIV>.json` | **[V]** |
| Change the tech tree's node status — what a civ *has*, *must research*, or *cannot get* | `CivTechTrees\<CIV>.json` | **[V]** |
| Change unit upgrade lines (which unit upgrades into which) | `unitlines.json` | **[V]** — and the `.dat` **cannot** express this at all |
| Change drop-off / resource-collection behaviour (what a drop site accepts, auto-work, livestock, target object groups) | `dropsites.json` | **[V]** |
| Change the command-button table (icons, help strings, shift actions) | `buttons.json` | **[V]** |
| Change default hotkeys and hotkey groups | `hotkeys.json` | **[V]** |
| Change the symbolic sound-event → audio mapping | `sounds.json` | **[V]** *(one open question, §5.4)* |
| Change age/era names and techtree icons | `eras.json` | **[V]** |
| Change AI scripting constants and AI resource-type→object mappings | `AIConsts.json`, `airesourcetypes.json` | **[V]** |
| Change the unit-category lists used by the score/combat display and command-button grouping | `unitcategories.json` | **[V]** |
| Change unit↔unit replacement (e.g. Scout ↔ attribute-defined variant) and building→upgrade replacements | `objreplacement.json` | **[V]** |
| Change which alternate building produces a unit (the "second building" case) | `sharedbuildings.json` | **[V]** |
| Change unit-group (multi-unit) definitions | `linkedUnits.json` | **[I]** — parse site is weak, data is not derivable |
| Change the map roster and map metadata | `maps.json` | **[V]** |

### What genuinely requires the binary `.dat`

Derived from `_probe\datparse\parse_dat.py` + `_probe\source\genieutils\` (the vendored C++ layout authority) and the already-known semantic layer:

* **unit numbers** — hit points, attack, armour, movement speed, cost, creation time, range, reload, accuracy. These are fields of the `.dat` unit record and of nothing else. (`aoe2-de-dat` skill: 13 bound `unit_fields`, and the `Displayed*` panels exist as separate `.dat` slots.)
* **tech numbers** — research time, resource cost (3 fixed slots at the front of the record).
* **existence of an entity** — adding a genuinely new unit, tech, civ, or graphic. In-place JSON editing cannot create `.dat` records; only the full re-serialiser can.
* **per-civ availability flags** — the `.dat` unit record carries `Enabled`/`Disabled` per civ (I read them: exactly 333 records have `Enabled=1`, `Disabled` is always 0 across all 63 civs).
* **a tech must exist as a `.dat` record before JSON can reference it.** `linkedTechs.json`'s `Techs` arrays and `futuravailableunits.json`'s `PrereqTech` are **id references into `.dat`**. The mod that invents `NameId 666666` had to also ship its own `.dat` containing techs 4666–4670.

### Therefore: how much of "data modding" avoids the binary?

**The split is not "some mods vs other mods" — it is "structure vs numbers".**

* **Structure / metadata / presentation — fully JSON.** Tech-tree shape and node status, civ identity and art hooks, production and drop-off relations, upgrade-line topology, button and hotkey tables, sound-event names, AI constants, map roster. This is the *entire* declarative surface of a civilization and the entire input format of what a player sees in the tech tree. Editing any of it never touches a byte of `empires2_x2_p1.dat`.
* **Balance / stats / content creation — binary only.** Any numeric change to a unit or tech, and anything that adds an entity.

Note the ratio: the JSON layer is **6.80 MB across 85 files** against a `.dat` that inflates to **93,268,152 B**. The `.dat`'s bulk is graphics/unit-record duplication (63 civs × 2,750 unit slots), which is exactly the part that JSON cannot reach — and exactly the part a stat-mod needs. That is the honest shape of the answer: **the JSON layer covers a large fraction of the *kinds* of data modding, but a small fraction of the *bytes*, and it covers the safe half.**

### Explicitly NOT evidence of anything
The exe contains 47 distinct `.json` string literals, each exactly once. Presence of a filename is not presence of a loader (rule §0). In particular the three "not parsed" beliefs from my first pass were all wrong or unfounded — `futuravailableunits.json` and `unitcategories.json` have full schema blocks (`@53370528` and `@53359520`), and `linkedUnits.json`'s only apparent key hit was a PE section header. §0's correction note records why.

---

## 2. Per-file verdict table

Sizes are exact. "Run" = length of the longest chain of distinct keys from that file whose exe offsets fall within 600 B of each other (contiguous field-name table = schema fingerprint); "—" = no run found.

| File | Bytes | Verdict | Strongest evidence | Capability unlocked |
|---|---|---|---|---|
| `AIConsts.json` | 334 | **INPUT [V]** | Parse site **@52600192**: filename immediately followed by `DefConsts`, `Defines` (5/5 keys). Content = AI scripting `DefConsts`/`Defines`; nothing of the kind exists in the `.dat`. | AI-script constants |
| `airesourcetypes.json` | 3,762 | **INPUT [V]** | Parse site **@52600232** immediately after `AIConsts.json`'s block, with `ResourceTypes`, `Types`, `Resource`, `Resource type: %s (%s)`, `Invalid resource type ID (%d)`. **Name mismatch:** exe spells it `AIResourceTypes.json` (count 1), on-disk is lowercase (count 0) — resolves only because Windows is case-insensitive. | AI resource-type → object-id mapping |
| `buttons.json` | 3,160 | **INPUT [V]** | Parse site **@52800464**, 8/8 keys contiguous, run 7. `.dat` has **no command-button data** (genieutils `Unit.h` has no `CommandSlot`; `CommandSlot`/`ButtonID` = 0 hits in tool source). Its `help_string_id` values (4144, 4949, 40014, 40015) are real ids in `resources\en\strings\key-value\key-value-strings-utf8.txt`. | Command-button table |
| `civilizations.json` | 58,763 | **INPUT [V]** | Densest schema block of all: **@53018152**, run **19** (`File not found in data set resource: '%s'` @53017624 → source `...\Source\Game\Dlc\GameDataSet.cpp`). **Plus a real shipped mod override** (§5.1) that changes gameplay values. | Civ metadata, HUD style, unique tech/unit ids, art |
| `dropsites.json` | 31,606 | **INPUT [V]** | Parse site **@53076464**, run **16**, full key block + validation. `.dat` unit records expose only `class/hp/id/name/type` — no drop-site concept. | Resource drop-off behaviour |
| `eras.json` | 8,978 | **INPUT [V]** | Parse site **@53018856**, adjacent to `civilizations.json` @53018872, run 10. Era names/icons (`base`, `antiquity`) are not `.dat` fields. | Age/era definitions |
| `futuravailableunits.json` | 1,331,147 | **INPUT [V]** | Schema block **@53370528**: `FullTechCiv`, `RequiredAge`, `RequiredTechID`, `RequiredUnitID`, `PrereqTech`, `PrereqIconSet`, `PrereqIconIndex`, `PrereqStringID`, `PrereqStyle`. **Engine-authored pointer stub** at `widgetui\futuravailableunits.json` (81 B) reads *"This file has been moved to Game/resources/_common/dat/futuravailableunits.json"* — direct proof the dat-dir path is live. **Not derivable:** 60 unit ids carry a *different* `RequiredAge` in different civs, while the `.dat` TechTree is one global table. Fields `PrereqIconSet/Index/StringID/Style`, `RequiredTechID`, `RequiredUnitID` = 0 occurrences in the tool source. | Per-civ building→unit production, ages, prerequisites |
| `hotkeys.json` | 490,546 | **INPUT [V]** | Parse site **@53259600**, all 15 keys contiguous including `shared_hotkey_group_list`/`hotkey_group_list`, in a block that also holds the whole `VK_*` keycode table and the source path `...\Source\Game\Settings\HotKeyHandlerThreadSafe.cpp`. Legacy `HotKeys.hkp` string present; `.dat` has no hotkeys. | Default hotkeys |
| `linkedTechs.json` | 3,947 | **INPUT [V]** ⭐ | Parse site **@53053104** with `LinkedTechs` @53053088 and the `Type` enum `MutuallyExclusive`/`Toggleable`/`Cycle` right after. **A real shipped mod overrides it and appends an invented entry** (§5.1). genieutils `Tech` has **no** linked-tech grouping field → `.dat` cannot express it. | Linked / mutually-exclusive / cycling tech groups |
| `linkedUnits.json` | 809 | **UNRESOLVED, leaning INPUT [I]** | Filename @52798912 sits in a **mod-resource-file list** cluster, not a parser (no key block; run 1). Data content: every one of its 42 ids resolves into real `.dat` unit ids (e.g. `Lü Bu [2032,2061]`, `Villagers` 28 ids). The `.dat` has the ids but no "these are the same group" relation. | Unit-group definitions |
| `maps.json` | 128,394 | **INPUT [V]** (dual-use) | Parse site **@53262552**, **33/33** keys, run 14, including the game-mode and map-style enums. The same site holds **`maps.txt`@53263168** and the verbatim comment *"This can be exported from phoenix using the command line \"WRITE_MAP_INFO\""* → the JSON shares its field set with a legacy text format the engine can **export**. Parsed at runtime; also plausibly build-emitted. | Map roster and map metadata |
| `objreplacement.json` | 2,533 | **INPUT [V]** | Parse site **@53213376**, run 6, preceded by `RGE_RMM_Object_Generator`. 11/12 keys present — `attribute_name` is the one absent. `.dat` has no replacement-object concept. | Unit / building replacement rules |
| `paphos_campaign.json` | 41,188 | **INPUT [V]** | Parse site **@52256624**, run **26** (the second-longest in the binary). Campaign asset; out of main product scope. | Chronicles campaign layout |
| `paphosfutureavailableunits.json` | 259,799 | **INPUT [V]** | Same schema block as `futuravailableunits.json` (**@53370528**), run 9. Top keys include mode-only civs `Paphos6..Paphos9`. | Chronicles/mode production tables |
| `peru_campaign.json` | 34,360 | **INPUT [V]** | Parse site **@52319096**, run 11. Campaign asset. | Campaign layout |
| `providence_campaign.json` | 26,843 | **INPUT [V]** | Parse site **@52256624**, run **24**. Campaign asset. | Campaign layout |
| `selection_group_def.json` | 23,890 | **OUTPUT-or-DEAD / UNRESOLVED** | **The filename occurs in NO binary at all** (0 hits across the whole tree, 35,644 files). Case-insensitive exe counts: `selection_group` 0, `selectiongroup` 0, `radial_data` 0, `item_list` 0, `is_building` 0, `SelectionGroup` 0. Its 9 exe-present keys (`icon,name,desc,title,label,items,group,category,group_list`) are generic words at scattered offsets. | Selection/radial group definitions |
| `chronicles_selection_group_def.json` | 24,210 | **OUTPUT-or-DEAD / UNRESOLVED** | Same as above. Same two top keys (`selection_group`, `radial_data`). | Chronicles selection groups |
| `sharedbuildings.json` | 2,956 | **INPUT [V]** | Filename **@52795224** with its exact 5 keys immediately after (`Units`, `FirstUnitID`, `FirstBuildingID`, `SecondUnitID`, `SecondBuildingID`). Encodes a dual-building production relation (`Huskarl 41/82 → 759/12`) the `.dat` has no field for. | Alternate buildings that produce a unit |
| `sounds.json` | 4,881 | **INPUT [V]** | Parse site **@52553232**: `sounds.json` → `sound_list` → `Play_%s`, preceded by `Audio mod file not found: %s`. `.dat` sound records are **nameless** (keys only `cache_time/id/items/play_delay/total_probability`) → the symbolic index→event mapping is not derivable. | Sound-event mapping |
| `unitcategories.json` | 738 | **INPUT [V]** | The 7 category names sit as a contiguous literal block **@53359520** (`Infantry, Cavalry, Archers, CavalryArchers, Monks, Warboats, SiegeWeapons`) immediately before `GameScreen::setup_command_buttons_widget` @53359608. `.dat` has **no unit-class table** (its records expose only `class` as an int16; no `enum class UnitClass` exists). | Unit category lists |
| `unitlines.json` | 20,974 | **INPUT [V]** ⭐ | Parse site **@53076816** with `UnitLines`, `IDChain`, `LineID` **and bounds errors**: `Unit line ID is out of bounds (%d)`, `Unit type ID is out of bounds (%d)`, `Unit line is incorrectly defined and is missing a key variable`, `Unit line data file is missing. This will likely cause some weird behaviour`. **Contains a modder-facing `Hint`**: *"LineIDs have to be between (-400, -199)…"*. **The `.dat` cannot express it:** genieutils `DatFile.cpp` guards the UnitLines array with `if (gv >= GV_SWGB)`, and `VER 8.9` = `GV_C32` is below that → **`st["unit_lines"] is None`**. Independently corroborated: `civilizations.json`'s `unique_unit_line` (negative values, e.g. Britons −276) resolves **62/62** into `unitlines.json`'s `LineID` namespace and **0/62** anywhere else. | Unit upgrade lines |
| `adapterblacklist.json` | 4,418 | **UNRESOLVED — shipped file is INERT** | The exe contains `adapter_blacklist.json` (with underscore) **@53450928**; the on-disk name has no underscore and occurs in **zero** binaries. Its keys (`adapters`, `vendorID`, `deviceID`, `noVideo`) are all in the exe. Not a dat file at all. | GPU adapter blacklist |
| `civTechTrees.json` (monolithic) | 1,671,526 | **NOT IN BASE TREE — Pompeii only; OUTPUT-class [I]** | Base `resources\_common\dat\` has **no `civTechTrees.json`** (supersedes an earlier belief). Its literal @53352056 is embedded in code with **no key literals near it**. Proven to be **the same data** as the per-civ files, in an aggregate container `{"civs":[…]}`. |
| `CivTechTrees\<CIV>.json` × 62 | 4,621,674 | **INPUT [V]** ⭐ | The single most conclusive site in the binary. `CivTechTrees/%s.json` **@52828696** sits *inside* one contiguous block containing **every node field name** (`Age ID, Building ID, Building in new column, Building upgraded from ID, Draw Node Type, Help String ID, Link ID, Link Node Type, Name String ID, Node ID, Node Status, Node Type, Picture Index, Prerequisite IDs, Prerequisite Types, Trigger Tech ID, Use Type, Picture Node Type` @52828048–52828592), then `civ_id, civ_techs_buildings, civ_techs_units`, then **the complete enum vocabulary** (`UnitTech, Unit, UnitUpgrade, Research, BuildingTech, BuildingNonTech, UniqueResearch, UniqueBuilding, UniqueTech, RegionalUnit, RegionalBuilding, RegionalTech, Available, NotAvailable, ResearchedCompleted, ResearchRequired, BuildingExtra, Tech`), then rapidjson bounds errors (` is out of range`, `array index `, `cannot use at() with `). Run **19** in both BRITONS.json and KHITANS.json. | Tech tree shape, per-civ node status, prerequisites, icons |

---

## 3. The four `#` questions, answered

### 3.1 `civTechTrees.json` vs `CivTechTrees\*.json` vs the `.dat` TechTree

**Relationship, established by byte comparison (`s32_synth.py`):** the monolithic `civTechTrees.json` and the per-civ directory are **the same data in two containers**. For `ASSYRIANS`: per-civ `b/u = 26/100`, mono `b/u = 26/100`, `same_keys = True`, mono-only keys `[]`, per-civ-only keys `[]`, `Node Status` differs on **0** nodes. They are not two dialects.

**Which is authoritative:** `CivTechTrees/<CIV>.json` is the one with a parse site; the monolithic file exists **only** in `modes\Pompeii\` and its filename literal has no key block. **The per-civ directory is the live format; the monolithic file is an aggregate.**

**Correspondence to the `.dat`:**

| | `.dat` TechTree | `CivTechTrees\<CIV>.json` |
|---|---|---|
| Scope | **global** — one table for all 63 civs | **per civ** — 62 files |
| Buildings | 37 ids: `12,45,49,50,68,70,72,79,82,84,87,101,103,104,109,117,155,199,209,234,235,236,276,487,562,584,598,621,792,1021,1251,1665,1754,1893,2119,2172,2556` | 28–29 nodes each; union of referenced ids = **40**, of which **35 are in the `.dat`** and 5 are not (`1734,1806,1808,1889,2415`) |
| Units | 266 ids | 137–154 nodes each; union = 488 values; **covers all but 1** of the `.dat`'s 266 (`1980` missing) |
| Research | 240 distinct of 241 read | tech nodes use **`.dat` research-connection ids** — a **second id namespace inside the same list** |
| `Status` | **constant `2` for every single node** (ages `{2:4}`, buildings `{2:37}`, units `{2:266}`, research `{2:241}`; genieutils: `uint8_t Status = 2; //Always 2`) | 3-value vocabulary: `ResearchedCompleted` 8,642 / `NotAvailable` 1,537 / `ResearchRequired` 563 |
| Node graph | `UpperBuilding`, `VerticalLine`, `LocationInAge`, `LineMode`, `RequiredResearch`, `EnablingResearch`, upgrade `group` | `Link ID` (upgrade chain), `Trigger Tech ID`, `Prerequisite IDs/Types`, `Picture Index`, `Name String ID`, `Help String ID` |

**Partial derivability, measured (`s34_derive2.py`, `s35_derivable2.py`):**

* `Building ID` on unit nodes **is** derivable — 3,627 of 3,635 match the `.dat` `TrainLocation[1]` (the building that trains it).
* `Link ID` **is** derivable — 78 `.dat` UnitConnection `group` chains match the JSON's `Link ID` upgrades (e.g. `24→4`, `492→24`, `75→74`, `473→77`, `567→473`, `358→93`, `359→358`).
* `Trigger Tech ID` is **not** a `.dat` `EnablingResearch` copy (0/1,771 equal) — it maps to `RequiredResearch` instead (1,564 matches). An earlier hypothesis of mine was wrong and is corrected here.
* `Picture Index` == `.dat` `IconID` on only 59/136 (BRITONS) to 66/146 (KHITANS). Where they agree they agree exactly, so they are the same quantity but the JSON carries its own value.
* `Age ID` vs `.dat` `LocationInAge`: units differ 4,052 / match 259 / no-`.dat`-record 4,682; buildings differ 1,060 / match 682 → not derivable.
* **`Node Status` is NOT derivable.** The `.dat` TechTree status byte is constant 2, and the per-civ `Enabled`/`Disabled` flags do not predict it either — pooled cross-tab over all 62 civs: `NotAvailable` en=0 1,227 / en=1 170 / no-record 31; `ResearchRequired` en=0 399; `ResearchedCompleted` en=0 5,759 / en=1 927 / no-record 480. Also `NotAvailable` nodes **are** present in the `.dat` civ's unit list, so status ≠ membership.
* Cross-check against `futuravailableunits.json` node membership: `NotAvailable` 95.2% absent, `ResearchRequired` 72.4% absent, `ResearchedCompleted` 83.0% absent → the two files are independent views, not one derived from the other.

**Do the 291 stale-`Name` mismatches prove they are outputs?** **No — and this is the most important "do not overclaim" result.**
Resolving all 10,742 nodes' `Name String ID` against the merged English table (36,392 ids, all 222 shipped tables): **5,945 exact, 4,506 differ only by soft line break / case** (`'Archery Range'` vs `'Archery\nRange'` — not staleness), **291 true text mismatches, 0 missing ids**. The mismatches split cleanly:

* a 3–5-per-civ **baseline** that is pure abbreviation style — `'Heavy Demolition Ship'` vs `'Heavy\nDemo Ship'`, `'Trebuchet (Packed)'` vs `'Trebuchet'`, `'Warships'` vs `'Medium Warships'`, `'Elite Composite Bowman'` vs `'E. Composite\nBowman'`. Stale *labels*, not stale *data*.
* **Chronicles civs only** (ACHAEMENIDS 27, ATHENIANS 25, SPARTANS 22, PURU 10, THRACIANS 7, MACEDONIANS 6) where the JSON holds the **legacy AoE2 name** and the table holds the **new Chronicles rename**: `405052 'Archer' vs 'Bowman'`, `405039 'Militia' vs 'Levy'`, `405042 'Champion' vs 'Paragon'`, `414055 'Hand Cannoneer' vs 'Gastraphetoros'`, `407090 'Feudal Age' vs 'Civic Age'`, `407008 'Karda' vs 'Sagaris'`.

Both readings survive this evidence: (a) files generated from an older source pass and never re-labelled, or (b) hand-maintained label text left stale. **`Name` is a display label; `Name String ID` is authoritative.** Since the exe's node-field block *does* contain `Name String ID` and *not* `Name`, the engine reads the id. The consequence for the product is the same either way: **never use `Name`, always resolve `Name String ID`** — which also means **the stale `Name` cannot be used as evidence of derivation.** The experiment that *would* settle it: set one node's `Name` to a garbage string and observe whether the in-game tech tree changes. **Not run — requires launching the game.**

### 3.2 Does a "modded"/increment overlay variant exist?

**For strings: yes, documented and shipped. For game data: NO.**

* All **17** language dirs ship three tables — `key-value-strings-utf8.txt`, `key-value-modded-strings-utf8.txt`, `key-value-paphos-strings-utf8.txt` — plus 9 campaign tables. `key-value-modded-strings-utf8.txt` is **605 B and contains zero ids**; its entire content is instructions including: *"If you would like to modify an existing string, copy only the strings you wish to modify into this file, and do not delete them from the original file."* This is the increment-overlay pattern, real and engine-documented.
* `morematerials.json` exists — **once**, at `modes\Pompeii\widgetui\morematerials.json` (990,932 B), i.e. the widget-texture layer only. `widgetui\materials.json` (2,494,306 B) has no sibling in the base tree. The `more*` overlay is **not generalised** to the dat JSONs.
* A recursive search of the entire install for `more*.json`, `*_modded*`, `extra*`, `override*`, `patch*` siblings of any in-scope filename returns **nothing**.

**What *does* exist is a different and more powerful override mechanism: whole-file shadowing through the mode/mod resource tree.**

* `modes\Pompeii\resources\_common\dat\` ships its own copy of 14 of the in-scope files. The mode tree **replaces the base file file-by-file** (exe literal `use_modes_path_for_mods` @52798888). Proof it is a *replacement*, not a merge: `modes\Pompeii\...\linkedTechs.json` is **235 B containing one entry** — `NameId 424010` redefined from base's `Comment "Merchant Trade Rates" / Cycle / StartingTech 1215 / Techs [1215,1216,1217]` to `Comment "Trade Boat Rates" / Toggleable / StartingTech 184 / Techs [184,185,186]`. **Same NameId, different mechanic, and the other 19 base entries are simply gone.** Likewise `sharedbuildings.json` = 22 B `{"Data":[]}` deliberately shadowing base's 11 entries — **an empty JSON is a valid way to disable content.** And `unitcategories.json` = 195 B with all 7 keys present and all lists empty.
* User mods use the same mechanism. Files found under `resources\_common\dat\` in mods: `297820_10 倍资源文明联盟3倍科技\...\civilizations.json` (43,485 B) and `550749_{2026}10倍资源文明联盟2倍科技 北欧dlc可用 v48\...\linkedTechs.json` (4,203 B).
* **No mod ships a `CivTechTrees\` directory or a `civTechTrees.json`.** Absence of precedent, not evidence of impossibility.

**Practical consequence for the tool: the way to modify these files is not a `more*` increment — it is to ship a replacement copy in the mod folder.** That is exactly what the two real data mods do, and it is what the whole-file-shadowing semantics require.

### 3.3 Which lever for which user-facing capability

| User wants to… | Right lever | Needs `.dat`? |
|---|---|---|
| change civilization bonuses | `civilizations.json` (metadata, unique techs) + `linkedTechs.json` (grouped/enabled mechanics) | **Yes** for the numbers of the bonus techs |
| change what a building produces | `futuravailableunits.json` (per-civ, per-age, with prereqs) and/or `CivTechTrees\<CIV>.json` | No |
| change the tech tree | `CivTechTrees\<CIV>.json` — `Node Status`, `Age ID`, `Picture Index`, `Link ID`, `Prerequisite IDs/Types` | No |
| change resource drop-off behaviour | `dropsites.json` | No |
| add a unit to a civ | **No JSON does this.** The unit must exist as a `.dat` record; `.dat` `Enabled` per-civ is the flag. JSON can only expose it in the tree (`CivTechTrees`) and in production (`futuravailableunits`) once it exists. | **Yes** |
| change a unit's stats/cost | — | **Yes** |
| rework unit upgrade lines | `unitlines.json` | No (the `.dat` cannot even hold it) |
| change commands / hotkeys / icons | `buttons.json`, `hotkeys.json` | No |
| swap a unit/building for another under a condition | `objreplacement.json` | No |
| change the map pool | `maps.json` | No |

### 3.4 The two id namespaces inside `CivTechTrees\<CIV>.json`

Worth stating separately because a naive join will silently corrupt a tree. Both `civ_techs_buildings` and `civ_techs_units` contain a `Node ID`, and within one civ **the two lists' Node IDs collide** (Node ID 87 is used by both a building and a unit, in all 62 civs) — they are separate namespaces. Worse, `Node ID`'s meaning depends on `Node Type`:

* `Unit / UnitUpgrade / RegionalUnit / UniqueUnit` → the id is a **`.dat` UnitConnection id**. Matches: Unit 1,551, UnitUpgrade 1,542, RegionalUnit 194, UniqueUnit 160.
* `Research / UniqueTech / RegionalTech / BuildingNonTech` → the id is a **`.dat` research-connection id**. Matches: Research 4,971, UniqueTech 127, RegionalTech 15, BuildingNonTech 62. (The `.dat` has only 240 research records; the union of all files' Node IDs is 488 values over range 3..2712.)
* Hence the raw "does this Node ID exist in the `.dat` unit list" test resolves only 136/145 for BRITONS; the 9 misses are exactly the Research/UniqueTech nodes (Gillnets 65, Hoardings 379, Spies/Treason 408, Fervor 252, Castle Age 102, Hand Cart 249, Warwolf 461, Atlatl 460). Likewise resolving `437 Thumb Ring` as a unit id gives `HPRITH`, and `1452 Cranequins` gives `"Yurt F (Rubble)"` — those are correct lookups in the *wrong namespace*.
* Also: `Name String ID` (14083, 14128, …) never equals a `.dat` unit id. Third namespace — the string table.

---

## 4. Reproducible script index

All under `D:\Software\DeepSeek Harness\工作区2\_probe\json_layer\`. Run with the bundled Python and `$env:PYTHONIOENCODING='utf-8'` (the console is GBK; CJK output crashes otherwise).

| Script | Question it answers |
|---|---|
| `s01_inventory.py` | file inventory, sizes |
| `s02_shape.py`, `s05_raw_small.py` | top-level JSON shape of every small file |
| `s03_exestrings.py`, `s04_exewindows.py`, `s07_allsites.py`, `s13_allsites.py` | all exe occurrences of each filename ± window |
| `s06_siblings.py` | search for `more*`/`*_modded*`/overlay siblings |
| `s08_style.py` | BOM, indentation, CRLF, authoring hints |
| `s10_ctt_schema.py`, `s11_ctt_enums.py` | `CivTechTrees` schema + full enum vocabularies (pooled over 62 files) |
| `s12_mono.py`, `s32_synth.py` | monolithic vs per-civ schema/structure compare |
| `s14_keytest.py`, `s16_coverage.py` | per-file exe key coverage + longest contiguous key run |
| `s15_regions.py`, `s17_schemablocks.py` | raw dumps of the schema-block regions |
| `s18_logscan.py`, `s19_logdetail.py` | engine runtime logs — **zero** in-scope filenames in 382,645 lines |
| `s20_mods.py`, `s21_modcivdiff.py` | real mod inventory; mod `civilizations.json` vs base, field-by-field |
| `s22_dat_dump.py`, `s23_moddat.py` | `.dat` stats; mod `.dat` comparison |
| `s24_civunits.py` | per-civ unit blob statistics |
| `s25_dat_techtree.py` | **full decode of the `.dat` TechTree section** (byte-exact, `pos=93268152 exact=True`) |
| `s26_sources.py`, `s31_fixes.py`, `s40_genie.py`, `s57_datclasses.py`, `s58_unitclass.py` | source/tool cross-references; genieutils structs; the "no unit-class table" result |
| `s27_ctt_join.py` | `CivTechTrees` ↔ `.dat` join, id overlap |
| `s28_nodes.py` | node semantics resolved against `.dat` names |
| `s29_derivable.py`, `s34_derive2.py`, `s35_derivable2.py` | **derivability tests** — the enabled/disabled cross-tab, Trigger Tech ID, Prerequisite IDs, Age ID, Picture Index |
| `s30_crosscheck.py`, `s33_names.py` | string-table authority test (10,742 nodes, 0 missing ids) |
| `s36_final.py` | `futuravailableunits.json` field inventory; mod evidence re-check |
| `s37_binaries.py` | every `.exe`/`.dll` ≥300 KB — all 19 filenames occur **only** in `AoE2DE_s.exe` |
| `s38_loader.py`, `s49_sites.py`, `s50_windows2.py`, `s55_windows3.py`, `s56_windows4.py`, `s65_chronicles.py` | loader/parse-site dumps |
| `s41_verify.py`, `s44_final2.py`, `s48_final3.py` | per-file evidence table; mismatch/inert files; structural joins |
| `s45_inventory.py`, `s59_table.py` | final inventory + the auto-generated per-file table |
| `s46_method2.py` | **independent cross-check** — 2,567 text files searched for all 27 candidate filenames |
| `s47_overlay.py`, `s61_overlay.py`, `s62_linked.py` | overlay semantics; mode-tree shadowing proof |
| `s51_jsonnames.py` | **complete list of all 47 `.json` literals in the exe** |
| `s52_selgroup.py`, `s64_selgroup2.py`, `s66_selgroup3.py` | the selection-group dead end (case-insensitive, filename assembly, `_def` suffixes) |
| `s53_content.py` | **full content dump of every small file** |
| `s54_civjoin.py` | `civilizations.json` / `unitlines.json` join into `.dat` id spaces |
| `s60_gamedata.py` | no `gamedata_x1/x2` dataset exists; only one `.dat` |
| `s63_fau_ctt.py` | `Node Status` vs `futuravailableunits.json` membership |
| `s67_rawscan.py` | raw-byte filename search across **35,644** files in the game and profile trees |
| `s68_barrename.py` | proves the `CivTechTrees` field-name block is alphabetically sorted and contains no bare `Name` |

**Three conclusions independently cross-checked by a second, different method:**
1. `CivTechTrees\<CIV>.json` is an input → method A: exe parse site with enum + bounds errors; **method B**: derivability — 4 of the file's fields (incl. the whole `Node Status` vocabulary) provably cannot be read out of the `.dat`, whose status byte is a constant 2.
2. `unitlines.json` is an input → method A: parse site with bounds errors; **method B**: `civilizations.json`'s 62 negative `unique_unit_line` values resolve 62/62 into `unitlines.json` and 0/62 anywhere else, plus genieutils' `gv >= GV_SWGB` guard proving the `.dat` has no UnitLines array at all.
3. The `-modded-` overlay pattern does **not** extend to game data → method A: recursive sibling search; **method B**: raw-byte literal search over 35,644 files (no `more*`/`_modded` dat file anywhere) contrasted with the 17 shipped string overlays.

Also cross-checked: the mode tree shadows the base tree file-by-file (method A: `use_modes_path_for_mods` literal + `sharedbuildings.json` 22 B stub; method B: the `linkedTechs.json` NameId 424010 redefinition with 19 entries missing).

---

## 5. Loose ends that are real, but not verdict-changing

**5.1 Real-mod evidence, in full.** The two data mods are currently `"Enabled": false` in `mods\mod-status.json`, but they were enabled in logged sessions and their files are on disk.
* `297820_10 倍资源文明联盟3倍科技\...\civilizations.json` (43,485 B vs base 58,763 B): 46 civs instead of 63 (the 17 newest DLC civs removed, none added); the writer **drops one field** (`tech_tree_description_string_id`) which proves it was edited against the schema rather than byte-copied; **55 differing fields, all meaningful** — `Franks unique_tech_id_2` 1496→83, `Portuguese unique_tech_id_2` 1404→572, `Incas hud_style` `CivAnde`→`CivMeso`, `Vikings hud_style` `CivNord`→`CivSlav`, `Chinese unique_unit_image_paths` 2→1, `Incas`/`Vikings` gained a second unique-unit image and string id.
* `550749_...\...\linkedTechs.json` (4,203 B): the first 20 entries **byte-identical to base**, plus one appended invention — `{"NameId": 666666, "Comment": "Aliance Cycle", "Type": "Cycle", "Instant": true, "StartingTech": 4666, "Techs": [4666, 4667, 4668, 4669, 4670]}`. A `NameId` outside the engine's 424xxx namespace and tech ids that must come from that mod's own `.dat` (which carries 5,851 techs vs base 1,510).
**This is the single strongest practical evidence in the whole investigation** that the JSON layer is a live moddable control plane, because it is two independent real-world writers doing it.

**5.2 No file carries a version, generator signature, or "do not edit" marker.** Scanned the first 4,000 bytes of every dat JSON: the only metadata-ish keys are `AIConsts.json`'s `Hint`, `linkedTechs.json`'s `Comment`, and `unitlines.json`'s modder-facing `Hint`. This is mildly *input*-flavoured (engine-written files usually stamp a version).

**5.3 Neither shipped modding tool knows these files exist.** Searching all of `_probe\source\` (`AGE\`, `genieutils\`, `pcrio\`): `linkedtech` 0 files, `linkedunit` 0, `selection_group` 0, `unitcategor` 0, `sharedbuilding` 0, `objreplacement` 0, `futureavailable` 0, `morematerials` 0, `map_list` 0, `default_map_type` 0. The JSON node vocabulary (`Node Status`, `Picture Index`, `Trigger Tech ID`, `Prerequisite IDs/Types`, `Building in new column`, `ResearchedCompleted`, `ResearchRequired`) exists **nowhere** in AGE or genieutils — those tools model only the `.dat` TechTree. And **no `DATProcessingToolConfig.json` exists anywhere on the game tree**; AGE's reference to it (`AGE_Frame\DATProcessingTool.cpp:9`) is AGE's external-converter hook, unrelated. Consequence: **there is no shipped, documented tooling for the JSON layer** — which is exactly the product gap this project is filling, and also why nothing here can be confirmed from vendor docs.

**5.4 `sounds.json` — one unresolved detail.** The file's `name` values (`Play_Button_Select`, …) are **not** in the exe (0/52 distinct), yet the exe emits `Play_%s`. `Play_`+Title_Case(key) reconstructs only 24/53; 29 are irregular (`button_tab`→`Play_Button_Paper`, `artifact_found` and `animal_found` **both** →`Play_Animal_Discovered`, `mercenaries`→`Play_The_Mongols`, `spies`→`Play_Spy_Infiltration`, `trumpet`→`Play_Salpinx_Trumpet_Signal`). So the mapping is data, not a formula — but *which* field the `%s` consumes is not statically determined.

**5.5 The runtime logs prove nothing about this question.** 382,645 lines across 28 engine log files contain **zero** occurrences of any of the 20 in-scope filenames. The engine logs mod enable/disable (`Enabling mod #0 (...)`) but **never** per-file loads — so logs cannot discriminate input from output. (They do prove the game has been run as recently as 2026/10/10 23:39, and give the init sequence `BaseGame constructor` → `PreModManagerInit` → `Game::open resource packages` → `Game::setup() before/after hotkeys` → main menu.)

**5.6 The base `civilizations.json` order is `.dat` order.** `.dat` civ order (British, French, Goths, Teutons, Japanese, Chinese, Byzantine, Persians, …) matches `civilizations.json` after its leading `Gaia` entry, while the `CivTechTrees\` *filenames* are alphabetical. So `CivTechTrees\<CIV>.json` must be joined via `civilizations.json.tech_tree_name` (which equals the `civ_id` inside the file), **never by array index** — `tech_tree_name` values are the 62 filenames plus `GAIA` (which has no file). Note the persistent spelling mismatch that forces this: `.dat` says `British/French/Byzantine/Mayan/Hindustanis/Magyars`, `civilizations.json` says `Britons/Franks/Byzantines/Mayans/Indians/MAGYAR`.

**5.7 The `CivTechTrees` field-name block is alphabetically sorted — a read/write-schema signature, not a coincidence (`s68_barrename.py`).** The 18 NUL-terminated literals at @52828048–52828624 are in strict alphabetical order: `Age ID, Building ID, Building in new column, Building upgraded from ID, Draw Node Type, Help String ID, Link ID, Link Node Type, Name String ID, Node ID, Node Status, Node Type, Picture Index, Prerequisite IDs, Prerequisite Types, Trigger Tech ID, Use Type, Picture Node Type`. That is what a **serialiser's field-name table** looks like (a code-generated list of members), and it is the reason this block is 19 keys deep and contiguous. It confirms the engine has a complete struct mirroring the file, not an ad-hoc key lookup. Two related facts:
* Bare `Name\x00` occurs 250× in the whole exe but exactly **once inside this block (@52829132)**, and that single hit is the `Name String ID` entry — i.e. the node schema declares **`Name String ID` and not a bare `Name` field**. The engine never looks up the file's `Name` key. This sharpens §3.1: the stale `Name` is *not* read at this site, which independently argues against using it as evidence of anything.
* The same alphabetical-order signature appears for the `futuravailableunits` metadata block (@53370528: `FullTechCiv, PaphosFullTechCiv, RequiredAge, RequiredTechID, RequiredUnitID, PrereqTech, PrereqIconSet, PrereqIconIndex, PrereqStringID, PrereqStyle` — alphabetical after the two `FullTechCiv` entries), which is the second-strongest parse-site in the set.

---

## 6. Unresolved — and the experiment that would settle each

I did **not** launch the game, so every verdict above is "the binary contains a loader for this file". None is "I watched it load." Stated plainly:

| # | Unresolved | Current position | Experiment that settles it (requires running the game) |
|---|---|---|---|
| 1 | `selection_group_def.json` / `chronicles_selection_group_def.json` | Filename in **no binary**; zero occurrences of `selection_group`/`radial_data`/`item_list` case-insensitively; the `modes\Pompeii` copy is **invalid JSON** (missing comma, line 381 col 5 char 5807) which a validating parser would reject. Best candidate for the real name: `chronicles_` is a **music-theme** prefix (@53278384, with `%s_theme.wem`, source `RgeSound.cpp`), not a selection-group one. | Put a sentinel value in a group label, start a skirmish, open the radial menu. If nothing changes, delete the file and repeat. **Do not run.** |
| 2 | `linkedUnits.json`, `sharedbuildings.json`, `unitcategories.json` | All three filenames sit in one region (@52798800–52799344) whose neighbours are UI/menu strings (`TechTreePreviewPanel`, `MenuPanel`, `Game::onPlayerDropped`, `TournamentMode`, `ScreenMultiplayerMatchmaking`), not a parser. `sharedbuildings.json` and `unitcategories.json` have their own key blocks; `linkedUnits.json` does not. | Change `linkedUnits.json`'s Villager list, boot, inspect the villager group. **Do not run.** |
| 3 | `civTechTrees.json` (monolithic) | Same data as the per-civ files; only in the Pompeii tree; literal with no key block. Its **always-present** full field set (vs the base per-civ files' conditional omission) is the classic serialiser-dumps-a-struct signature → leans OUTPUT/aggregate. | Delete it from a scratch copy of the mode tree; if the mode still loads tech trees, it is unused. **Do not run.** |
| 4 | `adapterblacklist.json` | The on-disk name occurs in **no binary**; the exe looks for `adapter_blacklist.json`. The shipped file is therefore inert. | Create `adapter_blacklist.json` with a bogus vendor id and see whether the engine reacts. **Do not run.** *(Out of scope for data modding regardless.)* |
| 5 | Whether `Name` in `CivTechTrees` is read | `Name String ID` is authoritative. The node schema block declares `Name String ID` and **no bare `Name`** (`s68_barrename.py`) — but a bare `Name` could still be read elsewhere, and 250 `Name\x00` literals exist in the exe. | Corrupt one node's `Name` only; if the in-game tree label is unaffected, `Name` is dead text. **Do not run.** |
| 6 | Whether a JSON edit actually takes effect at runtime | Supported by two real mods shipping JSON overrides and by 20 parse sites; **not observed**. | Enable `550749`'s `linkedTechs.json` alone (without its `.dat`) and check whether `Aliance Cycle` appears. This is the cleanest single experiment in the whole report, because that entry cannot come from base data. **Do not run.** |
| 7 | `futuravailableunits.json`'s unwritten schema fields | The exe declares `RequiredTechID`, `RequiredUnitID`, `PrereqStringID`, `PrereqStyle`; base populates `RequiredUnitID` (510×) and `RequiredTechID` (478×) but the other three only 295× each — consistent with a writer omitting unpopulated struct fields, **or** with optional loader fields. | Add `PrereqStyle` to a node that lacks it and observe. **Do not run.** |

**What I will not claim:** that any of these 85 files is *definitely* a generated output. The evidence I found points the other way for 20 of 23 root files plus the whole `CivTechTrees\` directory, and the two files where "output" is a plausible reading (`civTechTrees.json`, `selection_group_def.json`) fail for *different* reasons — one is an aggregate with no loader, the other has no loader **and** no valid JSON. Neither is a confirmed output, because I never watched the engine write either.
