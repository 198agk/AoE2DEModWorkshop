# In-place byte patching of `empires2_x2_p1.dat` — decisive experiment

**Verdict: in-place byte patching is VIABLE.** Same-width field edits at parser-derived offsets
survive reparse byte-exactly, leave the file geometry untouched, and change only the intended
bytes. The mechanism is sound. Caveats in §7.

- Target: `D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat`
- Version string: `VER 8.9`
- Compressed: 12,023,754 B · Decompressed: 93,268,152 B · raw DEFLATE (`window_bits=-15`)
- Instrumentation (new file, existing parser untouched): `_probe\datparse\patch_probe.py`
- Machine-readable results: `_probe\datparse\patch_results.json`, `_probe\datparse\patch_offsets.json`
- The **game original was never written to.** All outputs are new files in `_probe\datparse\`.

---

## 1. Offset table

### 1a. Top-level count fields

| Field | Type | Offset (dec) | Offset (hex) | Value |
|---|---|---|---|---|
| `numEffects` | int32 | 3,584,190 | `0x0036B0BE` | 1500 |
| `numCivs` | int16 | 3,899,440 | `0x003B8030` | 63 |
| `numTechs` | int16 | 93,067,555 | `0x058C1923` | 1510 |

### 1b. `Unit` field layout (relative to the start of the unit object)

| Field | Type | Delta from unit start |
|---|---|---|
| `Type` | uint8 | +0 |
| `ID` | int16 | +1 |
| `HitPoints` | int16 | +22 |

### 1c. `Tech` field layout (Fletching, index 199 — the tech actually patched)

| Field | Type | Absolute offset | Value |
|---|---|---|---|
| tech start | — | 93,085,014 | — |
| `Civ` | int16 | 93,085,043 | −1 (all civs) |
| `EffectID` | int16 | 93,085,055 | 192 |
| `IconID` | int16 | 93,085,059 | 34 → **0** |

### 1d. Villager (id 83) in civ 0 "Gaia"

| Field | Absolute offset |
|---|---|
| unit start | 3,967,288 |
| `HitPoints` | 3,967,310 (`0x3C894E`), value 25 |

### 1e. Offset-table proof of correctness

The recording parser's offsets were validated by **re-reading the raw bytes at every recorded
offset** and comparing to the parser's decoded values, independently of the parser:

```
offset-table proof : 136861/136861 unit objects re-read from raw bytes match (mismatches: 0)
offset-table proof : 1510/1510 tech objects (Civ/EffectID/IconID) re-read from raw bytes match (mismatches: 0)
```

136,861 = every unit object in all 63 civs. Zero mismatches.

---

## 2. The exact patch applied

Three output files were produced, each a full recompression of a patched copy of the
**original decompressed bytes**:

| Output file | Patch |
|---|---|
| `out_patched_techonly.dat` | Fletching `IconID` 34 → 0 (a valid icon id used by 114 other techs) |
| `out_patched_civ0.dat` | above **+** Villager id 83 `HitPoints` 25 → 99 in **civ 0 "Gaia" only** |
| `out_patched_allcivs.dat` | above **+** Villager id 83 `HitPoints` 25 → 99 in **all 63 civs** |

Written as `value.to_bytes(2, "little", signed=True)` — same width as the field, so no byte
is ever inserted or removed.

Recompression: `zlib.compressobj(level=6, zlib.DEFLATED, -15)`.

---

## 3. Verification results

### 3a. Byte-exact reparse with the UNMODIFIED verified parser

All three files were re-parsed by `parse_dat.py` **unmodified**:

| File | raw size | bytes consumed | leftover | byte-exact |
|---|---|---|---|---|
| `out_patched_civ0.dat` | 93,268,152 | 93,268,152 | 0 | **True** |
| `out_patched_allcivs.dat` | 93,268,152 | 93,268,152 | 0 | **True** |
| `out_patched_techonly.dat` | 93,268,152 | 93,268,152 | 0 | **True** |

This is the decisive structural result: the patched files parse to **exactly** the same byte
count with **zero** leftover. The file geometry is provably unchanged — every subsequent
field in the file is still found at the same offset.

### 3b. Patch took effect / did not leak

```
out_patched_civ0.dat      villager(id 83): patched civs=1,  hp values=[99]
                          sampled non-patched civs villager hp: [25]
out_patched_allcivs.dat   villager(id 83): patched civs=63, hp values=[99]
                          sampled non-patched civs villager hp: []   (none left)
