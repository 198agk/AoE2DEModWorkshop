# AoE2DE Graphics / Sound Modding Survey

**Scope:** what a beginner-friendly mod-making tool must know about AoE2:DE graphics (sprites) and audio (sound).
**Environment:** game root `D:\Games\Steam\steamapps\common\AoE2DE`, version `101.103.54800.0`, Steam appid 813780, buildid 25464371.
**Method:** the game tree was read-only throughout; every script and output lives in
`D:\Software\DeepSeek Harness\工作区2\_probe\survey_gfx_snd\`.

**Evidence grades used throughout:**
- **[V]** = verified by my own inspection of real bytes/files on this machine.
- **[D]** = documented (openage format specs, shipped readmes/licenses, official JSON in the install).
- **[C]** = community claim (forum posts / guides), not independently verified.
- **[I]** = inferred / unverified.

---

## 1. Bottom line

**Sprites**

- **Viable, and the cheapest win in the whole project is a pure file rename.** Animated game sprites are loose, uncompressed `.sld` files in one flat directory. Copying a donor `.sld` into a mod folder under the *target* sprite's filename replaces that sprite — no format knowledge, no tool, no bit parsing. **[V]** for the file layout and naming; **[C]** for the override actually taking effect (a mod published this way, "Cataphracts to Savar Replacer", was reported working). The silent failure mode is a frame-count mismatch between donor and target, which produces frames played in the wrong order rather than an error.
- **Reuse-what:** 15,486 shipped `.sld` files (~36.7 GB) are themselves the content library. A tool never needs to author art for "make villagers look like X" — it needs an index of which sprite names belong to which unit/building, and `.sld` names are already human-legible (`u_all_ant_female_farmer_walkA_x1.sld`, `b_west_town_center_age3_x1.sld`). **Palette files are plain JASC text**, so "make villagers wear red" is editing one small text file, not writing a shader. **[V]**
- **Hardest blocker:** *authoring new art*. There is no shipped `.smx`/`.slx` at all (**zero files, whole tree [V]**), so every community guide that says "find the SMX in drs\graphics" needs a file that no longer exists. The only first-party path is `DESpriteTool.exe` (PSD → SLD), which ships with a readme that lists required PSD layer *names* and nothing else; multiple modders say the layer contract is unusable without reverse engineering. Second-hardest blocker: the SLD container's internal per-layer layout is only partly decoded — see §3 and §11.

**Sound**

- **Viable but narrow.** All audio is packed in 39 Wwise `AKPK` containers; **there is not a single loose `.wav`/`.wem`/`.bnk`/`.ogg` anywhere in the install [V]**. A mod overrides sounds by dropping files at a path *that does not exist on disk* — `resources\_common\drs\sounds\<Title_Case_Name>.wem` — which the engine fakes. **[C]** but consistent and corroborated by a developer.
- **Reuse-what:** the 53-entry `resources\_common\dat\sounds.json` **[V]** is the only plaintext sound-name table shipped, and its `name` values are exactly the mod-facing filenames that a "broken sound mods" thread independently lists (36-name break list). Event identity inside the packs is **FNV-1-32 of the lowercased name** **[V]** — a solid, reusable key.
- **Hardest blocker:** the format/caching split. A developer of the game states on the current build that bare `.wav` (uncompressed PCM, formatTag 1, 16- or 32-bit — *not* unsigned 8-bit) now works for **UI sounds only**; **unit/in-game sounds still require `.wem`** because they are preloaded/cached. Looped sounds do not loop. Residual vanilla sounds play even when a file is correctly overridden. Producing a `.wem` requires the Wwise authoring tool, which is not free. **[C]/[D]**

---

## 2. Sprite formats inventory

Whole-tree `Get-ChildItem -Recurse` over `D:\Games\Steam\steamapps\common\AoE2DE` **[V]**:

| Ext | Files | Bytes | Notes |
|---|---|---|---|
| `.sld` | 17,672 | 40,964,829,170 (~40.96 GB) | **the only shipped animated-sprite format** |
| `.slp` | 205 | 60,211,075 | legacy; all version `2.0N` |
| `.smp` | 38 | 5,212,882 | legacy; `SMP$`, version `0x00000100` |
| `.smx` | **0** | 0 | not shipped at all |
| `.slx` | **0** | 0 | not shipped at all |
| `.pal` | 89 | 590,615 | JASC text |
| `.palx` | 5 | 65,822 | JASC / JASC-PALX text |
| `.bina` | 134 | 610,194 | legacy UI archive members |
| `.dds` | 2,221 | 3,158,312,984 | textures/atlases/icons |
| `.png` | 9,626 | 3,057,990,650 | source art for atlases |

### `.sld` breakdown **[V]**

- Whole tree: **17,672**. Exactly **two are 0 bytes**: `resources\_common\drs\graphics\u_shp_merchant_ship_x1.sld` and `..._x2.sld` (signature reads `00 00 00 00`).
- **x1 = 8,836, x2 = 8,836, neither = 0** — a perfect 1:1 pairing. Every sprite has a UHD (x2) twin. *A tool that swaps a graphic must swap both files or UHD users get the old sprite.*
- Signature `SLDX` on 17,670 files; **version 4 on every single one**. No other SLD version observed.
- Real paths:
  - `resources\_common\drs\graphics\` — **15,486 `.sld` / 36,693.3 MB**, plus 38 `.smp` (~5 MB) and 35 legacy `.slp` (~19 MB); 15,559 files total, **no subdirectories**.
  - `modes\Pompeii\resources\_common\drs\graphics\` — **2,082 `.sld` / 2,362.3 MB**.
  - `resources\_common\drs\small-trees\` — **104 `.sld` / 11.6 MB**, all `n_tree_*` in strict `_x1`/`_x2` pairs.
- Size extremes **[V]**: smallest unit sprite `u_misc_relic_x1.sld` 21,244 B; largest `u_sie_palintonon_death_unpacked_x2.sld` **146,279,820 B**. x2 files are roughly 4× their x1 counterparts.
- Frame-count range: min 0, max **3,232 frames** in one file.

### `.slp` breakdown **[V]**

- Version `2.0N` on **all 205** files. Comment field: `ArtDesk 1.00 SLP Writer` on 190, `RGE RLE shape file` on 15.
- Lives in exactly one directory, `resources\_common\drs\` — 35 files there named `game_b1.slp` … `game_b35.slp` (519,660–630,872 B each), and 170 more under `drs\interface\`.

### `.smp` breakdown **[V]**

- Signature `SMP$` on all 38. Header fields: version `0x00000100`, `num_frames` 8–10, `num_animations` 1.
- All 38 are in `drs\graphics\`, all in `_x1`/`_x2` pairs: `BEXP3_NN`, `COBRA`, `ESFLAG0`, `flags`, `FLM1A_NN`..`FLM4B_NN`, `groupnum`, `GRPE2`, `MFLAG`, `MNG_FLM`, `MOVETO`, `RUGS`.
- Sizes: `COBRA.smp` 110,364 / `COBRA_x2.smp` 411,368; `ESFLAG0.smp` 17,380 / `_x2` 55,324. **`groupnum.smp` and `groupnum_x2.smp` are byte-identical** (2,945 B) — x2 is not always larger.

### Naming convention **[V]**, decoded from real listings

`<prefix>_<civ-or-all>_<class>_<name>_<animation>_<x1|x2>.sld`

Prefix histogram over all 17,672 `.sld` basenames: `b` 7,626 · `u` 5,892 · `a` 940 · `s` 586 · `n` 304 · `p` 138.
(`b_` = buildings, `u_` = units, `n_` = nature/resources, `a_` = animals/ambient, `s_`/`p_` = structures/particles/shadow families.)

Examples: `u_all_ant_female_builder_death_x1.sld`, `u_all_ant_female_farmer_walkA_x1.sld`, `b_archaic_dock_age1_rubble_x1.sld`, `n_tree_oak_x1.sld`.
Animation suffixes observed: `attackA/B`, `death`, `deathA`, `decay`, `decayA`, `idleA/B`, `walk`, `walkA`, `carrywalkA`, `taskA`, `seedA`, `packed`, `unpacked`, `destruction`, `underwater`.

---

## 3. Format structure

### 3.1 `.sld` (the one that matters) — **[V]** for what is listed, plus one open unknown

**File header — 16 bytes, `Struct("<4s 4H I")` [V]:**

| off | type | field | observed |
|---|---|---|---|
| 0 | 4s | signature | `SLDX` |
| 4 | u16 | version | `4` (all 17,670 valid files) |
| 6 | u16 | num_frames | |
| 8 | u16 | unknown1 | `0x0000` |
| 10 | u16 | unknown2 | `0x0010` |
| 12 | u32 | unknown3 | `0x000000FF` |

**Frame header — 12 bytes, `Struct("<4H 2B H")` [V]:**

| off | type | field |
|---|---|---|
| 16 | u16 | canvas_width |
| 18 | u16 | canvas_height |
| 20 | i16 | canvas_hotspot_x |
| 22 | i16 | canvas_hotspot_y |
| 24 | u8 | **frame_type** (layer bitfield) |
| 25 | u8 | unknown1 |
| 26 | u16 | frame_index (not a sequential ordinal — see below) |

Frames follow the file header back-to-back until every layer of every frame has been consumed.

**`frame_type` bit mapping — REVERSED relative to the openage spec [V].**

The openage doc (`doc/media/sld-files.md`, local copy `aoe2docs\openage_sld-files.md`) lists
main/shadow/`???`/damage/playercolor at bits **7/6/5/4/3**. Real files use bits **0/1/2/3/4**; bits 5–7 are never set in valid frames.

| bit | layer | layer header kind |
|---|---|---|
| 0 | main graphics | 16-byte offsets header + command array |
| 1 | shadow graphics | same as main |
| 2 | `unknown5` | **not the doc's layout — see below** |
| 3 | damage mask | 2-byte header |
| 4 | playercolor mask | 2-byte header |

Decode table in practice: `0x00` → no layers · `0x01` → [main] · `0x02` → [shadow] · `0x07` → [main,shadow,unknown5] · `0x0f` → [main,shadow,unknown5,damage] · `0x17` → [main,shadow,unknown5,playercolor] · `0x1f` → all five.

Evidence:
- First-frame `frame_type` histogram over 7,743 `*_x1.sld` in `drs\graphics\`: **`0x17` 3914, `0x07` 1612, `0x1f` 1281, `0x0f` 560, `0x00` 273, `0x02` 1**. 7,367/7,641 non-shadow files have bit 0 set.
- **The decisive test:** of 101 files whose basename contains `shadow`, the first frame is **`0x02` (bit 1 alone) in 90 cases**, and only 6/101 have bit 0 set. A shadow-only sprite therefore tests as bit 1 alone ⇒ **bit 1 is shadow**, ⇒ the doc's numbering is mirrored.
- The doc's own worked example corroborates the reversal: it says of `0x17 = 0b0001 0111`, "This frame would contain a *main graphic layer*, a *shadow layer*, a *??? layer* and a *player color mask layer*." Under the doc's own table that reading is impossible (bits 0–2 are "Unused" and bit 4 is damage); under the reversed numbering `0x17` = bits 0,1,2,4 = main + shadow + unknown5 + playercolor — **the doc's prose is right and its table is wrong.**

**Confirmed doc errors (documentation vs reality):**

| openage doc claim | reality **[V]** |
|---|---|
| unknown3 = `0xFF000000` | `0x000000FF` (endianness error in the doc) |
| "The main graphics layer always exists and is not optional" | frame_type `0x00` frames exist and contain **no layers at all** — proven by a 28-byte whole-file dump |
| frame_type bits 7..3 | bits 0..4 (see above) |
| every layer begins with `content_length` counting itself, padded to a multiple of 4 | **correct** — matches the 28-byte stub file exactly |
| `.pal` files use `r g b` lines | real `.pal` files are JASC text with **3 or 4** components per entry, and the declared entry count does not always match the line count |

**Whole-file ground truth used as the anchor [V]** — `resources\_common\drs\graphics\b_archaic_dock_age1_rubble_x1.sld`, 28 bytes, entire file:
```
53 4c 44 58 | 04 00 | 01 00 | 00 00 | 10 00 | ff 00 00 00
58 02 58 02 2c 01 2c 01 00 80 00 00
```
= `SLDX`, version 4, num_frames 1, frame header canvas 600×600, hotspot (300,300), `frame_type 0x00`, unknown1 `0x80`, frame_index 0 — and then end of file. This proves the 12-byte frame header and the empty-frame case in one shot.

**Main/shadow graphics layer [V]** — begins immediately after the frame header:
```
u32 content_length          (counts itself)
u16 offset_x1, offset_y1, offset_x2, offset_y2
u8  flag1, u8 unknown1
u16 command_array_length
   command_array_length × { u8 skipped_blocks, u8 draw_blocks }
   (total draw_blocks) × 8-byte BC1 (main) / BC4 (shadow) block
