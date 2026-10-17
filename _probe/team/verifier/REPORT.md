# Independent verification of the `aoe2mod Smoke5 TreeVsPanel` artifact

**Verifier:** teammate `artifact-verifier` (shared task `task-2`)
**Date:** 2026-10-15
**Installed mod under test (READ-ONLY):**
`C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Smoke5 TreeVsPanel`
**Game install (READ-ONLY):** `D:\Games\Steam\steamapps\common\AoE2DE`
**Independence statement:** the Lead's `_probe/verify_smoke5.py` was **never executed or read**.
Every number below comes from my own stdlib-only scripts in `_probe/team/verifier/`. The
project parser `aoe2mod` was used **only** as a secondary cross-check (v9) and its result is
labelled as such; all primary evidence is raw-byte.

## Reproduce

```
$env:PYTHONIOENCODING='utf-8'
$PY = 'C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
& $PY "_probe\team\verifier\v1_inventory.py"     # inventory + inflate both .dat copies
& $PY "_probe\team\verifier\v2_diffs.py"         # raw positional .dat diff + JSON diffs
& $PY "_probe\team\verifier\v3_layout.py"        # decode the fields around each changed offset
& $PY "_probe\team\verifier\v4_json_checks.py"   # node-level JSON semantics
& $PY "_probe\team\verifier\v5b_diag.py"         # locate the unit Name by marker scan
& $PY "_probe\team\verifier\v6_name_map.py"      # name every changed unit via the game strings
& $PY "_probe\team\verifier\v7_structure.py"     # 63-block proof + JSON raw byte spans
& $PY "_probe\team\verifier\v8b_freshscan.py"    # from-scratch diff of the mod .dat on disk
& $PY "_probe\team\verifier\v10b_pureedit.py"    # prove pure insert / pure delete
# secondary (uses aoe2mod, needs PYTHONPATH):
$env:PYTHONPATH='D:\Software\DeepSeek Harness\工作区2'
& $PY "_probe\team\verifier\v9_semantic.py"
```

## Headline

**The `.dat` was NOT changed the way the claim says.** The claim says Villager (id 83)
hit points became 1000. That is true — but the artifact changed **1701 hit-point fields:
27 distinct unit IDs × 63 civs**, every one of them `25 -> 1000`. All 27 are the
villager/task-worker family. This is the single fact that decides the verdict.

---

## Claim 1 — Villager (id 83) HP == 1000 for all 63 civs; game has 25

> "Installed mod … has Villager (id 83) hit points == 1000 for ALL 63 civs, while the
> GAME's own `empires2_x2_p1.dat` has 25."

### Verdict: **CONFIRMED** (for id 83) — but the implied exclusivity is **REFUTED**

**Evidence A — file identity and inflation (v1, `v1_inventory.py`).**

| | mod | game |
|---|---|---|
| size | 11 983 020 B | 12 023 754 B |
| sha256 | `330665c06b53f0330d9f908ebe019b0b7139dfc75edade49462a9d9de68119e7` | `4aa2f0a719e88e5f1502517eddb27c669aeb40c2fe9d8c4f3eec7751c01e7baa` |
| header | `VER 8.9\x00` | `VER 8.9\x00` |
| inflated (raw) | 93 268 152 B, `eof=True`, `unused_tail=0` | 93 268 152 B, `eof=True`, `unused_tail=0` |
| inflated sha256 | `87d77751ef61fb1e988910bf4a392d02dca94138998780e382c534e68f8270e3` | `02a09b48a0fbd2116295cad2ebdd28dfa20b92b44e29b360f8639e5fb73405df` |

Both were inflated by me with `zlib.decompressobj(-15)` (raw deflate, window_bits = **-15**,
per `aoe2mod/dat/parser.py:300-315`). The two raw streams have **equal length**, so a
positional diff is well defined. (The skill warns that an emitted .dat must not be
hash-compared against a raw base file — here both are inflated to raw first, so the
comparison is apples-to-apples.)

**Evidence B — raw positional diff (v2, `v2_diffs.py`; re-derived from scratch in v8b).**

```
differing byte positions: 3402
differing byte VALUE pattern: Counter({(25, 232): 1701, (0, 3): 1701})
contiguous differing runs: 1701 ; run lengths: Counter({2: 1701})
every run is exactly LE-int16 25 -> 1000: True
```
That is `0x19 0x00` -> `0xE8 0x03`, i.e. little-endian int16 **25 -> 1000**, and **nothing
else in the 93 MB file differs**. Odd/even HP offsets: even 862 / odd 839 — the unit
records are *not* 2-byte aligned, because each record carries a variable-length debug
name; a first scan that stepped 2 bytes (v8) found only 862 of the 1701 fields.

