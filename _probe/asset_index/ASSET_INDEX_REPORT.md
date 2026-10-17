# ENTITY → ART ASSET INDEX (AoE2:DE)

**Scope.** Static, read-only derivation of the mapping from game entity (unit / building / tech id)
to the actual art files on disk. Sources: `empires2_x2_p1.dat`, `widgetui\materials.json`,
`widgetui\icons.json`, `resources\_common\drs\graphics\*.sld`, `widgetui\textures\ingame\**`.
Nothing under the game directory was written. Every number below is reproducible from a script
left in this directory (see *Script index*).

Evidence tags: **[V]** verified by my own inspection of real bytes or rendered pixels ·
**[I]** inferred from a pattern, not proven exhaustively · **[C]** community claim / unverified.

---

## 1. BOTTOM LINE

**You can map an entity to its art with high confidence, and the mechanism is a chain of
game-authored tables rather than any name-matching heuristic.**

- **Sprites:** `2,363 / 2,693` unit ids (87.7 %) resolve to `.sld` sprite filenames. The rule is
  nearly trivial and was verified byte-exactly: the `.dat` Graphic record's `FileName` field *is*
  the on-disk `.sld` stem. **[V]**
- **Icons:** `1,344 / 2,693` unit ids (49.9 %) resolve to an atlas tile **and this is not a
  coverage failure** — the other `1,349` carry `IconID` 0 or −1 in the `.dat`, i.e. they have no
  icon *by construction*. Of the 1,344 entities that *do* declare an icon, **1,344 / 1,344 (100 %)
  resolve; zero genuinely unresolvable.** **[V]**
- The one genuinely tricky part — *which of the two atlases a given `IconID` indexes* — is
  **decided by the game's own `widgetui\icons.json`, not by any heuristic.** I falsified the
  obvious heuristics (`Type==80`, `Class==3`) with a pixel-level counterexample: unit 42
  *Trebuchet* and unit 71 *Town Center* both carry `IconID 28`, but atlas `ingameunits[028]` is a
  trebuchet and `ingamebuildings[028]` is a town centre, so no type/class rule can be right for
  both. **[V]**
- **The single most useful fact for the product:** *the atlas is a property of the material name,
  not of the entity.* `icons.json` line 88 reads `"085": "UnitIcons03250730"` — a **Unit** material
  sitting **inside the `Buildings` section**. That is what makes the routing expressible at all. **[V]**

