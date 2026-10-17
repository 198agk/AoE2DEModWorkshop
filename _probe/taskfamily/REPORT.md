# Villager task-variant family: where the mapping actually lives

**Game:** AoE2 DE build 101.103.54800.0, root `D:\Games\Steam\steamapps\common\AoE2DE`
**Dat:** `resources\_common\dat\empires2_x2_p1.dat` (12,023,754 B compressed → 93,268,152 B, `gv=54`, 63 civs)
**Exe:** `AoE2DE_s.exe` (72,166,200 B, PE image base `0x140000000`)
**Probe dir:** `D:\Software\DeepSeek Harness\工作区2\_probe\taskfamily\`
**Symptom under investigation:** id 83 (`VMBAS`) `hit_points` patched 25 → 2500; idle villager reads 2500/2500, but once tasked the panel switches to 建筑者 and shows 25/25.

---

## VERDICT

**(a) DISCOVERABLE FROM GAME DATA.** The mechanism is a real, serialized per-unit field in the `.dat`:

> **`Bird.TaskSwapGroup`, `uint8`, at `unit offset(s) == "bird_start" + 10 + 2*len(DropSites)`.**
> Units sharing a non-zero value are the units the engine is allowed to swap between when the object is re-tasked.

This is **not** exe-hardcoded and **not** pure engine logic: it is authored data, one byte per unit record,
and the engine just reads it. The mod failed because it patched **one** record (id 83) out of the **27**
records that share the two villager swap groups.

- Group **1** (male basket), 14 ids: `56, 83, 118, 120, 122, 123, 124, 156, 259, 579, 592, 1810, 1892, 2333`
- Group **2** (female basket), 13 ids: `57, 212, 214, 216, 218, 220, 222, 293, 354, 581, 590, 1891, 2334`
- Group **3**, 5 ids — **fishing ships, not villagers**: `13 FSHSP, 2147 FSHSP, 2171 Oystering Ship, 2356 Antiquity Mode Fishing Ship, 2630 WHALING_SHIP`
- **Group 0** = everything else (2,661 distinct ids) including `Archer (4)`, `Scout (448)`, and — importantly — `206 (VMDL)` and `2714/2715 (VMREPAIRER/VFREPAIRER)`, which `linkedUnits.json` *wrongly* files under "Villagers".

An int32 twin-pair table mirroring groups 1+2 also exists in the exe (see §2), but it is a **derived copy**:
the exe has no `TaskSwapGroup` string (0 hits) and no field names, and the dat field is what the JSON-external
modding pipeline can read and write. **The dat is the authority.**

---

## 1. Dat-adjacent JSON — triage

Files under `D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\`:

| file | size | verdict |
|---|---|---|
| `linkedUnits.json` | 809 B | **RELEVANT — the JSON-side roster of the same family.** |
| `objreplacement.json` | 2533 B | Partly relevant, **different mechanism** (random gender swap only). |
| `unitlines.json` | 20,974 B | IRRELEVANT — tech-tree upgrade chains (`LineID` −400..−199). |
| `buttons.json` | 3160 B | IRRELEVANT — 14 UI command buttons; no unit ids. |
| `sharedbuildings.json` | 2956 B | IRRELEVANT to villagers — barracks-vs-castle buildable pairs. |
| `unitcategories.json` | 738 B | IRRELEVANT — 7 entries (siege/monks only). |
| `civilizations.json` | 58,763 B | IRRELEVANT — civ metadata. |
| `dropsites.json` | 31,606 B | NOT the authority; it names the `building_id`s that appear in each unit's `Bird.DropSites`. |

**`linkedUnits.json`** — shape `{"Data":[{"Name":str,"Units":[int,...]},...]}`, 8 entries:

```
[0] Lü Bu             n=2  [2032, 2061]      [4] Sun Jian          n=2  [2054, 2065]
[1] Guan Yu           n=2  [2034, 2064]      [5] Kongming Lantern  n=2  [2067, 2068]
[2] Sun Quan          n=2  [2042, 2063]      [6] Arariboia         n=2  [2641, 2642]
[3] Liu Bei           n=2  [2053, 2066]      [7] Villagers         n=28  (line 33)
```

`Villagers` roster = `[56, 57, 83, 118, 120, 122, 123, 124, 156, 206, 212, 214, 216, 218, 220, 222, 259, 293, 354, 579, 581, 590, 592, 1810, 1891, 1892, 2333, 2334]`.

Versus the dat truth (27 ids): **0 missed, 1 false friend (`206 VMDL`, tsg=0)**.
So `linkedUnits.json` → "Villagers" is a **good but not exact** roster. The dat field is exact.

**`objreplacement.json`** explains only the 83 ↔ 293 random gender swap
(`{"object_id":83,"object_override":{"name":"Villager (Female)","replacement_object":293,"chance":50}}`
and the mirror), i.e. which *base* record an untasked villager gets. It says nothing about task variants.

---

## 2. The exe

### 2.1 String anchors (ASCII; and the same patterns in UTF-16LE)

All dat-adjacent JSON filenames **are** present as plain ASCII:

```
linkedUnits      A n=1  0x325A5C0  rva 0x14325C5C0  .rdata
linkedTechs      A n=1  0x32986B0  rva 0x14329A6B0
unitlines        A n=1  0x329E350  rva 0x1432A0350
unitcategories   A n=1  0x325A700  rva 0x14325C700
objreplacement   A n=1  0x32BF8C0  rva 0x1432C18C0
sharedbuildings  A n=1  0x3259758  rva 0x14325B758
buttons.json     A n=1  0x325ABD0  rva 0x14325CBD0
dropsites        A n=3  0x32320AA / 0x3235F91 / 0x329E1F0
worker_object_group A n=1  0x329E220  rva 0x1432A0220
```
All UTF-16LE variants: **0 hits**. The modding JSON layer is loaded by filename from `.rdata`.

**Field-name search — all 0 hits (both encodings):** `TaskSwapGroup`, `TaskSwap`, `task_swap`,
`task swap`, `switches villager types`, `transform into another unit`, `WorkerObjectGroup`.
→ The engine does **not** carry the genieutils field name; the name is an external-library artifact.
This is why the parent's ASCII search for the *internal codes* (`VMBAS`, `VMBLD`, …) also found 0: the
codes are **dat strings**, never exe strings.

### 2.2 Numeric tables — two real ones found

Search was little-endian over the whole file, after the u16 searches
`[83,118] [118,212] [83,293] [293,83] [83,118,120,122] [83,293,1810]`, the full 14-member group-1 run,
the full 13-member group-2 run, the 5-member group-3 run and the 27-member roster **all returned 0 hits** —
i.e. the exe does **not** store the family as int16 and does **not** store it grouped male-then-female.
The ids are stored as **int32, as (male, female) twin pairs**:

**TABLE A — the villager twin-pair table**
```
file offset 0x32B1DCC   RVA 0x1432B3DCC   section .rdata
25 x int32 = 100 bytes  [0x32B1DCC .. 0x32B1E30)
values: [1, 118, 212, 259, 214, 83, 293, 122, 216, 123, 218, 124, 220,
         579, 581, 156, 222, 120, 354, 592, 590, 56, 57, 2333, 2334]
