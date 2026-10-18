# Documentation audit — docs vs code, `D:\Software\AI\帝国项目`

Audit performed 2026-10-18 against the workspace as it stands after recovery + path fix
(HEAD = `2678d05`, 4 commits). Everything below is re-measured or re-read, never inferred.
Measurement environment: game root `d:\games\steam\steamapps\common\AoE2DE`,
profile `C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods`,
parser = the project's own `aoe2mod.dat.parser`.

---

## VERDICT: STALE

The *research* in these docs is sound and the byte-level numbers are almost all reproducible — but
the three narrative layers that a new session actually reads (the status page's file map, all three
SKILL.md "honesty boundaries", and the graphics catalogue's header) were written before
2026-10-17/18 and were never updated, so they now deny proofs the project already owns and assert a
structural impossibility the project's own passing test refutes.

---

## Dead references

Paths cited by a doc that cannot be resolved anywhere in the tree, or that are attributed to the
wrong directory. Resolution was attempted against workspace root, `_probe/`, the AoE2 DE game root,
and a global basename search.

| doc file | line | what it claims | what is true |
|---|---|---|---|
| `.dsh/skills/aoe2-de-sprites/SKILL.md` | 279 | sprite comparison figure `_shots/sld_render/big_teamcolor.png` | `_shots/` **does not exist** anywhere in the workspace; 0 files matching `*big_teamcolor*` tree-wide. |
| `.dsh/skills/aoe2-de-ui-textures/SKILL.md` | 87 | HUD re-render evidence = `_probe/hud_render/` incl. `HUD_COMPARISON.png` and `HUD_COMPOSITE.png` | `_probe/hud_render/` exists (38 files, `hudrender.py` 28,428 B, `HUD_RENDER_REPORT.md` 39,384 B) but **neither PNG exists**; 0 matches for `*HUD_COMP*` tree-wide. |
| `项目状态.md` | 214 | last green run recorded in `_probe/out_suites_bundle2.txt` | file **absent**. The committed artifact is `_probe/out_suites_final2.txt` (UTF-16, 73 `exit=0` lines + `SUITES: ALL PASSED`). |
| `数据模组能力目录v1.md` | 850 | "实测（`_probe\_rng5.py`）" | `_probe/_rng5.py` absent (and `_rng3.py`, `_rng4.py` too). |
| `数据模组能力目录v1.md` | 918, 936 | `_probe\tech_describe_audit.py`, `_probe\tech_describe_audit2.py` | both absent. |
| `数据模组能力目录v1.md` | 923 | `_probe\cost_fallback_impact.py` (the "119 tech slots" decision evidence) | absent. |
| `数据模组能力目录v1.md` | 2265 | `_probe/probe_donor_bias.py` (the "Chronicles 27.8% of donors" figure) | absent. |
| `数据模组能力目录v1.md` | 4135 | script index row `_probe\_rng3.py / _rng4.py / _rng5.py` | all three absent. |
| `.dsh/skills/aoe2-de-dat/SKILL.md` | 126 | `build_resource_labels.py` (no directory) | exists at `_probe/schema/build_resource_labels.py`. |
| `.dsh/skills/aoe2-de-dat/SKILL.md` | 272 | `diag_drift.py` (no directory) | exists at `_probe/serializer/diag_drift.py`. |

**Shipped-code reference to a destroyed path** (requirement 4): `aoe2mod/dat/parser.py:7` still carries
`D:\\Software\\DeepSeek Harness\\工作区2\\_probe\\source\\genieutils\\` in its module docstring.
It is the **only** hit under `aoe2mod/` + `tools/` (both otherwise clean; `.dsh/skills/**` is clean).
Docstring only — no runtime effect — but it is exactly the string the recovery was supposed to erase.
Root-document hits (historical by design, listed for completeness): `项目状态.md:219`,
`能力目录v0.md:304`, `_恢复说明.md:7`, `_会话迁移记录.md:1,10,11,69`, `_会话清理记录.md:11,12,15`,
`插件可用清单v1.md:123,172`, `AoE2DE_DDS技术研究报告.md:349,385,545`.

**Paths that are fine.** All module paths, `aoe2mod/tests/*`, `_probe/run_suites.py`,
`_probe/run_long.py`, `_probe/sldlib.py`, `_probe/loose_override_proof.py`, `_probe/sections_last3_table.py`,
`_probe/sections_settle.py`, `_probe/schema/intents.json`, `_probe/test_panel_shape.py`,
`_probe/test_panel_is_not_build_menu.py`, `_probe/test_civ_unit_gate.py`,
`_probe/test_panel_vs_dat_train.py`, `_probe/probe_dat_layer_modifiable.py`, `tools/sync_engine.py`
all exist. Only 6 cited `_probe/*.py` are missing, all in `数据模组能力目录v1.md`.

---

## Contradictions between docs

### C1 — "sprite replacement is unproven" vs "sprite replacement was proven in game"

| citation | text |
|---|---|
| `.dsh/skills/aoe2-de-sprites/SKILL.md:335` | "**No in-game verification exists.** Every result stops at the file layer." |
| `.dsh/skills/aoe2-de-sprites/SKILL.md:338` | "**Zero of this machine's 9 installed mods ship any `.sld`/`.slp`/`.smp`** — the replacement path has community consensus and format derivation, but no local precedent." |
| `.dsh/skills/aoe2-de-sprites/SKILL.md:116` | "measured in game 2026-10-17 on `dsh test v10`." |
| `.dsh/skills/aoe2-de-sprites/SKILL.md:121` | "Measured in game 2026-10-17 on `dsh test v11`: every job was a sheep except…" |
| `.dsh/skills/aoe2-de-sprites/SKILL.md:179` | "`dsh test v13`, one `.dat` and zero `.sld`, villagers came out as sheep." |
| `项目状态.md:151` | "✅ **已实机证明（2026-10-17，Round 74）** `dsh test v10`（村民←绵羊，20 个松散 `.sld`，**零 `.dat`**）… 这是本项目第一次端到端证明 sprite 层" |
| `变更日志.md:9` | "2026-10-17 · Round 78 · ★★★★ 改名换皮：418 MB → 12 MB，且进游戏验证通过" |

Same file, 200 lines apart. The "no local precedent" half is *also* factually false: mod
`551412_村民变羊 - Villagers turn into sheep - 贴图替换版` ships **466 `.sld`** (rest of the mod: 1 png,
1 json, no `.dat`, 417.92 MB, 468 files).

### C2 — the graphics catalogue's header still describes the pre-proof world

| citation | text |
|---|---|
| `图形音效模组能力目录v1.md:6` | "游戏目录与用户档案目录**从未被写入**…本轮全部为静态只读研究，**未启动游戏**。" |
| `图形音效模组能力目录v1.md:22` | "游戏内渲染（端到端） \| ⚠️ **未验证** \| … **需要用户启动游戏配合**" |
| `图形音效模组能力目录v1.md:386` | "**我们没有启动游戏、没有写一个精灵 mod、没有截图确认。** 这是唯一剩下的真实未知" |
| `图形音效模组能力目录v1.md:389` | "本机 9 个已装 mod 提供 0 个 `.sld`。" |
| `图形音效模组能力目录v1.md:240` | "2026-10-17 `dsh test v10` 实机" |
| `图形音效模组能力目录v1.md:241` | "**2026-10-17 `dsh test v11` 实机**" |
| `图形音效模组能力目录v1.md:273` | "实机证明 \| `dsh test v12`（三层全生效） \| `dsh test v13`（「看了都是羊」）" |

§6/§8 (lines 6, 22, 386) say the game was never started and the profile never written; §"三层" (240-241,
273) cites four in-game tests by version number. 360 lines apart in the same 416-line file.

### C3 — "the `.dat` CANNOT express per-civ unit availability" vs "the `.dat` CAN"

| citation | text |
|---|---|
| `.dsh/skills/aoe2-de-dat/SKILL.md:46` | "**⚠⚠ NEW, DECISIVE: the `.dat` CANNOT express per-civilization unit availability — not "we have not found where", but "there is nowhere it could live".**" |
| `.dsh/skills/aoe2-de-dat/SKILL.md:467` | "### ⚠⚠ The `.dat` CAN express per-civ unit availability — the "cannot" was too strong" |
| `项目状态.md:126` | "✅ **能 —— 而且已实机证明** … **本条曾写作「❌ 结构上不可能」，那是错的**" |

Two sections of one file, 421 lines apart, no cross-reference; the early one is the one an operator
reads first. `_probe/test_civ_unit_gate.py` itself now ends with a printed "*** CORRECTION (2026-10-15,
Round 58): the word 'cannot' above is TOO STRONG ***" block.

