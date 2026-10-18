# Independent verification — `aoe2mod` (AoE2 DE data/sprite toolkit)

Auditor: `kernel-verifier`. Everything below was derived from the game install
(`D:\Games\Steam\steamapps\common\AoE2DE`) and the product's public API.
No file outside `_probe/team/kernel-verifier/` was written. No other auditor's
report or script was read or reused; every helper here is my own (stdlib
`zlib`/`struct`/`hashlib`/`json` only — the claim-2 script never imports the
product's parser).

Game data file: `resources\_common\dat\empires2_x2_p1.dat`,
12,023,754 B on disk, raw-deflate (`wbits=-15`), 93,268,152 B inflated.

Scripts, in order:
`s1_roundtrip.py` · `scratch/archer_atk_plus2/` + `s2_final.py` + `s2_census.py` ·
`s3_recon.py` · `s3_compare.py` · `s3_table.py` · `s3_detail.py` ·
`s4_badinput.py` · `s4b_followup.py` · `s4c_avail_dat.py` · `s4d_inflate_cmp.py` ·
`s5_honest.py` · `s6_final.py` · `s7_desc_vs_build.py` · `s8_gaps.py` ·
`s9_loose_ends.py` · `s10_noop_contract.py` · `s11_recheck.py`.

### Provenance note: the tree moved mid-audit

At 2026-10-18 11:19, while I was probing, `aoe2mod/dat/writer.py` and
`aoe2mod/dat/locate.py` changed on disk (`git status`: both `M`;
`locate.py` lost a 131-line demo `main()`). Claims 1–2 were measured before that.
I therefore **re-ran both against the current tree** with `s11_recheck.py`:

* claim 1 re-run: output 93,268,152 B, sha256 still
  `02a09b48…405df`, first differing offset **(none)** — unchanged.
* claim 2 re-run: 126 changed bytes, length delta 0, 63 pairs at a constant
  78 B gap, the single pattern `(4,6,4,6)`, ±200 window violations 0, debug
  markers 208,507 / 208,507 — unchanged. (The re-check reports last offset
  91,670,602 rather than 91,670,524: the earlier figure was the *primary* of the
  last pair, this one is the *mirror*; the 78 B gap reconciles them exactly.)

`aoe2mod/api.py`, `aoe2mod/intent/compiler.py` and `aoe2mod/mod/emitter.py` —
the files every defect below cites — were **not** modified (mtime 2026-10-17
23:44, clean in `git status`). No line I cite moved after I read it.

---

## VERDICT: PARTLY CONFIRMED

Byte-exact round-trip and surgical edits are real and hold to the byte; but the
"honest boundary" is present only on three of the four build strategies (the
core `.dat` patcher ships no `proven`/`not_proven` at all), and `plan()` still
promises edits that `build()` then refuses in four measured cases.

---

## 1. Byte-exact round trip — CONFIRMED: 93,268,152 B in, 93,268,152 B out, sha256 identical, no differing offset

`_probe/team/kernel-verifier/s1_roundtrip.py` imports `aoe2mod.dat.parser` and
`aoe2mod.dat.writer` directly (`W.serialize_dat(stats, raw=raw, strict=True)`),
parses the real install once, serialises with **no edits**, compares.

| measurement | value |
|---|---|
| input file bytes | 12,023,754 |
| input file sha256 | `4aa2f0a719e88e5f1502517eddb27c669aeb40c2fe9d8c4f3eec7751c01e7baa` |
| inflated bytes | 93,268,152 |
| inflate stream integrity | `eof=True`, `unused_data=0` bytes |
| inflated sha256 | `02a09b48a0fbd2116295cad2ebdd28dfa20b92b44e29b360f8639e5fb73405df` |
| file version header | `b'VER 8.9\x00'` |
| parse time | 6.16 s |
| parsed counts | `game_version=54`, units=1701, civs=63, techs=1510, graphics=21001, effects=1500 |
| serialize time | 14.24 s |
| **output bytes** | **93,268,152** |
| **sha256 match** | **True** (`out == raw` is `True`) |
| **first differing byte offset** | **(none)** |
| second serialize (idempotence) | `True`, 16.97 s |

Ten-parser-stage geometry the writer reproduced (offsets into the inflated
stream), for the record:

```
1 0x0         – 0x2394E     (145,742)
2 0x2394E     – 0x44DC0     (136,306)
3 0x44DC0     – 0x355E8E    (3,215,566)
4 0x355E8E    – 0x36B0BE    (86,576)
5 0x36B0BE    – 0x38F890    (149,458)
6 UnitLines   SKIPPED
7 0x38F890    – 0x3B8030    (165,792)
8 Civs        0x3B8030 – 0x58C1923 (89,168,115)
9 Techs       0x58C1923 – 0x58E2A14 (135,409)
10            0x58E2A14 – 0x58F28B8 (65,188)
```

Writer report: `model_bytes=6,402,501`, `opaque_bytes=86,865,651`,
`opaque_sites=22,306,938`, `output_bytes=93,268,152`, `raw_consumed=93,268,152`.
93.1 % of the stream is re-emitted from the original bytes rather than
re-modelled; the 6.5 % that is modelled comes back identical, which is the
stronger claim.

*(Correction to my own probe: an early printout claimed `leftover=93,268,152`.
That was my bug — I read a `final_offset` key the writer does not emit. Re-measured
`leftover` is 0.)*

---

## 2. A real edit lands where it says — CONFIRMED: 126 bytes changed, 0 length change, 63/63 civs, 0 violations in ±200 B

Built `{'intent':'unit.stat','unit':'步弓手','stat':'displayed_attack','delta':2}`
with `build()` into `_probe/team/kernel-verifier/scratch/archer_atk_plus2/`
(mod `.dat` 11,982,182 B). That `.dat` was then inflated **by my own stdlib
`zlib.decompressobj(-15)`** and diffed against my own inflation of the install
file. The product's parser is never imported by these scripts.

| measurement | value |
|---|---|
| base inflated | 93,268,152 B |
| emitted inflated | 93,268,152 B |
| length delta | **0** |
| changed bytes | **126** |
| change runs | 126 (every run is 1 byte wide; `widths == [1]`) |
| primary/mirror pairs | 63 / 63, gap between a primary and its mirror **78 B constant** |
| only byte pattern observed | `{(4,6,4,6): 63}` — u16 4 → 6 at the primary **and** the mirror |
| first primary offset | 3,915,460 |
| last primary offset | 91,670,524 |
| file-version header, both sides | `b'VER 8.9\x00'` |
| `b'\x60\x0a'` debug-string markers, base vs mod | 208,507 vs **208,507** (unchanged) |
| marker-shaped strings, base vs mod | 174,363 vs **174,363**, all offsets stable, **0** payloads differ |
| ±200 B neighbourhood violations around each edited offset | **0** |
| §civ attribution: slot indices covered | 0..62, all 63 unique |
| distance from each primary to its unit's `'ARCHR'` debug-string payload | **510 B, for all 63** (misses 0) |

Independent census of the unit's civ copies (a 600-byte fingerprint around the
edit site): 57 exact hits spanning 83.69 MB inside the Civs stage, first
3,915,460 / last 91,670,524, min/median/max spacing
1,413,047 / 1,413,052 / 5,652,211 B. (Civ spacing is irregular, so the "all 63
within a lattice" formulation is wrong and I do not rely on it; the fingerprint
census and the constant 510-byte offset to the unit's own debug string are the
two independent attributions, and both agree.)

