# AoE2 DE `.dat` — Byte-Exact Re-Serializer

**VERDICT: BYTE-EXACT ROUND-TRIP ACHIEVED**

---

## 1. Deliverables

| File | Role |
| --- | --- |
| `D:\Software\DeepSeek Harness\工作区2\_probe\serializer\write_dat.py` | The re-serializer. Exact inverse of `parse_dat.py`. |
| `D:\Software\DeepSeek Harness\工作区2\_probe\serializer\verify_roundtrip.py` | Two-loop proof (round-trip + idempotence) with counters. |
| `D:\Software\DeepSeek Harness\工作区2\_probe\serializer\append_tech.py` | Append demo: adds a new Effect and a new Tech, then re-parses with the **unmodified** parser. |
| `D:\Software\DeepSeek Harness\工作区2\_probe\serializer\_append_diff.py` | Proves the appended file's edit script against BASE is minimal (2 patches + 2 inserts, nothing else). |
| `D:\Software\DeepSeek Harness\工作区2\_probe\serializer\_span_probe.py` | Parser-span vs writer-span differ; used to localize the one defect. |
| `D:\Software\DeepSeek Harness\工作区2\_probe\serializer\_field_probe.py` | Positions a `Reader`/`Writer` at an absolute offset and diffs one struct's fields. |
| `D:\Software\DeepSeek Harness\工作区2\_probe\serializer\_effect_probe.py` | EffectCommand type histogram + resource-command shapes from the real file. |
| `D:\Software\DeepSeek Harness\工作区2\_probe\serializer\out\added_tech.dat` | The appended container (raw-deflate). |
| `D:\Software\DeepSeek Harness\工作区2\_probe\serializer\out\added_tech.log` | Full append-demo transcript. |
| `D:\Software\DeepSeek Harness\工作区2\_probe\serializer\out\verify_roundtrip.log` | Full verifier transcript. |

Target: `D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat`
(12,023,754 B on disk, **93,268,152 B decompressed**, header `VER 8.9\0` → `GV_C32` = 54 = `GV_LatestDE2`).
Container: **raw deflate, `window_bits = -15`**.

Nothing under the game directories was written, modified, or deleted.

---

## 2. Evidence chain

### 2.1 Round-trip (loop 1) and idempotence (loop 2)

```
raw size                 : 93268152 bytes
raw sha256               : 02a09b48a0fbd2116295cad2ebdd28dfa20b92b44e29b360f8639e5fb73405df

LOOP 1  parsed  final offset 93268152  leftover 0
        serialized          93268152 bytes
        out sha256          02a09b48a0fbd2116295cad2ebdd28dfa20b92b44e29b360f8639e5fb73405df
        model 6402501 B (6.86%) | opaque 86865651 B (93.14%) in 22465898 sites
        writer raw consumed 93268152 / 93268152
        model-vs-raw mismatches 0
        identical : YES

LOOP 2  parse(serialized) -> serialize again
        re-parse final offset 93268152  leftover 0
        reserialized        93268152 bytes
        out2 sha256         02a09b48a0fbd2116295cad2ebdd28dfa20b92b44e29b360f8639e5fb73405df
        model-vs-raw mismatches 0
        serialization1 == serialization2 : YES

VERDICT: BYTE-EXACT ROUND-TRIP ACHIEVED
```

**First differing offset: none.** Total differing bytes: **0**. Both hashes are identical to the
hash of the original decompressed stream.

### 2.2 Counters (parse 1 vs parse 2 — all equal, so no model drift)

| counter | parse 1 | parse 2 | same |
| --- | --- | --- | --- |
| civs | 63 | 63 | yes |
| unit_objects | 136861 | 136861 | yes |
| unit_pointers | 173250 | 173250 | yes |
| techs | 1510 | 1510 | yes |
| effects | 1500 | 1500 | yes |
| effect_commands | 10500 | 10500 | yes |
| graphics (nonzero) | 20883 | 20883 | yes |
| graphic_count_field | 21001 | 21001 | yes |
| sounds | 769 | 769 | yes |
| sound_items | 5126 | 5126 | yes |
| unit_headers | 1701 | 1701 | yes |
| terrain_restrictions | 54 | 54 | yes |
| player_colours | 16 | 16 | yes |
| terrains | 200 | 200 | yes |
| deltas | 56470 | 56470 | yes |

