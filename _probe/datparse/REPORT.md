# Pure-Python parser for the AoE2:DE `.dat` — final report

**Target:** `<game root>/resources/_common/dat/empires2_x2_p1.dat`
**Code:** `parse_dat.py` (pure Python 3, stdlib only: `zlib`, `struct`)
**Verdict: SUCCESS. The parser consumes the file to exactly the last byte.**

---

## 1. Headline result

```
final offset        : 93268152
data size           : 93268152
exact match         : YES
leftover bytes      : 0
parse time          : 4.7 s
```

Both entry points verified to produce identical results:

| Input | Detection | size | final offset | exact |
|---|---|---|---|---|
| `empires2_x2_p1.dat` (the original) | raw deflate, `window_bits=-15` | 93,268,152 | 93,268,152 | YES |
| `_probe\dat_raw.bin` (pre-inflated) | already starts `VER ` → pass-through | 93,268,152 | 93,268,152 | YES |

The parser inflates the original `.dat` itself (`zlib.decompressobj(-15)`) — the pre-inflated copy is only a shortcut.
Reading to exactly the end with zero leftover is the hard proof: one wrong field width anywhere in the 93 MB
would desynchronise the stream and the remaining sections would decode into garbage or run past EOF.

## 2. Top-level sections, in true `serializeObject()` order

| # | Section | Start | End | Bytes |
|---|---|---|---|---|
| 1 | FileVersion (`"VER 8.9\0"`) + terrain-restriction block | 0x00000000 | 0x000001BC | 444 |
| 2 | TerrainRestrictions (54 × [134 float + 134 × TerrainPassGraphic]) | 0x000001BC | 0x0002370C | 144,720 |
| 3 | PlayerColours (16 × 9 × int32) | 0x0002370C | 0x0002394E | 578 |
| 4 | Sounds (769) | 0x0002394E | 0x00044DC0 | 136,306 |
| 5 | Graphics count (int16 = 21,001) | 0x00044DC0 | 0x00044DC2 | 2 |
| 6 | Graphics pointer array (21,001 × int32) | 0x00044DC2 | 0x000595E6 | 84,004 |
| 7 | Graphics bodies (20,883 non-null) | 0x000595E6 | 0x00355E8E | 3,131,560 |
| 8 | TerrainBlock (200 Terrains) | 0x00355E8E | 0x0036B0B6 | 86,568 |
| 9 | RandomMaps (**0 maps**: count uint32 + ptr int32) | 0x0036B0B6 | 0x0036B0BE | 8 |
| 10 | Effects (int32 count = 1,500) | 0x0036B0BE | 0x0038F890 | 149,458 |
| — | *UnitLines — **not present** for this version* | — | — | — |
| 11 | UnitHeaders (int32 count = 1,701) | 0x0038F890 | 0x003B8030 | 165,792 |
| 12 | Civs (int16 count = 63) | 0x003B8030 | 0x058C1923 | 89,168,115 |
| 13 | Techs (int16 count = 1,510) | 0x058C1923 | 0x058E2A14 | 135,409 |
| 14 | Tail 7 × int32 (TimeSlice…RazingKillTotal) | 0x058E2A14 | 0x058E2A30 | 28 |
| 15 | TechTree | 0x058E2A30 | 0x058F28B8 | 65,160 |

Order after Graphics is: **TerrainBlock → RandomMaps → Effects → UnitHeaders → Civs → Techs → tail int32s + TechTree.**
The brief's expectation listed Techages/Effects → Techs → UnitHeaders → Units → Civs; the actual source order is
Effects **before** UnitHeaders, and Units are nested inside Civs, not a top-level section. Two things worth noting:
the "Graphics ptr-array @0x44dc0" figure is really the **count** field (the array proper starts at 0x44DC2), and
"Graphics bodies @0x595e6" is **exactly right**. RandomMaps holds **zero** maps in this file — it decodes to
`count=0, ptr=0`, which is why the earlier terrain-count heuristic scan kept flagging spurious candidates.

## 3. Counts

| Item | Value |
|---|---|
| FileVersion | `'VER 8.9'` → `GV_C32` = `GV_LatestDE2` |
| Terrain restrictions | 54 |
| `TerrainsUsed1` | 134 |
| Player colours | 16 |
| Sounds | 769 |
| Graphics (total slots) | 21,001 |
| Graphics (nonzero pointer, actually serialized) | 20,883 |
| Terrains in TerrainBlock | 200 |
| RandomMaps | **0 maps** (count=0, ptr=0 — DE ships random maps as external `.rms` scripts under `resources\_common\random-map-scripts`, so the in-dat array is empty and the `io_all_` double-pass at `RandomMap.cpp:62-63` runs over nothing) |
| Effects | 1,500 |
| Unit lines | **not present** (`gv >= GV_SWGB` is false) |
| Unit headers | 1,701 |
| Civs | 63 |
| Techs | 1,510 |
| TechTree ages / buildings / units / research | 4 / 37 / 266 / 241 |
| Unit objects decoded across all civs | 136,861 |

## 4. First 5 units inside `Civs` (as the file stores them)

| # | name | hit points | Type | id |
|---|---|---|---|---|
| 0 | `OLD-ACADEMY` | 1 | 70 (Creatable) | 0 |
| 1 | `LEGION` | 75 | 70 | 1 |
| 2 | `LEGION_D` | 0 | 30 (Dead_Fish) | 2 |
| 3 | `ARCHR_D` | 0 | 30 | 3 |
| 4 | `ARCHR` | 30 | 70 | 4 |