**Evidence C — structural identity of the changed field (v3, `v7`, `v8b`).**
Decoding the genieutils `Unit::serializeObject()` layout (`_probe/source/genieutils/src/dat/Unit.cpp:51-249`),
the field at each changed offset is preceded 21 bytes earlier by the unit ID
(`id` at HP−21, `class` at HP−11, `LoS` float at HP+2):

```
distinct unit IDs at HP-21: 27
per-ID counts: {56:63, 57:63, 83:63, 118:63, ... , 2333:63, 2334:63}
id 83 (Villager) occurrences: 63
all IDs changed exactly 63 times: True
HP identity (game, mod) at every changed offset: Counter({(25, 1000): 1701})
LineOfSight at HP+2 == 4.0 for all 1701 ; UndeadMode == 0 ; GarrisonCapacity == 0
groups of 27 fields: 63 ; every group has the same ID sequence: True
```

So id **83 IS changed in 63/63 civs, 25 -> 1000** — claim 1's specific statement is true.

**Evidence D — independent confirmation of the record identity (v5b/v6, raw marker scan).**
Hand-summing a field prefix is unreliable, so I located each record's debug `Name` by
scanning forward for the `serializeDebugString` marker `0x0A60`
(`ISerializable.h:310-316`). It sits at **HP+158** in all 1701 records and decodes to
`VMFIS`, `VFFIS`, `VMBAS`, … — and `LanguageDLLName` (i32 at HP−19) resolved through the
**game's own** `resources\en\strings\key-value\key-value-strings-utf8.txt` (v8) gives:

```
id 5121 -> "Villager (Male)"     id 5607 -> "Villager (Female)"     id 5606 -> "Villager"
```

**Evidence E — the 27 changed unit IDs** (all class 4, all 63 civs, all 25 -> 1000):

| ID | internal | display | ID | internal | display |
|---|---|---|---|---|---|
| 56 | VMFIS | Fisherman | 214 | VFFAR | Farmer |
| 57 | VFFIS | Fisherman | 216 | VFHUN | Hunter |
| **83** | **VMBAS** | **Villager (Male)** | 218 | VFLUM | Lumberjack |
| 118 | VMBLD | Builder | 220 | VFMIN | Stone Miner |
| 120 | VMFOR | Forager | 222 | VFREP | Repairer |
| 122 | VMHUN | Hunter | 259 | VMFAR | Farmer |
| 123 | VMLUM | Lumberjack | **293** | **VFBAS** | **Villager (Female)** |
| 124 | VMMIN | Stone Miner | 354 | VFFOR | Forager |
| 156 | VMREP | Repairer | 579 | VMGLD | Gold Miner |
| 212 | VFBLD | Builder | 581 | VFGLD | Gold Miner |
| | | | 590 | VFSHE | Shepherd |
| | | | 592 | VMSHE | Shepherd |
| | | | **1810** | **SVMBAS** | **Villager** |
| | | | 1891 | VFHER | Herder |
| | | | 1892 | VMHER | Herder |
| | | | 2333 | VMGLD | Pearler |
| | | | 2334 | VFGLD | Pearler |

`class histogram Counter({4: 27})` — class 4 is the villager/task-worker class. So the
change is **Villager plus the whole villager-family**, not Villager alone.

**Secondary cross-check (v9, uses `aoe2mod`) — labelled secondary, not used as proof.**
Iterating every civ's unit list with the project parser from `aoe2mod/dat/parser.py`
(`Parser.parse()` stage 8, `read_civ` at parser.py:854-871) reports the *same* answer:
`unit IDs whose hit_points differ: 27`, `every changed unit changed in exactly 63 civs:
True`, `union of (game_hp, mod_hp) pairs: {(25, 1000)}`, `id 83 present among changed:
True`. This agrees with the raw bytes; it is corroboration, not the proof. (The parser was
also the only source of the stage-8 byte offset 0x003B8030 used in v10.)