```
Layout constants verified against real bytes (`u_arc_bowman_death_x1.sld`, `n_tree_oak_x1.sld`): `width = offset_x2 - offset_x1`, `height = offset_y2 - offset_y1`; **`command_array_length` sits at layer offset +14, commands at +16**; the strong checksum `layer_offset + content_length == layer_offset + 16 + 2*ncmd + 8*sum(draw)` holds. Content is 4×4-block interleaved; main = BC1/DXT1, shadow = BC4/DXT4 grayscale, exactly as documented.

Worked example [V] — `u_arc_bowman_death_x1.sld`, 751,264 B, num_frames 481; frame 0 = canvas 200×200, hotspot (100,100), `frame_type 0x17`; first layer `content_length` 396, offsets 92/64/128/108 → 36×44, flag1 0x00, unknown1 0x01, `command_array_length` 14.

**KNOWN UNRESOLVED: the bit-2 (`unknown5`) layer layout.** The doc gives it no format at all ("`???` = `???`"). Empirically, walking it as a 16-byte graphics layer, as a bare 2-byte mask, or ignoring it entirely all produce the same result: the walk fails partway through rich frames. With the bit mapping fixed and the `ncmd` offset fixed, a 120-file sample yields only 2–4 exact-EOF walks; failures land deep in the file (`fail@ft=0f@1322`, `fail@ft=07@6278`, `fail@ft=17@2558`) and four near-misses are **exactly 2 bytes short** (`end=18542 filelen=18544`), the signature of a header field counted or omitted by 2. Hex inspection of the bit-2 layer start shows an unexpected structure: `u32 content_length` then a 4-byte value that is **`05 00 00 00` in every file examined**, followed by a run of **ascending `u16` left/right pairs** (e.g. `(13,44) (73,109) (151,195) (233,256)` in `n_mine_gold_33_x1.sld`) — an outline-table-like construct that the SLD doc does not mention at all, and that SLP/SMP/SMX have but SLD was documented as not having.

Also unexplained: a small number of files (5/120 in one sample, 4/300 in another) present a first-frame `frame_type` with **high bits set** (`0x50`, `0x32`, `0x86`, `0x72`) — possibly a different SLD sub-version or a non-sprite SLD. Sample: `p_mounted_trebuchet_shadow_x1.sld` (`ft=0x32`).

Reproduction recipe: `_probe\survey_gfx_snd\sld_final.py` (exact-EOF walker, reversed bits) and `sld_bit2.py` (six competing interpretations of bit 2), plus `sld_bit2_hyp.py` (enumerates candidate layer sizes and tests whether the next 12 bytes look like a plausible frame header — canvas 1..4096, hotspot inside canvas, `frame_type ≤ 0x1f`).

### 3.2 `.slp` (legacy) — **[D]**, spot-checked **[V]**

`Struct("< 4s i 24s")` = version[4], int32 num_frames, comment[24]. Version `2.0N` = AoE1 1997 / AoE2 1999 / SWGB / AoE2HD. Versions `3.0`/`4.0X`/`4.1X`/`4.2P` are AoE1:DE only; `4.2P` is an LZ4 container. Frame info `Struct("< I I I I i i i i")` = cmd_table_offset, outline_table_offset, palette_offset, properties, width, height, hotspot_x, hotspot_y. Outline table = per row `Struct("< H H")` (left_space, right_space; `0x8000` = fully transparent row). Draw commands are keyed on the low 4 bits of a command byte and include lesser/greater draw, skip, player-color draw, fill, shadow draw, plus extended commands (outline, dither, premultiplied alpha, 32-bit BGRA). Pixel width is 1 byte up to version 4.0, 2 bytes from 4.1 (display modifier + palette index), 4 bytes BGRA for 32-bit.

**[V]** Frame info decodes cleanly on a real file — `game_b1.slp` (557,705 B, 8 frames, comment `ArtDesk 1.00 SLP Writer`): frame 0 cmd_off 416, outline_off 288, width 32, height 32; frame 1 cmd_off 5404, outline_off 4704, width 325, height 175.
**[V] caveat:** the `properties` field is **not a reliable palette id** — it decodes as `7` on `game_b1.slp` but as `1278803831` on `game_b10.slp`. Treat "SLP palette id lives in `properties`" as doc-only, not verified.
**[D]** Palettes are separate JASC files (`JASC-PAL` / `0100` / count / rows), historically stored in `interfac.drs` under id `50500+x`.

### 3.3 `.smp` / `.smx` (legacy, not shipped)

**[D]** SMP signature `SMP$`, header `Struct("< 4s 7I 32s")` = signature, version `0x00000100`, num_frames, num_animations, frames_per_animation, checksum, file_size, source_format (`0x0B` = SLP, `0x0C` = PSD — i.e. the official `DEAssetTool.exe` input), comment[32]; then per-frame u32 offsets; frame header = 28 unused bytes + u32 layer count; layer header `Struct("< 8I")` = width, height, hotspot_x, hotspot_y, layer_type (`0x02` main, `0x04` shadow, `0x08` outline, `0x10` source-format-0x0B outline), outline_table_offset, cmd_table_offset, flags (offsets relative to the frame offset). Row edges use `0xFFFF` (SLP used `0x8000`). Only four commands keyed on the low 2 bits: skip `00`, draw `01`, playercolor draw `10`, end-of-row `11`, each covering `(cmd_byte >> 2) + 1` pixels. Pixel = `Struct("< B B H")` = px_index, px_palette, px_damage_modifier; `palette_index = px_palette >> 2`, `palette_section = px_palette & 0b11`, `color_index = px_index + 256 * palette_section`, `damage_modifier = (px_damage_modifier >> 4) & 0x01FF`, and the doc supplies a full Python `calculate_rgb_multiplier(damage_modifier, current_damage_percent)` clamping a sigmoid to [0, 0.65].

**[D]** SMX signature `SMPX`, header `Struct("< 4s 2H 2I 16s")` = file_descriptor, version, num_frames, file_size_comp, file_size_uncomp, comment[16]. Up to 3 layers (main/shadow/outline); frame header `Struct("< 2B I")` = frame_type, palette_number, uncomp_size. Two 5-byte-chunk compression methods: "4plus1" (4 palette-index bytes + a bitfield byte of four 2-bit palette sections) and "8to5" (2 pixels via a `0xFF03F03F` bitmask). The doc itself says DE uses SLD instead and SMX was Beta-only — **which matches the zero `.smx` files found on disk [V]**.

### 3.4 Palettes — **[V]**, and much more beginner-relevant than expected

**Player color is a palette swap, not a shader.** `resources\_common\palettes\` contains one small text file per color: `playercolor_red.pal` 2,311 B, `playercolor_blue.pal` 2,315, `playercolor_green.pal` 2,335, `playercolor_yellow.pal` 2,450, `playercolor_orange.pal` 2,419, `playercolor_teal.pal` 2,512, `playercolor_purple.pal` 2,433, `playercolor_grey.pal` 2,428, `playercolor_white.pal` 2,545, `playercolor_black.pal` 1,250, `playercolor_brown.pal` 2,351 — each with a full colorblind twin under `deuteranopia\`, `protanopia\`, `tritanopia\` (tritanopia additionally has `playercolor_pink.pal`).

Civilization/building palettes, all JASC text: `b_afri.pal` 15,746 · `b_asia.pal` 15,757 · `b_ceas.pal` 15,769 · `b_dark.pal` 15,474 · `b_east.pal` 15,750 · `b_indi.pal` 15,718 · `b_medi.pal` 15,619 · `b_meso.pal` 15,735 · `b_orie.pal` 15,725 · `b_scen.pal` 15,637 · `b_seas.pal` 15,773 · `b_slav.pal` 15,584 · `b_west.pal` 15,696 · `n_cliffs.pal` 15,769 · `n_trees.pal` 15,615.

File-format reality — **the JASC family is not uniform** **[V]**:
- `playercolor_red.pal` = `JASC-PAL` / `0100` / `256`, then **RGB** triples `255 0 0`, `238 0 0`, `221 0 0`, …
- `b_dark.pal` = `JASC-PAL` / `0100` / `1024`, then **RGBA** quads `254 254 242 255`, …
- `playercolor_artdesk.pal` declares `128` in its header but has 260 entries — **declared count ≠ actual line count**.
- `n_alpha_ground.palx` = `JASC-PAL` / `0100` / `1024`, then a `$ALPHA 192` **directive line**, then RGBA quads.
- `modulation_colors.palx` uses a **different magic literal**: `JASC-PALX`, with `#` comment lines and RGBA quads.