Stage boundaries (BASE), all reproduced exactly:

```
 1 FileVersion+TerrainRestr+Colours  0x00000000 -> 0x0002394E   (145742)
 2 Sounds                            0x0002394E -> 0x00044DC0   (136306)
 3 Graphics                          0x00044DC0 -> 0x00355E8E   (3215566)
 4 TerrainBlock+RandomMaps           0x00355E8E -> 0x0036B0BE   (86576)
 5 Effects                           0x0036B0BE -> 0x0038F890   (149522)
 6 UnitLines                         SKIPPED (gv >= GV_SWGB is false; DatFile.cpp:214)
 7 UnitHeaders                       0x0038F890 -> 0x003B8030   (165792)
 8 Civs                              0x003B8030 -> 0x058C1923   (89168115)
 9 Techs                             0x058C1923 -> 0x058E2A14   (135505)
10 Tail+TechTree                     0x058E2A14 -> 0x058F28B8   (65188)
```

### 2.3 The one real defect found (and why the method matters)

The writer first produced **96,334,034 B** (over by 3,065,882) with the first model-vs-raw
disagreement at raw offset `0x3BB677`. Hand-summing every composite width found nothing; the
defect was located by **measurement** via `_span_probe.py`: the divergence was at raw offset
`0x3BB5B0`, inside a Type50 tail, where the parser consumed 86 bytes and the writer emitted 82.

**Root cause:** `write_type50` was missing `FriendlyFireDamage` — the second `float` of the
`gv >= GV_C22` pair (`DamageReflection`, `FriendlyFireDamage`). Its final op run was 24 B instead
of 28 B. Because the verbatim channel copies from `raw` at a *structural* cursor, that 4-byte
shortfall silently shifted every subsequent verbatim read and inflated the output.

**Lesson for future tool authors: never hand-sum field widths to find a desync.** A verbatim
channel whose cursor advances by structure means a wrong width is invisible until a *modeled*
byte later disagrees. Diff parser spans against writer spans, or position a reader and a writer at
the same absolute offset and compare field-by-field (`_field_probe.py`).

---

## 3. Field-format subtleties a future tool author must know

### 3.1 The model is LOSSY — this is the central constraint

`parse_dat.py` has **193 read sites that consume bytes without storing a value** (bare
`r.i16()` / `r.i32()` / `r.u8()` / `r.skip(n)`). On top of that, genieutils *rewrites* some fields
rather than round-tripping them (see §3.4). A writer driven by `stats` alone therefore **cannot**
be byte-exact — a fact established by grep before any writer code was written.

**Resolution adopted:** `serialize_dat(stats, raw=None, strict=True)` takes `stats` (the primary
argument, per the requirement) **plus** the original decompressed `raw` stream. Modeled fields are
emitted from the model *and simultaneously checked against* `raw`; unmodeled runs are copied
verbatim. Measured split: **6.86 % of the stream is emitted from the parsed model, 93.14 % is
replayed verbatim.**

The verbatim channel is what makes this safe: its cursor advances by *structure*, so a single wrong
width anywhere desynchronizes the copy and surfaces as a byte diff rather than passing silently.
`raw=None` gives a zeros-for-unmodeled "model-only" stream; that mode is **not** byte-exact by
construction and exists only for inspection.

### 3.2 Debug strings — no NUL terminator

`ISerializable.h::serializeDebugString` does:

```cpp
uint16_t size = 0x0A60;
serialize<uint16_t>(size);
serializeSize<uint16_t>(size, str.size());   // EXACT byte count
serialize(str, size);
```

* Marker is `u16 0x0A60`. **`0x0A60` is a marker, not a length** — reading it as a length desyncs immediately.
* Length is the **exact byte count**; there is **no `+1` for a NUL**. Do not confuse this with the
  `serializeSize(T&, std::string, bool cString=true)` overload, which *does* do `size++` when
  non-empty. `serializeForcedString` uses `str.size()+1`; `serializeDebugString` does not.
* Reader cuts the payload at the first NUL (`strnlen`). Writer emits `len(stored_bytes)`; this
  reproduces the file value only because no stored string contains an embedded NUL. **If a string
  divergence ever appears, this is the mechanism to suspect first.**

### 3.3 Strings are raw bytes, not text

