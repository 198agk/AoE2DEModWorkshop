# `tech.create` reconnaissance — what it actually takes to add a brand-new technology

Scope: read-only recon against `empires2_x2_p1.dat` (93,268,152 B uncompressed, `VER 8.9`, gv=54),
`aoe2mod/dat/{parser,locate,writer}.py`, `aoe2mod/mod/strings.py`, `aoe2mod/game/{icons,buildpanel}.py`.
Nothing under `aoe2mod/` was modified; no mod was built or installed; the game was not started.
All experiments were in-memory serialisations re-parsed immediately.

---

## Verdict

**Feasible with caveats.** The `.dat` half already works: a brand-new tech record plus a
brand-new effect record append cleanly and re-parse exactly (+87 B for the tech alone, +122 B with
its effect, 0 model-vs-raw mismatches, byte-exact round-trip of the untouched stream). What does
**not** work is everything that makes the tech *visible*: the writer cannot write a tech's four
display-string ids at all (`aoe2mod/dat/writer.py:852` and `:860` hardcode `0` in the `_new` branch
and `w.op()` replay them for shipped techs), no code writes the two side-tables that make a tech
appear in a build menu, and the next free tech id (1510) collides with an existing unit id.

---

## What has to change

| # | what has to change | where it is written | code today? | measured number |
|---|---|---|---|---|
| 1 | Append the tech record | `aoe2mod/dat/writer.py:837` `if t.get("_new"):` | **YES** | record = `62 + len(name) + 9*nlocs` B; shipped 71..134, mean 89.7, sum 135,407 |
| 2 | Append the effect record | `aoe2mod/dat/writer.py:529` `if e.get("_new"):` | **YES** | `6 + len(name) + 11*cmds` B; shipped 6..2101, sum 149,454 |
| 3 | Tech count field | `aoe2mod/dat/writer.py:1046` `w.i16(len(s["techs"]))` | derived — nothing to do | 1510 → i16 cap 32767 |
| 4 | Effect count field | `aoe2mod/dat/writer.py:1029` `w.i32(len(s["effects"]))` | derived — nothing to do | 1500 → i32 cap 2.1e9 |
| 5 | Pick a tech id | tech id **is** the array position (`aoe2mod/dat/locate.py:433-442`) | **NO** — no `pick_free_id` for techs | 0..1509 all allocated; 1510 is **taken as a unit id**; first safe 2113 |
| 6 | `LanguageDLLName` + `LanguageDLLDescription` | `aoe2mod/dat/writer.py:852` writes `w.i32(0); w.i32(0)` in the `_new` branch; `:878` `w.op(4); w.op(4)` for shipped | **NO** | 1309/1510 shipped techs have a real name id; string id 0 exists in **0** of 17 locale tables |
| 7 | `LanguageDLLHelp` + `LanguageDLLTechTree` | `aoe2mod/dat/writer.py:860` writes `w.i32(0); w.i32(0)`; `:886` replay | **NO** | 1420/1510 have Help>0 and Tree>0 |
| 8 | `ResearchResourceCost[3]`, `RequiredTechs[6]`, `RequiredTechCount` | `aoe2mod/dat/writer.py:843-847` zero in `_new`; `:871-873` replay | **NO** | 3,298 of 4,530 cost slots are `(-1,0,0)` (the "unused" sentinel) vs only 337 `(0,0,0)`; `_new` writes `(0,0,0)` = literally free |
| 9 | `Repeatable` | `aoe2mod/dat/writer.py:865` writes `w.u8(0)`; `:891` replay | **NO** | 322 techs non-repeatable / 1188 repeatable |
| 10 | `icon_id` | `aoe2mod/dat/writer.py:857` `w.i16(t["icon_id"])` | **YES** | 134 of 313 `Techs` slots unused by any tech; **129 resolve to a real `.dds`**, 5 are `Xxx` dummies |
| 11 | Name/description strings shipped to the player | `aoe2mod/mod/strings.py:118 build_files`, `LAST_SHIPPED_ID` `:31` | **YES** (the `unit.create` path) | all 17 locales max id = 30030001, 15,351 ids, none above → first free **30030002** |
| 12 | Build-panel entry so a building offers the research | `aoe2mod/game/buildpanel.py` (`futuravailableunits.json`, 1,331,147 B, 57 civ keys) | **PARTIAL** — text-splice writer exists, but only units/availability use it | 363/563 researchable techs have a panel entry; **200 do not** |
| 13 | Tech-tree row | 7×i32 header then 241 research rows, replayed verbatim (`aoe2mod/dat/writer.py:976`) | **NO** (`aoe2mod/api.py` mentions `tech_tree` 0 times) | 231/240 tree ids are researchable; **332/563 researchable techs have no row** → optional |
| 14 | Intent + planner + builder | `aoe2mod/schema/intents.json` (12 intents, none is `tech.create`) | **NO** — grep for `tech.create\|new_tech\|_plan_new_tech\|add_tech` returns 0 hits | 12 intents / 0 for techs |
| 15 | Round-trip safety | `aoe2mod/dat/writer.py:982 serialize_dat` | **YES** | baseline re-serialise is byte-identical, 93,268,152 B, 0 mismatches |

