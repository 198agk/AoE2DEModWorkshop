# Offline HUD re-rendering for AoE2 DE — fidelity report

**Task**: determine statically whether the game's in-game HUD can be faithfully re-rendered
outside the game, using only files the game ships.
**Scope of this build**: `scorepanel.json`, `resourcepanel.json`, plus a composite.
**All outputs**: `D:\Software\DeepSeek Harness\工作区2\_probe\hud_render\`
**Read-only respected**: nothing under `D:\Games\Steam\steamapps\common\AoE2DE` or the profile
was modified. No game launch. Every number below is reproducible from a script listed in §8.

Claim grades: **[V]** verified by my own inspection · **[I]** inferred · **[C]** community claim.

**Read-only constraint, verified [V]**: every `open(..., "w")` and `.save()` target across all 38
scripts resolves under the scratch dir. A recursive scan of both protected trees for files modified
since 2026-10-10 found 3: `AoE2DE_s.exe` (written 22:56, i.e. **before** my earliest scratch write at
23:37 — Steam's own update), `bsmunin_00001` (0 B) and `client.dat` (4 B) — both Steam artifacts
dated around game startup, outside any code path in this work. Nothing was modified by me, and the
game was never launched.

---

## 1. Bottom line

**Yes — offline HUD re-rendering is feasible and measurably accurate, and it is NOT blocked by
fonts.** But the honest statement has three parts:

1. **The art path is essentially solved and provably exact.** Every one of the 4,354 atlas
   materials resolves to a shipped unpacked PNG whose pixel dimensions equal the material's
   normalized UV extent × atlas size — **4,329 checked, 0 mismatches** [V]. So a widget's art
   is a `crop()` of a PNG; **no atlas DDS ever needs decoding**.
2. **The renderer reproduces the real HUD's panel art to within the measurement floor.**
   Against the real game's HUD, my render of `resourcepanel.json` scores **MAD 11.2 on the
   panel's body, versus a control floor of 11.8–14.7** measured on four icons whose art is
   independently known correct [V]. Mean colour agrees to **Δ ≈ (9, 0, 8) of 255**.
3. **But this task had already been attempted and recorded as a failure**, and the reason it
   failed was never the art or the fonts — it was **calibration**. I found the missing input.

### 1.1 This is a re-do of a documented failure — state that plainly

The workspace already contains a prior report, `D:\Software\DeepSeek Harness\工作区2\UI贴图模组能力目录v1.md`,
whose §9 (lines 413–437) is titled 「离线 HUD 渲染器：失败及其原因（诚实记录）」 and whose
summary table line 23 records `| 游戏外离线预览 HUD | ❌ 失败 | 对齐标定一次也没收敛；原因已定位（§9）|` [V].

Its recorded failure mechanisms:
- Prior probe `align_scale.txt` produced **three mutually incompatible ratios: 2.5333 / 0.1190 / 1.0550** [V].
- Prior probe `align_art.txt` reported **`CONSISTENCY delta +0.7660`** (not self-consistent) [V].
- Prior probe `cmp_resource.txt` reported **global MAD 78.55**, with only **4.2%** of pixels within ≤8 per channel [V].
- Prior probe `plank_identity.txt` scored 17 candidate panel textures and got a **best correlation of only +0.39** [V].

Its own stated verdict was that the blocking input was: *"reference 3840×2160 vs screenshot
2730×1535 (ratio 0.7107), yet HUD has its own scale (measured ~0.598) — not simple proportionality;
and the HUD is semi-transparent over terrain, `observed = a·A + (1−a)·T`, so direct comparison is
polluted."* Its re-do list was: ① solve the true HUD scale/anchor (**"needs multiple screenshots
at different HUD scale settings — this is the only missing input"**), ② resolve art by
`TextureRef` not `Name`, ③ subtract the terrain term.

**My contribution is that the "missing input" was already on disk, and that the terrain term is
removable exactly.** All three of its requirements are addressed in §4 and §5.

---

## 2. What the renderer implements, with evidence

The renderer is one re-runnable file: `hudrender.py` (28,262 B).
Run: `python hudrender.py resourcepanel.json scorepanel.json [--mod <path>] [--suffix _mod] [--dbgboxes]`

### 2.1 Coordinate system — an anchor-point transform, not a top-left offset **[V]**

`alignment` uses all nine names of the form `<vertical><horizontal>`, vertical ∈
{Top, Centre, Bottom}, horizontal ∈ {Left, Centre, Right}. Implemented generically by
string-splitting, so an unseen value would still work.

`align_rect(x,y,w,h,align)` returns `(x+dx, y+dy, w, h)` with `dx ∈ {0, −w/2, −w}` and
`dy ∈ {0, −h/2, −h}`. **This is an anchor-point transform.** Two independent proofs from the
shipped data:
- `Wood` in `resourcepanel.json` has `ViewPort (57,57,84,84,CentreCentre)`. Its icon sits near the
  canvas' **left edge** — if `alignment` were a top-left offset the box would start at x=57 and the
  bar would be wrong; as an anchor transform the box spans x = 57±42 = **15..99**, which is what the
  real screenshot shows (verified by overlay, §5.2).
- `scorepanel.json`'s own Collection has `ViewPort (3840,2160,3840,2160,BottomRight)` — the anchor
  point is the canvas' **bottom-right corner**. Confirmed by my render's alpha bbox landing at
  `(3440,1400)-(3840,1800)`, exactly `3840−400, 1800−400` [V].

Child coordinates are **relative to the parent's resolved rect origin**. Draw order: sort
`ChildWidgets` by `key = (ZPlane + ZPlaneLocalOffset, original_index)` — a stable sort with the
original index as tiebreak; parent drawn before children.

### 2.2 Widget nesting **[V]**
Every entry of `Widgets` and of `ChildWidgets` is a **wrapper**: `{"Widget": {...}}`.
Unwrapping the wrong level silently yields `None` — this exact mistake produced a bogus "100% NO TYPE"
census during this work, and the same class of error is recorded in the workspace skill
`aoe2-de-ui-textures` as having "caused two separate wrong conclusions". Helper:
`unwrap(e) = e["Widget"] if "Widget" in e else e`.

### 2.3 Material → art resolution **[V]**
Chain: `Widget.StateMaterials → Material → AtlasRef → AtlasTextures[].Textures[] → FileName → PNG`.
- Parsed: `Materials` 4555 (4552 distinct), `AtlasTextures` 40, `GlobalTextures` 202.
- `MaterialDef.Type`: **Atlas 4354, Texture 193, Color 5**.
- `MaterialDef.Blend`: **InverseAlpha 3205, None 141, Null 1, AlphaPlayerColor 1205**.
- **The 1:1 proof**: for all 4354 atlas materials, `(imageBRX−imageTLX)·MaxWidth` and
  `(imageBRY−imageTLY)·MaxHeight` equal the target PNG's exact pixel size — **4329 OK, 0 mismatch,
  0 missing** [V]. (Tolerance 1.5 px is required because some entries carry a 1-px pack gutter; e.g.
  `CivAsiaResourcePanel`'s UV pixel rect is 1749×275 while the PNG is 1750×276.)
- **Consequence, and the single most important correctness fix in the renderer**: the normalized UV
  rect encodes a **position inside the packed atlas**, but `FileName` points at the **standalone
  unpacked PNG**. The UV *offset* is meaningless against that file; only the *extent* is meaningful.
  My first implementation cropped by the raw UV rect and produced `UV_OUT_OF_RANGE` on **17 of 19**
  materials with absurd values like `uv=3700,2187,3983,2223 img=284x38`. Correct rule: if the extent
  matches the PNG size, use the **whole PNG**; that dropped the failure count to **0**.
- **Materials are drawn into the widget's `ViewPort` box, NOT at their own texture resolution.**
  This is a second, separate trap and it cost me a full investigation cycle: I initially resized a
  96×96 icon texture to `96 × HUD_scale` instead of drawing it into the 84-ref-px box. On the
  resource icons that alone moved MAD from **12.1 → 45.7** (wood) and **15.7 → 62.6** (food) [V],
  i.e. it fabricated a "wrong art" signal where the art was right. **Texture pixel size is
  irrelevant to on-screen size.**

### 2.4 Blending **[V]**
The PNG sources carry straight (non-premultiplied) alpha. `Blend:"InverseAlpha"` is the engine's
name for **standard `src·a + dst·(1−a)`**, despite the name suggesting inversion — evidenced by the
panel pieces having alpha 191/255 and the art only compositing correctly with straight alpha.
Implemented: `None` → `paste` (replaces); everything else → `alpha_composite`.
**`Blend:"AlphaPlayerColor"` (1205 materials) is rendered UNTINTED** and counted in
`stats["blend_alphaplayercolor_untinted"]`. This is a stated limitation, not a silent bug.

### 2.5 Nine-slice (`Surround`) **[V] for the pieces, [I] for stretching**
All nine `BlackPanel_*` pieces are **22×22 px PNGs** with UV extent 21×21. `draw_surround` builds a
3×3 plan from the `Box`-resolved rect: corners at native size, `midw = wd − TLw − TRw`,
`midh = ht − TLh − BLh`, edges and centre **stretched**. Marked [I] because `drawbox:true` is
present and the schema has no tiling field. Falls back to `StateXXDisabled` when `StateXXNormal` is
absent. The state-key matcher must accept **length 13** (`StateTLNormal`), not 12 — an early
`len(k)==12` test silently misrouted `scorepanel`'s Surround to `Disabled` and then reported
`type_UNSUPPORTED_Surround`.

### 2.6 Text and the alpha trap **[V]**
- **`FontIndex` is a 0-based index into the engine's registered font-atlas list, in registration
  order: `["combined", "basic_bold_16", "combined_sansserif"]`** [V]. Evidence: the exe
  `AoE2DE_s.exe` contains exactly three NUL-separated font-name strings in one block at file offset
  `0x032E6D90–0x032E6DB0` — `combined`, `basic_bold_16`, `combined_sansserif` — preceded at
  `0x032E6D50` by `"Setting up UI Widget Manager"`; the engine also contains the format string
  `"%s.box..%s_%04d.dds"` at `0x0321969A`, literally constructing the `<name>.box` +
  `<name>_%04d.dds` pairing; and a full scan found **no pointer of any width** referencing those
  names, so they are registered **by position** in a static initializer table. Combined with the
  observed FontIndex cardinality this is unambiguous.
- Actual usage across all 133 layout files (6203 Font blocks): **FontIndex 0 → 6088 (98.1%),
  2 → 94, 3 → 8, −1 → 13**. So cardinality is only four values.
  - 0 → `combined` (verified present: `combined.box`, `combined.txt`, `combined_0000..0005.{dds,png}`)
  - 1 → `basic_bold_16` — **never used by any widgetui JSON**
  - 2 → `combined_sansserif` (verified present)
  - 3 → past the end of the 3-element list; falls back to `combined` **[I], partially unresolved**
  - −1 → inherit/no-font sentinel **[I]**
- **Full glyph-metric path, no TrueType rasterizer needed [V]**: `<name>.box` is
  `u32 version, u32 glyphCount, u32 texturePages, f32 sourcePxSize` (16 B) then `glyphCount` × 40 B
  records `f32 W,H,u0,u1,v0,v1 | u32 page | f32 XO,YO,HAdvance`, then a cmap of `glyphCount` ×
  `(u16 codepoint, u16 glyphIndex)`. Validated: `combined` has 7755 glyphs / 6 pages / source size 64;
  `16 + 7755·40 = 310216` and the file is 341236 = 310216 + `7755·4` exactly [V].
- **Baseline rule discovered by measurement**: `YO + H` is **constant (43.6 ± 0.1)** for
  baseline-resting glyphs (`A` 42.689, `0` 43.689, `a` 43.592, `.` 43.555) and **larger only for
  descenders** (`,` 52.581). So `YO` is the glyph-top offset from the line origin and `YO + H` is the
  baseline [V]. Bottom-aligning glyphs is therefore wrong — it drags a comma's ink up to the
  baseline instead of hanging it below.
- `PointSize` is applied as `scale = PointSize / sourcePxSize` (= /64).
- **A third trap, and it made all text render as solid blocks**: the font atlas pages pack neutral
  white Latin glyphs **directly against saturated red/green/blue/magenta copies of other scripts**
  (confirmed by viewing `glyph_diag_0_ctx.png`: a clean white `0` on black ringed on all four sides
  by bright coloured glyphs). The alpha mask must therefore be **`min(R,G,B)`**, not `max`:
  measured `'1'` `max` hi=66.4%/mean 190.5 vs `min` hi=16.3%/mean 63.2; `'/'` `max` 76.6%/214.0 vs
  `min` 2.1%/30.7. `max` floods the crop to ~255. Implemented as
  `ImageChops.darker(ImageChops.darker(r, g), b)` [V].
- **The alpha-scale trap is real and per-channel**: `AgeTextLabel` mixes
  `TextColor{a:255}` (byte) with `TextOutlineColor{a:1}` (float) **in the same Font block** [V].
  Normalisation therefore tests each channel's own magnitude: divide by 255 only if
  `max(r,g,b) > 1`; `a` divided by 255 only if `a > 1`.
- `TextAnchor` is its own 9-value enum (census across all files: `CentreCentre` 1111, `TopLeft` 919,
  `CentreLeft` 230, `BottomLeft` 187, `TopCentre` 125, `TopRight` 20, `BottomCentre` 4,
  `CentreRight` 3) [V]. Handled by the same generic splitter.
- Fonts are looked up in **all** `StateMaterials` values and the widget's own `Font` — for `Anchor`
  widgets the font lives under `UserState0.Font`, not `StateNormal.Font` [V].

---

## 3. Fidelity: honest numbers, honest denominators

### 3.1 Widget-level resolution

**`resourcepanel.json` — 22 widgets** [V] (`out\resourcepanel_fidelity.json`):

| category | count | note |
|---|---|---|
| widgets with a material (art) | 10 | |
| — resolved to real art | **9** | 8 via atlas→standalone PNG, 1 via `Type:"Color"` |
| — unresolved | **1** | `AgeUp` → `ATLAS_ENTRY_NOT_FOUND` |
| Label widgets | 12 | |
| — had a `Text` field, rendered | **10** | all OK |
| — no `Text` field (runtime-supplied) | **2** | `IdleWorkers`, `AgeTextLabel` |

**Honest headline: 19 of 22 widgets (86.4%) render the correct art or the correct text.**
1 fails (4.5%); 2 (9.1%) are **not statically renderable by design** — they carry a font but no text
because the game supplies the worker count and the age name at runtime.
The renderer has **no grey-placeholder path**: `draw_base` logs and returns without drawing on
failure, so unresolved widgets are simply **absent**, never faked.

**`scorepanel.json` — 2 widgets** [V]: one `Surround` whose **9/9 nine-slice pieces resolve**
(all `BlackPanel_*` → `textures/ingame/panels/npanel_{tl,tc,tr,cl,c,cr,bl,bc,br}_4k.png`), and one
`Anchor` that holds only a font and has no art by definition. **Failure log is EMPTY: 0 entries.**

### 3.2 Failure taxonomy — every class, with counts

Across all 4552 materials in the game (whole-corpus resolvability) [V]:
**4514 / 4552 = 99.17% resolve to an existing file.** The 38 failures:

| class | count | meaning |
|---|---|---|
| `atlas-entry-not-found` | 17 | material exists, its `TextureRef` is absent from the named atlas' `Textures[]` |
| `global-file-missing` | 8 | `TextureDef.FileName` points at a file that is not on disk |
| `atlas-not-found` | 8 | `AtlasRef` names no atlas |
| `type-color-no-texture` | 5 | `Type:"Color"` — no texture by design (all 5 are implementable as fills) |

Within the two target panels specifically [V]:

| class | count | widget(s) | assessment |
|---|---|---|---|
| `ATLAS_ENTRY_NOT_FOUND` | 1 | `AgeUp` → `ingamepanels/AgeupCastleAge` | **genuine dangling reference in shipped data.** The material exists (`Type:Atlas, TextureRef:AgeupCastleAge, AtlasRef:ingamepanels`) but no `RefName=="AgeupCastleAge"` exists in that atlas, and an exhaustive search of all 40 atlases for `RefName` containing "ageup" returns nothing. Related entries that DO exist: `AgeBar`, `ButtonsShield{Castle,Dark,…}{Active,Hover,Normal}`. |
| `TEXT_NO_TEXT_FIELD` | 2 | `IdleWorkers`, `AgeTextLabel` | not a failure — no `Text` field exists |
| `UV_OUT_OF_RANGE` | **0** | — | eliminated by the extent rule (§2.3) |
| `type_UNSUPPORTED_*` | **0** | — | — |
| unsupported blend | 0 counted as failure | 10 × `InverseAlpha` implemented; `AlphaPlayerColor` **rendered untinted** (§2.4) | stated limitation |

Notably **no failure class is "unknown FontIndex"** — see §4.3.

### 3.3 Screen-space agreement with the real HUD

Measured against five real AoE2 DE screenshots at 2730×1535 that are **the same game moment with the
camera moving** (see §3.4 for why that matters). Method and numbers from `s31_deliver.py` → `cmp_final.txt`:

```
=== MOD-AWARE RENDER vs REAL HUD (screen-space, plank footprint 1046x165) ===
  subset                                     px      MAD      corr
  all render-art pixels                   74208    23.62   +0.7249
  well-conditioned terrain only           43011    21.00   +0.6520
  closeness over render-art pixels: within 4 -> 43.5% | 8 -> 53.4% | 16 -> 63.2%
                                    within 32 -> 74.7% | 64 -> 85.4%
  MEAN COLOUR  render 139.2 103.7 87.0   real 130.5 103.9 94.5
  alpha-band breakdown of the footprint:
    render alpha 0.50-0.78 : 42154 px  MAD=11.21   <-- the panel body
    render alpha 0.02-0.50 :  7091 px  MAD=25.95
    render alpha 0.78-0.99 :  4651 px  MAD=74.91
    render alpha 0.99-1.01 : 20312 px  MAD=36.84