`palettes.conf` (1,328 B) is the **palette-id → file map** **[V]**, and confirms the SMP doc's claim that palettes are indexed by id:
```
0,original.pal  1,clf_pal.pal  2,pal_2.pal  3,pal_3.pal  4,pal_4.pal  5,pal_5.pal  6,pal_6.pal
16,b_dark.pal  17,b_orie.pal  18,b_seas.pal  19,b_ceas.pal  20,b_east.pal  21,b_west.pal
22,b_asia.pal  23,b_meso.pal  24,b_slav.pal  25,b_afri.pal  26,b_indi.pal  27,b_medi.pal
28,b_scen.pal  29,b_scen.pal  30,n_trees.pal  31,n_trees.pal
32,n_alpha_ground.palx  33,n_alpha_underwater.palx  40,n_cliffs.pal  41,effects_2.pal  42,b_scen.pal
50,playercolor_white.pal // Gaia player color
51/52/53,playercolor_black.pal // TEMP placeholders
54,effects.pal // SFX Fire
55..62,playercolor_{blue,red,green,yellow,orange,teal,purple,grey}.pal // Legacy Unit player colors
63,modulation_colors.palx // modulation palette
64..71,playercolor_black.pal // New Unit player colors (placeholder block)
```
The official build pipeline documents the same palette names as *inputs*: `Tools_Builds\Sprites\settings.json` sets `"DiffusePalette": "_palettes\\b_dark.pal"` and `"PlayerColorPalette": "_palettes\\playercolor_default.pal"` **[D]**.