---

## The three things that will probably break first

### 1. The tech has no name, and the writer physically cannot give it one

The `_new` branch at `aoe2mod/dat/writer.py:852` emits

```python
w.i32(0); w.i32(0)             # LanguageDLLName, LanguageDLLDescription
```

and `:860` emits `w.i32(0); w.i32(0)  # LanguageDLLHelp, LanguageDLLTechTree`.
I measured that **no shipped key-value table defines string id 0**: `resources/en/strings/key-value/key-value-strings-utf8.txt`
has 25,722 lines (17 locales identical) and none matches `^0\s`. So a synthesised tech resolves to
nothing — unnamed in the build panel, unnamed in the tech tree, blank tooltip.

And it cannot be fixed the easy way. For a **shipped** tech those four fields are `w.op()` replay
(`aoe2mod/dat/writer.py:878`, `:886`), so the model value is ignored:

```
setting tech[67]['lang_name']       = 30030002 -> bytes changed=False
setting tech[67]['costs']           = [[1,1,1],[-1,0,0],[-1,0,0]] -> bytes changed=False
setting tech[67]['required_techs']  = [999]    -> bytes changed=False
setting tech[67]['research_time']   = 5        -> bytes changed=False
```

The only model-writable tech fields are `civ` (`:874`), `effect_id` (`:881`), `type` (`:882`),
`icon_id` (`:883`), `name` (`:889`, the 4-byte-marker debug string) and `research_locations`
(`:893-895`). The model dict carries exactly
`['civ','effect_id','icon_id','name','research_locations','type']` (union over all 1510 records) —
there is no field for costs, prerequisites, or any display string.

Reusing one of the 104 inert slots does not help either, because of a second failure: **changing a
record's length in place desyncs the verbatim tail.**

```
slot 985, name=''    , loc (109,25,1,-1) -> delta +0   mm=0  re-parses, reads back correctly
slot 985, name='Recon' (5 B)            -> EOFError: read of 40 byte(s) at offset 93268141
                                           would pass end of file (93268152)
slot 1449, name='Recon Tech' (10 B)     -> EOFError: read of 40 byte(s) at offset 93268122
```

So slot reuse is byte-neutral-only, and a byte-neutral edit still cannot set `LanguageDLLName`
(replay field). **Both routes need new writer code; neither is a config change.**

### 2. Nothing tells the engine the tech exists (discovery is two third-party tables)

A tech record alone is inert. Two side-tables decide whether a player ever sees it:

* `resources/_common/dat/futuravailableunits.json` — 1,331,147 B, 57 top-level civ keys, shape
  `{civ: {"Buildings": [{"ID","Name","Techs":[{"ID","Name","RequiredAge"}],"Units":[...]}]}}`.
  Britons = 31 buildings, 92 tech entries (91 distinct); Loom is
  `{"ID": 22, "Name": "Loom", "RequiredAge": 1}` under building 109 (Town Center), identical for Teutons.
  `aoe2mod/game/buildpanel.py:47-50` records that it **must not be re-serialised** ("No `json.dumps`
  rule reproduces it, so the writer edits the TEXT surgically").
* `resources/_common/dat/CivTechTrees/*.json` — 62 files, 10,742 rows.

Coverage measured against the 563 techs that carry a `location_id >= 0` in the `.dat`:

| discovery layer | researchable techs covered | missing |
|---|---|---|
| `futuravailableunits.json` (+ paphos) | 363 / 563 | **200** |
| `CivTechTrees` research rows (240 distinct ids) | 231 / 563 | **332** |

Both layers are therefore *not strictly required* by the engine — 200 shipped techs are researchable
without a panel entry — but that also means a new tech with a valid `research_location` may simply
never be offered anywhere, and **no product code writes either table for a tech**. The one existing
writer covers the panel only for units/availability, and the tree only through replay. The most
likely observable outcome is a tech that exists in the `.dat`, is referenced by a building in the
`research_locations` array, and still cannot be clicked.

### 3. Counts and the id space — silent corruption, then a hard ceiling

**(a) The writer does not validate counts.** Bumping `tech_tree["research"]` from 241 to 242 without
adding a row produced **0 mismatches** — the stream was "successfully" written — and only died on
re-parse: `EOFError: read of 40 byte(s) at offset 93268122 would pass end of file (93268152)`.
`strict=True` does not catch a count/body disagreement, so a bad `tech.create` can build a mod that
fails at load with no error at write time.

**(b) The tech tree has a hard u8 ceiling.** `aoe2mod/dat/writer.py:966-967`
`w.u8(tt["research"])` (i16 only for the CCV2 build). Shipped value 241 → **14 rows of headroom**.
The tech count itself is i16 (`:1046`, 1510 sold, 31,257 free) and the effect count i32 (`:1029`).

**(c) The next tech id is already used by a unit.** A tech is addressed by its position —
`aoe2mod/dat/locate.py:433-442` "A tech is addressed by its POSITION in the array — the record
carries no id field" — so appending makes the new tech **id 1510**, and unit 1510 exists:
`'CityGate NE (Rubble)'`. The two spaces are merged in the CivTechTrees Node ID space
(`aoe2mod/game/buildpanel.py:52-54` "Unit ids and tech ids share an integer space (38 overlap)";
measured intersection = **43 ids**). First ids ≥ 1510 that are neither a tech nor a unit:
**2113, 2114, 2115, 2116, 2136, 2137, 2152**.

---

## What I did NOT verify (honesty boundary)

* **Nothing was tested in game.** Every claim about visibility, tooltips, tech-tree placement and
  clickability is `[inferred]` from the data layout and from shipped-data coverage, not observed.
* **Whether the engine reads `icon_id` per tech record.** `[inferred]` — evidence is that
  `Techs[000]`/`Techs[006]`/`Techs[017]`/`Techs[312]` line up with CropRotation/Loom/Forging/SapperTunnel,
  and `aoe2mod/game/icons.py:28` says "Technologies always use the \"Techs\" section". Proof would
  need a running game.
* **Whether a tech id > 1509 is accepted by the engine at all.** Untested. The 62 `CivTechTrees` files
  already name 517 Node IDs above 1509 (max 2712), which is *encouraging* but those are node ids, not
  proven `.dat` tech indices.
* **Whether a researchable tech with no panel entry really appears.** I only measured that 200 such
  techs exist in shipped data; I did not resolve which civ/building combination reaches them.
* **`required_techs` semantics beyond "list of tech ids".** The `Research.cpp` citations in the parser
  suggest an AND gate; I did not test an OR/empty case. Cost triple encoding
  `(resource_id, amount, enabled)` is read off the pattern `(3,300,1)`/`(1,1,1)`, not proven.
* **Effect command semantics.** I read types off `aoe2mod/schema/dat_bindings.json:151`, not from
  in-game behaviour. I did not verify that a tech pointing at `effect_id = -1` does nothing observable
  (330 shipped techs do exactly that, 62 of them researchable — suggestive, untested).
* **`futuravailableunits.json` entry requirements.** I saw `{"ID","Name","RequiredAge"}` and the
  `Prereq*` keys used by units, but did not determine which fields the engine *requires* for a tech row
  or what happens when `Name` disagrees with the `.dat` string id.
* **Localisation.** All 17 locale tables were counted for max id, but I only inspected the body of
  `en`, `zh`, `tw`. Whether the engine falls back to `en` for a missing id is untested.
* **The `_new` append was never written to disk or installed** — the probe mods under `_probe/`
  are from earlier sessions, and I added none.

---

## Raw-measurement appendix

### A. Container layout (measured)

```
file              93,268,152 B uncompressed, "VER 8.9", gv=54
civs              63 (civs_start = 3,899,442)
effects           count i32 @ 3,584,190 -> 1,500 ; section ..3,733,648
techs             count i16 @ 93,067,555 -> 1,510 ; section 93,067,557 .. 93,202,964 = 135,407 B
post-tech header  7 x i32 @ 93,202,964 = (30, 7, 14, 700, 1400, 5, 10)
tech tree         @ 93,202,992 .. 93,268,152
  ages u8=4  buildings u8=37  units i16=266  research u8=241  total_unit_tech_groups i32=116
```

### B. Tech record (gv=54; the `< GV_C31` scalars are absent)

```
RequiredTechs[6]                 i16 x 6      12 B   (prereq TECH ids, -1 padded)
ResearchResourceCost[3]          (i16,i16,u8)x3  15 B
RequiredTechCount                i16           2 B
Civilization                     i16           2 B   (-1 = available to all civs)
FullTechMode                     i16           2 B
LanguageDLLName                  i32           4 B
LanguageDLLDescription           i32           4 B
EffectID                         i16           2 B   (index into the effects array, -1 = none)
Type                             i16           2 B
IconID                           i16           2 B   (index into icons.json `Techs`)
LanguageDLLHelp                  i32           4 B
LanguageDLLTechTree              i32           4 B
debug string (u16 marker,u16 len) + bytes    4+len B
Repeatable                       u8            1 B
NumResearchLocations             i16           2 B
research_location x n            i16,i16,u8,i32  9 B each
```

**size = 62 + len(name in latin-1) + 9 × nlocs** — verified against all 1510 records with 0 mismatches
(simplified form `71 + len(name) + 9*(nlocs-1)`, also 1510/1510). Sizes 71..134, mean 89.7, sum 135,407,
57 distinct values → **not constant**.

`research_location` (9 B): `i16 location_id` (the building that researches it; -1 = not
player-researchable), `i16 research_time` (seconds), `u8 button_id`, `i32 hotkey_id`.
**`research_time` exists only here** — there is no scalar in the record for gv ≥ C31
(`aoe2mod/dat/parser.py:924`).

### C. Worked examples (all measured, raw values)

| tech | civ | icon | effect | required_techs | costs | locs | size |
|---|---|---|---|---|---|---|---|
| 22 Loom | -1 | 6 | 22 | [104] | (3,50,1),(-1,0,0),(-1,0,0) | (109,25,6,18022) | 75 B |
| 67 Forging | -1 | 17 | 67 | [101] | (0,150,1),(-1,0,0),(-1,0,0) | (103,50,1,18067) | 78 B |
| 263 Longbow (make avail) | 1 | -1 | 251 | [102,266] | all (-1,0,0) | (-1,0,0,-1) | 91 B |
| 383 C-Bonus, +25% Shepherd | 1 | -1 | 381 | [] | all (-1,0,0) | (-1,0,0,-1) | 93 B |
| 985 (inert) | -1 | -1 | -1 | all -1 | all (0,0,0) | (-1,0,0,-1) | 71 B |

Tech 22 byte dump: 12+15+2+2+2+4+4+2+2+2+4+4 = 55, then name marker/len (4) + `Loom` (4) + repeatable (1)
+ nloc (2) + 9 = **75 B at offset 93,069,459**.

### D. Population statistics (1510 techs)

```
civ           -1 -> 601 ; 0..62 -> 909 ; all 63 civs present ; nothing outside -1..62
type          0 -> 1488, 2 -> 3, 32 -> 6, 33 -> 13
effect_id     -1 -> 330 (62 of them researchable) ; valid -> 1180 ; max 1498
icon_id       -1 -> 974 ; 182 distinct ; 534 in 0..312 ; 8133 (tech 134), 8142 (tech 143)
RequiredTechCount  0 -> 393, 1 -> 752, 2 -> 347, 3 -> 17, 5 -> 1
RequiredTechs slot values  -1 x6908, 0 x661, 102 x298, 103 x285, 101 x104, 104 x93
cost triples  (-1,0,0) x3298, (0,0,0) x337, (1,1,1) x61, (3,300,1) x37
Repeatable    0 -> 322, 1 -> 1188
research_locations count  1 -> 1496, 2 -> 7, 3 -> 7
real researchable (loc>=0)  563 ; with lang_name>0 too  470
lang_name >0  1309 ; ==7000  734 ; desc==8000  714 ; help>0  1420 ; tree>0  1420
lang_name max 507034 ; desc max 508034 ; help max 607034 ; tree max 657034
shipped id pattern: name = 7000+id, desc = 8000+id, help = 107000+id, tree = 157000+id
```

### E. Effects

```
count i32 @ 3,584,190 -> 1500 ; section 3,584,190 .. 3,733,648 = 149,454 B
size = 6 + len(name) + 11 × cmds          (0 / 1500 mismatches)
sizes 6..2101, 291 distinct -> not constant ; 344 effects have 0 commands
commands total 10,500, mean 7.00, max 189
command = u8 type, i16 a, i16 b, i16 c, f32 d   (11 B, aoe2mod/dat/writer.py:525)
type histogram (top): 4x3026, 5x2366, 102x1969, 0x1094, 3x434, 101x377, 8x255, 201x132
effect ids referenced by >1 tech: 37 (max 88 refs) ; referenced by none: 486
```

### F. Inert slots and free ids

```
104 inert tech slots (civ=-1, effect=-1, icon=-1, type=0, lang=7000/8000/107000/150000, locs=((-1,0,0,-1),), name='')
  985 987 989 1077 1078 1101 1102 1104-1109 1117 1118 1119 1139 1156 1157 1168 1172 1178 1179
  1190-1194 1199 1200 1201 1219 1231-1239 1250-1257 1274 1337 1338 1339 1409-1449 1455 1456 1457
  1463 1466 1467 1468 1480 1487 1499
none of them is referenced by any of the 240 tech-tree research ids  (intersection = 0)
tech ids 0..1509 all allocated (no free slot inside the table)
unit ids run 0..2749 ; unit 1510 = 'CityGate NE (Rubble)' exists
shared Node ID intersection (tech-ish vs unit-ish) = 43 ids
first ids >=1510 that are neither tech nor unit: 2113 2114 2115 2116 2136 2137 2152
```

### G. Strings and icons

```
17 locales, key-value-strings-utf8.txt, 25,722 lines each, 15,351 numeric ids, max = 30030001
ids above 30030001: 0  ->  first free name id = 30030002, description = 30030003
id 0 defined: NO (0 of 17)
key-value-modded-strings-utf8.txt already ships in all 17 locales as a 605 B / 15-line instructions stub

icons.json (widgetui/, 75,114 B) sections:
  Buildings 117, Units 1000, Techs 313, StatIcons 24, CivTechTree 67, CivEmblem 67,
  InGameCivEmblem 63, CivHero 67, CivUniqueUnit 65, CivSecondaryUniqueUnit 65,
  MapIcons 217, History 87, Notification 2, MenuIcons 9
Techs keys "000".."312" contiguous, all 313 non-empty -> NO empty slot
but only 179 slots are used by any tech -> 134 free for reuse, 129 of which resolve to a real file
  e.g. 8  -> TechIconsT008WarGalley  -> textures/ingame/tech/008_war_galley.dds
       9  -> TechIconsT009CannonGalleon, 59 Galleon, 135 DragonShip, 150-153 ages, 173+ ...
  5 are dummies that do not resolve: 20, 24, 90, 102, 117 (material '...Xxx')
used slots that fail to resolve: 0 and 4
```

### H. Append experiments (in memory only)

```
baseline re-serialise                       : 93,268,152 B, identical, 0 mismatches
append tech only (_new, name 'Recon Probe Tech' = 16 B, 1 loc)
                                            : +87 B   == 62 + 16 + 9, formula holds exactly
append effect + tech                        : +122 B, 0 mismatches, re-parse OK (techs 1511, effects 1501)
reused slot 985, name='' , loc (109,25,1)   : +0 B, 0 mismatches, re-parses, reads back exactly
reused slot 985, name='Recon' (5 B)         : EOFError at 93268141 (record grew, tail desynced)
tech_tree['research'] 241 -> 242, no new row: 0 mismatches(!) then EOFError at 93268122 on re-parse
set tech[67] lang_name / costs / required_techs / research_time : all four "bytes changed=False"
```