### C4 — the "panel is not the build menu" claim, refuted by the project's own passing pin

| citation | text |
|---|---|
| `项目状态.md:143` | "**但它漏掉了每文明都肯定能造的 11 个建筑**，其中 10 个**在该文明整个面板文件里"任何块都没有"**：兵营(12)…**6 个基础建筑在全部 62 个文明的面板里出现 0 次。**… 常驻钉子 `_probe/test_panel_is_not_build_menu.py`（A–C 全 PASS）" |
| `.dsh/skills/aoe2-de-dat/SKILL.md:298-306` | "`futuravailableunits.json` is NOT the complete villager build menu" … ":303 **10 appear NOWHERE in that civ's entire panel file**" … ":304 **Barracks / Mill / House / Palisade Wall / Lumber Camp / Mining Camp each appear in 0 panels**" … ":306 **A write to the panel cannot add or remove a basic building**" |
| `数据模组能力目录v1.md:3204-3214` | "15.4ae ★★★★★ 面板的 `Builder` 块**不是**完整的村民建造菜单" … ":3212 **10 个在该文明的整个面板文件里"任何块都没有"**" |
| `数据模组能力目录v1.md:3517` | "15.4am ★★★ 面板的形状：block 是"能生产的地方"，entry 是"那里生产的东西"（Round 51 新增，**纠正一处我自己的误读**）" |
| `数据模组能力目录v1.md:3519` | "**我此前的错误主张**（写在 `test_panel_is_not_build_menu.py` 里）…**这是误读**" |
| `数据模组能力目录v1.md:3532` | "**★ 判据：「不在某个 `Units` 数组里」≠「不在面板里」。** 实测有 **434** 个（基础建筑 × 文明）对同时满足…" |
| `_probe/test_panel_shape.py:4-10` | "An earlier suite (`test_panel_is_not_build_menu.py`) claimed: 'each basic building appears in ZERO civs' panels' … **That is a misreading and this pin corrects it.**" |
| `项目状态.md:236` | "面板覆盖每个文明 30–31 个建筑（含兵营 12）" |