**There are two parallel color systems [V]:** the indexed `.pal` files above, and `resources\_common\palettes\spritecolors.json` (1,554 B), which defines `{"TeamColors":{...},"OutlineColors":{...}}` as **float RGBA** per player — Player 1 blue `(0,0,1)`, Player 2 red `(1,0,0)`, Player 3 green `(0,0.663,0.106)`, Player 4 yellow `(0.839,0.839,0.106)`, Player 5 cyan `(0.482,0.937,0.941)`, Player 6 purple `(0.541,0.075,0.969)`, Player 7 grey `(0.4,0.4,0.4)`, Player 8 orange `(1,0.573,0.02)`. An editor that changes a team color must keep both in step or a unit's fill and outline will disagree.
**[C]** corroboration that more colors exist than the UI exposes: SLX Studio offers "an additional 4 team colors that you don't have access to: brown, light blue, gold and pink" — and indeed `playercolor_brown.pal` ships while palette ids 64–71 are blanked.

### 3.5 Where the *other* textures live

**[V]** `.dds` (2,221 files, ~3.16 GB) and `.png` (9,626 files, ~3.06 GB) cover UI atlases, icons, terrain and cursor art:
- `widgetui\textures\` ≈ 7,840 files: 5,977 `.png`, 1,655 `.dds`, 206 `.jpg`.
- Unit icons in `widgetui\textures\ingame\units\`: 794 files, all 256×256, split between uncompressed 32bpp `A8R8G8B8`/BGRA with mip=1 (539) and DXT5 (245).
- UI atlases: BC7_UNORM (DX10 header, DXGI format 98) for UHD/HD, DXT5/BC3 for SD, all `dwMipMapCount = 1`.
- Terrain `resources\_common\terrain\textures\2x\*.dds`: `g_grs.dds` is 2048×2048 DXT1 with mip=3.
- Official DDS tooling ships: `Tools_Builds\texconv.exe` (660,480 B) and `texassemble.exe` (263,168 B).
- **[C]** icon recipe matches my own findings — "Uncompressed A8R8G8B8 (32-bit) … the image must be 256 × 256".

---

## 4. Where sprites live

**[V]** `D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\` contains exactly four directories and two files:

```
resources\_common\drs\
├── graphics\            15,486 .sld (~36.7 GB) + 38 .smp + 35 .slp   ← ALL animated game sprites, FLAT, no subdirs
├── small-trees\            104 .sld (11.6 MB)   all n_tree_* _x1/_x2 pairs
├── interface\              170 .slp + 134 .bina  legacy UI graphics
├── gamedata_x2\            RMS/AI only (.rms, .rms2, .inc, .per, .per2, .ai, .scx, random_map.def) — no graphics
├── graphics_x1.txt      UTF-8-BOM, 6 lines: human-readable category list
└── graphics_x2.txt      UTF-8-BOM, 22 lines: human-readable category list
```

`graphics_x1.txt` reads "Buildings / More Buildings / Civilians and Eye Candy / Infantry, Archers, Camels, Elephants / Horse Cavalry / Other Military Units and Ships". `graphics_x2.txt` reads "Dark Age Buildings / Scenario Buildings / Western European Buildings / Central European Buildings / Eastern European Buildings / Southern European Buildings / African Buildings / Middle Eastern Buildings / Southeastern Asian Buildings / Eastern Asian Buildings / Indian Buildings / Central Asian Buildings". **These are category labels, not file indexes** — there is no shipped sprite index anywhere.

`modes\Pompeii\resources\_common\drs\graphics\` adds 2,082 more `.sld` (2.36 GB) for the Pompeii DLC. That is where the 17,672 whole-tree total comes from (15,486 + 2,082 + 104).

**There is no packed archive and no graphics section in the `.dat` that matters for sprites [V].** The Genie data file `resources\_common\dat\empires2_x2_p1.dat` (12,023,754 B, raw-deflate, decompressing to 93,268,152 B, header `VER 8.9`) references graphics by *name*, and the engine resolves that name to a file in `drs\graphics\` by convention. Community confirmation **[C]**: "The Definitive Edition does not use DRS files, so the SLP number does not matter."

**`resources\_common\slp\slp.txt` is a 63-byte placeholder** (one line, no content) — there is no shipped SLP index. `resources\_common\dat\` is the real data home.

Also **[V]**: `resources\_packages\` is **empty**; `Docs\` ships only EULA/legal PDFs and legacy AoK/TC manuals — **no sprite or audio authoring documentation ships there**.

---

## 5. Sprite intent mapping

| Beginner intent | Concrete file/format involved | Difficulty |
|---|---|---|
| **Make villagers (or any unit) wear red** | Player color is per-player, not per-unit. Realistic beginner framing: "make my units this color" = edit `resources\_common\palettes\playercolor_*.pal` (JASC text, RGB triples) and keep `spritecolors.json` in step. | **Trivial** for a recolor; **requires a data mod** to make it civ-specific rather than player-specific **[C]** |
| **Recolor a specific unit / civ** | Edit the civ's palette `b_*.pal` (JASC text, 1024 RGBA entries) — see `palettes.conf` for the id map. Affects every sprite drawn with that palette. | **Easy** |
| **Change tree to smaller (small trees)** | Already shipped as a resource: `resources\_common\drs\small-trees\` (104 `n_tree_*.sld`). Rename-to-replace those names. | **Trivial** (rename), **medium** to generate new sizes |
| **Resize a building** | Its `b_*_x1.sld` + `b_*_x2.sld` (must be rescaled as a pair; x2 is ~4× x1). Community path uses SMX + SLX Studio's "Resize Graphic Scale", which needs art that is no longer shipped. | **Hard** — tooling is aimed at a format the game no longer ships |
| **Swap a unit's appearance for another unit's** | Copy donor `u_*_<anim>_x1.sld` + `_x2.sld` into the mod folder under the target's filenames, for every animation. Published, working example ("Cataphracts to Savar Replacer"). | **Trivial to implement, silently fragile** — frame counts must match or animations combine wrong frames **[C]**; needs a per-unit animation list |
| **Make a unit civ-specific (regional skins)** | Requires repointing graphics in `empires2_x2_p1.dat` (AGE). | **Hard** — data mod, must be selected before each game, cannot be combined freely **[C]** |
| **Replace a portrait / icon** | `widgetui\textures\ingame\units\*.dds`, 256×256, uncompressed A8R8G8B8 32-bit or DXT5. Tooling ships (`texconv.exe`); PNG sources also ship. | **Easy** |
| **Replace UI / emblems** | `widgetui\textures\ingame\emblems\*.png` etc. A subscribed mod on this machine does exactly this (600 `.png`). | **Trivial** |
| **Author genuinely new animated art** | PSD layer stack → `DESpriteTool.exe` → `.sld`. | **Hard** — undocumented CLI, layer contract reverse-engineered |

**The strategic conclusion for the tool:** the two highest-value, lowest-risk sprite features are (a) a **name-level swap** driven by an index that maps "Cataphract" → its `.sld` filenames, and (b) **palette editing**. Neither requires parsing the SLD container at all. Everything that requires *editing inside* an SLD is currently expensive.

---

## 6. Sprite tooling

### First-party (ships with the game) — **[V]** for presence and licensing, **[D]** for the readmes

| Tool | Path / size | Purpose | Read/Write | Licence |
|---|---|---|---|---|
| **DESpriteTool.exe** | `Tools_Builds\Sprites\DESpriteTool.exe` 1,038,336 B | **SLP and PSD → SMP/SMX/SLD** | write only (authoring) | shipped with game; not open source |
| `convert_psd.bat` / `convert_slp.bat` | `Tools_Builds\Sprites\` (101 / 69 B) | batch entry points: `start DESpriteTool.exe "buildings"` etc.; `DESpriteTool.exe "slp"` then `-compress "slp\*.smp"` | — | — |
| **ArtDesk.exe** | `Tools_Builds\ArtDesk.exe` 4,523,008 B | legacy SLP authoring — **the same `ArtDesk 1.00 SLP Writer` that wrote the comment on 190 of the 205 shipped `.slp` files** | read/write (legacy) | shipped with game |
| **Advanced Genie Editor 3** | `Tools_Builds\AdvancedGenieEditor3.exe` 10,115,072 B | edits `empires2_x2_p1.dat`: unit stats, **and graphic repointing** | read/write `.dat` | **GPLv3**, source `Tools_Builds\docs\Source.7z`, latest https://github.com/Tapsa/AGE |
| **texconv.exe / texassemble.exe** | `Tools_Builds\` 660,480 / 263,168 B | DDS conversion | read/write | shipped with game |
| Palettes | `Tools_Builds\Sprites\_palettes\` `b_dark.pal` 15,474 · `b_scen.pal` 15,637 · `n_trees.pal` 15,615 · `playercolor_default.pal` 2,309 | conversion inputs | — | — |

`Tools_Builds\docs\AGE_ReadMe.txt` **[D]** confirms GPLv3 and adds an independent confirmation of the sprite compression story: "**`lz4` is used for decompressing some sprites.**" It also notes "`SFML` is used for simultaneous audio playback."

**DESpriteTool's PSD contract [D], verbatim from `Tools_Builds\Sprites\readme.txt`:**
> "Under one of the needed folders (buildings / nature / units), create a subfolder consisting of your PSD frames in filename_0000.psd format. … Each PSD requires the following layers: - Damage (for nature/buildings, clipping mask of Diffuse) OR Blood (for units, clipping mask of Diffuse) - AmbientOcclusion (clipping mask of Diffuse) - Diffuse (main layer, masked with white-on-black bitmap) - Decal - Background - Height - Normals."

Per-category defaults that reveal the real graphics model **[V]** — `settings.json` (root) sets `"DiffusePalette":"_palettes\\b_dark.pal"`, `"PlayerColorPalette":"_palettes\\playercolor_default.pal"`, `"PSDPaletteNumber":16`, `"GenerateX1Assets":true`, `"Damage":{"Type":"On","Strength":0.65}`, `"FacetCount":1`, `"Compress":true`, `"DeleteSMP":true`, `"PalettePath":"..\\..\\resources\\_common\\palettes"`. Overrides: `units\settings.json` = `{"DiffusePalette":"_palettes\\b_scen.pal","PSDPaletteNumber":28,"GenerateOutlines":true,"FacetCount":16,"Damage":{"Type":"Off"}}`; `nature\settings.json` = `{"DiffusePalette":"_palettes\\n_trees.pal","PSDPaletteNumber":30,"DisablePlayerColor":true,"Damage":{"Type":"Off"}}`; `buildings\settings.json` = `{"Damage":{"Type":"On"}}`.
⇒ **units = playercolor + outlines + 16 facets (directions), no damage; nature = no playercolor, no damage; buildings = damage on.**

**Beginner-hostility of DESpriteTool is documented and blunt [C]:** "How is anyone supposed to use this DE sprite tool? The templates were shared for both units and buildings a while back, but there is no documentation on how to set up the export functions from software like blender. Also there is no explanation for how modders can utilize the various layers like decal. **There needs to be a readme for the readme.**" and "DESpriteTool.exe is a command line tool … it's a bit more technical to do sadly." **[C]** The PSD layer semantics were reverse-engineered by the community: shadows = decal layer + white-on-black mask on diffuse; main = diffuse + AmbientOcclusion split mask; **Height and Normals appear inert** ("when replacing the entire Normal Layer with transparency there seems to be no difference in the output file hex data"); **player-color → PSD layer mapping remains unresolved** ("As for player color, I have no clue"). A working sample `unit_template_0000.psd` circulates at `https://drive.google.com/file/d/1CAgHVHgT88p8aKRRG6shsLkjSdtpdwYI/view` (a building template existed but is lost).