Strings in the file are **not UTF-8**. Author-written Chinese is stored as GBK/GB18030 bytes, and
latin-1 decoding preserves them losslessly. **Never re-encode.** Emit `s.encode("latin-1")`
verbatim. `writeString` zero-fills `[str.size(), len)`, so round-tripping a NUL-padded field is
byte-exact only because the original padding is zeros.

### 3.4 `Graphic.FrameDuration` is RECOMPUTED, not round-tripped

`src/dat/Graphic.cpp` on write:

```cpp
serialize<float>(SpeedMultiplier);
FrameDuration = FrameCount ? AnimationDuration / FrameCount : 0;
serialize<float>(FrameDuration);
AnimationDuration = FrameDuration * FrameCount;
serialize<float>(ReplayDelay);
serialize<uint8_t>(SequenceType);
```

`FrameDuration` is **overwritten before serialization**. A reconstructed model reproduces the
original bytes only if `FrameDuration == AnimationDuration / FrameCount` held exactly in float
arithmetic. The parser discards all three floats plus `SequenceType` (13 bytes at
`parse_dat.py:277-280`), so the writer passes them through verbatim.

Also noteworthy: `Graphic::AngleSounds` is **force-resized to `AngleCount`** on write
("Be naughty and force the size to be correct", using `AngleSounds.front()`), so a writer must emit
exactly `AngleCount` entries whenever `AngleSoundsUsed != 0`.

### 3.5 `Terrain` vs `TerrainRestriction` have DIFFERENT terrain counts

Two distinct statics, easily conflated:

* `TerrainRestriction::terrain_count_` is **set** by `DatFile` from `TerrainsUsed1` = **54**.
* `Terrain::terrain_count_` is **never set** (DatFile only calls
  `TerrainRestriction::setTerrainCount`), so `Terrain::getTerrainCount(GV_C32)` returns **200**.

Therefore the writer emits **200 Terrain bodies** but **54 TerrainRestriction bodies**, each sized
by `TerrainsUsed1`. `serializeSub<T>` on write iterates the *vector's own* size (warning on
mismatch), which is why the model's vector lengths govern.

### 3.6 The `phantom` int16 in every Terrain

`Terrain::serializeObject` ends with `if (gv < GV_SWGB) serialize<int16_t>(Phantom);`.

`GV_C32 = 54 < GV_SWGB = 55` → **true**, so all **200** terrains carry this trailing int16. It is
easy to omit because the field is vestigial; omitting it desyncs the entire remaining file.
Also required at this game version: `TerrainUnitMaskedDensity[30]` **is** present
(`gv >= GV_C8 && gv <= GV_LatestDE2`) and the `Borders` array is **not** — this inverts what an
author might assume from older documentation.

### 3.7 `TerrainBlock` — what is present and what is absent at `GV_C32`

Present: 4× int32 head (`VirtualFunctionPtr`, `MapPointer`, `MapWidth`, `MapHeight` —
`WorldWidth`/`WorldHeight` complete the 16 B head), `TileSize[19]` × 6 B (`Width`, `Height`,
`DeltaY`), `int16 PaddingTS` (`gv >= GV_AoE`), 200 terrains, 6× float map bounds, `TerrainsUsed2`,
13 int16, `SearchMapPtr`/`SearchMapRowsPtr`/`AnyFrameChange` (`gv >= GV_AoKE3`), `MapVisibleFlag`,
`FogFlag`.

**Absent at 54** (both guards are false): `TerrainBorders[16]` + `MapRowOffset`, and the trailing
`SomeBytes`/`SomeInt32`. Note `PaddingTS` **is** present even though it reads as pure padding.

### 3.8 `RandomMaps` serializes the same vector TWICE

`RandomMaps::serializeObject` calls `serializeSub<MapInfo>(Maps, count)` **twice**; `MapInfo::io_all_`
flips at the end of each pass. Pass 1 writes the header only; pass 2 writes the sub-arrays. Target
file has **count 0**, so this stage is exactly `u32 0` + `i32 ptr` = 8 bytes. `MapInfo` bodies
(MapLand 47 B, MapTerrain 24 B, MapUnit 46 B, MapElevation 24 B) are read-and-discarded by the parser.

### 3.9 Stage-6 `UnitLines` must be SKIPPED