`_probe/test_panel_shape.py` **passes** (I ran it). I independently confirmed with
`aoe2mod.game.buildpanel`: in the Britons panel all ten "missing" buildings are present as **top-level
blocks** — 12, 68, 70, 72, 562, 584, 598, 792, 236, 45, all `block=True`; across 67 non-Gaia civs the
frequencies are 12→67/67, 68→63/67, 70→67/67, 72→67/67, 562→61/67, 584→61/67, 598→67/67, 792→67/67,
236→46/67, 45→60/67. **Zero of the ten appear nowhere.** The catalogue retracts the claim at 15.4am but
15.4ae (313 lines earlier) carries no deprecation marker, and neither `项目状态.md:143` nor
`aoe2mod/de-dat/SKILL.md:298-306` carries the correction at all. `项目状态.md` contradicts itself
(line 143 vs line 236).

### C5 — intent / strategy counts

| citation | text |
|---|---|
| `项目状态.md:123` | "**8 个意图端到端**" (lists exactly 8) |
| `aoe2mod/schema/intents.json` | **10**: `unit.stat`, `unit.attack_class`, `unit.cost`, `tech.research_time`, `tech.cost`, `tech.effect`, `unit.availability`, `tech.availability`, **`unit.sprite`**, **`unit.art`** |
| `项目状态.md:124` | "**三策略**：`.dat` + 单位空间 JSON + 科技空间 JSON + 松散 `.sld`" (names four things) |
| `.dsh/skills/aoe2-de-sprites/SKILL.md:17` | "the reskin strategy is one of **three** `_split_by_strategy` returns" |
| `aoe2mod/api.py:1978-1997` | docstring says "-> (in_place_patch, civtechtrees_json, loose_files)" but body is `dat, js, sld, paint = [], [], [], []` and adds `elif s == "repaint_sld": paint.append(r)` → **4** |
| `aoe2mod/schema/intents.json` | strategy histogram `{in_place_patch: 6, civtechtrees_json: 2, loose_files: 1, repaint_sld: 1}` = **4 distinct** |