### Community / third-party

| Tool | Author | URL | Format support | Maintenance |
|---|---|---|---|---|
| **SLX Studio** | Tevious | https://aok.heavengames.com/blacksmith/showfile.php (thread `https://aok.heavengames.com/cgi-bin/forums/display.cgi?f=9,44685,,60`); Discord `https://discord.gg/FDdHx9g6`, `https://discord.com/invite/5Jrk4cfDev`, `https://discord.com/invite/3jXRgwZkp` | SLP, **SMP/SMX read+write**; **does not support SLD** | **Stalled [C]**: "SLX studio can update the Frame counts … but doesn't currently support SLD format"; "waiting for Tevious to update SLX Studio … no idea how long"; only works with pre-SLD backup files. Licence unverified (freeware) |
| **SMX Workshop** | WAIFor | https://aok.heavengames.com/blacksmith/showfile.php?fileid=13410 (Beta 1.9.2) | SMP/SMX only | Low activity; SLD not supported. Licence unverified |
| **SLD Extractor** | — | https://aok.heavengames.com/blacksmith/showfile.php?fileid=13852 ; online variant https://ageofnotes.com/sld-extractor-online-aoe2/ | **SLD → SLX, one-way only**: "you can't convert edited SLX files into SLD … You can convert SLD into SLX using this program" | Unknown. Reported gap: "The 'Sld Extractor' couldn't **export the unit color mask**" — exactly the playercolor mask from §3, consistent with the unresolved bit-2/mask layout |
| **Turtle Pack** | — | not found | named as a beginner sprite tool | **No download URL located**; repeatedly named as a tool that *doesn't exist* in SLD form ("no Turtle Pack or SLX Studio equivalent atm") |
| **genieutils-py** | hszemi | https://github.com/SiegeEngineers/genieutils-py | read+write `empires2_x2_p1.dat`; ships `dat-to-json` | Active. Licence unverified (GitHub unreachable) |
| **GenieDatParser** | Alian713 | https://github.com/Divy1211/GenieDatParser | read+write `.dat` | Licence unverified |
| **IrfanView** | Irfan Skiljan | — | batch image resize (external resizing changes output sizes) | freeware for non-commercial use |
| **TexConvGUI** | — | — | DDS conversion UI over `texconv` | unknown |
| **Blender + GIMP/Photoshop/Substance Painter** | — | — | the actual art pipeline feeding DESpriteTool or SLX Studio | n/a |
| **Yorok0's SLD program** | Yorok0 | not published | **SLD read+edit — the one independent working SLD tool found.** "I have created a special program for changing decay graphics files. I switched this program to SLD format **based on this documentation** — https://github.com/SFTtech/openage/blob/master/doc/media/sld-files.md" | private |

**Two lessons from this table.** (1) The openage SLD doc is *sufficient to build a working SLD tool* — one hobbyist did exactly that — so a from-scratch reader is feasible. (2) But the proven-tractable operation is narrow: "I just **duplicated and removed frames from existing SLD files**, which is much easier to do than **encode/decode images to/from SLD**." Frame duplication/removal is the realistic programmatic feature; pixel resampling is not.

**Tool-availability caveat:** `web_search` is unavailable in this session (no API key), GitHub and Steam Community are unreachable, and only `forums.ageofempires.com` responds. **Licences and exact maintenance status for every third-party tool above are therefore unverified** and are marked as such.

---

## 7. Sound: storage location and format

### Structure — **[V]**

