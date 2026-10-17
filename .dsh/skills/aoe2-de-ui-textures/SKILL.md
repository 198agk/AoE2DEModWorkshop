---
name: aoe2-de-ui-textures
description: Replace AoE2 DE in-game and menu textures, HUD panels, icon atlases and UI strings as a loose-file mod. Use when a task maps a visible icon/widget to an on-disk PNG, swaps an emblem or panel texture, edits widgetui layouts, wpfg XAML, or produces a UI/texture mod folder. Covers the loose-PNG-overrides-atlas proof (no atlas rebuild, no .dds authoring), the three emblem families, the size constraint, materials.json/morematerials.json, and icons.json's 14 segments.
---

# AoE2 DE UI and texture mods

Game root: `D:\Games\Steam\steamapps\common\AoE2DE`. User profile: `C:\Users\26913\Games\Age of Empires 2 DE`.

## The one thing that makes this cheap

**A loose PNG at the atlas source's `FileName` wins over the baked atlas DDS.** Proven end-to-end: a shipped mod containing **zero `.dds` files** replaces HUD emblems and the game renders the new art.

Consequence: texture replacement = **copy a file**. No atlas rebuild, no `.dds` authoring, no mipmaps. Pillow's DDS limitations are irrelevant.

Chain to walk when asked "which file do I edit?":
```
widget Name -> Material -> AtlasRef -> AtlasTextures[].Textures[].FileName -> disk PNG
```
`materials.json` paths are relative to **`widgetui/`**, not the game root. Widget names are frequently built at runtime (`%sIcon` printf-style), so a literal search for the material name can miss.

## Guardrails

- **`materials.json` has two different wrapper layers.** `Materials[i]` is `{"MaterialDef": {...}}`; `AtlasTextures[i]` is `{"AtlasDef": {...}}` with `Textures[]` *inside* `AtlasDef`. Unwrapping the wrong level returns `None` silently and makes an entire batch of lookups look "unmapped". This has caused two separate wrong conclusions — verify with a known-good control sample before believing a mass miss.
- **Keep the original pixel size when replacing.** 508 of 510 published replacement files do. Resize the user's image on import and tell them.
- **`icons.json` is NOT an engine input.** The exe contains the string `icons.json` **zero** times (the case-insensitive hit is `CustomMapIcons.json`), while `materials`, `morematerials`, `buttons.json`, `objreplacement.json` and `futuravailableunits.json` are all named by the engine. Treat `icons.json` as editor-side metadata for human-readable categorisation; **runtime truth is `materials.json` + disk + atlas DDS**.
- **Search for bare stems, not filenames, in the exe.** `morematerials.json` has 0 hits but `morematerials` has 1, sitting immediately next to `materials` in the same string block — the engine appends extensions. Searching only the extension form yields the false conclusion "the engine does not read it".
- **Do not trust a third-party asset listing against itself.** Constants and command tables published by community sites diverge from the shipped build in **both** directions. Validate against `resources/_common/xs/Constants.xs` and shipped game files.

## Three emblem families — do not confuse them

| Family | Directory | Used by |
|---|---|---|
| **V1** | `widgetui/textures/ingame/emblems/` (singular `berber.png`) | in-game command panel; atlas `ingamepanels`; material `CivEmblem<Civ>` |
| **V2** | `resources/_common/wpfg/resources/civ_emblems/` (plural `berbers.png`) | WPF menu layer; **premultiplied grey variant of V1, nearly invisible on dark backgrounds** |
| **V3** | `widgetui/textures/menu/civs/` | in-game player roster / tech tree; atlas `defaultwidgets`; material `<Civ>Icon` |

The widget `Name` `CivIcon` is **not** a material name — the engine builds `<Civ>Icon` at runtime from `playerName + "Icon"`.

## Size and shape facts worth keeping

- `widgetui/` = 133 layout JSONs, 116 contain widgets, **6,504 widgets / 30 types**. `Surround` (9-slice, `gridstep 32`) is only 1.09%.
- Layout reference resolution is **3840x2160**, integer pixels, anchor via `ViewPort.alignment` (`Top*` grows down, `Bottom*` grows up from the origin).
- Text alpha is dimensionally inconsistent: some sites use `a:1` (float), others `a:255` (byte). Parsers must defend.
- `widgetui/textures/` = 7,840 files (5,977 png / 1,655 dds / 206 jpg). Note the loose PNG source tree ships with the game.
- Menu layer: `resources/_common/wpfg/` = 3,039 files, **complete readable WPF XAML source** (233 `.xaml`, 2,708 `.png`).
- Strings: use the official per-language overlay `key-value-modded-strings-utf8.txt` — the engine merges it; never rewrite `key-value-strings-utf8.txt`.