as pairs from index 1:
 (118,212) VMBLD/VFBLD   (259,214) VMFAR/VFFAR   ( 83,293) VMBAS/VFBAS
 (122,216) VMHUN/VFHUN   (123,218) VMLUM/VFLUM   (124,220) VMMIN/VFMIN
 (579,581) VMGLD/VFGLD   (156,222) VMREP/VFREP   (120,354) VMFOR/VFFOR
 (592,590) VMSHE/VFSHE   ( 56, 57) VMFIS/VFFIS   (2333,2334) VMGLD/VFGLD
```
12 pairs = both swap groups (minus `1810 SVMBAS`, `1891/1892`, which are in the dat only). Leading `1`
is an unrelated preceding value (the maximal 0<v<3000 run starts one int32 earlier at `0x32B1DCC`).

**TABLE B — the broader "linked object" twin table**
```
file offset 0x3232E30   RVA 0x143234E30   section .rdata
48 x int32 = 192 bytes  [0x3232E30 .. 0x3232EF0)
values: [259,214, 122,216, 56,57, 123,218, 118,212, 156,222, 592,590, 120,354,
         124,220, 579,581, 41,555, 759,761, 755,757, 886,887, 1225,1227,
         1254,1255, 1658,1659, 1660,1661, 1738,1740, 1759,1761, 93,358, 359,1786,
         56,57, 1892,1891]