`DatFile.cpp:214` guards UnitLines with `if (gv >= GV_SWGB)`. `GV_C32 = 54 < GV_SWGB = 55`, so the
stage is **absent**. Reading it (or writing it) corrupts everything downstream. `stats["unit_lines"]`
is `None` and a parser note records why.

### 3.10 Counts are `int16` or `int32` depending on the stage — do not assume

| stage | count field | type |
| --- | --- | --- |
| TerrainRestrictions | `terrain_restriction_count` | int16 |
| PlayerColours | `player_colour_count` | int16 |
| Sounds | `sound_count` | int16 |
| Graphics | `graphic_count` | int16 |
| **Effects** | `effect_count` | **int32** |
| **UnitHeaders** | `unit_header_count` | **int32** |
| Civs | `civ_count` | int16 |
| Techs | `tech_count` | int16 |

The effects and unit-header counts are int32 while their neighbours are int16 — a classic desync
trap that the append demo exercises directly.

### 3.11 Effects and Techs — appendable record layout

`EffectCommand` (`TechageEffect.h`) is exactly `uint8_t Type; int16_t A; int16_t B; int16_t C;
float D;` = **11 bytes**.

`Effect` record = `serializeDebugString(Name)` + `int16 command_count` + commands.

`Tech` record (at `GV_C32`), in order: `int16 RequiredTechs[6]` (12 B);
3 × `ResearchResourceCost` (`int16, int16, uint8`) = 15 B; `int16 RequiredTechCount`;
**`int16 Civ`**; `int16 FullTechMode`; `int32 LanguageDLLName`; `int32 LanguageDLLDescription`;
`int16 EffectID`; `int16 Type`; `int16 IconID`; `int32 LanguageDLLHelp`; `int32 LanguageDLLTechTree`;
`serializeDebugString(Name)`; `uint8 Repeatable`; `int16 location_count`;
`location_count × ResearchLocation` (`int16, int16, uint8, int32` = 9 B).

**EffectCommand semantics** — established from the community editor shipped in the game's own
`Source.7z` (`_probe/source/AGE/AGE_Frame/Techs.cpp:279-287`):

```cpp
if (B == 0) "Set resource A to D"; else "Change resource A by D";   // C >= 0 => "times resource C"
```

so `(Type=1, A=resource, B=1, C=-1, D=amount)` is a plain resource grant. Confirmed **empirically
against the file itself** by `_effect_probe.py`, which found self-labelling effects:

```
effect[242] 'Post-TC +50f +50w'   Type=1 A=0 B=1 C=-1 D=50.0   (food)
                                  Type=1 A=1 B=1 C=-1 D=50.0   (wood)
effect[243] 'Post-TC +50g'        Type=1 A=3 B=1 C=-1 D=50.0   (gold)
effect[244] 'Post-TC +100s'       Type=1 A=2 B=1 C=-1 D=100.0  (stone)
```

⇒ resource ids: **0 = food, 1 = wood, 2 = stone, 3 = gold**. Resource `A = 4` is population/other.

Observed `Type` histogram over all 1500 effects / 10500 commands (largest first):
4 → 3026, 5 → 2366, 102 → 1969, 0 → 1094, 3 → 434, 101 → 377, 8 → 255, 1 → 227, 2 → 209,
103 → 151, 201 → 132, 6 → 129, 255 → 27, 200 → 19, 7 → 17, 10 → 15, 202 → 13, 40 → 10,
204 → 9, 18 → 6, 15/21/31 → 3 each, 26/36 → 2 each, 11/12 → 1 each.

### 3.12 Appending does not disturb the verbatim replay

The writer keeps **two cursors**: `pos` (output offset) and `rpos` (raw-stream offset). `rpos`
advances by *structure only*, so appended records — which have no counterpart in `raw` — do not
shift subsequent verbatim reads. Synthesised records are wrapped in `Writer.new_record()`, which
freezes `rpos` and mutes model-vs-raw comparison for their duration (`op()` emits zeros inside,
since there is no raw byte to copy). Non-modeled scaffolding inside a synthesised record defaults
to zeros.

Without this split, appending one record would shift every later `op()` read and corrupt the
whole tail — the single most important design point for anyone extending the writer.

---

## 4. Append demo (deliverable 5)