Civ[0] is `Gaia` (2,693 units); the other 62 civs each hold 2,164.

## 5. Independent correctness evidence

Byte-exact length could in principle come from two compensating errors, so the parse was validated
two further ways (`validate_semantics.py`, **10/10 PASS**):

**Internal cross-section consistency**
- all 7 distinct unit `Type` values are legal `UnitType` enum members (10, 20, 25, 30, 60, 70, 80);
- unit ids unique within all 63 civs;
- all 1,510 tech `EffectID`s are `-1` or a valid index into the 1,500-element Effects array (cross-section integrity — a desynchronised stream cannot satisfy this);
- all tech `Civ` values are `-1` (all-civs sentinel) or a valid index into the 63 civs, max = 62 = last civ;
- the only negative graphic SLP is the `-1` "no sprite" sentinel (5,000 graphics);
- all 5,733 empty-name units are `Type=10` (EyeCandy decoration slots), hp=1;
- all 136,861 unit names are clean ASCII (no mojibake).

**External ground truth** — 11/11 canonical AoE2 unit ids decode to their exact known hit points:
Archer (id 4) 30, Skirmisher (7) 30, Longbowman (8) 35, Knight (38) 100, Militia (74) 40,
Man-at-Arms (75) 45, Villager (83) 25, Spearman (93) 45, Scout Cavalry (448) 45,
Light Cavalry (546) 60, Eagle Scout (751) 50.

## 6. Uncertainties — explicit

**One genuine ambiguity was found and resolved; nothing is papered over.**

1. **`Terrain.Phantom` (2 bytes) — RESOLVED, not uncertain.** The `GV_C32` analysis initially treated
   `GV_SWGB` guards as false. `Types.h` orders `GV_C32` = **54** and `GV_SWGB` = **55**, so
   `gv < GV_SWGB` is **TRUE** and `Terrain.cpp:196 serialize<int16_t>(Phantom)` **does** execute.
   Omitting it made every terrain record 2 bytes short (429 vs the true 431), which surfaced as a
   400-byte EOF overrun at stage 4 (200 terrains × 2). A full re-audit of every `GV_SWGB` site showed
   `Phantom` was the **only** behavioural change (`getZoneCount`/`getSlots` stay 10; `TerrainPassGraphic`
   still 4 bytes; the fixed-size-name branches are not taken).
2. **`UnitLines` absent — a deliberate, source-backed omission.** `DatFile.cpp:214` guards UnitLines with
   `if (gv >= GV_SWGB)`, false for `GV_C32`, so a `VER 8.9` file has no UnitLines array at that position.
   The task brief listed it as stage 6; the source contradicts that, and reading it would corrupt every
   following section. The parser skips it and records the note.
3. **`Terrain::getTerrainCount` return of 200 — confirmed empirically, not guessed.** `Terrain.cpp:55-74`
   returns 200 for `gv >= GV_C8 && gv <= GV_LatestDE2`. Note `DatFile.cpp:160` calls only
   `TerrainRestriction::setTerrainCount`, so `Terrain::terrain_count_` stays 0 and the 200 literal applies.
   Independently confirmed: terrain 0 decodes to a real terrain record (Name `Grass`, Name2 `g_grs`,
   SLP 15001, 431 bytes) and the 200-terrain block lands exactly on the RandomMaps header.
4. **No other field width was guessed.** Every remaining read is a direct transcription of the C++
   `serialize<T>` calls with the `GV_C32` branch hardcoded.

Nothing else is uncertain. The only section whose existence/width needed reconstruction was `Phantom`,
and that is now proved rather than assumed.

## 7. The decision-relevant question

**Is a pure-Python, dependency-free parser of the full DE `.dat` realistically achievable? — Yes, clearly.**

- **It is done, and it is complete.** 93,268,152 / 93,268,152 bytes, zero leftover, no overrun, in 4.7 s.
- **Size of the real parser: `parse_dat.py` = 1,026 lines / ~40 KB / 46 functions.** That covers every
  top-level section plus the full nested tree (Terrains, Graphics with pointer indirection, Terrains/TileSizes,
  RandomMaps with the `io_all_` double pass, Effects, UnitHeaders/Tasks, Civs/Units and all seven unit
  sub-structs, Techs, TechTree). Validation adds 183 lines. Total ≈ 1,209 lines.
- **Cost driver is not code volume, it is spec fidelity.** The bytes are trivial (`struct` + bounds checks;
  the whole `Reader` class is ~110 lines). The effort is transcribing the *version-conditional* read order
  and getting the guards right — the single `GV_C32 < GV_SWGB` mis-evaluation cost the entire stage-4
  investigation. With the shipped C++ as the spec this is mechanical.
- **Runtime cost is negligible:** 4.7 s and no dependency beyond `zlib`/`struct` for a 93 MB file.
- **Recommendation:** viable as a product dependency. The one thing to institutionalise is a
  version-guard test matrix — the format is version-conditional everywhere, and a wrong guard fails
  silently as a desync, not as an exception. Prefer discriminating on a human-readable field (e.g. a
  terrain name) over structural plausibility scans when debugging, and always assert
  `offset == len(data)` at the end.

Ambiguity note for the record: the only structural fact that could not be settled from the included C++
alone was whether `Terrain.Phantom` is present; it was resolved by arithmetic against the known file size
(400-byte overrun = 200 × 2 bytes) and then confirmed by landing exactly on the next section.