The `u16` at `primary-1` moves from 1024 to 1536, i.e. it is *not* the field
start — a naive "offset-1 is the value" reading would have been wrong, which is
exactly why the measurement used the diff, not an assumption.

Structure intact: EOF parses exactly (both my scans reach 93,268,152 with 0
leftover), the ten-stage layout is unchanged, no debug string moved, and no byte
outside the 126 edited offsets differs anywhere in 93 MB.

---

## 3. Preview and build agree — PARTLY: 11/13 cases agree exactly; 2 disagree (both are "plan promises, build refuses")

13 intents, each `plan()` then `build()` into its own directory, then measured
with stdlib zlib only.

| # | intent | plan `edit_count` | build `edit_count` | dat length Δ | changed bytes (mine) | files written | agree? |
|---|---|---|---|---|---|---|---|
| 1 | archer `displayed_attack +2` | 126 | 126 | 0 | 126 | 2 | yes |
| 2 | militia `hit_points +5` | 63 | 63 | 0 | 63 | 2 | yes |
| 3 | archer `movement_speed +0.3` | 63 | 63 | 0 | 189 (3-byte f32) | 2 | yes |
| 4 | archer `cost wood −5` | 63 | 63 | 0 | 63 | 2 | yes |
| 5 | archer `attack_class armour 4 +1` | 126 | 126 | 0 | 126 | 2 | yes |
| 6 | Loom `research_time −1` | 1 | 1 | 0 | 1 | 2 | yes |
| 7 | Loom `effect +5` | 1 | 1 | 0 | 1 | 2 | yes |
| 8 | Loom `cost food −10` (**no food slot**) | 0 | **raises** | — | — | **0** | **NO** |
| 9 | `unit.availability` grant archer→AZTECS (**already has it**) | 2, `editable=False` | **raises** | — | — | **0** | **NO** |
| 10 | `unit.sprite copy` archer←longbow | 20 | 20 | no dat | — | 21 (20 `.sld` + `info.json`), 37,802,283 B | yes |
| 11 | `unit.sprite rename` archer←longbow | 10 | 10 | 0 | (record edits) | 2 | yes |
| 12 | archer `garrison_capacity +1` | 63 | 63 | 0 | 63 | 2 | yes |
| 13 | Loom `research_time` scoped to one civ | 1 | 1 | 0 | 1 | 2 | yes |