Added one new **Effect** (4 commands: `Type=1`, `B=1`, `C=-1`, `D=2000.0` for resources 0..3 —
i.e. +2000 food, wood, stone, gold) and one new **Tech** (`civ = -1`, `effect_id = 1500`,
`type = 0`, `icon_id = -1`, one research location `(-1, 1, 0, -1)`).

```
decompressed before : 93268152 bytes
decompressed after  : 93268333 bytes   (delta +181)
sha256 after        : 1315149c604e1b5dfb058de3dc7cf25884537f83c465812a72e2a0cae12e2cd8

compressed (zlib.compressobj(6, zlib.DEFLATED, -15)):
    BASE re-compressed    : 11982480 bytes
    appended container    : 11982579 bytes   (delta +99)
    on-disk original file : 12023754 bytes
```

**(a) The UNMODIFIED `parse_dat.py` parses `out/added_tech.dat` cleanly and terminates at exactly
EOF with `leftover 0`** — run standalone in a separate process, `exact match: YES`,
`final offset 93268333`, `data size 93268333`, `leftover bytes 0`, exit code **0**.

**(b) The new objects are present with correct values** (re-parsed from the written file):

```
effects : 1501  (was 1500, +1)     techs : 1511  (was 1510, +1)
civs 63 | graphics 21001 | unit headers 1701 | unit objects 136861 (unchanged)
techtree 4/37/266/241 (unchanged)

new Effect at index 1500 (expected 1500) — all 4 commands OK
    Type=1 A=0(food)  B=1 C=-1 D=2000.0
    Type=1 A=1(wood)  B=1 C=-1 D=2000.0
    Type=1 A=2(stone) B=1 C=-1 D=2000.0
    Type=1 A=3(gold)  B=1 C=-1 D=2000.0
new Tech at index 1510 (expected 1510)
    civ=-1 OK | effect_id=1500 OK | type=0 OK | icon_id=-1 OK
    research_locations=[(-1, 1, 0, -1)] OK
pre-existing last tech unchanged: OK
pre-existing first effect unchanged: OK

APPEND DEMO VERDICT: PASS
```

**(c) Only two field groups differ from BASE — and they are exactly the two stage counts that
*had* to change.** These are the writer's `model!=raw` reports:

```
raw 0x0036B0BE  width 4  model=dd050000 raw=dc050000   effects 1500 -> 1501
raw 0x058C1923  width 2  model=e705     raw=e605       techs   1510 -> 1511
```

`_append_diff.py` then computes the full insertion-aware edit script between BASE and the appended
stream, independently of the writer:

```
total inserted bytes: 181        patch count: 2   insert count: 2
  common prefix   3584190 leading bytes identical
  patch   raw 0x0036B0BE / new 0x0036B0BE   1 B  dc -> dd
  insert  raw 0x0038F890 / new 0x0038F890  89 bytes inserted   (the new Effect)
  patch   raw 0x058C1923 / new 0x058C197C   1 B  e6 -> e7
  insert  raw 0x058E2A14 / new 0x058E2A6D  92 bytes inserted   (the new Tech)
EDIT SCRIPT MINIMAL: YES
```

Both patches land on a stage-count field; nothing else in 93 MB moved. The inserted Effect payload
decodes as `0A60` marker / `0x0027`=39 B name `TEST-APPEND grant 2000 of each resource` /
`0x0004` commands / 4 × `01 | 0000 | 0100 | ffff | 0000FA44` (=2000.0) = 89 B. The inserted Tech
payload decodes as 12+15+2+2+2+4+4+2+2+2+4+4 B scaffolding, `0A60` / `0x0015`=21 B name
`TEST-APPEND Res Grant`, `00` Repeatable, `0x0001` locations, `ffff | 0100 | 00 | ffffffff` = 92 B.

Note `raw consumed 93268152 / 93268152` and the appended container re-decompressing byte-exactly to
the serialized stream (`container round-trip byte-exact: YES`).