**Rule that works, in one line:** entity `IconID` → `icons.json` section (`Buildings` if that
section's entry for the id *names* the entity, else `Units`) → material name → `materials.json`
`MaterialDef.AtlasRef` → that atlas's `Textures[]` entry by `RefName` → `FileName` + flat
`imageTLX/imageTLY/imageBRX/imageBRY` UV rect.

**Corroboration is visual, not statistical.** Where the game ships its own author-named loose
icons (`widgetui\textures\ingame\buildings\028_town_center.DDS`), I rendered the loose file beside
the atlas slice my index names, for all 300 building-routed entities: 24/24 contact-sheet rows are
**visually identical**, and a 10-unit named cross-check (Archer, Villager, Knight, Militia, Town
Center, Barracks, Castle, House, Longbowman, Monk) is 10/10 identical. **[V]**

**What is *not* solved** (§7): 330 unit ids (12.3 %) have no usable sprite, split into 141 with no
graphic assigned at all and 189 whose `.dat` names a legacy/placeholder graphic with no matching
`.sld`; icon coverage for the 2,693-id population is 49.9 % *by construction*, not by limitation.

---

## 2. THE CORRESPONDENCE RULES, WITH EVIDENCE

### R1 — sprite rule: `Graphic.FileName` + `.sld` **[V]**

The `.dat` `Graphic` record's `FileName` field, with `.sld` appended, is the filename in
`resources\_common\drs\graphics\`. It is **not** a debug token and needs no translation.

- Evidence: `8,185 / 8,296` DE-style `Graphic.FileName` values (`98.66 %`) have the file present
  with that exact stem. The residue is `none` and legacy names (R1 misses analysed in §6).
- The `.dat` `name` field, by contrast, is a *different* thing from `FileName` and is the
  `id`-keyed internal token; it is why the task brief warned about debug tokens — but the
  correspondence rule does not need `name` at all.
- Worked example **[V]**: unit 4 Archer `standing_1` → graphic slot 633 → `FileName`
  `u_arc_archer_idlea_x1` → file `u_arc_archer_idlea_x1.sld` exists on disk.

### R2 — the `_x1` / `_x2` twin **[V]**

Each sprite stem exists twice: `<stem>_x1.sld` and `<stem>_x2.sld`. The `.dat` stores the `_x1`
name; the `_x2` twin is the same stem with the suffix changed. `7,743 / 7,743` pairs verified
present on disk — zero exceptions. **[V]**

### R3 — animation sets: token substitution, **not** slot adjacency **[V]**

A unit's other animations (walk, attack, dying, …) are found by **substituting the animation token
in the standing stem** (`idlea` → `walka`/`attacka`/`deatha`/…), keeping prefix and civ token.
The tempting alternative — "the graphic whose `.dat` slot is adjacent to `standing_1`" — was
**disproved** and must not be used.

- Worked example **[V]**: `u_arc_archer_idlea_x1` → `u_arc_archer_walka_x1`, `u_arc_archer_attacka_x1`,
  `u_arc_archer_deatha_x1`, all present on disk.
- This is why the deliverable resolves 12 sprite field slots per unit from the `.dat` fields
  (below) and *additionally* offers the substituted animation set — the substitution is a
  convenience, the 12 slots are the ground truth.

### R4 — icon rule (the hard one): `icons.json` decides the atlas **[V]**

Chain: `entity.IconID` → `icons.json[section][%03d]` → material name →
`materials.json.Materials[material].AtlasRef` → `materials.json.AtlasTextures[atlas].Textures[]`
entry whose `RefName == material` → that entry's `FileName` (PNG/DDS path) and its flat UV keys.

- **The falsified heuristics [V].** Over the 1,344 `IconID>0` entities:
  `Type==80 → ingamebuildings` routes 358 entities but produces **63 false** (17.6 %) — it gives
  unit 42 *Trebuchet* (`IconID 28`) the town-centre tile. `Class ∈ {1,3,11,14,27,39,49,52}` routes
  390 with **93 false** (23.8 %). The winning rule routes 300 with **0 false** and 0 units-side
  misses. Type-70 control: 0.0 % of 840 entities match a building name, so the test discriminates.
- **Why a *section* is not the answer either [V].** The `Units` and `Buildings` sections of
  `icons.json` overlap on all 117 building ids (`000` is both `UnitIcons00050730` and
  `BuildingIcons000ArcheryRange1`), and the two atlases hold **genuinely different images**: of
  109 shared numeric stems, **109 DIFFER, 0 identical**. So the namespace choice is load-bearing.
- **The decisive text [V].** `icons.json` line 88: `"085": "UnitIcons03250730"` inside the
  `Buildings` section. The atlas follows the **material name**, not the section — so the rule is
  expressible per entity.
- **The tie-break that works [V].** Use the `Buildings` section entry only when its *name denotes
  this entity* (token overlap between the entity's English name and the material's name / the
  loose-file label); otherwise use `Units`. Per-Class denote rates: Class 3 → 85.6 % (167/195),
  39 → 100 % (97), 52 → 90.9 % (10/11), 49 → 66.7 %, 27 → 33.3 % (walls/spawn helpers — the weak
  class), 54 → 0 % (trebuchets), 51 → 0 % (packed), 14 → 71.4 %.
- **Result: 1,344 / 1,344 resolved, 0 unresolved** — routing 300 → `ingamebuildings`,
  1,044 → `ingameunits`. `RefName != material`: **0 of 1,344**, i.e. the index points at exactly the
  tile the material names.
- **Verified by pixels, not by names [V].** The `UnitIcons<NNN>50730` RefNames carry **no text**,
  so no name test can ever fire on the 1,044 unit-routed entities. They were adjudicated by
  rendering: `png/shipped_icon_check.png` (15 rows) reads archer / villager / knight / axeman /
  spearman / monk / trebuchet / **town centre** / **barracks (crossed swords)** / **castle** /
  house / farm / watch tower / longbowman / mangonel — all correct artwork.
  `png/loose_vs_shipped_buildings.png` puts the game's own loose icon beside my atlas slice for all
  300 building-routed entities: **24/24 rows visually identical**.

### R5 — building definition: a **union**, tagged per entity **[V]**

Neither available definition alone matches the art:
- `type == 80` selects 491 entities, but **20 of them have non-`b_` art** (id 42 Trebuchet prefix
  `u`; 682/683 Bad Neighbor & God's Own Sling `u`; 1690/1691 Warwolf `u`; 331/729/730 packed
  trebuchets `u`; 345 Ruins, 635 BBURNED, 1847/2002/2003/2004/2081 bridge pieces, 2421 Mole `s`;
  1887 GREN_DELAY_D `p`; 2281 Sapper Tunnel `s`; 2412/2413 Supply Cart `u`).
- **138 entities have `b_*` art but `type != 80`** — mostly rubble/scenario variants (1089 Granary,
  1065 Fence (Rubble), the 1402–1440 "… (Rubble)" set), type 10 / class 14.

So the deliverable tags every building with `building_definition ∈ {type80+b_art, type80_only,
b_art_only}`. Use **`sprite_prefix == "b_"`** as the art-facing test and `type == 80` as the
gameplay-facing one; the union is 629 ids. Note `standing_1` is frequently `-1` for buildings
(Gates, Docks, Bridges), so the *dominant* resolved prefix is the correct metric, not the standing
one — that distinction explains the otherwise alarming "241 type-80 entities whose standing prefix
isn't `b_`" (of which only 86 have no `b_` art anywhere, and 66 of those have no resolved sprite at
all).

### R6 — tech rule: `IconID` → `icons.json.Techs` → `ingametechs` **[V]**

`tech.IconID` → `icons.json["Techs"]["%03d"]` → `TechIconsT<NNN>` → `AtlasRef` = `ingametechs`.
Record level: `422 / 1,510` tech records declare `icon_id > 0`, `419` resolve, **3 unresolved** —
`synthetic upgrade stubs` whose ids (`8133`, `8142`) exceed the `%03d` id space entirely, plus
`Cartography` (`icon_id 4`) whose `TechIconsT004Cartography` has **no MaterialDef** in
`materials.json`. In the deduplicated deliverable (1,095 techs keyed `tech_id|civ`): 409 with
`icon_id>0`, **407 resolved, 2 unresolved** (Cartography; Shadow Tower — Age Four 8142).

---

## 3. DELIVERABLES

All under `D:\Software\DeepSeek Harness\工作区2\_probe\asset_index\`.

| File | Size | Contents |
|---|---|---|
| `index_units.json` | 4.22 MB | 2,693 unit ids (string keys) → `{unit_id, internal_name, en, zh, type, class, hit_points, civ_count, sprite_prefix, sprites{12 fields}, icon, per_civ_variants}` |
| `index_buildings.json` | 1.24 MB | 629 building ids → `{building_id, internal_name, en, zh, hit_points, type, class, building_definition, sprite_prefix, sprites, icon}` |
| `index_techs.json` | 304 KB | 1,095 deduped techs (`<tech_id>\|civ<n>`) → `{name, civ, type, effect_id, icon_id, icon, research_locations}` |
| `index_coverage.json` | 1.7 KB | counts below + `sprite_field_resolution_histogram` + `rules` R1–R6 |

**Sprite slot shape [V]** (12 fields per unit): `standing_1, standing_2, dying, undead,
attack_graphic, attack_graphic2, garrison_graphic, spawning_graphic, upgrade_graphic,
hero_glow_graphic, idle_attack_graphic, special_graphic`, each
`{graphic_slot, FileName, resolution, sld_x1, sld_x2, animations?}` where `resolution ∈ {direct,
unresolved, unset(-1 sentinel), graphic has no FileName}`. Example:
`{"graphic_slot": 633, "FileName": "u_arc_archer_idlea_x1", "resolution": "direct",
"sld_x1": "u_arc_archer_idlea_x1.sld", "sld_x2": "u_arc_archer_idlea_x2.sld"}`.

**Icon block shape [V]**: `icon = {material, atlas, RefName, TextureFileName, uv{x1,y1,x2,y2},
atlas_max, resolved, icon_id, icons_json_section, why}`.

---

## 4. COVERAGE, WITH HONEST DENOMINATORS

### Units — denominator **2,693** unit ids (all civs' union) **[V]**

| Measure | Count | % of 2,693 |
|---|---|---|
| Sprite mapped | **2,363** | 87.7 % |
| Sprite failed | **330** | 12.3 % |
| Icon mapped | **1,344** | 49.9 % |
| Icon failed | **1,349** | 50.1 % |
| **Both** sprite and icon | **1,294** | 48.1 % |
| **Neither** | **280** | 10.4 % |

> **The icon denominator must be stated honestly.** The 1,349 "failures" are **all** `IconID 0 or
> −1` in the `.dat` — they have no icon *by construction*, and **0 of them are unresolvable**. The
> meaningful icon figure is **1,344 / 1,344 = 100 % of entities that declare an icon**.
> `index_coverage.json` carries this as `note_icon_denominator`.

### Buildings — union **629** ids (405 `type80+b_art`, 86 `type80_only`, 138 `b_art_only`) **[V]**

| Measure | Count | Note |
|---|---|---|
| Sprite mapped | **563** | 543 `b_` art + 20 non-`b_` (the trebuchets/bridges, §R5) |
| Icon mapped | **360** | 300 from `ingamebuildings` + 60 fallback to `ingameunits` |
| Icon failed | **269** | **all** `IconID ≤ 0` by construction; **0 unresolvable** |
| 269 split | 89 / 44 / 136 | `type80+b_art` / `type80_only` / `b_art_only` |

### Techs — denominator **1,510** records (= 1,095 deduped) **[V]**

| Measure | Count |
|---|---|
| Records with `icon_id > 0` | 422 |
| Resolved | 419 |
| Unresolved | 3 (`icon_id` 8133, 8142 exceed `%03d`; `Cartography` has no MaterialDef) |

### Per-slot sprite resolution (units, 12 fields × 2,693 = 32,316 slots) **[V]**

| Resolution | Slots |
|---|---|
| `unset` (−1 sentinel, no graphic assigned) | 15,173 |
| `direct` (resolved to an on-disk `.sld`) | 5,919 |
| `unresolved` (named, no matching stem) | 3,843 |
| `graphic has no FileName` | 3 |

Per-unit roll-up **[V]**: fully resolved (every non-sentinel slot resolved) **1,141**;
some slots unresolved **1,408**; no resolved slot at all **144**.

Best- and worst-covered slots **[V]**: `standing_1` is the best (direct 2,271 / unresolved 254 /
unset 165); the weak ones are `upgrade_graphic` (955 unresolved), `spawning_graphic` (838),
`hero_glow_graphic` (818), `snow_graphic` (290), `garrison_graphic` (99).

---

## 5. INDEPENDENT CROSS-CHECKS

### C1 — every referenced file exists **[V]**
`7,834` distinct `sld_x1`/`sld_x2` filenames are named across the deliverables; **0 missing**
(`a38_crosscheck.py`). Note this check deliberately does *not* re-run mapping logic — it only
opens the files the index names.

### C2 — the mandated 10-unit named check **[V]**
`a44_crosscheck10.py` renders, per unit, the game's own loose icon beside the shipped atlas slice,
and prints the sprite filenames. Result: **10/10 rows visually identical**, **10/10 sprite
filenames obviously match**, **10/10 confirmed present on disk**.

| id | Entity | Atlas / RefName | Sprite (idle) filename |
|---|---|---|---|
| 4 | Archer | `ingameunits` / `UnitIcons01750730` | `u_arc_archer_idlea_x1.sld` |
| 83 | Villager | `ingameunits` / `UnitIcons01550730` | `u_vil_male_villager_idlea_x1.sld` |
| 38 | Knight | `ingameunits` / `UnitIcons00150730` | `u_cav_knight_idlea_x1.sld` |
| 74 | Militia | `ingameunits` / `UnitIcons00850730` | `u_inf_militia_idlea_x1.sld` |
| 71 | Town Center | `ingamebuildings` / `BuildingIcons028TownCenter` | `b_west_town_center_age2_back_x1.sld` |
| 12 | Barracks | `ingamebuildings` / `BuildingIcons002Barracks1` | `b_dark_barracks_age1_x1.sld` |
| 82 | Castle | `ingamebuildings` / `BuildingIcons007Castle` | `b_west_castle_age3_x1.sld` |
| 70 | House | `ingamebuildings` / `BuildingIcons034House` | `b_dark_house_age1_x1.sld` |
| 8 | Longbowman | `ingameunits` / `UnitIcons04150730` | `u_arc_longbowman_idlea_x1.sld` |
| 125 | Monk | `ingameunits` / `UnitIcons03350730` | `u_monk_west_idlea_x1.sld` |

Rendered evidence: `png/crosscheck10.png` (2 cols × 10 rows, left = loose, right = shipped).

### C3 — 300-entity loose-vs-atlas comparison **[V]**
All 300 building-routed entities have a loose author-named counterpart; MAD min 2.8 / median 13.5 /
max 21.1. Contact sheet `png/loose_vs_shipped_buildings.png`: **24/24 rows visually identical**.

> **Instrument caveat, learned the hard way [V].** MAD is a *broken* instrument here: the atlas
> slice and the loose file differ by one texel in size (127 vs 128), which inflates MAD on
> pixel-identical images. The high-MAD rows (House 17.4, Castle 19.9) look *identical* by eye.
> An early all-`DIFFER` MAD verdict on `ingameunits` was an artifact of exactly this and was
> overturned by the rendered contact sheet. **Trust the contact sheet; use MAD as corroboration
> only.**

### C4 — negative control **[V]**
`Type 70` (the largest Type class, 840–869 entities) matches a building-atlas name **0.0 %** of the
time, confirming the name-denotes test is not trivially satisfied.

### C5 — the `RefName == material` integrity check **[V]**
`0 of 1,344` mismatches: the index always points at the atlas tile the material name designates.

---

## 6. FAILURE TAXONOMY (WHY each class fails)

### Sprite failures: 330

**F1 — no graphic assigned at all: 141 [V].** Every sprite slot for these entities is `-1`. 91 of
them are `type 10 / class -1`. These entities have no art and no graphic reference; there is
nothing to resolve. Not a bug in the rule.

**F2 — `.dat` names a graphic with no matching `.sld`: 189 [V].** Only **61 distinct unresolved
`FileName` values** across 292 field slots. The taxonomy:
- the literal string **`none` × 192 slots** — a sentinel the modders wrote into the `.dat`;
- **`farm0nng` × 15** — a farm graphic that no longer exists as an `.sld`;
- smoke/flame/projectile leftovers: `smoke_nn`, `s_smoke`, `boltx_nn`, `catst_nn`, `boltf_nn`,
  `wfall_nn`, `flm1a_nn` …
- **6 names resolve to `.smp` files only** (`FLM1A_NN.smp`, `FLM1B_NN.smp`, `FLM2A_NN.smp`,
  `FLM3A_NN.smp`, `FLM4B_NN.smp`) — **a pre-DE sprite format the DE engine no longer ships as
  `.sld`**;
- **54 of the 61 have no file of any kind** under that stem, in any extension.

**F7 — recoverable under a different name: 18 [V].** These entities *do* have art on disk, under a
name the `.dat` doesn't point at: Tree 201 → `n_tree_acacia_x1.sld`; Pasture 1893/1897 →
`a_pasture_ibex_*`; Nessie 1973 → `a_nessie_x1.sld`; Flame 1–4 (939–942, 1333–1336) →
`u_sie_flamethrower_*`; Plant (Bush, Dry) 1361 → `n_plant_bush_green`; Sea Gate 1382/1386/1390/1394
→ `b_afri_gate_fortified_corner_*`; Farm 50 → `u_all_ant_female_farmer_*`. A future pass could
recover these by name-search, but **it cannot be automated safely** — 47 of the 330 failures have
no `.sld` containing the entity name at all, so a name-search heuristic would silently invent
mappings for the other 312.

Worst `(type, class)` sprite-failure rates **[V]**: `(10, -1)` 91/91 = 100 %, `(20, 11)` 7/7 =
100 %, `(70, 64)` 8/10 = 80 %, `(80, 49)` 7/9 = 77.8 %, `(80, 27)` 27/39 = 69.2 %,
`(20, 14)` 15/22 = 68.2 %.

### Icon failures: 1,349 units + 269 buildings **[V]**
**Every single one is `IconID ≤ 0`.** There is no unresolvable icon class. The 6 `icons.json`
`Buildings` entries with no material (`046–051`) and the 6 `Techs` entries with no material
(`004 Cartography, 020, 024, 090, 102, 117`) are the only structural holes, and only two of them
(Cartography, and 8142) are reached by a live entity.

### Tech icon failures: 3 records / 2 entities **[V]**
`8133` and `8142` exceed the `%03d` id space (no `icons.json` entry can exist); `Cartography`'s
material name has no `MaterialDef`.

---

## 7. UNRESOLVED / DO NOT OVERCLAIM

1. **330 unit ids have no sprite.** 141 genuinely have none; 189 name a dead graphic. Only ~18 are
   recoverable, and only by manual inspection. **Do not report sprite coverage as 100 %.** The
   honest figure is 2,363/2,693 = 87.7 %.
2. **Icon coverage is 49.9 % of the 2,693-id population but 100 % of the 1,344 that declare an
   icon.** Any percentage quoted without both numbers is misleading. State the denominator.
3. **The 300-vs-1,044 atlas split rests on a name-denotes heuristic for the 300 building-routed
   entities.** It scores 0 false positives on the checks I ran and is pixel-corroborated on all 300,
   but **Class 27 (walls/spawn helpers) denotes only 33.3 % of the time** — that is the weakest
   spot in the rule and the place a wrong answer is most likely to hide. **[I]**
4. **The 1,044 unit-routed entities were arbitrated by rendered pixels, not by text** — the
   `UnitIcons<NNN>50730` RefNames carry no text. I rendered 15 of them plus all 300 building rows.
   The remaining ~1,029 were **not** individually eyeballed; their correctness rests on the
   `RefName == material` integrity check (0 mismatches) and the shared rule. **[I]**
5. **`Type`/`Class` are not sufficient to classify an entity as a building.** The deliverable tags
   the union and ships `building_definition` per entity so a consumer can choose. Do not use
   `Type==80` alone for anything art-facing.
6. **The atlas counts in the task brief are partly stale.** Measured: `ingameunits` 794 embedded
   ids, `ingamebuildings` **110** embedded (not 117/109), `ingametechs` **307** embedded. There is
   no `ingameicons` atlas with 190 entries in this install.
7. **`icons.json` sections `CivTechTree`, `CivEmblem`, `InGameCivEmblem`, `CivHero`, `MapIcons`,
   `History`, `Notification`, `MenuIcons` have zero `MaterialDef` matches** — they name non-atlas
   textures and were not resolved. Emblems/heroes/map icons are therefore **not** in these
   deliverables.
8. **HD/UHD atlas tiers are BC7 (DX10/DXGI 98), which I cannot decode**; all pixel verification
   used the SD tier (`DefaultSource`, BC3/DXT5). UVs normalise against the DECLARED
   `MaxWidth`/`MaxHeight`, which is the HD size, so the UV rects are correct for all tiers — but
   only the SD tier was visually proven. **[I]**
9. **`ingameunits` UVs are stored at lower precision** than the other atlases (1,494/3,176 values
   off the N+0.5 grid). A consumer should round with a ±3-texel tolerance rather than assume
   exactness. **[V]**
10. **The internal `.dat` `name`/`slp` fields are NOT to be used to derive filenames** — only
    `Graphic.FileName` is. `name` is a debug token (only 310/1,651 resolved ids had internal name
    == English name in earlier work) and 51 tokens map to multiple different units.

---

## 8. SCRIPT INDEX

Run with `$env:PYTHONIOENCODING='utf-8'` and
`C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`.

**Produce the deliverables**
- `a36_build_index.py` — **the builder**. Writes all four index JSONs. Supersedes `a17_build_index.py`.

**Rules & their evidence**
- `a01_graphics_dump.py` — dumps all 21,001 graphic records (`graphics_raw.json`).
- `a02_correspondence_probe.py`, `a03_rule_characterize.py` — establish R1 and characterise its misses.
- `a04_miss_forensics.py`, `a05_shorttoken_forensics.py` — why `FileName`s miss.
- `a06_unit_graphics.py` — per-civ unit re-parse; captures the unit → graphic-slot links the stock parser discards (`unit_sprite_sets.json`).
- `a13_anim_probe.py`, `a14_sibling_rule.py` — establish R3 and disprove slot adjacency.
- `a30_icons_json.py` — analyses `widgetui\icons.json`, the key discovery (`icons_json_analysis.json`).
- `a33_icons_resolve.py` — R4 end-to-end (`icon_resolution.json`).
- `a35_building_rule.py` — establishes R5 as a union.

**Arbitration of the hard question (which atlas)**
- `a28_atlas_rule.py`, `a29_class_namespace.py` — test and reject `Type`/`Class` discriminators; pixel-compare the two atlases.
- `a31_icon_arbitrate.py` — scores the three candidate routing rules as error metrics (`icon_arbitration.json`).
- `a32_loose_truth.py` — uses the game's own author-named loose files as non-circular ground truth.
- `a34_audit_route.py` — audits routing for false positives.

**Coverage, failure taxonomy, cross-checks**
- `a37_bldroot.py` — reconciles the conflicting building-prefix counts.
- `a38_crosscheck.py` — C1 (`7,834` files, 0 missing) + C2/C3. **This script found the icon-routing bug.**
- `a39_final_audit.py` — full coverage + failure taxonomy over the shipped deliverables.
- `a40_sprite_miss.py` — characterises the 61 distinct unresolved graphic names.
- `a41_orphan_check.py` — finds the 18 entities with art under an alternate name.
- `a44_crosscheck10.py` — the mandated 10-unit check → `png/crosscheck10.png`.

**Visual proof**
- `a23_pixel_proof.py`, `a24_pixel_proof.py`, `a27_loose_vs_atlas.py` — loose vs atlas pixel work.
- `a25_dump_png.py`, `a26_icon_sheet.py` — atlases → PNG. `a26` contains the correct DDS decoder.
- `a42_render_shipped.py` → `png/shipped_icon_check.png` (renders the shipped index's own claim).
- `a43_loose_vs_shipped.py` → `png/loose_vs_shipped_buildings.png` (300 rows).

**Data intermediates** (regenerable, listed for completeness): `graphics_raw.json` (3.8 MB),
`units_raw.json` (58 MB), `techs_raw.json`, `sld_inventory.json`, `unit_sprite_sets.json`,
`failtax_detail.json` (F1 141, F2 100, F4 55, F7 18, F5 13, F6 3), `unmapped_units.json`,
`icon_resolution.json`, `icon_arbitration.json`, `icons_json_analysis.json`, `out_a32.txt`,
`out_a33.txt`, `out_a34.txt`, `out_a35.txt`.

**PNG evidence**: `crosscheck10.png`, `loose_vs_shipped_buildings.png`, `shipped_icon_check.png`,
`loose_vs_atlas.png`, `units_named.png`, `sheet_ingameunits.png`, `sheet_ingamebuildings.png`,
`sheet_ingametechs.png`.