Two further availability builds, run to cover the strategy with a *successful*
build and not only a refusal:

* grant 长弓兵 → AZTECS (a real change): plan `edit_count=2, changes_dat=True,
  dat_is_carrier=False`, build `edit_count=2, changes_dat=True` — **agree**, 4
  files (`info.json`, `.dat`, `CivTechTrees/AZTECS.json`,
  `futuravailableunits.json`). But plan's `writes` string names only `.dat` +
  the tree file, so it under-reports the panel file the build actually writes.
* revoke 步弓手 → BRITONS: plan `edit_count=0, changes_dat=False,
  dat_is_carrier=True`, build identical — **agree**, and the `.dat` shipped is
  byte-identical to the base on purpose (carrier, see the emitter's own warning).

Description equality (`plan["description"]` vs `man["resolved"]`): **8/13
identical**. The 3 that differ are wording-granularity, not scope:

| case | `plan()` says | `build()` says |
|---|---|---|
| Loom effect | `织布机 平民 生命值 +5` | `织布机 科技效果 +5` |
| sprite copy | `20 file(s) copied from Longbowman to Archer/Bowman, covering 63 civilization(s)` | `步弓手 改用 长弓兵 的造型` |
| sprite rename | `10 graphics record(s) repointed from Archer / Bowman to Longbowman, covering 63 civilization(s); no .sld file is shipped` | `步弓手 改用 长弓兵 的造型` |

Note case 8 and 9 are refusals, so `man["resolved"]` does not exist: for those
two the *only* disagreement is "plan promised, build refused". That is the
defect class §4 also hits.

---

## 4. Bad input refused readably, and refusals write nothing — PARTLY: 18/24 refused by both entry points (16 with identical text), 4 refused only at build, but 0 files ever left behind by any refusal

24 malformed/impossible/no-op intents. `plan()` and `build()` were both called
for each, into a fresh directory; the directory was then listed.

| # | intent | plan | build | same message | files left |
|---|---|---|---|---|---|
| 1 | unit name `不存在的单位XYZ` | raises `IntentError: no unit matches '不存在的单位XYZ'` | same | yes | 0 |
| 2 | unit id `999999` | raises `no unit matches 999999` | same | yes | 0 |
| 3 | tech name `不存在的科技XYZ` | raises `no tech matches …` | same | yes | 0 |
| 4 | intent `unit.bogus` | raises `unknown intent 'unit.bogus'; known: …` | raises `intent 'unit.bogus' declares compile strategy None, which this build does not implement` | **no** | 0 |
| 5 | missing `unit` field | raises `intent 'unit.stat' needs a 'unit' field` | same | yes | 0 |
| 6 | missing `delta`/`value` | raises `needs a 'delta' or a 'value'` | same | yes | 0 |
| 7 | both `delta` and `value` | raises `give either 'delta' or 'value', not both` | same | yes | 0 |
| 8 | stat `armour` | raises `unknown stat 'armour' … known: …` | same | yes | 0 |
| 9 | `delta=-100000` (overflow) | raises `生命值 would become -99970, which does not fit in the 16-bit signed field (allowed -32768..32767). Reduce the change.` | same | yes | 0 |
| 10 | `value=40000` | raises same field-range message | same | yes | 0 |
| 11 | `civs: ["NOPE"]` | raises `unknown civilization 'NOPE'` | same | yes | 0 |
| 12 | `unit.availability` civ `NOPE` | raises `unknown civilization 'NOPE' for the tech-tree layer; known: <63 names>` | same | yes | 0 |
| 13 | resource `faith` | raises `unknown resource 'faith'; known: food, gold, population, stone, wood` | same | yes | 0 |
| 14 | stat the type cannot store (`树木 H` attack) | **returns dict**: `edit_count=0`, `"树木 H has no displayed_attack to change"` | **raises** `树木 H has no displayed_attack field to change (its unit type does not store one)` | — | 0 |
| 15 | donor `不存在兵种XYZ` | raises `no unit matches …` | same | yes | 0 |
| 16 | donor == target (步弓手←步弓手) | **returns dict** `editable=false`, readable reason | **raises** the same reason text | — | 0 |
| 17 | effect command index 99 | raises `Loom has 3 effect commands; index 99 is out of range` | same | yes | 0 |
| 18 | picture path does not exist | raises `no such picture: …` | same | yes | 0 |
| 19 | intent is a `str`, not a dict | raises **`AttributeError`** `'str' object has no attribute 'get'` | same (uncaught, not `IntentError`) | yes | 0 |
| 20 | `{}` empty dict | raises `unknown intent None; known: …` | raises `intent None declares compile strategy None, …` | **no** | 0 |
| 21 | `delta=0` (resolvable no-op) | returns dict, `edit_count=63`, desc `步弓手 生命值 +0` | **returns manifest**, writes 2 files | — | **2** |
| 22 | grant already held (AZTECS←步弓手) | returns dict `editable=false, edit_count=2` | **raises** `AZTECS can already build 步弓手; nothing would change` | — | 0 |
| 23 | `tech.cost` food on Loom | returns dict `edit_count=0`, `"织布机 has no 成本 food to change"` | **raises** `织布机 has no 成本 food field to change (none of its 3 cost slots declares that resource)` | — | 0 |
| 24 | `unit.stat` on 兵营 (building) | returns dict `edit_count=252` | **succeeds**, `edit_count=252` | n/a | 2 |

Tally (24 cases): **18 rejected by both entry points** (1–13, 15, 17–20);
**4 accepted by `plan()` and refused by `build()`** (14, 16, 22, 23);
**1 accepted by both and shipped as a no-op** (21); **1 accepted by both and
really edited** (24). 22 of the 24 hit a refusal somewhere.
`plan()` and `build()` gave the *identical* message in **16 of those 22**; they
differed only on the two unparseable-intent cases (4, 20 — D9), and the four
build-only refusals cannot have "the same message" because `plan()` returned a
dict instead of raising (D2).

*Refusals never write anything*: **0 files** were on disk after all 22 refused
cases, including the four build-only refusals (the raise happens before
`emit_*`). That half of the claim holds cleanly. The only two cases that left
files are the two the API chose to accept (21, 24).

The stated contract — *"reference that cannot be resolved → raise; reference
resolves but the change is a no-op → return a dict saying so"* — is honoured by
`plan()` in cases 14/16/22/23 and violated by `build()`, which raises for
exactly those four. Case 21 shows the mirror-image problem: `build()` accepts a
genuinely empty change and ships a 12 MB mod.

Message quality is good where it fires: every refusal names the offender, and
most name the legal alternatives (the 63 civ names, the 5 resources, the 14
stats). Two messages are worse than they need to be: case 4/20 (build says
"declares compile strategy None" for a *typo*, never the word "unknown"), and
case 19 (a bare `AttributeError` escapes).

---

## 5. The honest-boundary fields exist — REFUTED for data mods, CONFIRMED for sprites

Measured across all four compile strategies plus both bundle paths.

| build | `verification` keys | `proven` | `not_proven` |
|---|---|---|---|
| `unit.stat` (in_place_patch, `.dat`) | `changed_bytes, claimed_bytes, final_offset, leftover, ok, problems, size, unclaimed_missing, unexpected_changes` | **ABSENT** | **ABSENT** |
| `tech.research_time` (in_place_patch, `.dat`) | same nine keys | **ABSENT** | **ABSENT** |
| `unit.availability` (civtechtrees_json) | 20 keys incl. `proven`, `not_proven` | **7 entries** | **1 entry** |
| `unit.sprite mode=copy` (loose_files) | `checked, civ_count, files, identical_to_target, missing_on_disk, not_proven, ok, proven, refusals, warnings, wrong_bytes` | **2 entries** | **1 entry** |
| `unit.sprite mode=rename` (loose_files) | `no_sld_shipped, not_proven, ok, proven, renamed, renamed_but_wrong, untouched_but_moved` | **3 entries** | **1 entry** |
| bundle, `.dat`-only | same nine byte keys | **ABSENT** | **ABSENT** |
| bundle, `.dat` + availability | nine byte keys + `availability.verification.{proven,not_proven}` | only under `availability` | only under `availability` |
| bundle, availability-only | `ok, renamed_records, reparse_ok, why_not_dat` | **ABSENT** | **ABSENT** |
| bundle, sprite-only | the `_sprite_verification` dict (also mirrored at `sprite_verification`) | **2 entries** | **1 entry** |

Quoted, sprite `copy` build (the case the claim asks about):

> **proven**
> 1. `that each of the 20 file(s) this mod ships is on disk holding the donor's own bytes, and that none of them is byte-identical to the file it replaces (so this is a change, not a no-op)`
> 2. `that the target names are the engine's own: resolved from the unit record's standing graphic through the graphics record's 'file' string, not guessed from a filename`
>
> **not_proven**
> * `that this run of the running game draws the new art from these loose .sld files.  The copy model IS proven in game (2026-10-17: villagers came out as sheep from 20 loose .sld and no .dat), but every launch is a separate load, so a fresh install still has to be looked at once`

Quoted, `civtechtrees_json` grant (proves the lists are not just boilerplate —
the proven list grows with what was actually done, and the not-proven list names
the specific unproven load):

> **proven** (6th of 7) — `the '.dat' half the game confirmed was written: a new effect was appended carrying the anchor technology 42's own commands plus 'make unit 8 available', and the technology now points at it (this is what 'dsh test v7' did, and the user confirmed the unit appeared at 0:00)`
>
> **not_proven** — `that THIS mod renders unit for that civilization -- the recipe is the one confirmed in game (2026-10-16, 'dsh test v7', three controls: villagers stayed at 1000 hp, the Castle Longbowman was unaffected, and the Dark Age Barracks showed the unit), but each new mod is a new load and only an in-game test settles it`

For the `.dat` path there is **no** honesty boundary anywhere in the manifest —
not at `man["verification"]`, not under another key (`[k for k in man if
"proven" in k] == []`). A caller that reads `proven`/`not_proven` for doubt
finds the key missing precisely on the strategy that patches 93 MB of the game's
own data. Claim 5 as worded ("for a data-mod build AND for a sprite build") is
**refuted** by the data-mod half.

---

## Defects found

**D1 — the `.dat` build ships no `proven`/`not_proven`, and neither do the bundle paths.** *Severity: high (refutes claim 5; the doubt is largest here).*
Cause: `aoe2mod/api.py:1967` does `man["verification"] = rep["verification"]`, and
`rep["verification"]` is built by `aoe2mod/intent/compiler.py:1904 verify()`,
whose entire key set is created at `compiler.py:1906`–`1932` and contains no
honesty fields. The bundle reproduces this: `aoe2mod/api.py:2742` sets
`verification = {"ok": True, "why_not_dat": "no .dat sentence"}` and
`api.py:2848` reuses the sprite report only when there is no `.dat`/JSON layer.
The project's own test asserts the key for the sprite path
(`aoe2mod/tests/test_api.py:1218`) and for the tech-availability path
(`test_api.py:1055`) but never for `in_place_patch`, so nothing catches this.

**D2 — `plan()` promises edits for a change it will refuse, in four measured cases.** *Severity: high (it is the claim-4 contract, broken in the direction that costs the user a 12 MB build).*
Cause is a preview that returns a dict instead of raising while the build re-runs
the same check and raises: `aoe2mod/api.py:1812`–`1814` (unit branch, "has no X
to change"), `api.py:1759`–`1761` (tech branch), `api.py:938`–`939` (reskin:
`if not rep.get("ok"): raise`), `api.py:2287`–`2288` (availability bundle),
and the single-intent availability path around `api.py:382`–`386` where
`editable=False` is set and returned. Measured: Loom `cost food`, 树木 H
`displayed_attack`, 步弓手←步弓手 sprite, AZTECS grant-when-held — all four
return a dict from `plan()` and raise from `build()`.

**D3 — a non-editable availability plan still advertises work.** *Severity: medium.*
`aoe2mod/api.py:367`–`374` sets `edit_count` (`2`) and `changes_dat=True` from the
schema *before* the `if not rep["ok"]` branch at `api.py:382` sets
`editable=False`. Measured: `{'unit':'步弓手','civ':'AZTECS','action':'grant'}`
→ `editable=False` **and** `edit_count=2, changes_dat=True`. A UI that shows
either number before consulting `editable` tells the user two edits will happen
and then the build refuses.

**D4 — `changes_dat=True` on a build whose `.dat` is byte-identical to the base.** *Severity: medium (the manifest contradicts its own warning).*
`aoe2mod/mod/emitter.py:355`: `manifest["changes_dat"] = False if dat_carrier else (dat_bytes is not None)`
— this reports "a `.dat` was handed in", not "a `.dat` byte changed". With
`delta=0` the manifest ends up carrying `changes_dat=True`,
`dat_identical_to_base=True`, and the warning
`"the emitted .dat is byte-identical to the base game, so this mod changes nothing"`
(same file, `emitter.py:415`–`417`). Three fields, one of which is wrong.

**D5 — `verification.claimed_bytes` counts 2× the bytes that can change, and `unclaimed_missing` can never fail the check.** *Severity: medium (`ok=True` cannot see a no-op).*
`aoe2mod/intent/compiler.py:1926`–`1932`: `claimed` is the union of
`range(e.width)` per edit, while `changed` is the measured diff; `problems` never
includes `unclaimed_missing`, and `report["ok"] = not report["problems"]`
(`compiler.py:1938`). Measured on 9 successful builds —
`archer_atk` changed 126 / claimed 252, `militia_hp` 63/126, `archer_speed`
189/252, `archer_cost_wood` 63/126, `archer_armour` 126/252, `loom_time` 1/2,
`loom_effect` 1/4, `archer_garrison` 63/63, `loom_time_civ` 1/2 — with
`unclaimed_missing` = the difference each time. The `delta=0` build reports
`changed_bytes=0, claimed_bytes=126, unexpected_changes=[], ok=True`: a mod that
changed nothing is certified `ok`. `unexpected_changes` (the half that *does*
gate `ok`) is the one that is always empty.

**D6 — the no-op `delta=0` is accepted, planned as 63 edits, and shipped.** *Severity: medium (violates the stated no-op contract; 12 MB of user disk and mod-manager noise for nothing).*
`aoe2mod/api.py:1807`–`1808` counts `writes = sum(len(tg) …)` from the targets,
not from values that differ, so `delta=0` reports `edit_count=63`;
`build()` then writes `info.json` + a 11,982,480 B `.dat`. The only signal is a
`warnings` entry, and (see D4) it is contradicted by `changes_dat=True`.

**D7 — `plan()` on an `in_place_patch` intent omits `editable` and `changes_dat`.** *Severity: medium (API asymmetry a UI will crash on).*
`aoe2mod/api.py:1679`–`1681` builds the base dict with no `editable`; only
`_plan_reskin`/`_plan_paint`/`_plan_availability` add it. Measured plan keys —
`unit.stat`: `['amount','civ_count','civs','description','edit_count','entity_id','entity_name','kind','op','stat']`;
`tech.research_time` likewise, with no `editable`, no `changes_dat`. The same
question answered by `unit.availability` returns both. `test_api.py:1042`
asserts `plan(...)["editable"] is True` for a `civtechtrees_json` intent, so the
key is clearly expected to exist.

**D8 — `plan()`'s `writes` string under-reports the files `build()` emits.** *Severity: low.*
`aoe2mod/api.py:368`–`370` advertises `".dat + CivTechTrees/<CIV>.json"`, but the
build writes four files and the fourth (`futuravailableunits.json`, the panel
splice) is neither listed nor hinted at. Measured on the AZTECS grant.

**D9 — an unknown intent name gets a worse message from `build()` than from `plan()`.** *Severity: low (both refuse, so no bad write).*
`aoe2mod/api.py:1910` reads `_strategy()` before resolving, so a typo falls
through to `api.py:1946`–`1949`: `"intent 'unit.bogus' declares compile strategy
None, which this build does not implement"`. `plan()` says the useful thing:
`"unknown intent 'unit.bogus'; known: tech.availability, tech.cost, …"`. The same
happens for `{}` (`intent None …`).

**D10 — a non-dict intent escapes as `AttributeError`, not a readable refusal.** *Severity: low.*
`aoe2mod/api.py:1678`/`1910` call `.get` on the argument with no type guard;
`tk.plan("unit.stat 步弓手")` raises `AttributeError: 'str' object has no attribute 'get'`,
which the documented refusal type cannot catch.

**D11 — the documented refusal type is not exported from the documented entry point.** *Severity: low (but it bit me on the first probe run).*
`aoe2mod/api.py:32` is `__all__ = ["Toolkit", "open_toolkit"]`, and `IntentError`
lives only in `aoe2mod.intent.compiler` (`compiler.py:139`); `api.py` uses it as
`C.IntentError` at ~20 sites but never binds the name, so
`A.IntentError` raises `AttributeError`. A caller following the public entry
point has to import an internal module to catch the library's own error.

**D12 — `build()`'s `resolved` drops the detail `plan()` computed, for 3 of 13 cases.** *Severity: low–medium (a UI that shows plan text then build text changes the sentence under the user).*
`aoe2mod/api.py:1968` (`man["resolved"] = rep["resolved"]`) and
`api.py:732`/`:839` (`man["resolved"] = r.describe()` for paint and retarget)
use the generic resolver sentence, discarding the target/attribute/donor detail
that `plan()` assembled at `api.py:1691`–`1736`. Measured: the three rows in §3.

**D13 — "`unit.stat` on a unit type that does not store the stat" is not really testable through a building, but is testable through an object.** *Severity: informational.*
兵营 (id 12) *does* store attack/reload/cost across its age-variant family
(plan and build both report 252/504/252 edits), so it is a bad example. The real
case is `树木 H` (id 406): `plan()` says `edit_count=0` and `build()` raises —
which is D2, not a separate defect. Recording it so the citation in claim 4 is
not misleading.

---

## Claims I could not test

1. **Any `not_proven` sentence.** I cannot launch the game, so I cannot
   adjudicate "a running game draws this", "the game offers the unit", "the
   build menu changes", or the `dsh test v7/v9/v13` precedents the strings cite.
   I confirmed the sentences are *present and specific* on three strategies; I
   did not confirm they are *accurate*, and by construction nobody inside a
   static test can.
2. **`repaint_sld` (`unit.art`) successful build.** It needs a real source PNG
   that I do not have, so only its missing-picture refusal was exercised. Its
   `proven`/`not_proven` (`api.py:719`/`:727`) are present in code and in the
   bundle's `sprite_verification` replacement (`api.py:2827`/`:2836`), but I did
   not see a live manifest.
3. **The mod-manager / install path** (`mod-status.js`, profile enablement,
   `info.json` acceptance). Out of scope of the five claims and it would write
   outside my scratch dir.
4. **Whether the mirrored edit is semantically the right second write.** I proved
   the mirror is at a constant +78 B, changes with the primary, and touches
   nothing else — I did not prove the engine reads that mirror for damage, only
   that the toolkit believes it does.
5. **Civ attribution by name.** My two attributions are structural (fingerprint
   census over the Civs stage; constant 510 B to the unit's own `'ARCHR'` debug
   string). An earlier attempt to name each copy via the nearest civ-name debug
   string produced only 58/63 coverage and 114 candidate payloads, so I discarded
   it rather than report a number I could not defend. "All 63 civs" is therefore
   supported structurally, not by reading 63 civ labels.
6. **`plan()`/`build()` agreement over the whole intent schema.** I sampled 13
   build intents and 24 malformed ones; the schema declares 10 intents with
   further fields (`civs`, `mode`, `scope`, `fill`, `families`, `picture`, …)
   that I did not enumerate exhaustively.