```
D:\Games\Steam\steamapps\common\AoE2DE\wwise\
├── 13 × .pck      root         total ~2.04 GB   (SFX / effects)
├── en\  13 × .pck total ~657.9 MB                (localized VO + music)
└── zh\  13 × .pck total ~633.6 MB
```
Only `en` and `zh` audio directories exist, despite 16 language directories under `resources\`.

| Pack | root | `en\` | `zh\` |
|---|---|---|---|
| `Base.1.pck` | 733,879,405 | 205,106,290 | 198,450,412 |
| `Base.pck` | 292,260,719 | 24,415,107 | 24,084,102 |
| `DLC1.pck` | 86,967,703 | 36,457,456 | 35,023,364 |
| `DLC2.pck` | 95,434,077 | 39,873,331 | 36,714,792 |
| `DLC3.pck` | 75,999,464 | 33,369,853 | 32,084,513 |
| `DLC4.pck` | 79,229,841 | 36,958,040 | 31,066,765 |
| `DLC6.pck` | 133,935,892 | 60,324,515 | 60,918,783 |
| `DLC7.pck` | 92,243,811 | 35,889,653 | 34,165,748 |
| `DLCParis.pck` | 77,000,578 | 34,511,949 | 33,348,798 |
| `DLCPortland.pck` | 99,767,984 | 43,025,877 | 41,463,492 |
| `DLCProvidence.pck` | 151,300,561 | 48,715,070 | 49,085,274 |
| `DLCVV.pck` | 71,690,542 | 54,018,269 | 51,925,570 |
| `Pompeii.pck` | 230,777,676 | 37,157,493 | 36,052,160 |

**No loose audio exists [V].** A recursive count for `*.wav`, `*.wem`, `*.bnk`, `*.ogg`, `*.mp3`, `*.xma`, `*.wma` across the entire game root returned **0 for every extension**. All audio is inside the `.pck` containers. There is also **no directory** matching `sound|audio|music|stream` anywhere under `resources\` [V] — the paths sound mods use do not exist on disk.

### Container format — **[V]**

- All **39** `.pck` files (13 root + 13 `en` + 13 `zh`) begin with ASCII **`AKPK`** — a standard Wwise bank container, not a bespoke format. Header size (`u32@4`) varies 1,032–53,088.
- Each `.pck` contains exactly **one** UTF-16LE bank-name string: `"sfx"`.
- `wwise\Base.pck` (292,260,719 B) contains standard Wwise bank structures: `RIFF` × 6,902, `WAVE` × 6,902, `fmt ` × 6,902, plus `BKHD` (bank header), `DIDX` (data index), `DATA`, `HIRC` (object hierarchy), `STMG`, `ENVS`, `INIT`. First `WAVEfmt ` at offset 0x13308.
- **Gotcha for any parser [V]:** the first `RIFF` in the file is at offset 0 but is **not** a WEM — it is the AKPK header itself. A naive "scan for RIFF" reader is wrong here.
- `vorb`/`Vorb` literal = **0 occurrences** in the first 200 MB, so codec identification cannot be done by searching for Vorbis magic text.

### Where sound *names* come from — the reconciliation

Three name spaces exist. This is the answer to "which is authoritative":

1. **`AoE2DE.dat` (4,094,807 B) — a decoy. [V]** Fully encrypted/opaque: entropy 7.999 bits/byte on *every* 256 KB block, zero readable runs, `.wav` count 0, no zlib/deflate header. It holds no usable strings and is **not** the Genie data file.
2. **`resources\_common\dat\empires2_x2_p1.dat` — the real Genie data. [V]** 12,023,754 B, **raw-deflate (zlib `wbits=-15`)**, decompressing to **93,268,152 B**, header `VER 8.9`. Inside it, `.wav` appears 4,416 times and there are **2,149 distinct `.wav`-terminated strings** (`BLAC.wav`, `BRKS.wav`, `CRCH.wav`, `CSTL.wav`, `DOCK.wav`, `FARM.wav`, `MILL.wav`, `MRKT.wav`, `eleat1.wav`, `MANGO.wav`, `wind1.wav`, `cricket.wav`, `wave1..5.wav`, …). These are **legacy logical `.wav` names, not files** — nothing on disk matches them.
3. **`resources\_common\dat\sounds.json` (4,881 B) — the only plaintext sound-event table shipped. [V]** Structure `{"sound_list":[{"key","name"}]}` with **53 entries** mapping a UI/notification key to a Wwise event name: `button_select`→`Play_Button_Select`, `button_ui`→`Play_Button_UI`, `civ_jingle`→`Play_Civilization_Jingle`, `age_up`→`Play_Age_Up`, `under_attack`→`Play_Under_Attack`, `townbell_start`→`Play_Townbell_Start`, `trumpet`→`Play_Salpinx_Trumpet_Signal`, `atheism`→`Play_Huns_Mockery`, `crusades`→`Play_The_Crusades`.

**Authoritative answer: `sounds.json` (plus the community *AoE2 DE Audio Spreadsheet*) is authoritative for what a modder must name a file; the Genie `.dat`'s 2,149 `.wav` strings are the engine's internal logical names; the `.pck` banks are authoritative for what actually plays.** A whole-tree scan of 34,735 files for the literal strings `Play_Button_Select`, `Play_Attack`, `BLAC.wav`, `Play_Civilization_Jingle` found matches **only in `sounds.json`** [V] — no other shipped file exposes these names.

**Event identity inside the packs is FNV-1-32 of the lowercased name [V].** Tested against `wwise\Base.pck`: `fnv1a`-style exact-case produced **0 hits** for all four names; **FNV-1 (no final XOR, multiply = 0x01000193) over the lowercased ASCII name produced hits for all four** (`Play_Button_Select` → `0x7946f0c9`, `Play_Button_UI` → `0x60896e13`, `Play_Error` → `0xa1c180e0`, `Play_Victory` → `0x9239e360`). This is a reusable key for any tool that needs to locate a sound inside a bank.

**Important negative result [V]:** a full reconciliation of all 53 event names and 200 `.wav` names against the packs gave **no usable signal** — 5/53 event names matched versus **5/53 for a random-32-bit control**, and 15/200 `.wav` names matched versus **11/200 for random**. With 4-byte hashes in a 260 MB buffer, `bytes.count(pack("<I", h)) > 0` has a ~5 % false-positive floor. **Those matches must not be reported as mappings.** Only the four names validated against an exact-case negative control are trustworthy.

**Design consequence:** a beginner tool cannot reliably say "this .wem inside the pack is the villager voice line" by hash alone. It must work from the *name* the engine expects (the `sounds.json` / spreadsheet names) and treat the pack as a black box.

---

## 8. Sound: mod replaceability

### The mechanism

**[C]** but consistent across many independent posts and corroborated by a game developer:

- A mod places files at `...\mods\local\<ModName>\resources\_common\drs\sounds\<Name>.wem`. **This directory does not exist in the shipped install** — "The above directories don't exist. Yet, when you mod DE audio, you have to point to the above paths, pretending that they exist. Makes no sense, but it works." Same for `resources\_common\sound\stream` (also absent on disk, verified).
- **Filenames are Title_Case and case is load-bearing [C]:** "the filenames in the AoE2 DE Audio Spreadsheet has typos. It lists certain sounds as lowercase when they need to be uppercase. The following need to be uppercase: **Notification.wem, Chat_Received.wem, Chat_Received_2.wem**."
- **The 36-name break list** from the 2025-04 "Sound mods broken since last patch" thread is the single most practical artifact found — these are the names whose override produced **silence** after update 141935, when `resources/_common/drs/sounds` disappeared: `Age_Up, Animal_Attack, Animal_Discovered, Button_GFX, Button_Select, Button_UI, Capture_Broken, Capture_Everything, Chat_Received, Chat_Received_2, Error, Farm_Depleted, Flare, Gate_Close, Gate_Open, Gatherpoint_Set, Market_Buy, Market_Sell, Monk_Attacking, Monk_Convert_Complete, Notification, Objective_Changed, Opponent_Found, Player_Eliminated, Population_Capped, Relic_Pickup, Spy_infiltration, Technology_Researched, Town_Under_Attack, Townbell_Start, Townbell_Stop, Tribute, Under_Attack, Wonder_Completed, Wonder_Destroyed, Wonder_Started` — all `.wem`. **This list corresponds almost 1:1 with the 53 `name` values in `sounds.json` [V]**, which is strong independent corroboration that `sounds.json` names are the mod-facing filenames.

### Current-build format rules (developer statement)

From thread 289884, ".wav files still do not work for audio modding", on **build 101.103.54800.0 — the exact build surveyed**:

- Developer (Forgotten Empires): *"I am unable to reproduce the issue. Did you make sure to restart the game / refresh local mods between attempts? Also, please keep in mind that **only formatTag 1 (uncompressed PCM) is supported with this. You cannot use any other non-Wwise formats.**"* — and links a working test mod.
- Reporter follow-up: *"it has to be **16-bit PCM**, otherwise (eg. with 32-bit PCM) it won't work"*, then amended: *"ok **32-bit PCM works as well, but (unsigned) 8-bit PCM doesn't**"*.
- Reporter: *"the **button_select** updates correctly, but **unit sounds (scoutm, scoutm1, scoutm3) do not** — but it is the same exact identical file only renamed… I did confirm that scoutm, scoutm1, scoutm3 work correctly to mod using **.wem**"*.
- Developer final: *"Thanks, I will forward this for investigation. **I suspect it might have to do with the fact that in-game (unit) sounds use preloading/caching whereas UI sounds don't.**"*

**⇒ UI sounds: bare `.wav` (uncompressed PCM formatTag 1, 16- or 32-bit) now works. Unit/in-game sounds: still require `.wem`.**

### Known limitations **[C]**

- **Looped sounds do not loop.** The official guide states: "Looped sounds (burning fire) are currently not supported with this. The loop will not be preserved and the sound will play just once. This is a known issue."
- **Residual vanilla audio persists.** A modder who overrode "every annoying and loud battle alarm, monk, etc. sound" still heard "the default battle alert sounds mixed in with my modded sounds … Maybe are hidden files somewhere"; later, "still 30% vanilla game's sounds due to hidden files somewhere".
- **Some sounds appear un-overridable.** The chat doorbell / notification sound is the recurring example: the community mod "Original Sounds" changes it, but a hand-built mod doing "the exact same thing and even copying/pasting that mod's chat sounds" did not.
- **Looping/language overlays:** localized VO lives in `wwise\en\` and `wwise\zh\`; only those two exist.
- **Mod-folder override is per-file opt-in on the engine side.** Files known *not* to override from a local mod folder include `resources\_common\drs\sounds\[civilization]_jingle.wem`, `resources\_common\drs\interface\50500.bina`, `widgetui\futuravailableunits.json`, `widgetui\civTechTrees.json`, and `resources\en\strings\history\[civilization]-utf8.txt`.
- **Fragility across patches.** Sound mods are routinely broken by game updates; the docs also note a mod is automatically **disabled after a game update**.
- **Operational hazard [C]:** renaming a local mod folder triggered an in-game **"tampering detected"** lockout that persisted after renaming back; matching `info.json` `Title` to the folder name (spaces → underscores) restored it.

### Evidence from real mods on this machine — **[V]**

The user profile `C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\` was inspected: `mods\local\` is **empty**, and `mods\subscribed\` holds 6 mods. **Audio file count across the entire profile = 0** — no `.wav/.wem/.bnk/.pck/.ogg/.mp3` in any mod. Extension histogram across all subscribed mods: `.png` 600, `.json` 8, `.txt` 5, `.dds` 2, `.dat` 2, `.jpg` 1. **So there is no working sound mod on this machine to copy a structure from**; the mechanism above rests on forum evidence plus the shipped engine behaviour, not local proof.

Two of the six subscribed mods are **data mods** (they ship a `.dat` in `resources\_common\dat\`) — relevant because data mods are the restrictive category.

**Mod-folder mechanics [V]:** `mods\mod-status.json` schema `{"Mods":[{"CheckSum","Enabled","LastUpdate","Path":"subscribed//<name>","Priority","PublishID","WorkshopID","Title"}],"Unsub":[]}` (6 entries, priorities 1–6, two disabled); per-mod `info.json` `{"Author","CacheStatus":0,"Description","Title"}`.

**The modding model, from `docs__mods__index.md` [D]:** *"Mods work by modifying or adding files in your game directory. That's it. The hard part is figuring out which files you need to modify, and how."* A local mod is `...\mods\local\<AnyName>\` mirroring the game tree exactly, plus `info.json`. Four categories: additional content, UI mods, graphic mods, data mods. **Guidance from a modder [C]: *"Modders should create mods by replacing individual files and avoiding data modding whenever possible."*** Known breakage **[D]**: "Maybe you are trying to combine a data mod with a User Interface or Content mod. While that should be possible according to the patch notes, this functionality seems to be broken again."

---

## 9. Sound intent mapping

| Beginner intent | Feasibility | Notes |
|---|---|---|
| **Change a UI sound** (button click, error, chat ding, age-up, under-attack alarm) | **Easy now** | Drop an uncompressed 16- or 32-bit PCM `.wav`, or a `.wem`, at `resources\_common\drs\sounds\<Title_Case_Name>.wem`. Use the `sounds.json` 53 names as the picker list. Some (chat doorbell, some alarms) resist override. |
| **Change a unit's voice line / attack sound** | **Hard** | Requires a real `.wem`; bare `.wav` is ignored because unit sounds are preloaded/cached. Producing `.wem` needs the (non-free) Wwise authoring tool. |
| **Replace villager voice lines wholesale** | **Hard** | Same as above, multiplied by the number of lines, and localized VO is split into `wwise\en\` / `wwise\zh\` packs. |
| **Add custom music** | **Hard** | No loose music files; the "no guide anywhere" complaint is explicit. Persistent reports of music mods not playing. |
| **Make the game quieter / mute a category** | **Easy-ish** | A tool can ship a silent (correctly formatted) replacement file for the offending names from the `sounds.json` / spreadsheet list — this works for UI sounds. Not guaranteed for cached unit sounds or for the sounds that fall through to "hidden files". |
| **Replace a taunt** | **Medium** | Same mechanism; community reports the taunt path works, though patches broke it more than once. |
| **Replace the civ jingle** | **Blocked** | `resources\_common\drs\sounds\[civilization]_jingle.wem` is on the known not-overridable list. |

**Strategic conclusion for the tool:** sound is a **name-selection problem, not a format-authoring problem**, for everything the engine lets you replace. The valuable asset is a friendly, searchable list of the ~53 `sounds.json` names (plus the audio-spreadsheet names) with plain-language descriptions, backed by a converter that emits a correct uncompressed PCM WAV. The tool should **not** promise unit-voice replacement or custom music.

---

## 10. Difficulty ratings

| Area | Rating | Justification |
|---|---|---|
| **Swap a unit/building/nature sprite for another shipped one** | **1/5** | Pure file copy + rename, both `_x1` and `_x2`. No format knowledge. Published working example. Only hazard: frame counts must match, which fails *silently* (wrong frames played), so a tool should pre-check and warn. |
| **Replace a portrait / icon** | **2/5** | `widgetui\textures\ingame\units\*.dds`, 256×256, uncompressed A8R8G8B8 or DXT5. `texconv.exe` ships. |
| **Recolor units / change player or civ colors** | **1/5** for the edit, **3/5** to do it safely | The files are plain JASC text and are 2–16 KB. Complexity is in *which* of 89 `.pal` files plus `spritecolors.json` must stay consistent, not in the format. |
| **Small trees** | **1/5** | Already shipped as 104 named `.sld` in `drs\small-trees\`; it is a rename mod by construction. |
| **Resize a building / unit sprite (new pixel dimensions)** | **5/5** | The community toolchain (SLX Studio) works on SMX, and **zero `.smx` files ship** — it needs pre-SLD art from an old Steam depot. DESpriteTool could regenerate from PSD, but the PSD contract is undocumented for this purpose. |
| **Author new animated art from scratch** | **5/5** | Requires a multi-layer PSD per frame with a reverse-engineered layer contract (player-color layer still unmapped; Height/Normals apparently inert), plus Blender/GIMP/Substance, plus DESpriteTool's CLI. Explicit community verdict: "There needs to be a readme for the readme." |
| **Make a unit civ-specific / regional skin** | **4/5** | Requires editing `empires2_x2_p1.dat` with AGE — a **data mod**, which is mutually exclusive with other data mods, must be selected before each game, and is awkward in multiplayer. |
| **Programmatically read/edit SLD contents** | **4/5** | Header and frame headers fully decoded; main/shadow layer decoded and checksum-validated; **bit-2 layer layout unresolved**, so a general reader is not yet achievable. Frame *duplication/removal* is proven tractable by a third party. |
| **Replace a UI sound (WAV)** | **2/5** | Needs the target name (from `sounds.json`) and a correct uncompressed 16/32-bit PCM WAV at a path that does not exist on disk. Developer confirmed on the current build. |
| **Replace a unit sound** | **5/5** | Requires `.wem`; bare WAV is ignored due to preloading/caching; Wwise authoring tool is not free. |
| **Custom music / taunts / civ jingles** | **4–5/5** | "There seems to be no guide anywhere"; override refused for jingles; frequent patch breakage. |
| **Overall: a rename-and-palette mod tool** | **2/5** | Everything needed is shipped and legible. |
| **Overall: a sprite-authoring tool** | **5/5** | No documented first-party path; the one official tool is a CLI with an unexplained layer contract. |

---

## 11. Unknowns

Each entry states what could not be determined and **what test would settle it**.

1. **The SLD bit-2 (`unknown5`) layer layout — the single biggest graphics unknown.**
   *Known:* the bit mapping (bit 2 = this layer); that it is present in every rich frame type; that its start is `u32 content_length` followed by a 4-byte value that is `05 00 00 00` in every file examined; and that after that comes a run of ascending `u16` left/right pairs (`(13,44) (73,109) (151,195) (233,256)` in `n_mine_gold_33_x1.sld`) — an outline-table-like structure the SLD doc never mentions.
   *Not known:* whether that pair table has a length prefix, whether the layer carries its own command array, and the exact block count rule.
   *Test:* hex-dump a small `ft=0x07` file end-to-end and hand-walk the chain between the shadow layer's end and the next frame header; verify against 3–5 files whose second frame is also `ft=0x07`. Scripts `sld_final.py`, `sld_bit2.py`, `sld_bit2_hyp.py` are the harness.
2. **Two-byte near-miss.** Four files in one sample ended exactly **2 bytes short** of EOF (`end=18542 filelen=18544`, `end=20634 filelen=20636`). *Test:* identify the field that is 2 bytes; it is very likely the mask layer header and would close several failures at once.
3. **`frame_type` values with high bits** (`0x50`, `0x32`, `0x86`, `0x72`; 4–5 files per 120–300 sample, e.g. `p_mounted_trebuchet_shadow_x1.sld`). *Test:* check whether these are a different SLD sub-version (the version field still reads 4) or non-sprite SLDs; compare against `nf=1` files.
4. **SLP palette-id reliability.** The `properties` field of SLP frame info decodes as `7` on `game_b1.slp` but as `1278803831` on `game_b10.slp`. *Test:* render the same SLP under candidate palettes with `verify_sld.py`'s decoders and compare against a screenshot of the shipped `game_b*.slp` sprite (they are the AoK building sprites used by the original campaigns).
5. **`frame_index` semantics.** It is **not** a sequential ordinal — adding a `frame_index == i` constraint to the solver *reduced* the number of solvable files. *Test:* find a file where the frame index sequence is monotonic and correlate with animation direction/facet.
6. **Which `_x1`/`_x2` sprites a given unit or building uses, per animation.** The engine resolves names by convention but no shipped index maps "Cataphract" → its file list. *Test:* correlate `empires2_x2_p1.dat`'s graphics section (parseable with `genieutils-py` / `GenieDatParser`) against the filenames in `drs\graphics\`. **This is the single highest-value next piece of research for the beginner tool** — it turns rename-to-replace from "you must know the filenames" into a menu.
7. **Whether a mod-folder `.sld` override actually wins in the current build.** The evidence is one published mod from 2023 plus forum consensus; it was **not** verified locally (no sprite mod exists on this machine and the game was not modified). *Test:* drop one renamed donor `.sld` into `mods\local\` and observe.
8. **Fully authoritative sound-name list.** `sounds.json` has 53 entries, but the community "AoE2 DE Audio Spreadsheet" has at least "UI Sounds", "In-Game Play Events" and "Original Sounds" tabs and is larger; the Genie `.dat` has 2,149 `.wav` logical names. *Test:* obtain the spreadsheet (its URL was not recovered — Steam Community is unreachable from this session) and cross-tab it against `sounds.json` and the 36-name break list.
9. **Whether unit-sound `.wav` support has since landed.** The developer said the unit-sound failure was "forwarded for investigation" as a preloading/caching issue. *Test:* re-run the reporter's exact experiment on the newest build.
10. **Binary/licence status of the third-party tools.** SLX Studio, SMX Workshop, SLD Extractor, Turtle Pack, SLP Studio, TexConvGUI, genieutils-py and GenieDatParser have **no verified licence** — `web_search` has no API key in this session and GitHub/Steam Community fetches fail. *Test:* perform the same lookups from a network context that can reach GitHub and Steam.
11. **Whether the audio packs can be edited in place at all** (as opposed to file-level override). The `.pck` files are standard Wwise (`BKHD`/`DIDX`/`HIRC`) and event names hash as FNV-1-32-lowercased, so in principle a repacker could work; nobody in the surveyed corpus did it, and one modder called it "a nightmare … and/or impossible". *Test:* use Wwise's own tools against `Base.pck` on a copy.

---

## Appendix — artifacts produced by this survey

All under `D:\Software\DeepSeek Harness\工作区2\_probe\survey_gfx_snd\`:

- `probe_sprites.py` / `sprites_probe.json` — whole-tree `.sld`/`.slp`/`.smp` census, versions, frame counts, SLP frame-info parse.
- `dump_hex.py` — raw hex ground truth for anchor files.
- `verify_sld.py` / `sld_verify.json` — BC1/BC4 decoders plus an SLD frame walker that renders a frame's main layer to PNG via Pillow.
- `sld_walk.py`, `sld_fast.py`, `sld_solve2.py`, `sld_solve3.py`, `sld_bitorder.py` — superseded solver attempts (they read `frame_type` at the wrong offset; retained only as history).
- `sld_bitrev.py` / `sld_bitrev.json` — **the offset fix and the shadow-file histogram that proved the reversed bit mapping.**
- `sld_final.py` / `sld_final.json` — exact-EOF SLD walker on the corrected bits.
- `sld_bit2.py` / `sld_bit2.json` — six competing interpretations of bit 2.
- `sld_bit2_hyp.py` / `sld_bit2_hyp.json` — bit-2 layer size hypotheses validated against next-frame-header plausibility, with hex dumps.
- `probe_sound.py` / `sound_probe.json`, `probe_pck_names.py` / `pck_headers.json`, `probe_pck_strings.py` / `pck_strings.json` — `.pck` AKPK census and Wwise signature scan.
- `probe_dat*.py`, `probe_dat_decompress.py` / `dat_decompressed.json` / `empires2_x2_p1.raw` — Genie `.dat` raw-deflate discovery and the 2,149 `.wav` name extraction.
- `probe_event_names.py`, `probe_fnv.py`, `probe_hash2.py`, `probe_hash_reconcile.py` / `hash_reconcile.json`, `probe_hash_control.py`, `probe_event_hash.py` / `event_hash.json` — FNV-1-32-lowercase discovery plus the random-control test that invalidated the wider reconciliation.
- `dat_sounds.py` — created but never run; the `.dat`↔`sounds.json` reconciliation was achieved by other means, so it is optional.