out_patched_techonly.dat  sampled non-patched civs villager hp: [25]
                          (all three) tech icon after patch: [(199, 'Fletching', 0)]
```

The `civ0` file has exactly **one** civ at hp 99 and the other 62 still at 25. The `allcivs`
file has all 63 at 99. Per-civ copies are genuinely independent memory (§6).

### 3c. Semantic validator (`validate_semantics.py`, unmodified, monkeypatched `DAT`)

| File | exit code | result |
|---|---|---|
| original | 0 | 11/11 ground truth OK |
| `out_patched_techonly.dat` | **0** | all checks PASS |
| `out_patched_civ0.dat` | 1 | 10/11 ground truth (Villager 99 ≠ expected 25) |
| `out_patched_allcivs.dat` | 1 | 10/11 ground truth (Villager 99 ≠ expected 25) |

The exit-1 files fail on **exactly one** check — the external ground-truth table's hard-coded
`83: ("Villager", 25)`. Every structural check still passes:

```
PASS  parser consumed the file EXACTLY: leftover 0
PASS  all 7 distinct unit Type values (10,20,25,30,60,70,80) are legal UnitType enum members
PASS  unit ids unique within all 63 civs
PASS  unit counts per civ are consistent: {2693: 1, 2164: 62}
PASS  all 1510 tech EffectIDs are -1 or a valid index into the 1500 Effects
PASS  all tech Civ values are -1 or a valid index into the 63 civs
PASS  the only negative graphic SLP is the -1 'no sprite' sentinel (5000)
PASS  all 5733 empty-name units are Type=10 (EyeCandy slots), hp=1
PASS  all 136861 unit name strings are clean ASCII
FAIL  only 10/11 canonical unit ids match their known hit points
```

This failure is **by design** and is itself independent confirmation the patch landed and is
visible to a reader that knows nothing about our offset table. The tech-only patch (which
changes nothing in the ground-truth table) exits **0**, proving the validator is not simply
rejecting anything modified.

---

## 4. Diff quantification — the surgical-patching proof

Byte-diff of patched-decompressed vs original-decompressed:

| File | differing bytes | differing regions | surgical |
|---|---|---|---|
| `out_patched_techonly.dat` | 1 | 1 | **True** |
| `out_patched_civ0.dat` | 2 | 2 | **True** |
| `out_patched_allcivs.dat` | 64 | 64 | **True** |

`surgical` here means: **every** differing region lies entirely inside exactly one intended
2-byte field, and **no** intended field was left untouched (silent fields = 0). There are zero
unexpected regions and zero missing regions in all three files.

Note on region width: a diff region is emitted only where a byte *value* actually changes.
`25 → 99` is `0x0019 → 0x0063`; the high byte is `0x00` in both, so only **1** byte per field
changes, not 2. That is why `civ0` shows 2 changed bytes (one hp byte at 3,967,310 and one
icon byte at 93,085,059) across 2 one-byte regions rather than 2 two-byte fields. The
containment test is the correct criterion; an earlier naive "region == field" equality test
reported these as non-surgical, which was a bug in the test, not in the patch.

Result: **a multi-byte edit deep inside a 93 MB file changed exactly the bytes intended and
nothing else.** No reformatting, no shifting, no collateral damage to any neighbouring field.

---

## 5. Compressed sizes

| File | compressed size | Δ vs original |
|---|---|---|
| **original** | **12,023,754** | — |
| control: unmodified recompress (level 6) | 11,982,480 | −41,274 |
| `out_patched_techonly.dat` | 11,982,478 | −41,276 |
| `out_patched_civ0.dat` | 11,982,485 | −41,269 |
| `out_patched_allcivs.dat` | 11,983,127 | −40,627 |

Two facts matter here:

1. **Recompression does not reproduce the original bytes**, and the output is ~0.34 % *smaller*
   (different deflate implementation/tuning). This is expected and harmless — the game reads
   the *decompressed* bytes, and both the official AGE editor and genieutils write a plain
   recompressed stream.
2. **The patch's own cost is tiny and monotonic**: +647 bytes for the 63-civ villager edit
   (vs the civ0-only file), −2 bytes for the single tech icon. A real mod changing one field
   across all civs costs well under 1 KB compressed. The 0.34 % shrink is a recompression
   artefact, not a data loss — verified by §3a (byte-exact reparse) and §4 (only 64 bytes differ).

---

## 6. Auxiliary findings

### 6a. Per-civ unit copies are INDEPENDENT — confirmed

- Villager id 83 appears **exactly 63 times**, once per civ (`villager_copies_per_civ = {1}`,
  `villager_total_copies = 63`, `civs_with_villager = 63`).
- Pre-patch hp histogram across all 63 copies: `{25: 63}` — uniform, but stored per civ.
- Patching civ 0's copy left the other 62 at hp 25 (§3b). **They are separate bytes.**

**UX consequence (important):** a modder editing "the Archer" must apply the change **63 times**,
once per civ, unless the tool deliberately writes all copies at once. The `allcivs` variant
exists precisely because the single-copy edit is invisible to 62 of the 63 civs. A production
tool should default to "all civs" and treat per-civ editing as an advanced option.

Not all units are shared, though: there are **2693 distinct unit ids**, of which **2164 appear in
all 63 civs**; civ 0 "Gaia" carries **2693** units while every other civ carries **2164**
(529 Gaia-only decoration/eyecandy units). So "id 83 exists in every civ" is not true of every
id — a correct tool must look up per-civ membership rather than assume 63.

### 6b. The 63 / 58 / 62 discrepancy — reconciled

Three different numbers, three different meanings:

- **63 dat civs.** The actual civ records, in file order (with unit counts):
  `Gaia`(2693), then `British, French, Goths, Teutons, Japanese, Chinese, Byzantine, Persians,
  Saracens, Turks, Vikings, Mongols, Celts, Spanish, Aztecs, Mayan, Huns, Koreans, Italians,
  Hindustanis, Incas, Magyars, Slavs, Portuguese, Ethiopians, Malians, Berbers, Khmer, Malay,
  Burmese, Vietnamese, Bulgarians, Tatars, Cumans, Lithuanians, Burgundians, Sicilians, Poles,
  Bohemians, Dravidians, Bengalis, Gurjaras, Romans, Armenians, Georgians, Achaemenids,
  Athenians, Spartans, Shu, Wu, Wei, Jurchens, Khitans, Macedonians, Thracians, Puru, Muisca,
  Mapuche, Tupi, Saxons, Varangians, Danes` (all 2164 units each).
- **62 files in `CivTechTrees\`** = the 63 dat civs **minus Gaia** (the non-playable nature/gaia
  civ has no tech tree). Cross-check: dat civs with no tech-tree file = `Gaia`, plus two pure
  spelling mismatches — dat `Magyars` vs file `MAGYAR.json`, dat `Hindustanis` vs file
  `INDIANS.json`.
- **58 keys in `futuravailableunits.json`** = the 62 playable civs **minus the 6 newest civs not
  yet in that file**, **plus** two non-civ/legacy keys: `Gaia` and `FullTechCiv`.
  Arithmetic: 62 − 6 (`Achaemenids, Athenians, Spartans, Macedonians, Thracians, Puru`) + 2
  (`Gaia`, `FullTechCiv`) = **58**. ✓

**Name-alias table** (file key → dat civ), which any tool must normalise:

| dat civ `Name` | `futuravailableunits.json` / `CivTechTrees` spelling |
|---|---|
| British | Britons |
| French | Franks |
| Byzantine | Byzantines |
| Mayan | Mayans |
| Hindustanis | Indians |
| Magyars | Magyar |
| Gaia | *(fav only; no tech tree)* |
| — | FullTechCiv *(fav only; not a dat civ)* |

Keys present in the json but with no corresponding dat civ:
`Britons, Byzantines, Franks, FullTechCiv, Indians, Mayans` (aliases plus the pseudo-civ).
After applying the alias table, dat civs still absent from the json (newest DLC):
`Hindustanis, Achaemenids, Athenians, Spartans, Macedonians, Thracians, Puru`.

**Practical rule:** do not use either JSON file as the civ roster. `numCivs` in the dat is
authoritative (63); the JSON is a partial, aliased, lagging view and also carries a pseudo-civ.

### 6c. How many civs share an identical unit stat block?

Hashing the full `(type, id, hit_points)` tuple stream per civ:

- **62 of 63 civs are byte-identical**: `b07fdd0136fce6f9` (British … Danes, i.e. every
  playable civ).
- **1 civ is unique**: civ 0 `Gaia` = `ee8a4122df26cc5a` (it has the 529 extra eyecandy units).

So at the dat level, **every playable civ stores the exact same base unit stat block**; civ
differences live in the Tech/Effect data, not in the per-civ unit records. Two consequences:

1. A tool that edits a unit's base stats for "all civs" is really applying the **same edit 63
   times to 62 identical blocks plus Gaia** — the repetition is structural, not semantic.
2. Because 62 blocks are identical, "does this edit affect all civs?" can be answered cheaply:
   hash each civ block, and treat all civs in a hash group identically.

This also means a smarter tool could detect the common case and write to the 62 identical
blocks (or 62 + Gaia) with one logical operation, while still emitting 63 physical writes.

---

## 7. Verdict and caveats

### Verdict

**In-place byte patching is a viable product mechanism.** The evidence:

- Offsets derived by the verified parser are **provably correct** (136,861/136,861 units and
  1,510/1,510 techs re-read from raw bytes with 0 mismatches).
- Same-width edits leave the file **structurally identical**: all three patched files reparse
  to exactly 93,268,152 bytes with leftover 0 under the unmodified parser.
- The edits are **surgical**: 1, 2 and 64 changed bytes respectively, all confined to the
  intended fields, with no unexpected regions.
- A patch is **independently observable**: the unmodified semantic validator, which knows
  nothing of the offset table, reports the Villager at 99 in the patched files and 25 in the
  tech-only file.
- The compressed write is **normal**: level-6 raw deflate, ~0.34 % smaller than the original,
  same as what AGE/genieutils produce.

Because no field changes width, we avoid every risk of a full re-serializer: no length
recomputation, no offset drift, no cascading offset fix-ups.

### Caveats

1. **Version-specific offsets.** The entire offset table is derived from `VER 8.9`. Any game
   patch can shift every offset downstream of a changed section. A product must **re-derive the
   offset table per dat version** and refuse to patch on an unrecognised version rather than
   guess.
2. **Width discipline is mandatory.** Field writes must be exactly the field's width and must
   bounds-check (e.g. `HitPoints` is int16; 99 is fine, 40000 would overflow into the next
   field and silently corrupt the file). A naive `struct.pack` without range checks is a
   corruption vector.
3. **Geometry changes are out of scope.** This mechanism can only edit fields in place. Adding
   or removing units, civs, graphics or techs changes lengths and shifts every following
   offset — that still requires a full re-serializer and is not covered by this result.
4. **Not validated in-game.** This experiment proves the *file* is valid and the parser reads
   it back correctly. It does **not** prove the running game accepts the patched file — no
   AoE2DE launch was performed. Caveat emptor until an in-game smoke test is done.
5. **Multiplayer / integrity concerns.** Modifying the game's own dat can be treated as
   cheating in ranked multiplayer, and Steam "verify integrity of game files" or a game update
   will silently restore the original. A product should write to a **mod path**, not
   `resources\_common\dat\`, and should never overwrite the original (this experiment did not).
6. **Per-civ repetition is real work.** Editing one logical unit means 63 physical writes
   (§6a). Any tool that forgets this ships a mod that changes nothing for 62 of 63 civs.
7. **The validator's ground-truth table is a fixture, not an oracle.** It fails on any
   intentional stat change to a canonical unit (expected here). A product needs a validator
   that distinguishes "deliberately changed" from "corrupt", e.g. by diffing against the
   pre-patch baseline rather than hard-coded retail values.
8. **Civ roster is not in the JSON files.** Use `numCivs` from the dat (§6b); the JSONs are
   aliased, incomplete and include a pseudo-civ.

---

## 8. Artifact index

Scripts (all in `_probe\datparse\`):
- `patch_probe.py` — the recording parser + patcher + verifier. Imports `parse_dat.py`;
  monkeypatches `read_civ`/`read_tech` to record offsets and subclasses `P.Parser` as
  `RecordingParser`. Does **not** modify `parse_dat.py` or `validate_semantics.py`.
- `patch_probe_stdout.txt` — full console capture.
- `patch_results.json` — all counts, offsets, diffs, verification, validator results.
- `patch_offsets.json` — the offset table alone.

Output dat files (never write these over the original):
- `out_patched_techonly.dat` — 11,982,478 B
- `out_patched_civ0.dat` — 11,982,485 B
- `out_patched_allcivs.dat` — 11,983,127 B

Unmodified reference artifacts: `parse_dat.py`, `validate_semantics.py`, `REPORT.md`.