## `icons.json` — 14 segments, 86.1% resolved

Non-empty values 2,138; resolved 1,840. **The unresolved 298 are all individually explained** (no "cause unknown" remainder): 206 are `Units` slots with genuinely no art on disk (missing from index 757), 66 are the dead `CivHero` segment, 6 dead `MenuIcons` entries, 6 literal `"None"` in `Buildings`, 6 `Techs` placeholders, 4 comma-joined ids, 4 plural-filename mismatches.

Resolution rules:
- **R1** value (or its `TextureRef`) is a `MaterialDef.Name` -> take the atlas `FileName`
- **R2** value `<dir>_<stem>` -> `wpfg/resources/<dir>/<stem>.png`
- **R3** value is the whole filename -> `wpfg/resources/<dir>/<value>.png`
- **R4** `Notification` is a hardcoded alias: `wonder_icon` -> `ScorePanelWonder`, `relic_icon` -> `ScorePanelRelic`
- **`StatIcons` needs normalised matching, not a derivation function.** Four value styles coexist: `stat_icon_<x>` -> `StatIcons<TitleCase(x)>`; punctuation/case variants including a material whose real name contains a hyphen (`stat_icon_range_armor` -> **`StatIconsRange-Armor`**); bare material names (`stat_icon_powerup`, plus 5 PascalCase `StatIconsPowerUp*`); and one truncated form (`stat_icon_hpregen` -> **`StatIconsHpRegeneration`**). Try exact -> TitleCase -> strip-punctuation-lowercase -> unique substring, and all 24 resolve. The exe hardcodes `<MATERIAL=StatIconsRange-Armor,1>` among 10 such tokens, confirming the family is engine-referenced by name.
- **`MenuIcons`: 3 of 9 resolve** — `submenu_oligarchy|democracy|tyranny` are **Return of Rome government tech icons** (`TechIconsT155Oligarchy` / `T156Democracy` / `T154Tyranny`). The other 6 are genuine dead entries (8 independent negative checks). Found only by dumping the exe's neighbouring strings, where `Oligarchy`/`Democracy`/`Tyranny` sit beside `Reset Oligarchy` etc.
- **`CivHero` (66 values) is a dead segment**: no `civ_hero` directory anywhere, `civ_hero_*` absent from disk and exe (contrast `civ_techtree` = 9 exe hits), and only `icons.json` itself mentions the prefix. Render placeholders; do not report a parse error.

## Mod mechanics the tool must implement

- Mod root = the folder containing `info.json`; subdirectories **mirror the game root directly** (no extra `resources/` level).
- `info.json` keys in practice: `Author`, `CacheStatus`, `Description`, `Title`. `Unpublished` / `thumbnail` / `previewIcon` / `mainmenu_bg.dds` also exist engine-side and are optional.
- **Parse `info.json` with `json.loads(text, strict=False)`** — real `Description` values contain raw CR/LF control characters and strict parsing fails.
- `mod-status.json` under the profile holds `Priority` (load order), `Enabled`, `CheckSum`, `Path`, `WorkshopID`. The tool must read and write it, and **validate that each `Path` exists** (users rename folders by hand).
- **No central manifest**: coverage is same-named files landing on the mirrored path, local overriding base by `Priority`.
- **Official incremental channel:** `morematerials.json` merges with `materials.json` by name (199 overlapping names in the shipped pair). A texture mod does **not** need to rewrite the 2.5 MB `materials.json` — write the much smaller overlay instead. Same pattern for `key-value-modded-strings-utf8.txt`.
- **Shipped mods carry redundant files.** Detect "content unchanged vs the base game" during packaging, or the user gets meaningless diffs.
- Publish validation to pre-empt: banned filename/title characters, PNG-only for images, and the official warning that **data mods and scenario mods must not be mixed** — ship them as two separate mods.
- `modes/` (e.g. `Pompeii`) is a first-party content mode, **not mod-overridable**.

## Instrumentation traps (these produced wrong answers before)