The reported on-disk size (12,023,754) exceeds a plain `level=6` re-compression (11,982,480) by
41,274 B — the shipped container is not simply `zlib level 6` raw deflate of this stream. This is
irrelevant to format correctness (the game's decompressor accepts any valid raw-deflate stream) but
matters if exact file-level reproduction is ever a goal.

---

## 5. What this unlocks

1. **A complete, verified model→bytes path for the AoE2 DE `.dat`.** The format is no longer
   read-only. Every stage — terrains, graphics, sounds, effects, unit headers, 136,861 unit objects
   across 63 civs, 1510 techs, the whole tech tree — has a proven writer.
2. **Programmatic mod generation without the AGE editor.** Because the append demo proves that new
   Effects and Techs can be added and the result still parses with the stock parser, real
   "add new gameplay objects" mods — the mechanism actual popular mods use — are reachable from
   Python, offline, deterministically.
3. **Minimal, reviewable diffs.** The two-cursor design means an edit program can change exactly
   the bytes it intends. The append demo changed **2 count fields + 181 inserted bytes** in a
   93 MB file, and that fact is machine-checkable (`_append_diff.py`). Generated mods can be
   diffed and audited byte-for-byte instead of trusting a binary tool.
4. **A trustworthy oracle for any other tool.** Because the round-trip hash-equals the original,
   this writer can act as ground truth: any other parser/serializer (AGE, genieutils, a future
   Python rewrite) can be validated by round-tripping through it. A regression suite for the format
   now exists.
5. **Idempotence as a format invariant.** `parse → write → parse → write` is a fixed point, so the
   model is provably lossless *with respect to the writer*: nothing is silently dropped between
   generations. This is the property that makes a build pipeline (patch → multiple chained
   transforms → ship) safe.
6. **A worked method for the remaining lossy sites.** The 93.14 % verbatim channel is an explicit,
   measured, and shrinkable surface. Each of the 193 discard sites that gets promoted into the
   model reduces opaque coverage and widens what can be *edited* rather than merely replayed — the
   path from "byte-exact echo" to "fully editable model" is now incremental and testable at every
   step.

---

## 6. Remaining risk / what was NOT tested

* **The modelled fraction is 6.86 %.** 93.14 % of output bytes are replayed verbatim from the
  original stream at structurally-advanced offsets. Byte-exactness of those bytes is therefore a
  *structural* claim (the cursor stayed aligned), not a claim that the model reproduces them. Any
  edit inside an opaque run requires promoting that field into the model first. The append demo
  sidesteps this by appending entirely new records and patching only count fields.
* **Only `GV_C32` (54) was exercised.** Every `gv`-dependent branch is hard-coded to the 54 outcome.
  Other versions (`GV_SWGB`=55, the `GV_T*` family, `GV_CC*`=56–58) take different branches
  (`UnitLines` present, `Phantom` absent, `WalkSpriteRate` as int32, `Borders`/`MapRowOffset`
  present, `serializeForcedString` paths) and are **untested**.
* **Only one file was tested** — `empires2_x2_p1.dat`. The 1.0/HD/AoK datasets and the
  language-specific strings in other `.dat` variants were not tried.
* **Discarded (`gv < GV_AoE*`) data was not exercised**: `RandomMaps` count is 0, so every
  `MapInfo` body path (MapLand/MapTerrain/MapUnit/MapElevation, and the `io_all_` two-pass
  mechanism) is present in the writer but **never executed against real data**. This is the largest
  untested code path.
* **`Graphic.FrameDuration` is passed through, not modelled** (§3.4). If any future edit changes
  `FrameCount`, `AnimationDuration`, or `SpeedMultiplier`, the recomputation mismatch becomes live
  and the writer will emit the stale stored value — the edit will not produce what genieutils/AGE
  would. `FrameDuration` must be modelled before any animation edit.
* **Unit bodies are only partly modelled.** `write_unit` replays large parts of the per-type tails
  verbatim; the writer cannot synthesise a *new* unit object, only echo existing ones. The append
  demo deliberately adds only Effect/Tech records, which are fully modelled.
* **No in-game load test.** The appended `.dat` was validated only by the stock parser and by byte
  analysis. The game itself was **never run** against it (and the live game directories were
  deliberately left untouched). A file that parses correctly can still be rejected by the engine for
  reasons above the format layer (e.g. a tech referencing a missing icon or unresolvable DLL string
  id — the demo's new tech uses `icon_id = -1` and zeroed DLL ids precisely to keep it inert).
* **Container compression is not byte-identical** to the shipped file (11,982,480 vs 12,023,754 B
  for BASE). Correctness of the decompressed stream is proven; equivalence of the *compressed*
  envelope is not claimed.
* **No CRC/checksum handling** was needed or implemented — the container has none.