The SKILL.md copied a docstring that the product code itself no longer matches. `unit.art`
(`repaint_sld` → `aoe2mod/intent/repaint.py`) appears nowhere in `项目状态.md`.

### C6 — tree-writing: "unproven" vs "proven"

`数据模组能力目录v1.md:2988` says a JSON tree write is "**未证实**而不是**已被证伪**" and quotes
`api.py` as saying "**NO in-game test has yet shown EITHER file taking effect**". That string **does not
exist in `aoe2mod/`** (grep: 0 hits); the `not_proven` blocks were updated on 2026-10-17 and now read
e.g. "Loose .sld loading is proven (2026-10-17)". The *conclusion* at :2988 is still correct (I measured
0 CivTechTrees / panel files inside any of the 11 installed mods), but the quote is now fabricated by
drift. `数据模组能力目录v1.md:2001, 2099, 2209` still say "本机 9 个已装 mod" and "从未在游戏内观察过";
the mod count is 11.

### C7 — a proof reported as done and as pending, in the same table

`项目状态.md:147` says `mode: "rename"` was "2026-10-17 `dsh test v13` 实机通过" and
`mode: "copy"` was "2026-10-17 `dsh test v12` 实机通过"; `项目状态.md:152` ends with
"**`v12` 已装待验**". Line 147 asserts v12 passed; line 152 (five lines later) says it is installed and
still awaiting verification.

### C8 — catalogue size stated three ways

`项目状态.md:4` "（**422 KB**）" vs `项目状态.md:163` "（**313,909 B，2,800+ 行**）" vs measured
**451,749 B / 4,143 lines**. Both doc figures are stale and they contradict each other.

### C9 — internals of the ui-textures skill

`.dsh/skills/aoe2-de-ui-textures/SKILL.md:42` "**6,504 widgets / 30 types**" vs `:82` "6,504 widgets /
**31 Types**". Measured: **31** distinct `Type` values. Line 42 is stale.

---

## Numbers re-measured

`MATCH` = reproduced exactly; `MISMATCH` = counter-evidence measured today.

