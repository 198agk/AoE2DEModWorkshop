---
name: aoe2-de-sprites
description: Read, render, edit and write AoE2 DE .sld sprite files (unit, building, animal animations) and swap in-game sprites as a loose-file mod. Use when a task touches resources/_common/drs/graphics/*.sld, unit or building animations, player colour / team tinting, palette (JASC .pal) work, sprite recolouring, or offline sprite preview. Covers the byte-exact SLD reader/writer, the block-grid rule that makes rendering correct, the playercolor BC4 mask, and the unknown2 honesty boundary.
---

# AoE2 DE sprites (`.sld`) — read / render / edit / write

**Bottom line: the `.sld` format is fully solved. The reader, renderer and writer are
all in `_probe/` and byte-exact-verified.** Use the existing scripts; do not write a new
parser.

| Tool | Path | What it is |
|---|---|---|
| Reader + decoders + renderer | `aoe2mod/game/sld.py` (vendored from `_probe/sldlib.py`) | `read_sld(path)`, `parse_rect_layer`, `parse_mask_layer`, `grid_of`, `placed_blocks`, `decode_bc1_plane`, `decode_bc4_plane`, `render_frame` |
| Unit → art resolution + swap planning | `aoe2mod/game/sprites.py` | `art_index(game_root, graphics)`, `art(unit)`, `plan_swap(target_art, donor_art)`, `swap_files(...)`, `anim_of`, `anim_keys`, `stem_of_name` |
| The `unit.sprite` intent | `aoe2mod/intent/reskin.py` | `plan()`, `describe()`, `read_payload()`, `verify_files()` |
| **The UI-facing entry point** | `aoe2mod/api.py` | `tk.plan({'intent':'unit.sprite','unit':4,'donor':8})` / `tk.build(...)`; **and inside a `plan_bundle`/`build_bundle` sentence list** — the reskin strategy is one of three `_split_by_strategy` returns |
| Writer | `_probe/sldwrite.py` | `serialize_sld(s)` + `roundtrip_all()` |
| Edit end-to-end proof | `_probe/u2_verify_write.py` | byte-diff localisation + re-parse + render |
| Colour enumeration | `_probe/u2_colours.py` | list real opaque colours of a main layer (use before setting thresholds) |
| Tests | `_probe/test_unit_sprite_chain.py`, `_probe/test_sprite_chain.py`, `_probe/test_reskin.py` | all in `_probe/run_suites.py` |
| Reference doc | `图形音效模组能力目录v1.md`, `数据模组能力目录v1.md` | full conclusions, tables, honest boundaries |

## Proven facts (do not re-derive, do not contradict)

- **Full-tree byte-exact round-trip: 15,484 / 15,484 files, 4,850,222 frames, 0 differing,
  and idempotent.** If your change breaks this, you changed the format.
- **Sprite replacement is free**: `.sld` files are loose and uncompressed, so replacing a
  sprite = **copy the donor `.sld` and rename it**, into
  `<mod root>/resources/_common/drs/graphics/<name>_x1.sld` **and `_x2.sld`**.
  **Both must be done** — the tree has exactly **7,743 x1 / 7,743 x2 with perfect pairing
  (0 orphans on either side)**. Measured 2026-10-17; an earlier note in this file said
  8,836, which is wrong. Directory total = **15,559 files: 15,486 `.sld` + 38 `.smp` +
  35 `.slp`**. No format knowledge, no tool, no compression needed.
- **The parser's real value is not replacement** (that needs none) — it is **offline
  preview, name→file lookup, and programmatic recolouring/variant generation**.

## Which `.sld` draws a given unit? (solved — do not guess from filenames)

The chain is **in the `.dat`**, and it was found by chasing a field the parser read and
threw away:

```
unit record  --standing_graphic[0]-->  graphics id  --(look up by the record's OWN `id`
                                                      field, NOT its array position)-->
graphics record's `file` string  +  ".sld"  =  <file>_x1.sld   (x2 is <file> with the
                                                                trailing `_x1` swapped)
```

- **Look up graphics by `id`, not by array position**: 89.8% vs 57.7% resolve. The two
  agree often enough that the wrong rule looks plausible.
- **`standing_graphic[1]` is the unit's ALTERNATE IDLE** (13,470 of 136,861 records set
  it; 13,092 point into the same art group).
- **`graphics.record.name` is a human label (`"Archer (Idle)"`); `file` is the disk name.**
  The `name` field is **never** equal to a filename stem (0 of 8,291) — name-based lookup
  is a dead end.

## Grouping animations: use the engine's `name`, NOT the filename prefix

**A unit's art group is declared by the graphics records themselves**: strip the
parenthesised suffix from `name` (`"Archer (Attack)"` → `Archer`) and that is the group.

**The filename-prefix rule is refuted — do not use it.** It makes unit 15 (Junk) claim
**7 files** (`u_shp_canoe_x1`, `u_shp_caravel_x1`, `u_shp_dreki_x1`, `u_shp_dromon_x1`, …),
which are different ships with different bytes (`u_shp_junk_x1.sld` 85,988 B vs
`u_shp_canoe_x1.sld` 51,540 B vs `u_shp_caravel_x1.sld` 243,180 B). 7,743 base names nest
(`b_misc_waypoint_flag` would swallow all 57 civilization flags). Across all units,
prefix == name-group for only 1,086 of 2,693.

**Animations are matched by the engine's parenthesised label, lowercased** (`walkA` and
`walk` both → `walk`), never by raw filename token — the Bowman's files are `_walk`/`_death`
while the Longbowman's are `_walkA`/`_deathA`, and token equality would call those
different animations.

**One file can serve SEVERAL animations.** The engine labels `a_herd_sheep_idleA_x1` both
`"Sheep (Idle)"` and `"Sheep (Attack)"` — the sheep headbutts, so one art plays for both.
321 of 8,656 files are pointed at by more than one record label. **Keying a file by
whichever record happened to come first makes the sheep look like a donor with no idle
animation at all** — build the label→file map as a *set* per file.

## Per-civilization art

**302 of 2,273 unit ids have a DIFFERENT art group per civilization** — unit 4 is
`u_arc_archer` for 57 civilizations and `u_arc_bowman` for the six Chronicles ones; unit 10
has 17 distinct stems. Any "swap this unit's art" operation is therefore per-civ and takes
a union, and two civilizations naming different donors for the SAME target file is a
**contradiction to refuse**, not something to resolve by ordering.

### ★★ A single-sentence guard is NOT enough once sentences can be combined

`reskin.plan` refuses "one file has to hold two pictures" **within one sentence**
(`Longbowman <- Archer` across all civilizations). But two `unit.sprite` sentences naming
the same target are where that conflict is first *possible* — the single-sentence check
cannot see across sentences by construction. Without a second guard in `Toolkit._sprite_bundle`,
the later sentence overwrites the earlier one's files **in silence while the manifest
describes both**.

- The bundle keeps a `claims` map (`relpath -> the sentence that put it there`) and refuses
  the whole sentence, **naming both sentences in the user's own words**:
  `two sentences need u_arc_archer_attackA_x1.sld to hold different pictures (步弓手 改用 长弓兵 的造型 and 步弓手 改用 弩手 的造型), and one file cannot do that`.
- Identical content is NOT a conflict (`prev != data` is the test), so two sentences that
  happen to want the same bytes compose.


## ★★★ A unit's picture is decided in THREE places, and only two walk the records

This is the single most expensive lesson in this area; both halves were paid for
in game, one day apart.

1. **The record's own `standing_graphic`** — the obvious one.
2. **A sibling record, chosen by `Bird.TaskSwapGroup`** — the engine re-points the
   unit when it is given a job, and *every sibling names its own art*. A villager
   is **27 records over 18 stems** (`Villager Male`, `Builder Male`,
   `Lumberjack Male`, `GoldMiner Male`, `Farmer Male`, …). Replacing one stem
   gives a unit that is a sheep while standing and a human while chopping:
   measured in game 2026-10-17 on `dsh test v10`.
3. **The resource being carried** — and this one is named by **no unit record at
   all**, so walking the tables can never reach it. `GoldMiner Male` has 6 files;
   `StoneMiner Male` has **2**, one of which is literally one of `GoldMiner
   Male`'s files. The engine picks it because the villager is carrying stone.
   Measured in game 2026-10-17 on `dsh test v11`: every job was a sheep except
   the stone miner while carrying.

The product handles all three: `whole_family` for (2), and `plan_swap`/`swap_files`
automatically carry (3). Use `SpriteIndex.resource_variants(stem)` — returns
`[(variant_stem, [files only the variant names])]`.

**Do not loosen the variant rule.** It matches exactly 4 stems in the shipped
game (stone/gold miner, base and Antiquity art). Looser shapes match hundreds of
unrelated pairs — snow variants, damage states, gate parts — and a reskin would
start shipping art the user never asked for. The four conditions are: variant
animation labels are a proper subset; at least one shared filename; stem word
bags differ by exactly one word on **each** side; variant animations are all
resource-dependent (`carry`/`work`). `_probe/test_reskin.py` section I pins the
count at 4 so a widening rule fails a test rather than a user's game.

**It is also a set-cover problem.** A villager family needs 10 animations; **no
entity in the game owns all 10** (`seed` on 4 unit ids, `task` on 6, `carry` on
36, `work` on 61). `fill=True` (on by default with `whole_family`) lets a nearby
donor animation stand in, but only when the angle count matches and the stand-in
has **at least as many frames** — the engine indexes by the record's grid, so too
few frames is garbage while extra frames are simply never asked for.

## Shipping a reskin as a mod

Use the product kernel: `tk.plan({'intent':'unit.sprite','unit':4,'donor':8})` then
`tk.build(...)`. The compiler strategy is **`loose_files`**, and its product is a set of
game-root-relative paths → bytes under `resources/_common/drs/graphics/`.

- **No new emitter was needed.** `emit_json_mod(mod_dir, {relpath: bytes}, info, ...)` is a
  generic "relative path → bytes" writer; the name is historical. A sprite layer and a
  `CivTechTrees/<CIV>.json` override land in the SAME mod folder through the same mapping.
- **A reskin mod must NOT carry a `.dat`.** `resources/_common/dat/` is a *different*
  storage point that forces a carrier `.dat` (see `aoe2-de-dat`); `resources/_common/drs/`
  does not. A redundant `.dat` pins the file at today's bytes and silently rolls back the
  next game patch.
- **Both `_x1` and `_x2` are always written** (7,743 perfect pairs). A plan that names only
  one is a bug.
- **`edit_count` for a reskin means FILES**, not bytes. Inside a bundle it must be summed
  with the byte patcher's edits and the availability `.dat` halves, or the preview and the
  build disagree — the recurring defect class of this project.
- A bundle that is *only* reskins reports `mod_contains_dat: False`; one that also has a
  `.dat` or tree sentence reports `True`. Do not conflate "some sentence wrote `.dat`
  bytes" with "the mod folder contains a `.dat`" (a carrier counts).

### ★★★ Two delivery models: `mode` is a FIELD, not a strategy

`unit.sprite` declares one compile strategy (`loose_files`) but has **two products**, and
both are proven in game (2026-10-17). The model is chosen per sentence by `mode`:

| `mode` | what it ships | size (villager family) | coexists with a data mod? |
|---|---|---|---|
| `copy` (default) | 466 loose `.sld`, no `.dat` | 418 MB (18 MB for one stem) | **yes** |
| `rename` | one `.dat`, **no picture at all** | **11.98 MB** (244 record renames) | no — one data mod per match |

- **Why `rename` is possible at all**: a `.dat` graphics record carries its own `file`
  string, and the engine takes the picture from THAT rather than from the neighbouring
  `slp` id. Changing `file` retargets the art without copying a byte. Proven in game:
  `dsh test v13`, one `.dat` and zero `.sld`, villagers came out as sheep.
- **`rename` requires a variable-width `.dat` writer.** A picture name that is 3 bytes
  longer used to produce 991,273 model/raw mismatches and a 3 MB-bloated file, because
  `Writer._emit` advanced `pos` and `rpos` by the same count. Every earlier edit in this
  project was an equal-width in-place patch, so the assumption was never tested. Pass
  `raw_len=` through `debug_string`.
- **`Reader.debug_string()` returns `(marker, text)`, not `(length, text)`.** Reading the
  marker as a length steps the cursor by ~2,656 bytes per string and breaks even a
  zero-edit round trip. The stored byte count lives in `Reader.last_string_len`.
- **`x2` is derived, never named.** Measured: 8,291 records name an `_x1` file and **0**
  name an `_x2`. The copy model must ship the derived siblings (the engine asks for them);
  the rename model only needs the donor's own `_x2` to exist on disk.
- **A plan that reports the model is not a build that delivers it.** The real defect here:
  `plan` honoured `mode: rename` and `build` silently produced the 466-file copy model.
  Pin it by asserting preview and manifest agree on `sprite_mode`, on `edit_count`, AND
  on whether any `.sld` landed on disk (`_probe/test_retarget.py` E/F).
- **In a bundle, the rename stage runs LAST.** It is the only stage that changes a
  `.dat` field's LENGTH without appending a record, so every earlier stage's offsets stop
  existing once it has run. It must also re-derive its model from the stream it is growing,
  via `locate.locate(cur, parser=p)` — **`parser`'s own `stats["civs"]` throws
  `StandingGraphic` away**, so using it makes every rename refuse with "no art".

## ★★★ Frame grids: report the mismatch, or the game plays the wrong frames silently

The engine pairs an animation with the art by the graphics record's
`frame_count` × `angle_count`. When a swap changes that grid it does **not** refuse —
it plays the wrong frames. So the grid is part of the answer, and it is **not a corner
case**: of reskin pairs that share an animation at all, **85.7% (74,109 / 86,468)** differ
on at least one animation's grid. Only 4.5% agree on everything.

- `SpriteIndex.art(unit)['grids']` is `{animation_key: [[frames, angles], …]}`;
  `sprites.grid_mismatches(target, donor, pairs=None)` returns
  `[{'animation', 'target', 'donor'}]`. `reskin.plan()` puts it in `grid_mismatches` and
  renders one warning sentence.
- **A grid can vary by civilization.** The male villager's attack is `60x16` in 57 civs and
  `45x16` in the 6 Chronicles ones, so one sentence covers two different changes. Merge by
  animation and say "depends on the civilization" — never print one number for all 63.
- **`SpriteIndex.grid(file)` returns a SET, and it has to.** 16 of the 7,618 shipped files
  are named by records that disagree about their grid (`a_hunt_ibex_idleA_x1` is claimed as
  both `(30,16)` and `(60,16)`). Pick one and you have made a silent guess.
- **The record's grid is an approximation of the file, not the file.** Against the real
  16-byte SLD header: 5,177 equal / 3,008 not / 9,174 no such file, typically off by 1–6
  frames. Fine for "do these two agree", wrong for "how many frames does this hold".
- Carry the **structured numbers** in the preview as well as the sentence
  (`plan()['grid_mismatches']`, `sprites[].grid_mismatches`), so a UI can draw a frame
  ruler without parsing prose.

## File layout (authoritative)

```
FILE HEADER (16 B)  <4s 2H 2H H
  sig 'SLDX' | version u16 (always 4) | num_frames u16
  | u1 u16 (0x0000 or 0x0010, semantics [U]) | frame_offset u16 | magic u16 (low byte 0xff)
  ★ frame_offset is 16 in 15,053 files and 14 in 431 — USE IT, never hardcode.
    It is a struct of 14 B, so when frame_offset == 16 there are 2 gap bytes.

FRAME HEADER (12 B)  <2H 2h 2B H
  canvas_w canvas_h (u16) | centre_x centre_y (i16) | frame_type u8 | unknown u8 | frame_index u16
  ★ unknown is a real flag: 4,846,644 frames = 0, 3,578 frames = 128 across 1,322 files.
    READ AND WRITE IT. Hardcoding 0 makes exactly those 1,322 files differ (at offset 25).
  ★ do NOT assume first frame has frame_index 0 (a first frame with idx=674 exists).

LAYER RECORD
  u32 size | (size-4) payload | pad
  ★ next_offset = off + ceil4(size)     # pad measured FROM THE SIZE FIELD
    NOT ceil4(off + size)               # that absolute-alignment rule fails 431 files
  ceil4(x) = x + ((4 - x % 4) % 4)

  main / shadow : 4×u16 rect | u16 fmt | u16 ncmd | ncmd×(u8 skip, u8 draw) | blocks
                  size == 16 + 2*ncmd + 8*sum(draw)
  playercolor   : u16 fmt | u16 ncmd | ncmd×(u8 skip, u8 draw) | blocks     ← NO rect
                  size ==  8 + 2*ncmd + 8*sum(draw)
  damage        : same layout as playercolor, and 66,620/66,620 verified
  unknown2      : see below

FRAME TYPE BITS  (real = 7 - openage's published bit)
  bit0 main | bit1 shadow | bit2 unknown2 | bit3 damage | bit4 playercolor
  Observed: 0x17 main+shadow+unknown2+playercolor (7,835 files)
            0x07 (3,230) | 0x1f all five (2,568) | 0x0f (1,131) | 0x00 no layers (535) | 0x02 (185)
```

## The one rule that makes rendering correct

**Blocks must be placed by the `skip/draw` command list, not poured in order.**
`sum(skip+draw)` is the **cell count** on the block grid; `sum(draw)` is the number of
**drawn** blocks. `bw = ceil(rect_w/4)`, `bh = ceil(rect_h/4)`; the command array is a
linear run list that wraps at width `bw`. Use `placed_blocks(cmds, bw, bh)` to get
`(cell_index, order_index)` and place the *order_index*-th block into that cell.

Symptom of getting this wrong: `comp == size` passes, everything looks self-consistent,
but the render is horizontal smears. **Self-consistency is not semantic correctness.**

## Player colour (team tinting)

`playercolor` is a **BC4 mask that indexes the main layer's grid 1:1** — decode it on the
main grid, not across the canvas. `fmt` decides where the command array comes from:
`0x0100` → same run-list as main; `0x0180` → carries its own.

Render: `f = mask/255`, then linearly blend the team colour over main by `f`.
Verified visually: the same knight frame tinted blue / red / green with all other pixels
unchanged (`_shots/sld_render/big_teamcolor.png`).

Player colours come from `resources/_common/palettes/spritecolors.json`
(`{TeamColors, OutlineColors}`, 9 entries each = Gaia + P1..P8). The three colour-blind
variants (`spritecolors_{deuteranopia,protanopia,tritanopia}.json`) use a **different value
style** (`HexColor.argb` like `"ff0000ff"`) while the main file uses `FloatRGBA`
(`{"r":0.0,...,"a":1.0}`) — **a parser must accept both.**

**Do not claim "player colour is a palette swap".** That community claim is falsified:
`palettes.conf` ids 64–71 (`// New Unit player colors`) all point at
`playercolor_black.pal`, a placeholder — if DE units resolved team colour through the
palette registry they would all render black. The real path is the BC4 mask above.

## Editing sprites safely

1. `s = read_sld(path)`, modify `layer.data` in place, `out = serialize_sld(s)`.
2. **Re-parse the output with the unmodified reader** and assert: frame count, all layer
   size invariants, and exact EOF. This catches any structural drift.
3. Measure the byte diff: it must be **confined to the blocks you edited**, with
   **size delta 0**. Anything else means you shifted structure.

**★ Enumerate real colours before choosing an edit threshold.** A recolour demo whose
predicate was `b > 90 and b-r > 40 and b-g > 40` matched **zero** blocks and produced a
byte-identical file — looking exactly like "the editor does nothing". The archer's real
tunic colour is `rgb(65,76,90)`. Run `_probe/u2_colours.py` first.

BC1/BC4 palettes: `c0 > c1` → 4 colours, else the 4th is transparent; BC4 with
`a0 > a1` → 8 values, else 6 + `0, 255`. The BC4 interpolation for the 8-value case is
`((6-i)*a0 + (i+1)*a1)//7` — **`(6-i)`, not `(7-i)`** (the latter overflows a byte).

Widths are all little-endian; `struct` format errors like `'B' format requires 0 <= number <= 255`
usually mean you did not mask a generator to the field width.

## `unknown2` — the honesty boundary

- 4,737,215 layers = **25.6% of all layers**. Always present when `main` is.
- Payload head is always literal `u32 == 5` (100%), followed by a strictly increasing u16
  run, then a variable tail.
- **Eight hypotheses tested and all refuted**: identical across a file's frames (no — 10,832
  files differ), shared across files (no — 94.3% of payloads unique), cumulative offset
  table (no — offsets overshoot the tail), zlib/deflate (no — 1.8% noise), K equals a
  geometric quantity (no — best fit is 43%).
- **It does not block anything.** The writer carries it as opaque bytes, which is *why* the
  15,484/15,484 round-trip holds. **"Cannot interpret" ≠ "cannot handle".**
- The tail's section-leading bytes look like BC1 endpoint bytes (`0xff`/`0x00`/`0x88`/`0xcc`),
  hinting at embedded block data — **unproven, mark [U].** Do not assert a layout.

## Palettes (JASC `.pal` / `.palx`)

`resources/_common/palettes/` holds 72 `.pal`/`.palx` + `palettes.conf` + 4
`spritecolors*.json`. Plain text, `JASC-PAL` (71 files) / `JASC-PALX` (1). `$ALPHA <n>` is
used by `.palx`. `//` and `#` are both comments. **Do not trust the declared colour count** —
`playercolor_artdesk.pal` declares 128 and holds 256. Count lines instead.

## Do not overclaim

- **No in-game verification exists.** Every result stops at the file layer. Frame count
  mismatch is known to play wrong frames silently, but whether it crashes or is rejected
  is unknown.
- **Zero of this machine's 9 installed mods ship any `.sld`/`.slp`/`.smp`** — the
  replacement path has community consensus and format derivation, but no local precedent.
- Audio is a separate problem: **all audio is packed** (39 `.pck`, 0 loose files), and the
  developers state only uncompressed PCM **UI** sounds work — **do not promise unit voice or
  music replacement.**