```
The first 10 pairs are villager twins; the rest are the **Elite-upgrade / shared-building pairs** that
`sharedbuildings.json` also lists (41/555 Huskarl, 755/757 Tarkan, 1225/1227 Konnik, 1658–1661 Serjeant,
93/358 Spearman/Pikeman, 359/1786 Halberdier). This is the engine's object-substitution pair list.

**Why believed, not coincidence:** exact ordered runs of 4–12 consecutive family ids at a fixed 4-byte
stride, inside `.rdata`, and the non-villager pairs of Table B independently match pairs known from
`sharedbuildings.json`. Occurrence counts: `u32 [118,212]` = 2 hits, `u32 [83,293]` = 1 hit — all inside
these two tables.

**Disbelieved hits (explicitly dismissed):** `u16 [118,83]` (6 hits) and `u16 [56,57]` (21 hits) are all
inside UTF-16LE UI strings — verified by dumping context: `PaphosCivSelectionCard.xaml`,
`PaphosCivSelectionDialog.xaml`, `ACHIEVEMENT_SURYAVARMAN_RELICS` (the `8.9` build digits),
`ACHIEVEMENT_ALARIC_SPEED_RUN` (`9.8`), `0.1.2.3.4.5.6.7.8.9.A.B.C.D.E.F`, `application/json`.
These are ASCII digits/letters plus a `0x00` high byte. Coincidence.

**Other large small-int runs containing ≥3 family ids** (`0x3477894`, `0x3479B84`, `0x34C8A04`,
`0x3555544`, `0x35C4630`, `0x35C6B54`, `0x36243B0`, `0x3625104`, `0x3634544`, `0x358B038`, `0x358B3EC`,
`0x358C130`, `0x358C40C`) are dense enumerations of nearly-consecutive small integers
(e.g. `…255,257,259,261,263…`) — unit-id lookup/index tables that merely *cover* the id range.
Dismissed.

---

## 3. The .dat — the authoritative field

**genieutils definition** (`_probe\source\genieutils\include\genie\dat\unit\Bird.h:41-53`):
```cpp
int16_t DefaultTaskID = -1;
float   SearchRadius  = 0;
float   WorkRate      = 0;
std::vector<int16_t> DropSites;
/// If activated unit switches villager types
uint8_t TaskSwapGroup = 0;      // <-- Bird.h:47, serialized at Bird.cpp:80
int16_t AttackSound; int16_t MoveSound;
uint32_t WwiseAttackSoundID; uint32_t WwiseMoveSoundID;
uint8_t RunPattern;
std::vector<Task> TaskList;     // "only in aoe/ror" -> empty in DE
```

**Reachable in the dat:** yes, but only by wrapping the reader — the repo's
`_probe\datparse\parse_dat.py` `read_bird()` at :820 *discards* its own return value and
`intent_patch.walk_unit()` records nothing from Bird. The probe monkey-patches `P.read_bird`
with a `_PosProxy` wrapper that adds `at(k)` (returning `r.pos` when the reader lacks `marks`) so the
same code works with both `parse_dat.Reader` and `intent_patch.Orec`.

**Raw-byte proof** (offset = the `TaskSwapGroup` byte; 8 bytes before + 8 after in hex):
```
unit  83 VMBAS   tsg_off=0x3C8A3C  value=1  ctx 44 00 10 07 fc 09 65 09 [01] 2d 01 2d 01 dc d3 8c 42
unit 293 VFBAS   tsg_off=0x3E9C1F  value=2  ctx 44 00 10 07 fc 09 65 09 [02] b2 01 b2 01 aa 57 99 a3
unit 118 VMBLD   tsg_off=0x3CE188  value=1  ctx 00 41 00 00 80 3f 00 00 [01] 27 01 2d 01 89 d1 31 65
unit 448 SCOUT   tsg_off=0x3F9097  value=0  ctx 80 40 00 00 80 3f 00 00 [00] da 01 d3 01 0b 39 27 bb
unit   4 ARCHR   tsg_off=0x3BBD08  value=0  ctx c0 40 00 00 80 3f 00 00 [00] a6 01 a5 01 67 21 37 e0
```
(The `44 00 10 07 fc 09 65 09` before 83 = DefaultTaskID `-1`, SearchRadius 1.0f,
WorkRate 1.0f, DropSiteCount 4 then two int16 drop sites `0x09fc=2556`, `0x0965=2405`.)

**Census over 136,861 physical records / 2,693 distinct ids:**
`tsg=None (type < 40, no Bird struct) 46,671` · `tsg=0 88,174` · `tsg=1 882` · `tsg=2 819` · `tsg=3 315`.

**The `Task` list carries no unit-swap field.** `_probe\source\genieutils\include\genie\dat\UnitCommand.h`
`class Task` has `TaskType, ID, IsDefault, ActionType, ClassID, UnitID, TerrainID, Resource*, Work*,
AutoSearchTargets, SearchWaitTime, EnableTargeting, CombatLevelFlag, GatherType, WorkFlag2,
TargetDiplomacy, CarryCheck, PickForConstruction, {Moving,Proceeding,Working,Carrying}GraphicID,
{ResourceGathering,ResourceDeposit}SoundID, Wwise…, Enabled`. No "become unit X". So the swap is **not**
expressed through per-unit task data — it is solely `TaskSwapGroup`. This confirms genieutils' comment
("If activated unit switches villager types") and rules out the task-list hypothesis.

### Per-unit records of the family (`villager_family.json`)

Offsets are the exact file offsets of the `TaskSwapGroup` byte, read verbatim from
`_probe\taskfamily\villager_family.json` (`rows[][11]` = `off_tsg`):

| id | name | dll | tsg | work_rate | drop_sites | tsg byte offset |
|---|---|---|---|---|---|---|
| 83 | VMBAS | 5121 | 1 | 1.00 | 109,68,1808,2556,2405 | 0x3C8A3C |
| 293 | VFBAS | 5607 | 2 | 1.00 | 109,68,1808,2556,2405 | 0x3E9C1F |
| 1810 | SVMBAS | 5606 | 1 | 1.00 | 109,68,2556,2405 | 0x4A41E5 |
| 56 / 57 | VMFIS / VFFIS | 5499 | 1 / 2 | 0.43 | 109,68,45,2172,2556,2405 | 0x3C3FA7 / 0x3C4390 |
| 118 / 212 | VMBLD / VFBLD | 5122 | 1 / 2 | 1.00 | (none) | 0x3CE188 / 0x3DFCA8 |
| 120 / 354 | VMFOR / VFFOR | 5402 | 1 / 2 | 0.31 | 109,68,2556,2405 | 0x3CE85E / 0x3EFACA |
| 122 / 216 | VMHUN / VFHUN | 5124 | 1 / 2 | 0.41 | 109,68,1808,2556,2405 | 0x3CECF0 / 0x3E069B |
| 123 / 218 | VMLUM / VFLUM | 5125 | 1 / 2 | 0.39 | 109,562,1808,2556,109×11,2405 | 0x3CF3A3 / 0x3E0E3E |
| 124 / 220 | VMMIN / VFMIN | 5126 | 1 / 2 | 0.36 | 109,584,1808,2556,109×11,2405 | 0x3CF75F / 0x3E12EA |
| 579 / 581 | VMGLD / VFGLD | 5482 | 1 / 2 | 0.38 | same 16-entry list as 124 | 0x40AA66 / 0x40AF98 |
| 259 / 214 | VMFAR / VFFAR | 5123 | 1 / 2 | 0.53 | 109,68,1734,2556,2405 | 0x3E5C78 / 0x3E0209 |
| 592 / 590 | VMSHE / VFSHE | 5496 | 1 / 2 | 0.33 | 109,68,2556,2405 | 0x40CA73 / 0x40C5E3 |
| 156 / 222 | VMREP / VFREP | 5127 | 1 / 2 | 12.5 | (none) | 0x3D419B / 0x3E1841 |
| 1892 / 1891 | VMHER / VFHER | 5897 | 1 / 2 | 0.4759 | 1890,68,109,2556,2405 | 0x4AEBDD / 0x4AE7B1 |
| 2333 / 2334 | VMGLD / VFGLD | 21332 | 1 / 2 | 0.38 | 109,584,1808,2172,45,2556,2405 | 0x4F452B / 0x4F488C |
| 2714 / 2715 | VMREPAIRER / VFREPAIRER | 5127 | **0** | 12.5 | (none) | 0x52E7A9 / 0x52EDB3 |
| 206 | VMDL | 5653 | **0** | 1.00 | 109,68 | 0x3DEE9D |
| 13, 2147 | FSHSP (class 21) | — | 3 | — | — | — |
| 2171 / 2356 / 2630 | Oystering Ship / Antiquity Mode Fishing Ship / WHALING_SHIP (class 21) | — | 3 | — | — | — |

(`villager_family.json` covers the villager family only; the tsg=3 fishing-ship ids come from
`task_swap_groups.json` and their identity from `probe_exe_tables2.py`.)

**Mechanism (matches the observed symptom exactly):** when an object is given a task, the engine picks,
from the object's `TaskSwapGroup`, the member whose current task is the new task, and re-points the object
at that unit **record**. The mod set `hit_points=2500` on id 83 only; tasking the villager swaps it to
id 118 (building, tsg=1), whose `hit_points` is still 25 → the panel shows *建筑者 25/25*.
Per-civ duplication compounds this: every one of the 27 ids exists in up to 63 civs, so a correct mod
must edit all physical copies of all 27 (`intent_patch.find_units` per id).

---

## 4. Data-driven heuristic for other units — measured

**Ground truth** = dat `TaskSwapGroup`; positives = tsg ∈ {1,2} = **27 ids**.
Scoring: for each id, its heuristic "siblings" are the other members of its group; TP/FP count the
sibling pairs emitted. `siblings_found_for` = how many of the 27 positives got **at least one** sibling.

| # | heuristic | positives covered | pair TP | pair FP |
|---|---|---|---|---|
| H1 | identical **full** stat signature (type, class, hp, icon, LOS, garrison, sort, speed, ranges, reload, accuracy, projectile, frame_delay, displayed_*, sorted attacks/armors/costs/train_locations, work_rate, search_radius) | **4 / 27** | 4 | 196,436 |
| H2 | identical **loose** signature (type, class, hp, icon, line_of_sight, speed) | 22 / 27 | 70 | 200,784 |
| H3 | **same `linkedUnits.json` entry** | **27 / 27** | 729 | 41 |
| H4 | same `LanguageDLLName` | 24 / 27 | 28 | 1,074,554 |
| H5 | **same dat `TaskSwapGroup`** (the truth) | 27 / 27 | 338 | 20 |

**H1 fails the villager family outright.** With the strict signature, **83, 118, 293 and 212 are all
singletons**; over 2,693 ids there are 1,177 signatures, 177 multi-member clusters, 1,693 ids in clusters,
1,000 singletons — and cluster purity vs TaskSwapGroup is 177 pure / 0 impure, which looks good only
because the tsg=0 mega-cluster is trivially "pure". Stat-identity **cannot** discover this family
(male/female twins differ in gender-dependent fields).

**H2** is worse in practice (2.5× the FPs of H1 for 5.5× the coverage) — a 2,600-id mega-cluster.

**H4** is interesting: each male/female twin pair **does** share its `LanguageDLLName` exactly —
`5122→[118,212]`, `5123→[214,259]`, `5124→[122,216]`, `5125→[123,218]`, `5126→[124,220]`,
`5127→[156,222]`, `5402→[120,354]`, `5482→[579,581]`, `5496→[590,592]`, `5499→[56,57]`,
`5897→[1891,1892]`, `21332→[2333,2334]` (12 of 12 pairs; 83/293 and 1810 are the exceptions, with
5121/5607/5606). But it is swamped by `dll=0` (430 ids, all unnamed) and by unrelated sharing groups,
hence FP > 1 million. Usable only as a *tie-breaker inside* an already-narrow candidate set.

**H3 is the best pure-data proxy:** `linkedUnits.json` → "Villagers" contains **all 27** real members
(0 missed) plus exactly **one** false friend (`206 VMDL`). Best practice for a mod tool:
**`linkedUnits.json` for the candidate roster + the dat's `TaskSwapGroup != 0` as the filter** — that
combination is exact (it drops 206 and adds 1810/1891/1892, which the JSON already has).

### Practical rule for a mod tool
1. Enumerate ids from `linkedUnits.json` entries (they encode the *intent* to link objects), then
   **verify each candidate's `Bird.TaskSwapGroup`** — keep only non-zero.
2. Regression: any stat edit to a unit with `TaskSwapGroup != 0` must be mirrored onto every other
   member of the same group, in **every civ that carries a copy**.
3. `TaskSwapGroup` is exposed by `_probe\datparse\parse_dat.py` only through a patched `read_bird`
   (return value discarded at :820; `intent_patch.walk_unit` records nothing from Bird). Reading it
   needs the `_PosProxy` wrapper described in §3. To *write* it, the byte offset must be recorded —
   which the wrapper provides.
4. Do **not** trust stat clustering or `LanguageDLLName`, and do **not** trust `linkedUnits.json` alone.

---

## Appendix — repro

```
python -X utf8 _probe\taskfamily\probe_dat_taskfamily.py   # tsg census + villager_family.json
python -X utf8 _probe\taskfamily\probe_exe_tables.py       # anchors + u16/u32 scan + exe_scan.json
python -X utf8 _probe\taskfamily\probe_exe_context.py      # hit-by-hit context (dismisses UI-string hits)
python -X utf8 _probe\taskfamily\probe_exe_dump_table.py   # maximal small-int runs
python -X utf8 _probe\taskfamily\probe_exe_tables2.py      # table extents + tsg=3 identity
python -X utf8 _probe\taskfamily\probe_heuristics.py       # H1..H5 measurement
python -X utf8 _probe\taskfamily\probe_final_offsets.py    # file offset -> RVA for Tables A/B
```
Artifacts in `_probe\taskfamily\`: `exe_scan.json`, `exe_tables_dump.txt`, `exe_tables_final.txt`,
`heuristic_measurement.txt`, `task_swap_groups.json`, `villager_family.json`, `clusters.json`.

All operations were read-only on the game directory; the game was never launched.