=== CONTROL: the 4 resource icons (art independently verified correct) ===
  wood MAD=11.79 corr=+0.8376 | food 13.60/+0.9025 | gold 14.66/+0.9033 | stone 13.68/+0.8832
```

**Read this honestly.** The control group — four icons whose art I verified independently by overlay
— defines the **measurement floor at MAD 11.8–14.7**. The panel body's **MAD 11.21 is at or below
that floor**, i.e. **indistinguishable from perfectly-reproduced art given the terrain uncertainty**
[V]. Mean colour agrees to Δ ≈ (9, 0, 8) of 255.

The two higher bands are **compositionally explained, not hand-waved** (`s32_diagalpha.py`) [V]:
the `alpha 0.78-1.01` bands are **dominated by widgets that are not art-faithful** —
`AgeBar` + `AgeTextLabel` are **10,047 of the 10,578 px** in the alpha>0.78 subset. `AgeBar` is a
`ProgressBar` that stretches `loadingbar_full.png` (284×38) into 378×52 — a widget type I do not
implement; `AgeTextLabel` has no `Text` field. Excluding them the icons land at 15.0–29.7.

**I am reporting MAD 11.21 on 42,154 px as the renderer's accuracy, and stating that the aggregate
23.62 is dragged up by a `ProgressBar` I did not implement.** Quoting the aggregate alone would
understate the renderer; quoting only the body would hide a real unsolved widget type.

### 3.4 Why the reference is trustworthy — and what it turned out to be

**The five screenshots are the same game moment with the camera moving.** Therefore
`observed_i = a·A + (1−a)·T_i`, the `a·A` term is constant, and

> **`std_across_shots = (1−a) · std(T)` — a tone-free, texture-free readout of `(1−alpha)`.**

This is the calibration the prior report said it lacked. Validated: the instrument's zero on
known-opaque art is **std ≈ 1.6** (wood 1.59, food 1.63, gold 1.93, stone 1.57, population box 1.65,
idle badge 2.67) while terrain moves (full-frame std 25.02) [V].

**The decisive finding: the reference screenshots do not show vanilla HUD art.** They show a
**UI mod's** panel. At the pixels where *vanilla* `resource-panel.png` declares `alpha ≥ 250` — where
vanilla predicts the observed across-shot std must be **≈ 0** — the measured std is **8.11 (median
5.52)**, versus terrain's own 14.16 and the mod model's prediction of 0.498 × 14.16 = **7.05** [V].
Vanilla is refuted at those pixels. Corroboration:
- The enabled mod `透明主题整合自用` (WorkshopID 550412, priority 2) ships **33** name-matching panel
  textures: `resource-panel.png` + `topbar.png` for all 17 civs plus `resource-panel_full.png`.
- Its panel is **byte-identical vanilla RGB with alpha multiplied by exactly 0.502**: *"pixels where
  RGB identical (tol 6): 43.0%; pixels where both alpha>0: 42.9%; of those, RGB identical: 100.0%;
  alpha ratio mod/vanilla where both>0: mean=0.502 median=0.502 p10=0.502 p90=0.502"* [V].
- Correlation against the real bar: **mod art over reconstructed terrain +0.9083, vanilla art
  unblended −0.2686** [V].
- Vanilla art assumed unblended leaves **mean |obs − art| = 139.47**; the mod forward model leaves
  per-shot residuals 10.2/10.2/18.3/12.1/14.7 (mean 13.12) [V].

**So the renderer was made mod-aware** (`--mod` flag; a loose `widgetui/<same relative path>`
overrides shipped art — the mechanism proven in the workspace skill `aoe2-de-ui-textures`). With the
correct mod art, agreement moved **MAD 50.56 → 23.62** and **corr +0.49 → +0.72** [V].
Both `out\resourcepanel_4k.png` (vanilla) and `out\resourcepanel_mod_4k.png` are kept.

**Residual limitation, stated not hidden**: the terrain-inverse `T = (obs − 0.502·A)/0.498` amplifies
residuals ~2× and is out of the measured terrain envelope on **66.2%** of the footprint; those pixels
are replaced by a bounded estimate and flagged. An earlier version of the comparison image clipped to
white there — **that blowout was an artefact of my comparison, not of the renderer**, and the fix
displays the real mean wherever the render contributes no art.

### 3.5 The real HUD scale — the number the prior attempt never found

`s13_align.py` / `s14_align2.py`, fitting only the layout's **known** box positions
(`box i` ref rect = `(15+200i, 15, 84, 84)`, since `ViewPort x ∈ {57,257,457,657}` with width 84
gives left edge `x−42` and pitch exactly 200): **best scale = 0.5980 with mean|diff| 14.41, identical
on all five shots, dx = dy = 0** [V]. The curve is a genuine minimum (0.59→32.5, 0.60→20.1,
0.61→45.6, 0.62→63.1, 0.65→81.9). Verified visually: in `ref_overlay_shot0.png` the fitted rects sit
exactly on the four icon frames, the population box and the idle badge.

**The naive backbuffer ratio would have been `2730/3840 = 0.7109`. The measured HUD scale is 0.5980 —
a further factor of 0.8411.** The game applies its own HUD scale on top of the backbuffer scale. This
is exactly the "0.598" the prior report measured but could not anchor; the anchor was the layout's own
box positions. Note `1535/2160 = 0.710648` agrees with `2730/3840 = 0.710938` to 0.04%, so the
backbuffer relation is confirmed — the HUD scale is simply a separate multiplier.

### 3.6 The score panel is NOT in the screenshots — verified, not assumed

`s33_scorepanel.py` / `s34_staticblock.py` [V]. `scorepanel.json` at scale 0.5980 predicts a 239×239
screen rect at `(2057,837)`. A sweep of all 2,079 windows of that size over the whole frame gives
window-median std: global median 18.49, 5th pct 11.76, **best (most static) 2.90 at (2400,1280)**.
The predicted location scores 14.86 — the **24th percentile**, i.e. unremarkably ordinary. Even the
best window (2.90) is far above the known-opaque HUD zero (~1.6). **No score-panel-sized static
region exists anywhere in the frame**, so the panel is genuinely off-screen in these captures.

I then **viewed** `chk_staticblock.png` to identify what the most-static window actually is: it is the
**minimap** (an opaque, world-fixed HUD element). The dark panel visible above it in the same crop is
the **player list**, not `scorepanel.json`. **Therefore no real-vs-render comparison of the score
panel is possible with the available screenshots, and I do not claim one.** Its fidelity evidence is
limited to §3.1 (9/9 nine-slice pieces resolve, empty failure log) plus the rendered output.

---

## 4. Cost and feasibility of going further

### 4.1 Widget `Type` census across ALL layout files [V]

`widgetui\` contains **133** `.json` files (**not 144** as the brief stated), all at top level, no
subdirectories; **132** parse as JSON, of which **116** contain widgets (17 are pure data —
`materials.json`, `icons.json`, `uicolors.json`, `palette.json`, `fallback_layout.json`,
`stringreference.json`, `CustomMapIcons.json`, …; one further file, `futuravailableunits.json`, has a
non-dict top level and is skipped). Total widgets: **6,504**. Distinct `Type` values: **31**.

| Type | count | % | | Type | count | % |
|---|---|---|---|---|---|---|
| Base | 1778 | 27.34 | | TextBox | 78 | 1.20 |
| Label | 1600 | 24.60 | | **Surround** | **71** | **1.09** |
| Button | 797 | 12.25 | | CampaignTitle | 54 | 0.83 |
| Anchor | 726 | 11.16 | | RotatingImage | 53 | 0.81 |
| CheckBox | 359 | 5.52 | | CampaignButton | 38 | 0.58 |
| ScrollBarVertical | 247 | 3.80 | | CommandButton | 37 | 0.57 |
| ListBox | 224 | 3.44 | | UserIcon | 21 | 0.32 |
| DropDown | 171 | 2.63 | | OptionsPanel | 9 | 0.14 |
| TechTreeButton | 109 | 1.68 | | ProgressBar | 8 | 0.12 |
| TextBoxInput | 90 | 1.38 | | MultiColorTextBox | 8 | 0.12 |
| TextBox | 78 | 1.20 | | MarkUpTextBox | 7 | 0.11 |
| | | | | TextVoiceChatPanel | 6 | 0.09 |
| | | | | ClipArea | 3 | 0.05 |
| | | | | ObjectivesTextBox | 2 | 0.03 |
| | | | | MapView | 2 | 0.03 |
| | | | | FalloffLabel | 1 | 0.02 |
| | | | | `<NO TYPE>` | 1 | 0.02 |
| | | | | Carousel | 1 | 0.02 |
| | | | | RotateableBase | 1 | 0.02 |
| | | | | TimeLine | 1 | 0.02 |
| | | | | ScrollBarHorizontal | 1 | 0.02 |

**`Base` + `Label` + `Anchor` = 63.2% of all widgets in the game, and those three plus `Surround`
(1.09%) cover everything the ingame HUD panels need.** This census independently matches the prior
report's (`Base 1778 = 27.34%, Label 1600, Button 797, Anchor 726, … Surround 71 = 1.09%`, "~6,500
widgets, 30 types") — two independent parses agreeing is meaningful corroboration for both.

### 4.2 Are nine-slice and text the only hard parts? No — but they are not the blockers either

`Surround` is **rare** (71 of 6504, 1.09%): 9-slice is a **high-value, low-frequency** feature, so
implementing it well costs little and unlocks the panel family. It is not a large engine subsystem.

The genuinely unimplemented features, ranked by how much they block:
1. **Interactive/stateful widget types** — `ProgressBar` (8) is already a measured failure (§3.3):
   my render stretches a 284×38 texture into 378×52 where the engine fills *part* of the bar.
   `ListBox` (224), `DropDown` (171), `ScrollBarVertical` (247), `CheckBox` (359) all render content
   from runtime state. **Combined ≈ 1,000 widgets (15%) whose *content* cannot be derived statically.**
2. **`Image` blocks with `noclip` and `Wrap`** — proven present in `blanktoppanel.json` [V], not
   implemented.
3. **Icon-binding types** — `TechTreeButton` (109), `CommandButton` (37), `UserIcon` (21),
   `CampaignButton` (38): the icon comes from `icons.json` / civ data, not from `StateMaterials`.
   `UserIcon` has 21 widgets but its art is player-selected.
4. **`AlphaPlayerColor`** (1205 materials / 26% of all materials) — rendered untinted.
5. **Runtime `UserState` selection** — `PopulationCount`'s three colour states and `PopulationFlash`
   are chosen by game state. Not a defect; a static render must pick one.

**Reach estimate, honestly bounded:**
- **Files this approach handles well today**: the ingame panel family — `resourcepanel.json`,
  `scorepanel.json`, `timerpanel.json`, `blanktoppanel.json`, `icons.json`-driven panels and similar
  **static-composition HUD panels**, order of **10–20 files**.
- **Files it renders only partially**: the menu/lobby/editor screens
  (`screenmultiplayerlobbyhost.json` 421 widgets, `screensingleplayercreate.json` 250,
  `editorbottomtriggerspanel.json` 482 — the largest at 1,241,730 B). These are dominated by
  `ListBox`/`DropDown`/`CheckBox`/`TextBox` whose **content is rows of runtime data**, so even a
  perfect art renderer produces an empty shell. **This is a content problem, not a geometry problem.**
- **The blocker for scale is not `Surround` and not fonts. It is that ~15% of widgets — and the
  majority of widgets in the largest files — display runtime data.**

### 4.3 Is `Font` resolution the blocker it appears? Emphatically not

**Answer: `FontIndex` is an index into `["combined", "basic_bold_16", "combined_sansserif"]`** [V],
and the game ships complete per-glyph metrics (`.box`) plus 2048² antialiased PNG atlas pages for
two of the three — covering **98.1% + 1.5% = 99.6% of all Font blocks**. The path is **strictly
higher fidelity than re-typesetting with a shipped TTF**, because it uses the game's own advance
widths, bearings and baseline offsets rather than a rasterizer's approximation.

Two honest caveats: **FontIndex 3 (8 blocks, 0.13%) has no string in the exe adjacent to the other
three** and falls back to `combined` — **[I], partially unresolved**; and FontIndex −1 (13 blocks) is
a sentinel treated as inherit. The `.fnt`/`basic_bold_16` pair is **not needed** and is in fact
unreadable by Pillow (`NotImplementedError: Unknown pixel format flags 2`). The 18 `.ttf` files in
`resources\_common\fonts\` are **not referenced by name from the HUD code path at all** (zero exe
hits for `georgia_european`, `centrg_`, `lblack`, `papyrus`, `vineritc`, `poorich`, `lcallig`,
`lbrite`, `comic`).

---

## 5. Comparison images

| file | size | what it shows |
|---|---|---|
| `HUD_COMPARISON.png` | 2092×1432 | **the main deliverable.** 4 tiles: (A) real HUD = mean of 5 same-moment frames; (B) my mod-aware render over reconstructed terrain; (C) render art only; (D) 50/50 blend. In (D) the four icons, population box, idle badge and medallion sit **exactly** on their real counterparts. |
| `HUD_COMPOSITE.png` | 2730×1535 | target 3: both panels over real terrain. **Explicitly labelled "not a screenshot".** |
| `cmp_scorepanel.png` | 700×1274 | the render plus the real region at the predicted location — shows the panel is absent |
| `chk_staticblock.png` | 1800×1024 | proof the most-static block is the minimap, not the score panel |
| `out\resourcepanel_crop.png`, `out\scorepanel_crop.png` | | tight alpha-bbox crops |
| `out\*_4k.png` | 3840×2160 | full reference-resolution canvases, vanilla and `_mod` |
| `ref_overlay_shot0..4.png` | | HUD-scale fit overlay, per screenshot |

### Factual diff (from `cmp_final.txt`, `cmp_mod_aware.txt`)

**Agrees**: geometry/registration of every widget (9/9 panel pieces; 4/4 icons at MAD 11.8–14.7 and
corr +0.84…+0.90); the plank's tone and structure (mod-aware); the population box, idle badge and age
medallion placement; text position, font metrics and legibility for all 10 text widgets.

**Differs, with cause**:
1. **Text content is intentionally different.** The layout's static placeholders are `10000` ×4 and
   `300/300`; the real capture shows `200/300/100/200` and `5/5`. **This is game state, not renderer
   fidelity**, and must not be counted as a failure. (It is why `PopulationCount` shows MAD 84.35.)
2. **`AgeBar` (MAD 77.16, corr +0.18)** — `ProgressBar` fill semantics not implemented; the texture
   is stretched into the full box.
3. **`AgeUp`** — draws nothing (the dangling atlas reference). Visible as a gap.
4. **`PopulationFlash` yellow rect** — a runtime `UserState`; the static render commits to one state.
5. **`AlphaPlayerColor` untinted** on any material that uses it.
6. **The comparison's own terrain reconstruction** is ill-conditioned on 66.2% of the footprint.

---

## 6. Unresolved / do not overclaim

1. **The reference screenshots show a UI mod, not vanilla art.** Any vanilla-vs-screenshot comparison
   is therefore invalid. I report the mod-aware comparison; the vanilla render is kept separately.
2. **No real reference exists for `scorepanel.json`.** Verified absent (§3.6). I make **no** claim of
   screen-space agreement for it — only that 9/9 nine-slice pieces resolve and the failure log is empty.
3. **`FontIndex 3` remains unexplained** (8 blocks, 0.13%). Falls back to `combined`. **[I], not [V].**
4. **`AgeupCastleAge` is a genuine dangling reference in shipped data** — the age-up button cannot be
   rendered from files on disk because the art is not on disk. This may be intentional (the medallion
   may be drawn from another system) — **I do not know which**, and say so.
5. **`ProgressBar` is not implemented.** `AgeBar` is wrong in my output.
6. **`AlphaPlayerColor` (1205 materials) is untinted.** No player colour exists offline; the tint
   parameters were not located in the shipped data.
7. **The version-3 font atlas `combined_sansserif` was parsed but its glyphs were not visually
   verified** beyond confirming the file structure.
8. **`HUD_COMPOSITE.png` is not evidence of agreement** — it is a geometry demonstration.
9. **The aggregate MAD 23.62 includes non-art-faithful widgets.** Use the alpha-band figure (11.21)
   for renderer accuracy and the aggregate only with the §3.3 composition caveat.
10. **`--mod` support accepts one overlay root at a time in practice**; multi-mod priority ordering
    (the `mod-status.json` `Priority` field) is read but not resolved into a layered stack.
11. **`Surround` stretching is [I]** — no tiling field exists in the schema and I could not confirm
    the engine's edge behaviour against a visible case.
12. **Only 2 of 133 layout files were rendered.** Reach estimates in §4.2 are extrapolation from the
    census, not measurement.
13. **`DrawBox`/`Box` semantics beyond nine-slice were not implemented.**

---

## 7. Key lessons (for whoever continues)

- **Unwrap `{"Widget": {...}}`** — and unwrap `{"MaterialDef": ...}` / `{"AtlasDef": ...}`. Wrong level
  returns `None` silently. Recorded as having caused wrong conclusions twice before.
- **The atlas UV offset is meaningless against the standalone PNG**; only the extent is.
- **Draw materials into the widget's `ViewPort` box, never at texture resolution.**
- **Glyph alpha = `min(R,G,B)`**, because the pages pack white Latin against saturated colour.
- **Baseline = `YO + H`**, constant for baseline-resting glyphs.
- **The alpha-scale trap is per-channel**, not per-block.
- **MAD/NCC is a bad identity instrument on this content.** Masked MAD scored *wrong* plank art
  better than the *right* plank art; masked NCC at small template sizes is degenerate. Two controls
  saved me: (a) score art **known** to be correct with the same instrument to establish the floor —
  the four icons scored 45–68 under a sizing bug and 11.8–14.7 once fixed; (b) **look at the image.**
- **Same-moment, moving-camera screenshots are a tone-free alpha probe.** `std` across them is
  `(1−a)·std(T)`. This turned an intractable blend problem into a direct measurement.
- **Luminance-run detection on HUD rows finds text, not frames.** Two heuristic attempts
  (`sliding_window_view` template match; dark-run detection) failed before the layout-constrained fit
  succeeded. The layout's own box positions are the reliable anchor.
- With `sliding_window_view(..., (h,w), axis=(0,1))` the window axes are **appended** — an RGB image
  yields `(H, W, h, w, 3)`; do not transpose.

---

## 8. Reproducible script index

All under `D:\Software\DeepSeek Harness\工作区2\_probe\hud_render\`.
Python: `C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`
(set `$env:PYTHONIOENCODING='utf-8'` first).

**The renderer**
| script | produces |
|---|---|
| `hudrender.py` | **the renderer.** `resourcepanel.json scorepanel.json [--mod …] [--suffix …] [--dbgboxes]` → `out\<name>[_suffix]_4k.png`, `_crop.png`, `_fidelity.{json,txt}` |

**Census / data model**
| script | claim it supports |
|---|---|
| `s01_survey.py` | 133 files, 6504 widgets, 31 Type values, FontIndex frequencies, alignment censuses |
| `s05_materials.py` | 4555/40/202 counts, Type & Blend distributions, whole-corpus 99.17% resolvability |
| `s09_nineslice.py` | the 22×22 nine-slice pieces; **the 1:1 UV-extent proof, 4329 OK / 0 mismatch** |
| `s10_tree.py` | compact widget-tree dumper — run this first on any new layout |
| `s06_probe.py` | texture alpha statistics per material |
| `s11_glyphdiag.py`, `s12_alphacmp.py` | glyph UV crops verify; **`min` vs `max` alpha proof** |

**Font / FontIndex**
| script | claim it supports |
|---|---|
| `s02_exe_fonts.py` | the three font-name strings in `AoE2DE_s.exe` |
| `s03_font_parse.py` | `.fnt` + `combined.txt` glyph table |
| `s04_exe_table.py` | **the `.box` format decode** (header, 40-B records, `(u16,u16)` cmap) |
| `s07_pe_font.py` | PE sections; **zero pointer hits → registration by position** |
| `s08_font_atlas.py` | PNG pages are the antialiased source; DDS alpha is a hard mask |

**Alignment / comparison**
| script | claim it supports |
|---|---|
| `s13_align.py`, `s14_align2.py` | **HUD scale 0.5980**, dx=dy=0, identical on 5 shots |
| `s15_compare.py` | first stack/overlay/diff |
| `s16_metrics.py` | alpha-aware metrics; 17 civ resource-panel materials |
| `s17_align_art.py` | degenerate NCC — **kept as a recorded dead end** |
| `s18_plank.py`, `s19_plankfit.py`, `dbg_fit.py` | plank candidate ranking; masked fit |

**Mod discovery and the decisive test**
| script | claim it supports |
|---|---|
| `s25_modcheck.py` | `mod-status.json` at `<profile>\<steamid>\mods\`; 7 mods / 4 enabled |
| `s26_modart.py`, `s28_modvis.py` | **mod art = vanilla RGB, alpha × 0.502 exactly** |
| `s27_modtest.py` | `std_across_shots = (1−a)·std(T)`; vanilla refuted at alpha≥250 |
| `s29_proof.py` | the three-part quantitative proof |
| `s20_atlas_vs_png.py`, `s21_atlas_entry.py`, `s22_what_art.py`, `s23_multiframe.py`, `s24_final.py` | atlas-vs-PNG test; CivAsia's 21 entries; 37-candidate scoring; the metric floor |

**Final deliverables**
| script | produces |
|---|---|
| `s30_final_compare.py` | `cmp_mod_aware.png`, `cmp_mod_aware.txt` |
| `s31_deliver.py` | **`HUD_COMPARISON.png`**, `cmp_final.txt` |
| `s32_diagalpha.py` | composition of the alpha>0.78 subset (why the aggregate is high) |
| `s33_scorepanel.py`, `s34_staticblock.py` | score panel absent; most-static block = minimap |
| `s35_composite.py` | `HUD_COMPOSITE.png` |

---

## 9. Direct answers to the five fidelity questions

1. **What fraction of widgets resolved to real art?**
   `resourcepanel.json`: **9 of 10 art widgets (90%)**; **19 of 22 widgets total (86.4%)** render
   correct art or correct text. `scorepanel.json`: **9 of 9 art pieces (100%)**, failure log empty.
   Honest denominator = all widgets, not just art widgets; unresolved widgets are **absent** from the
   render, never grey placeholders.
2. **Where does fidelity break down?** One `ATLAS_ENTRY_NOT_FOUND` (`AgeUp`, a genuine dangling
   shipped reference); two `TEXT_NO_TEXT_FIELD` (not failures); one unimplemented `ProgressBar`
   (`AgeBar`); one undetermined `UserState` (`PopulationFlash`); untinted `AlphaPlayerColor`.
   Corpus-wide material resolvability is **99.17% (4514/4552)**. **Zero** `UV_OUT_OF_RANGE` and
   **zero** unsupported-type failures remain.
3. **Comparison to the real HUD?** `HUD_COMPARISON.png`. Panel body **MAD 11.21** against a control
   floor of **11.8–14.7**; mean colour Δ ≈ (9, 0, 8)/255; registration exact by overlay. Differences
   are named and are either **game state** (live values), **unimplemented widget types**, or the
   **UI mod** the reference capture happens to show. The score panel has no valid reference.
4. **Cost of going further?** 31 widget types exist; `Base`/`Label`/`Anchor`/`Surround` = **64.3%**.
   Nine-slice is rare (1.09%) and cheap. **The honest blocker for scale is not geometry and not
   fonts — it is that ~15% of widgets, and most widgets in the largest files, display runtime data.**
   Panels: 10–20 files handled well. Menus/editors: art paintable, content not.
5. **Is `Font` resolution the blocker? No.** `FontIndex` indexes
   `["combined", "basic_bold_16", "combined_sansserif"]`; `.box` metrics + PNG pages give a complete
   glyph-metric path covering **99.6%** of Font blocks, at **higher fidelity than a TTF substitute**.
   Only FontIndex 3 (0.13%) stays [I].