| claim | doc value | measured value | verdict |
|---|---|---|---|
| `.dat` decompressed size (`项目状态.md:118`, `数据模组能力目录v1.md:16`) | 93,268,152 B | 93,268,152 B | MATCH |
| parse EOF leftover | 0 | 0 | MATCH |
| civs / techs / effects / sounds / unit headers / player colours (`数据模组能力目录v1.md:87`) | 63 / 1,510 / 1,500 / 769 / 1,701 / 16 | identical | MATCH |
| graphics slots / non-empty (`数据模组能力目录v1.md:69-71,87`) | 21,001 / 20,883 | 21,001 / 20,883 | MATCH |
| `.sld` on disk (`图形音效模组能力目录v1.md:44,297`, sprites `:33`) | 15,486 | 15,486 | MATCH |
| graphics dir total = sld+smp+slp | 15,559 = 15,486+38+35 | identical | MATCH |
| zero-byte stubs `u_shp_merchant_ship_x1/x2.sld` (`图形音效:297`) | exactly 2 | exactly 2 | MATCH |
| valid round-trip / frames (`sprites:26`) | 15,484 / 4,850,222 / 0 differing | identical | MATCH |
| x1/x2 pairing (`sprites:31-34`) | 7,743 / 7,743 / 0 orphans | identical | MATCH |
| graphics `file` non-empty; `_x1` records; `_x2` records (`图形音效:282`) | 17,359 / 8,291 / 0 | identical | MATCH |
| **files pointed at by >1 label** (`项目状态.md:146`, `图形音效:225`, `sprites:77`) | **8,656 files / 321** | **8,657 / 322** | **MISMATCH** |
| crate `name` never equals file stem (`图形音效:212`, `sprites:55`) | 0 of 8,291 | 0 | MATCH (denominator = records, not distinct names) |
| CivTechTrees files / rows (`项目状态.md:181`) | 62 / 3,686 | 62 / 3,686 | MATCH |
| tree nodes modeled (`项目状态.md:140`; `数据模组:2166,2197,2209,2334,2610`) | 287 unit / 238 tech | 287 / 238 | MATCH |
| panel-vs-dat agreement (`项目状态.md:153`; `数据模组:3261`) | 4,239 / 20 / 64 | 4,239 / 20 / 64 | MATCH |
| distinct train maps (`数据模组:3260`, dat SKILL `:334`) | 4 (56/3/3/1) | 4 (56/3/3/1) | MATCH |
| Britons tree building rows / Builder block entries (dat SKILL `:302`) | 29 / 18 | 29 / 18 | MATCH |
| **civs with a building-118 block** (`项目状态.md:143`, dat SKILL `:300`, `数据模组:3210`) | **62/62** | **67/68** (union of the two panel files; only `Gaia` lacks it) | **MISMATCH** |
| **"10 buildings appear NOWHERE in the panel file"** (`项目状态.md:143`, dat SKILL `:303`, `数据模组:3212`) | 10 of 10 nowhere | **0 of 10 nowhere** (each is a top-level block in 46–67 of 67 civs) | **MISMATCH** |
| **"6 basic buildings appear in 0 of 62 panels"** (dat SKILL `:304`) | 0 / 62 | Barracks 67/67, Mill 63/67, House 67/67, Palisade 67/67, Lumber Camp 61/67, Mining Camp 61/67 | **MISMATCH** |
| `screentechtree.json` widgets / names (`项目状态.md:154`) | 59 / 53 | 59 / 53 (58 children + named `Collection` root) | MATCH |
| **intents** (`项目状态.md:123`) | **8** | **10** | **MISMATCH** |
| **compile strategies** (`项目状态.md:124`, sprites `:17`) | **3** | **4** | **MISMATCH** |
| **`run_suites.py` suite count** (`项目状态.md:86` = 63; `:209`, `:214`, `_恢复说明:20` = 64) | 63 / 64 | **73** | **MISMATCH** |
| `run_long.py` suites (`_恢复说明:36`) | 7 | 7 | MATCH |
| committed suite artifact | `out_suites_final2.txt`, 73 `exit=0`, ALL PASSED | same (UTF-16) | MATCH |
| **`aoe2mod/` `.py` count** (`项目状态.md:165` = 28; `_恢复说明:18` = 38) | 28 / 38 | **38** | 28 MISMATCH, 38 MATCH |
| **`_probe/` `.py` count** (`项目状态.md:166` = 582; `_恢复说明:19` = 820) | 582 / 820 | **828** top-level, **1,214** recursive | both MISMATCH (582 badly) |
| workspace `.py` total (`_恢复说明:17`) | 1,337 | 1,281 (excluding this session's `_probe/team/` scratch) | MISMATCH (small; counting method) |
| **old-path file/line count** (`项目状态.md:219`, `_恢复说明:26`) | **390 files / 455 lines** | pre-fix commit: **353–354 files / 403–410 lines**; today 28 `.py` still contain `工作区2` | **MISMATCH** |
| **commit count** (`项目状态.md:219` = "两个提交"; `_恢复说明:11` = "三个提交") | 2 / 3 | **4** | **MISMATCH** both |
| **`数据模组能力目录v1.md` size** (`项目状态.md:4` = 422 KB; `:163` = 313,909 B / 2,800+ lines) | 422 KB / 313,909 B | **451,749 B / 4,143 lines** | **MISMATCH** both |
| **`aoe2-de-dat/SKILL.md` size** (`项目状态.md:164`) | 96,850 B | **147,505 B / 541 lines** | **MISMATCH** |
| **mods where Title ≠ folder name** (`项目状态.md:78`) | 8/8 | **11 mods**: 10/10 subscribed differ, 1/1 local same | **MISMATCH** |
| **installed mod count** (`图形音效:292,329,389`; sprites `:338`) | 9 | **11** (1 local + 10 subscribed) | **MISMATCH** |
| **mods shipping any `.sld`** (`图形音效:329,389`; sprites `:338`) | 0 | **1 mod ships 466 `.sld`** (`551412_村民变羊…贴图替换版`) | **MISMATCH** |
| **mods writing the DAT root that also carry `.dat`** (dat SKILL `:448`) | 5 of 5 | **6 of 6** (297820, 423821, 550749, 551103, 551420, `dsh test v13`) | **MISMATCH** |
| copy model size (`项目状态.md:147`) | 466 `.sld` / 418 MB | 466 `.sld` / 417.92 MB / 468 files | MATCH |
| `sync_engine.py` sha256 assertions (`项目状态.md:211`, `_恢复说明:37`) | 四条 | **8** `assert` statements | **MISMATCH** |
| `dat_bindings.json` `tech_fields` (dat SKILL `:38`) | `research_time` + `cost` (2) | **3 keys** — `research_time`, `cost`, `effect` | **MISMATCH** |
| `resource_labels.json` names (dat SKILL `:39`) | 328 | 328 | MATCH |
| palettes `.pal`/`.palx`; JASC-PAL 71 / PALX 1; conf ids 64–71 → `playercolor_black.pal` (`图形音效:287-289`, sprites `:328`) | 67+5 / 71+1 / 8 ids | identical | MATCH |
| `widgetui` layout JSONs / with widgets / widgets / Surround share (`ui-textures:42`) | 133 / 116 / 6,504 / 1.09% | 133 / 116 / 6,504 / 71 = 1.09% | MATCH |
| `widgetui` distinct widget `Type`s (`ui-textures:42` vs `:82`) | 30 vs 31 | **31** | `:42` MISMATCH |
| `widgetui/textures/` file mix (`ui-textures:45`) | 7,840 = 5,977 png / 1,655 dds / 206 jpg | identical | MATCH |
| `wpfg/` file mix (`ui-textures:46`) | 3,039 = 233 xaml / 2,708 png | identical | MATCH |
| `icons.json` segments / non-null values (`UI贴图:25,203`) | 14 / 2,138 | 14 / 2,138 | MATCH |
| `materials.json` ↔ `morematerials.json` overlap (`ui-textures:69`) | 199 names | 199 | MATCH (see note: `morematerials.json` exists only at `modes/Pompeii/widgetui/`, not next to `materials.json`) |
| `.box` fonts, `combined.box` size (`ui-textures:81`) | 3 files, 341,236 B | 3 files, 341,236 B | MATCH |
| `.dat` round-trip 5/5 (`_恢复说明:36`) | 5/5 byte-exact | not re-run this audit (long suite) | UNVERIFIED |

---

## Highest-risk stale claim

**`.dsh/skills/aoe2-de-dat/SKILL.md:306` — "**A write to the panel cannot add or remove a basic
building**", and its source claim at `.dsh/skills/aoe2-de-dat/SKILL.md:303` / `项目状态.md:143` that ten
basic buildings "appear NOWHERE in that civ's entire panel file".**

Why this one: it is a *closure* claim, not a stale count. It tells a future session that the JSON build
panel is structurally incapable of the thing the project's main open objective needs, so the session
will not run the experiment. But `_probe/test_panel_shape.py` — which **passes today and is registered in
`run_suites.py`** — was written specifically to refute it ("That is a misreading and this pin corrects
it"), measured **434** (basic building × civ) pairs that are absent from every `Units` array yet present
as blocks, and `数据模组能力目录v1.md:3517-3552` retracts the same claim in prose. All ten buildings are
blocks in 46–67 of 67 civs. So the doc closes a direction that the code has reopened, using the evidence
of a test whose author already apologised for it — and two of the three documents carry no correction at
all. Runner-up: `.dsh/skills/aoe2-de-sprites/SKILL.md:335-338`, which tells an operator "no in-game
verification exists" and "no local precedent", when the same file records four in-game proofs and a
466-`.sld` mod is installed on this machine.

---

## What I did not check

- **Not re-run:** `_probe/run_long.py` (7 long suites), `tools/sync_engine.py`, and any in-game
  verification. All "proven in game" claims are taken from the docs' own record; I cannot start the game.
- **Not re-implemented:** `icons.json`'s four resolution rules (R1 materials-name, R2 wpfg-strip,
  R3 wpfg-whole, R4 Notification), so `1,840 / 2,138 = 86.1%` is **unverified, not refuted**. Only the
  2,138 non-null count is confirmed.
- **Not re-measured:** `图形音效模组能力目录v1.md:254-255` grid-vs-header joins (7,602/7,618 consistent,
  16 inconsistent; 5,177 equal / 3,008 differ / 9,174 missing on disk) — these need the full
  `frame_count × angle_count` join and were out of budget.
- **Not re-measured:** byte-exact round-trip of the 15,484 `.sld` (I confirmed header facts — version 4,
  `u1` all 0, `frame_offset` 16 in 15,053 / 14 in 431 — but not a full re-serialisation).
- **Not counted:** per-civ panel block distributions for all 68 civs (I checked Britons in depth and the
  ten claimed buildings across all 67 non-Gaia civs, plus the aggregate 434 figure from the pin).
- **Not verified:** the 244-record rename figure for `dsh test v13` (the installed mod's own `info.json`
  Description asserts 244; the shipped `.dat` is 11.43 MB vs the doc's 11.98 MB — the delta is plausibly
  pre/post-compression, not checked).
- **Skipped by design:** `_会话迁移记录.md`, `_会话清理记录.md`, `插件可用清单v1.md`,
  `AoE2DE_DDS技术研究报告.md` beyond the old-root string scan; `能力目录v0.md` (explicitly superseded);
  `aoe2-de-ai-scripting` and `aoe2-de-xs` skills (not in scope).
- **Not exercised:** whether `locations.resolve_mod_name` survives the six mod `info.json` files that are
  invalid JSON under a strict parser (raw control characters inside strings). The claim at
  `项目状态.md:78` may be *right about the mechanism* and wrong only about the count.
- **Git history depth:** I read `git log` and per-commit line stats, but did not walk the pre-recovery
  commit `df7b614` file-by-file beyond the `工作区2` grep.

---

### One-line summary

The corpus is **STALE**: its measurements are overwhelmingly reproducible (`.dat` 93,268,152 B, 15,486
`.sld`, 63 civs, 287/238 tree nodes, 4,239/20/64 panel agreement — all exact), but its narrative layers
deny proofs it owns (four in-game sprite tests), assert refuted structure (panel/"NOWHERE"), and quote
file counts that have since doubled.