- **MAD/NCC is a bad instrument for "which source was rendered".** A dark premultiplied texture against a dark background scores a deceptively low MAD. Compute on `alpha > threshold` art pixels and **confirm with a side-by-side visual** before concluding.
- **Measure camera displacement before judging whether the HUD changed.** Naive per-region diff reported every region as changing because the camera had moved. Use a wide search radius; a ±80 px window gave NCC 0.17–0.30 (meaningless) where ±300 gave >=0.97.
- **"HUD transparency" has no single answer.** Within one bottom HUD, y=1250 transmitted 0.96 while y=1350 transmitted only 0.38. Answer per row or per widget.
- **Offline HUD re-rendering WORKS — and the earlier "it failed" verdict was superseded.** A first attempt did not converge (3840x2160 reference vs a 2730x1535 screenshot implies 0.7107, yet the true HUD scale is **0.5980** — the game multiplies by its own HUD zoom on top of the backbuffer). The re-do succeeded on three recovered inputs: (1) **calibrate by fitting the layout's own hard-coded box positions** (`box i = (15+200i, 15, 84, 84)`), which give `dx=dy=0` and identical solutions on all five screenshots — so the "need screenshots at several HUD scales" the first attempt asked for was a **false requirement**; (2) the five reference shots are **one game moment with the camera moving**, so the across-frame `std` equals `(1-alpha)*std(terrain)` — a **tone-free alpha probe** that removes the terrain term; (3) that probe proves the reference shots show a **UI mod, not vanilla art** (vanilla predicts std ~0 where it declares alpha >= 250; measured 8.11 vs terrain 14.16). Result: `resourcepanel.json` body **MAD 11.21 against a control floor of 11.8-14.7** — statistically indistinguishable from perfect — `scorepanel.json` 9/9 nine-slice pieces with an **empty failure log**.
- **★ Never compare an observation against vanilla art when a texture mod is enabled.** The earlier "everything mismatches" readings were all comparing the screenshot to vanilla. The enabled panel mod was **byte-identical vanilla RGB with alpha multiplied by exactly 0.502**; making the renderer mod-aware moved MAD 50.56 → 23.62. Check `mod-status.json` and `materials.json` for what is actually loaded before measuring fidelity.
- **Art needs no atlas decoding and no font substitution.** For all 4,354 atlas materials, normalized UV extent x atlas size == the shipped loose PNG's pixel size (**4,329 checked, 0 mismatches**) — so HUD art is a `crop()` of a PNG. Text is better served by the shipped **`<font>.box` metrics + 2048x2048 glyph pages** than by the TTFs (which the HUD path never references by name): `<name>.box` = header + 40-byte records (`W,H,u0,u1,v0,v1,page,XO,YO,HAdvance`) + a `(u16 codepoint, u16 glyphIndex)` cmap, validated exactly (`16 + 7755*40 = 310216`, file 341236 = that `+ 7755*4`). **`FontIndex` is a 0-based index into `["combined","basic_bold_16","combined_sansserif"]`** — registered by position in a static initializer, 98.1% of 6,203 Font blocks use index 0. Baseline rule: **`YO + H` is constant (43.6 +/- 0.1)** for baseline-resting glyphs; `YO` is the glyph-top offset.
- **The real blocker for a full HUD renderer is runtime data, not geometry.** 6,504 widgets / 31 Types across 133 files; `Base`+`Label`+`Anchor` = 63.2% and `Surround` (nine-slice) only **1.09%**. But ~15% of widgets (`ListBox` 224, `DropDown` 171, `ScrollBarVertical` 247, `CheckBox` 359) and most widgets in the largest files display values that are not statically derivable — a perfect art renderer still yields an empty shell. About **10-20 ingame panel files** render well today; menus/editors are art-paintable only.
- **Glyph alpha is `min(R,G,B)`, not `max`** (pages pack white Latin against saturated CJK; `max` floods to 255 and makes every glyph a solid block). The alpha-scale trap is **per-channel, not per-block** (`AgeTextLabel` mixes `a:255` and `a:1` inside one Font block). And draw materials into the widget's ViewPort **box**, never at texture resolution — that sizing bug alone fabricated MAD 45.7 where the truth was 12.1.

## Reference

Full evidence, per-value tables and a script index: `UI贴图模组能力目录v1.md` in the workspace root; probes under `_probe/` (notably `loose_override_proof.py`, `sections_last3_table.py`, `sections_settle.py`). The HUD renderer re-do is `_probe/hud_render/` (`HUD_RENDER_REPORT.md`, `hudrender.py`, `HUD_COMPARISON.png`, `HUD_COMPOSITE.png`). Read-only research; the game directory has never been written to in this line of work.