**What is NOT proven here.** The offset `HP−21` *is* the ID field, and `HP−19` *is*
`LanguageDLLName`, by the genieutils layout; two independent implementations
(genieutils C++ and the project's parser) agree on it, and the `0x0A60` name marker
independently corroborates record identity — but there is no self-describing marker in
the raw bytes that *proves* the ID offset. Any conclusion that a changed offset belongs to
"unit 83" therefore rests on that layout. The layout-independent fact is: **1701
identical 2-byte int16 fields, arranged in 63 uniform groups of 27, all 25 -> 1000.**

---

## Claim 2 — mod `BRITONS.json` grants Champi Scout (node 2550)

> "grants Champi Scout (node 2550, Use Type Unit, Age ID 1, Building ID 12) to BRITONS,
> and that row was NOT in the shipped BRITONS file."

### Verdict: **CONFIRMED**

**Evidence A — raw bytes (v7/v10b).** The two files differ by **exactly one contiguous
insertion of 419 bytes** at offset 74564, with the tail byte-identical:

```
game 74572 B  sha256 0418f78c030c15215d01947db98dcebc73daf3379e3833d30414b4ace8154bd0
mod  74991 B  sha256 6802baf4ecb52fbed6717ddcb42d187c7d1a9512b2dd3b24580786369180de00
length delta +419 ; common prefix 74564 ; PURE INSERTION: game[74564:] == mod[74983:] ? True
game + inserted-block == mod : True
sha256 recomputed = 6802baf4ecb52fbed6717ddcb42d187c7d1a9512b2dd3b24580786369180de00  (== mod on disk)
```
The inserted 419 bytes are verbatim:
```
,\r\n    {\r\n      "Name": "Champi Scout",\r\n      "Node Type": "RegionalUnit",\r\n
"Link Node Type": "Unit",\r\n      "Draw Node Type": "UnitTech",\r\n      "Use Type": "Unit",\r\n
"Node Status": "ResearchedCompleted",\r\n      "Name String ID": 14526,\r\n      "Age ID": 1,\r\n
"Building ID": 12,\r\n      "Help String ID": 105526,\r\n      "Node ID": 2550,\r\n
"Picture Index": 540,\r\n      "Trigger Tech ID": 1350\r\n    }
```

**Evidence B — semantics (v4).** Both files have top-level keys
`['civ_id','civ_techs_buildings','civ_techs_units']`; node count mod **174** vs game **173**;
`added Node IDs = [2550]`, `removed = []`, `field-changed = []`. Node 2550 is absent from
the game file and present in the mod, and its `Node ID`=2550 / `Use Type`="Unit" /
`Age ID`=1 / `Building ID`=12 all match the claim. **It is the only tree-node difference.**

---

## Claim 3 — Militia (74) removed from panel key `Britons`

> "Its `futuravailableunits.json` no longer lists Militia (id 74) for the panel key
> `Britons`, while the game's own copy DOES list it at building 12 with RequiredAge 1,
> and all other civs that shipped it still have it."

### Verdict: **CONFIRMED**

**Evidence A — raw bytes (v7/v10b).** One contiguous **deletion of 112 bytes** at
offset 52214, tail byte-identical:

```
game 1331147 B  sha256 1abbcd6c4c5a1fd56e4032e59131840adb29a98651b688eb0054460a837091bf
mod  1331035 B  sha256 faeca198b2c17fd3e52595ce7b4134e218c1e6a52a1c73d05491c33dd40433bd
length delta -112 ; common prefix 52214 ; PURE DELETION: game[52326:] == mod[52214:] ? True
game - deleted-block == mod : True
sha256 recomputed = faeca198b2c17fd3e52595ce7b4134e218c1e6a52a1c73d05491c33dd40433bd  (== mod on disk)
```
Deleted bytes verbatim:
```
4,\r\n            "Name": "Militia",\r\n            "RequiredAge": 1\r\n          },\r\n          {\r\n            "ID": 7
```
(the deletion removes `{"ID": 74, "Name": "Militia", "RequiredAge": 1}` from between
`{"ID": 7` and the next entry).

**Evidence B — semantics (v4).** Both files have the **same 58 top-level keys**. Total
leaf/path differences game -> mod: **21**, all under the single top-level key
**`Britons`** (`distinct top-level keys touched: ['Britons']`). The 21 diffs are exactly
`/Britons/Buildings/3/Units/len` 8 -> 7 plus the positional shift of that list
(game `[74,75,77,473,567,93,358,359]` -> mod `[75,77,473,567,93,358,359]`).
The game's Britons holds unit 74 at `/Britons/Buildings/3/Units/0` =
`{"ID": 74, "Name": "Militia", "RequiredAge": 1}` inside container
`{"ID": 12, "Name": "Barracks", ...}` — **building ID 12, RequiredAge 1**, exactly as
claimed. (The only other ID-74 hit anywhere is `/Buildings/6/Techs/12` =
`{"ID": 74, "Name": "Scale Mail Armor", "RequiredAge": 2}`, a different entity sharing the
number; unchanged by the mod.) The mod's Britons has **no unit-74 entry at all**.

**Evidence C — every other civ still has it (v4).** Across all 58 panel keys:
`civs shipping unit 74 in GAME: 57`, `in MOD: 57`,
`GAME-shipping but MOD-missing: []`, `MOD-shipping but GAME-missing: []`. No other civ lost it.

---

## Claim 4 — "Nothing else changed", and the mod contains exactly 4 files

### Verdict: **CONFIRMED** for the three sub-claims as literally written; **REFUTED** if read to include the `.dat`

**4a. Exactly 4 files — CONFIRMED (v7, includes hidden files).**

| relative path | size | sha256 |
|---|---|---|
| `info.json` | 319 | `5c94a49a2a97924b8035709114ab9d039c97df7af37216108fe1f08c2236e700` |
| `resources\_common\dat\empires2_x2_p1.dat` | 11 983 020 | `330665c06b53f0330d9f908ebe019b0b7139dfc75edade49462a9d9de68119e7` |
| `resources\_common\dat\futuravailableunits.json` | 1 331 035 | `faeca198b2c17fd3e52595ce7b4134e218c1e6a52a1c73d05491c33dd40433bd` |
| `resources\_common\dat\CivTechTrees\BRITONS.json` | 74 991 | `6802baf4ecb52fbed6717ddcb42d187c7d1a9512b2dd3b24580786369180de00` |

`total files in mod: 4`, no empty directories. `info.json` verbatim:
```json
{
  "Author": "aoe2mod probe",
  "CacheStatus": 0,
  "Description": "Tests which file drives the build menu. Barracks should show Champi Scout if the tree file is read; Militia should be MISSING if the panel file is read. Villager HP 1000 is the control that the mod loaded.",
  "Title": "aoe2mod Smoke5 TreeVsPanel"
}
```

**4b. No other civ's tree — CONFIRMED (v8).** The mod ships exactly one tree file:
`mod CivTechTrees entries: ['BRITONS.json']`. Nothing else could have changed.

**4c. No other civ's panel entries — CONFIRMED (v4).** As in claim 3: the only top-level
key touched in `futuravailableunits.json` is `Britons`.

**4d. `.dat` "nothing else changed" — REFUTED.** This is the failing dimension. The claim
frames the `.dat` edit as the single Villager control; in fact **1701 hit-point fields
across 27 unit IDs × 63 civs** were rewritten, 25 -> 1000 (see claim 1). The mod's control
value is real, but it is not isolated to Villager.

---

## UNPROVEN / caveats

1. **"63 civs" mapping to named civs is not independently established.** The raw bytes
   show 63 *uniform groups* of 27 changed fields — that part is proven. Reading
   `civ_count` as `int16` = 63 at offset `0x003B8030` (v10) used the byte offset printed by
   the project parser's stage trace, so it is **secondary**. A fully independent civ count
   would require walking every preceding variable-length record from scratch, which my
   scanner does not do. The observation that the game ships **62** `CivTechTrees\*.json`
   while the `.dat` carries **63** per-civ unit-vector copies is unexplained and was not
   investigated.
2. **The "Villager = id 83" identification rests on the record layout.** The ID field
   offset (HP−21) and `LanguageDLLName` (HP−19) come from the genieutils layout, agreed by
   two independent implementations, and corroborated by the `0x0A60` name marker giving
   `VMBAS` and by the game's own string table giving "Villager (Male)". No raw
   self-describing marker proves the offset. What is layout-independent: **1701 int16
   fields, 63 uniform groups of 27, all 25 -> 1000, and no other byte differs.**
3. **A bogus line in my own `v7_structure.py` output** —
   `bytes strictly between = 88885344 (= changed byte count 3402): False` — compares the
   whole inter-prefix/suffix span against the byte count and is meaningless. The
   authoritative changed-byte count is **3402** (v2, re-derived in v8b).
4. **Stated as `UNPROVEN`, not decided:** whether the Lead *intended* only unit 83 and a
   toolchain turned it into a villager-family, or intended the whole family. The artifact
   is what it is; intent is outside this task.

---

VERDICT: ARTIFACT DIFFERS - the .dat change is not limited to Villager id 83: 1701 HitPoints fields across 27 villager-family unit IDs x 63 civs all went 25 -> 1000
