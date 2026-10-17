# UI / 贴图模组能力目录 v1

> 面向"意图驱动模组工具"的**界面与贴图**方向研究结论。
> 与 `数据模组能力目录v1.md`（`.dat` 方向）互补。
>
> 所有结论均**实测**得出，复现脚本见 §11。游戏目录与用户档案目录**从未被写入**；本轮全部为静态只读研究，**未启动游戏**。

---

## 0. 一页结论

**核心判断：贴图模组是本项目**最低成本、最高确定性**的能力 —— 因为它根本不需要处理格式。**

| 能力 | 状态 | 一句话证据 |
|---|---|---|
| 用松散 PNG 替换图集里的一片贴图 | ✅ **已证明** | 一个**不含任何 `.dds`** 的已发布 mod 在实机里成功换掉了 HUD 徽章（§3） |
| 找出"该改哪个文件" | ✅ 已证明 | 控件 → 材质 → 图集 → `FileName` 四跳全链路（§3.2） |
| 不需要重打图集 | ✅ 已证明 | 引擎按 `FileName` 重读，**优先取松散文件**（§3.4） |
| 不需要创作 `.dds`、不需要 mipmap | ✅ 已证明 | mod 只用 PNG；Pillow 的 DDS 短板（无 mipmap / DX10 头）**不构成阻塞** |
| 替换贴图的尺寸约束 | ✅ 已量化 | 510 个已发布替换文件里 **508 个保持原尺寸**（§4） |
| 改文案 | ✅ 已证明 | 官方专用通道 `key-value-modded-strings-utf8.txt`（§7） |
| 改菜单 / XAML 界面 | ✅ 已证明 | `wpfg/` 是完整可读 WPF 源码，mod 覆盖实测有效（§6） |
| 游戏外离线预览 HUD | ❌ **失败** | 对齐标定一次也没收敛；原因已定位（§9） |
| 游戏内渲染（端到端） | ⚠️ **间接证明** | 有第三方 mod 的成功实例，但**我们没有自己启动游戏验证过** |
| `icons.json` 全 14 段落地规则 | ✅ 已闭合 | 非空值 2,138 个，**解析 1,840 个 = 86.1%**；未解析的 298 个**全部逐条定性，无"原因不明"剩余**（§5.3） |
| `icons.json` 是否引擎输入 | ✅ **已否决** | exe 中精确 0 命中（大小写不敏感的那 1 次是 `CustomMapIcons.json` 假阳性）；**它是编辑器侧清单，运行时真相在 `materials.json`**（§5.3.4） |

**一句话能力边界：** 贴图替换 = **复制文件**。工具的职责是把"用户看到的那个图标"翻译成"磁盘上那个 PNG 路径"，并在用户拖图进来时**自动缩放到原尺寸**。

---

## 1. 三层 UI 表层（关键：界面不止一层）

游戏把界面拆成**三套完全独立的系统**。改错层是社区最常见的失败原因。

| 层 | 路径 | 形式 | 适合改什么 |
|---|---|---|---|
| **表层 1 — `widgetui/`** | `widgetui/*.json` + `widgetui/textures/` | 4K 整数像素坐标 + 图集 | 游戏内 HUD、命令面板、资源条、小地图 |
| **表层 2 — `wpfg/`** | `resources/_common/wpfg/` | **标准 WPF XAML** + 松散 PNG | 主菜单、设置、科技树 UI、文明选择 |
| **表层 3 — 文案** | `resources/<lang>/strings/key-value/` | `id<tab>"value"` 文本 | 一切文字 |

- `widgetui/` 与 `resources/` 是游戏根下的**同级兄弟目录** → mod 里也必须同样放在自己根下的 `widgetui/`。
- `widgetui/` 有 **132 个布局 json**（根目录）+ **2 个 `.ps1`**（构建脚本）+ `templates/` 1 个 → **共 133 个布局 json**，其中 **116 个含 widget、合计 6,504 个 widget**。
- `widgetui/textures/` 共 **7,840 个文件**（png 5,977 / dds 1,655 / jpg 206）。
- `wpfg/` 共 **3,039 个文件**（png 2,708 / xaml 233 / dds 28 / ttf 24 / jpg 22 / ps 10 / dx11 10 / txt 4）。
- **决定性架构利好：游戏把图集的原始未打包 PNG 源树整个随游戏发出来了。** 我们不需要从 DDS 里反切图集。

### 1.1 参考分辨率与对齐模型（已用两个已知良好文件验证）
- 根结构：`{"Collection": {"Name", "ViewPort": {xorigin, yorigin, width, height, alignment}, "Widgets": [...]}}`
- **参考分辨率 = 3840 × 2160（4K）整数像素**。
- **对齐模型**：`Top*` → 原点在**上边**向下延伸；`Bottom*` → 原点在**下边**向上延伸。
  - 验证例：`resourcepanel.json` `(0,0,1935,228,"TopLeft")` = 顶部资源条 ✓
  - 验证例：`scorepanel.json` `(3840,2160,3840,2160,"BottomRight")` = 全屏 ✓
  - 验证例：`commandpanel.json` `(0,2159,2246,413,"BottomLeft")` = 底部命令面板 ✓

### 1.2 两个必须记住的陷阱
1. **九宫格不是贴一张图**：`Type:"Surround"` + `Box:{gridstep:32,drawbox:true}` + 9 向 `StateTL/TC/…/BR × Normal/Disabled`；面板拉伸靠引擎按 `gridstep` 切九宫格。
2. **文字 alpha 量纲不一致**：有的地方 `a:1`（float 0–1），有的地方 `a:255`（byte）。**解析器必须防御**。

---

## 2. 三族文明徽章（本项目最容易搞混的一件事）

**同一个文明有最多三套完全不同的徽章美术，分属三个不同层。** 这解释了一个长期困惑：为什么"改了徽章但截图上没变"—— 因为改的是 B 族，而看的是 A 族。

| 族 | 磁盘目录 | 文件数 | 走哪条链 | 出现在哪 |
|---|---|---|---|---|
| **V1** | `widgetui/textures/ingame/emblems/` | **62 png** | 图集 `ingamepanels` → 材质 `CivEmblem<Civ>` | **底部命令面板** `/BackgroundRight/CivEmblem` |
| **V2** | `resources/_common/wpfg/resources/civ_emblems/` | **65 png** | `icons.json` 的 `CivEmblem`/`InGameCivEmblem` 段 | **WPF 菜单层** |
| **V3** | `widgetui/textures/menu/civs/` | **79 png** | 图集 `defaultwidgets` → 材质 `<Civ>Icon` | **游戏内玩家列表 / 科技树** |

**三族的视觉差异（数值，无可争议）：**

| civ | V1 meanRGB | V2 meanRGB | V3 meanRGB |
|---|---|---|---|
| britons | `[66.1 51.1 37.6]` | `[5.8 5.8 5.8]` | `[189.7 146.5 136.1]` |
| lithuanians | `[88.5 68.1 49.4]` | `[7.3 7.3 7.3]` | `[187.9 156.5 138.8]` |

- **V2 三通道恒等 → V2 = V1 的预乘 alpha 灰化变体**（alpha 形状完全一致，RGB 被乘到近黑）→ **V2 在深色背景上几乎不可见**。
- **V2 与 V1 的一个真实差别**：V2 用复数文件名（`berbers.png`），V1 用单数（`berber.png`）。
- **★ 教训（踩过的坑）**：判断"哪个源被渲染了"**不能用 MAD/NCC 数值** —— 深色预乘的 V2 与深色背景的 MAD 天然低，数值上会赢，但视觉上是 V1 在显示。**必须以人眼/并排图为准。**
- **★ 另一条更深的原则**：**图集 DDS 才是事实来源。** 想判断"某贴图是否生效"，**第一步就是解码对应图集 DDS 切片**。实测图集是从 V1 松散 PNG 烘焙的（MAD 4.3–5.4，对 V2 则是 100–110）。

---

## 3. ★★★ 松散 PNG 覆盖图集切片 —— 已决定性证明

这是本轮最重要的结论，也是整个 UI 方向的地基。

### 3.1 一句话
**把一个 PNG 放到"图集源 `FileName`"这个相对路径上，引擎就会用它，而不理会在 `.dds` 里已经烘焙好的那片像素。**

### 3.2 证据链（四步全部实测通过）
- **A. 该 mod 不可能重打图集**：`182654_Age of Anime (Chibi Edition)` 的文件清单 = `{'.json': 1, '.png': 63}`，**`.dds` 文件数 = 0**，**没有任何名为 `atlas` 的目录**。
- **B. 控件 → 材质**：`commandpanel.json` 里名为 `CivEmblem` 的 widget 1 个，位于 `/Collection/Widgets[0]/Widget/ChildWidgets[1]/Widget`，`type: Base`，`ViewPort {403, 93, 450, 280, "TopLeft"}`，材质 `["CivEmblem"]`。
  - **注意**：widget 列表项是 `{"Widget": {...}}` **包装结构**，递归必须遍历**所有键**（不能只走 `ChildWidgets`）；`StateMaterials` 里的 `Material` 键要递归收获（`{"UserStates":1,"UserState0":{"Material":"CivEmblem"}}`）。漏掉这点会导致"找不到控件"。
- **C. 材质 → 图集 → `FileName`**：
  - **`materials.json` 里裸名 `CivEmblem` 不存在** → 引擎**运行时把当前文明名拼进去** → `CivEmblemLithuanians`。
  - 条目 `CivEmblemLithuanians` → `{'Name':'CivEmblemLithuanians','Type':'Atlas','Blend':'InverseAlpha','TextureRef':'CivEmblemLithuanians','AtlasRef':'ingamepanels'}`
  - → **`FileName = textures/ingame/emblems/lithuanians.png`**
  - 图集 `ingamepanels`：`UHDSource = textures/atlas/UHD/ingamepanels.dds`、`DefaultSource = textures/atlas/SD/ingamepanels.dds`。
- **D. mod 的松散文件正落在该 `FileName` 上**：

| | 路径 | 大小 | sha256 前 16 |
|---|---|---|---|
| MOD | `…\182654_…\widgetui\textures/ingame/emblems/lithuanians.png` | 46,774 B | `1f0f29802884fcf7` |
| GAME | `…\AoE2DE\widgetui\textures/ingame/emblems/lithuanians.png` | 57,555 B | `d7e84314f4e2afc1` |

**内容不同，且实机截图显示的是 mod 的美术（动漫少女）而非原版蚀刻纹章。**

### 3.3 配套事实
- **`materials.json` 的 `FileName` 路径基准是 `widgetui/`**，不是游戏根。（这是第一版比对脚本 62/62 全 UNMATCHED 的根因。）
- **引擎认识 `<Civ>Icon` 这类运行时拼出的名字**：exe 里 `%sIcon` 出现 1 次，其上下文含 `PlayerColor%sIcon` / `Player%sActiveIcon` / `Player%sNormalIcon` → **printf 风格运行时拼材质名**。
- **`CivIcon` 是控件 Name，`<Civ>Icon` 是材质名**：布局 json 里 `Material` 含 `"CivIcon"` 的引用 **0 个**；`materials.json` 里裸 `Civ*Icon` **0 条**（而 `Unit*Icon` 794 条、`PlayerColor*Icon` 11 条）。

### 3.4 为什么这是最大的架构利好
- **工具不需要写 DDS 编码器**：不是"不需要"，而是"根本用不到"。
- **工具不需要重打图集**：不必复刻 `texassemble` + `texconv` 流水线。
- **Pillow 的 DDS 短板全部失效**：本工具只需读 PNG / 写 PNG。Pillow 不生成 mipmap、`BC2/BC3/BC5` 写出 DX10 头这两点**不构成任何阻塞**（仅在"用户想直接给 DDS"时才相关，而那并非必需路径）。
- **失败模式是"没生效"而非"崩游戏"**：写错路径只是不覆盖，风险极低。

---

## 4. 替换贴图的尺寸约束（已量化）

**口径**：扫全部订阅 mod 的 `widgetui/` 下的 `.png/.jpg/.dds`，若其相对路径命中 `materials.json` 的 `AtlasTextures[].Textures[].FileName`（或 `GlobalTextures[].TextureDef.FileName`），用 Pillow 比对像素尺寸。

```
total on-source files: 510   same-size: 508   different-size: 2   game-missing: 0
```

**只有 2 个不同尺寸**（都来自 `550412_透明主题整合自用`，都是用同一张 500×180 图去顶替两个不同尺寸的装饰条）：

| 相对路径 | MOD 尺寸 | GAME 尺寸 |
|---|---|---|
| `textures/menu/decoration/header_ornaments.png` | (500, 180) RGBA 2,104 B | **(1167, 155)** RGBA 298,776 B |
| `textures/menu/decoration/header_ornaments_plain.png` | (500, 180) RGBA 2,104 B | **(1185, 166)** RGBA 57,491 B |

**投产规则：**
- ✅ **替换贴图应保持原始像素尺寸。** 508/510 的已发布 mod 都这么做。
- ⚠️ 上面两个尺寸不符的是"用一条装饰条顶替另一个装饰条"的取巧用法，**不应当作规范**。
- **工具行为**：导入时**自动把用户图缩放到原尺寸**并给出提示（而不是拒绝或静默变形）。

---

## 5. `materials.json` 结构与 `icons.json` 全部 14 段落地规则

### 5.1 `materials.json` 的规模与形态
| 项 | 值 |
|---|---|
| 顶层键 | `Materials` / `AtlasTextures` / `GlobalTextures` |
| `Materials` | **4,555** 条 |
| `AtlasTextures` | **40** 个图集 |
| `GlobalTextures` | **202** 条 |
| distinct atlas source `FileName` | **4,540** |
| `MaterialDef.Type` | `Atlas 4354 / Texture 193 / Color 5` |
| `MaterialDef.Blend` | `InverseAlpha 3205 / AlphaPlayerColor 1205 / None 141 / Null 1` |
| 材质 key-set | `(AtlasRef,Blend,Name,TextureRef,Type) 4346`、`(Blend,Name,TextureRef,Type) 201`、`(Blend,Color,Name,Type) 5` |
| `AtlasDef` key-set | 带 `SDSource` 的 2 个、**不带的 38 个**（`DefaultSource` 为常态） |

**材质键构成规则**（决定工具如何反查）：
```json
{"MaterialDef": {"Name": "...", "Type": "Atlas", "Blend": "...",
                 "TextureRef": "...", "AtlasRef": "..."}}
```
`TextureRef` 才是图集里的条目名，**不一定等于 `Name`**（实测 `CivAsiaResourcePanel` 的 atlas entry 为 `None`）。工具必须**先试 `TextureRef`，再退回 `Name`**。

### 5.2 ★ 官方增量通道 `morematerials.json`（抵消了本项目最大顾虑）
- 引擎**同时读** `materials.json` 与 `morematerials.json`。**exe 侧逐字确证**（@0x0325A618，两个 stem 在同一段代码里紧邻，**均无扩展名**）：
```
CommandPanel\0\0storage_point_list\0\0replace\0use_modes_path_for_mods\0linkedUnits.json\0futuravailableunits.json\0paphosfutureavailableunits.json\0\0morematerials\0\0\0materials\0\0\0\0\0\0TechTreePreviewPanel...
```
  - **注意检索方式**：`morematerials.json` 字面量在 exe 里 **0 命中**，`morematerials`（裸 stem）**1 命中** —— 引擎拼扩展名。**只搜带扩展名的形式会得出"引擎不读它"的错误结论。**
- 官方 `modes/Pompeii/widgetui/build_atlas.ps1` **以 `morematerials.json` 为读写目标**。
- **叠加语义实测**：`more` 的 `Materials` **799** 条、`main` **4,552** 条，**名称重叠 199 个** → **同名即覆盖，是"合并两份字典"而非整文件替换**。`more` 顶层键与 `main` 完全相同（`Materials` / `AtlasTextures` / `GlobalTextures`）。
- **→ 做贴图 mod 不需要重写 2.5 MB 的 `materials.json`，只需写小得多的 `morematerials.json` 追加条目。这是"增量而非替换"的官方先例。**

### 5.3 `icons.json` 全 14 段落地规则（**86.1% 解析，其余 298 个全部逐条定性**）

**四条解析规则**：
- **R1 `materials-name`**：值（或其 `TextureRef`）是 `MaterialDef.Name` → 取图集 `FileName`
- **R2 `wpfg-strip`**：值形如 `<dir>_<stem>` → `wpfg/resources/<dir>/<stem>.png`
- **R3 `wpfg-whole`**：值本身就是文件名 → `wpfg/resources/<dir>/<value>.png`
- **R4 特例**：`Notification` → 硬编码映射到 `ScorePanel*` 材质

| 段 | 条数 | 空 | 解析 | 命中规则 | 未解析（原因） |
|---|---|---|---|---|---|
| `Buildings` | 117 | 0 | **111** | R1:111 | 6 — 值是字面量 `"None"`（`046`–`051`） |
| `Units` | 1000 | 0 | **794** | R1:794 | 206 — 索引 757–999，**磁盘上确实无对应图**（`textures/ingame/units/` 只有 447 个文件） |
| `Techs` | 313 | 0 | **307** | R1:307 | 6 — `Cartography` + 5 个 `Xxx` 占位 |
| `StatIcons` | 24 | 0 | **24** | 见 §5.3.1（**需归一化匹配，不能只做 TitleCase 推导**） | — |
| `CivTechTree` | 67 | 1 | **66** | R3:66 → `wpfg/resources/civ_techtree/` | — |
| `CivEmblem` | 67 | 2 | **63** | R2:63 | 2 — `civ_emblems_inca` / `civ_emblems_berber`，**磁盘用复数** `incas` / `berbers` |
| `InGameCivEmblem` | 63 | 1 | **60** | R2:60（去 `ingame_` 前缀） | 2 — 同上复数问题 |
| `CivHero` | 67 | 1 | **0** | — | 66 — **未使用段**（见 §5.3.5） |
| `CivUniqueUnit` | 65 | 0 | **65** | R1:62 + R3:3 | — |
| `CivSecondaryUniqueUnit` | 65 | 0 | **61** | R1:24 + R3:37 | 4 — 值是**逗号拼接的两个 id**（`UnitIcons39150730,UnitIcons39250730`），拆开后两个都在 Materials 里 |
| `MapIcons` | 217 | 20 | **197** | R3:197 → `wpfg/resources/mapicons/` | — |
| `History` | 87 | 0 | **87** | R3:87 → `wpfg/resources/history/` | — |
| `Notification` | 2 | 0 | **2** | R4 | — |
| `MenuIcons` | 9 | 0 | **3** | 见 §5.3.3（`submenu_oligarchy/democracy/tyranny` → Return of Rome 政体科技图标） | 6 — **真死条目**（见 §5.3.3） |

**合计：非空值 2,138 个，解析 1,840 个 = 86.1%。**
（此前记录为 1,819 / 85.1%；本轮 `StatIcons` 由 6 → **24**（+18）、`MenuIcons` 由 0 → **3**（+3），差额 +21 恰好对上。）

**未解析的 298 个全部已逐条定性**（无"不知道原因"的剩余）：
| 原因 | 数量 |
|---|---|
| `Units` 槽位本身无图（磁盘只有 447 个 `%03d_50730.dds`，缺失从索引 757 起） | 206 |
| `CivHero` 整段未落地（§5.3.5） | 66 |
| `MenuIcons` 真死条目（§5.3.3） | 6 |
| 值就是字面量 `"None"`（`Buildings` 的 `046`–`051`） | 6 |
| `Techs` 占位（`Cartography` + 5 个 `Xxx`） | 6 |
| `CivSecondaryUniqueUnit` 逗号拼接需拆分（4 条，拆开后两个 id 都在 `Materials` 里） | 4 |
| 磁盘用复数文件名（`incas`/`berbers`；`CivEmblem` 与 `InGameCivEmblem` 各 2） | 4 |

#### 5.3.1 `StatIcons` 段 —— 24/24 全解（**这条修正了此前"6+18、1 未解析"的记录**）

**规则必须写成"归一化匹配"，不能写成单一推导函数。** 该段取值风格**逐条不一致**，四种形态混用：

| 形态 | 条数 | 例子 | 解析法 |
|---|---|---|---|
| `stat_icon_<x>` → `StatIcons<TitleCase(x)>` | 12 | `stat_icon_armor` → `StatIconsArmor` | 直接推导 |
| `stat_icon_<x>` → 需归一化（大小写/标点） | 6 | `stat_icon_movement_speed` → `StatIconsMovementSpeed`；`stat_icon_range_armor` → **`StatIconsRange-Armor`（材质名里带连字符！）** | 去非字母数字后小写比对 |
| 裸值本身即材质名 | 6 | **`stat_icon_powerup` 本身就是一个材质名**；5 个 `StatIconsPowerUp*`（`Armor`/`Range`/`Regeneration`/`ReloadTime`/`MovementSpeed`）**是 PascalCase 原值，推导会得到错误的 `StatIconsPoweruparmor`** | 先查精确名 |
| 子串归一化才能救 | 1 | `stat_icon_hpregen` → **`StatIconsHpRegeneration`**（**不是等长**，`hpregen` 是 `hpregeneration` 的截断） | 去标点小写后子串匹配 |

**统一规则（推荐实现顺序）**：① 精确查 `MaterialDef.Name`；② `StatIcons + TitleCase(去前缀)` 精确查；③ 去非字母数字小写后精确查；④ 去非字母数字小写后按 `StatIcons` 前缀做唯一子串匹配。**四步走完 24/24 全中。**

解析结果（全部 `atlas=ingamepanels`，`FileName` 均在磁盘存在）：`powerup.png`、`armor.png`、`convert.png`、`damage.png`、`food.png`、`garrison.png`、`gold.png`、`hp.png`、**`hpRegen.png`**、`movementSpeed.png`、`pierceAttack.png`、`hpLoss.png`、`range.png`、**`range-armor.png`**、`reloadtime.png`、`stone.png`、`transport.png`、`wood.png`、`workrate.png`、`powerup_armor.png`、`powerup_range.png`、`powerup_regeneration.png`、`powerup_reload.png`、`powerup_speed.png`。

**★ 引擎侧硬证据（决定这条规则不是我们的臆测）**：exe 串池里硬编码了 10 个 `<MATERIAL=StatIconsXxx,1>` 富文本标记 —— `StatIconsFood/Wood/Stone/Gold/Hp/Damage/Range/Armor/Garrison`，以及 **`StatIconsRange-Armor`**（连字符形态在引擎里逐字存在）。另有 `StatIconsAge1..4` 字符串与 `StatIconsAge` 前缀。
- → **`StatIcons*` 家族是引擎直接按名字引用的**，所以它必须存在于 `materials.json`；`icons.json` 只是在旁边记录同样的名字。

**走另一个图集的 4 个**：`StatIconsAge{1,2,3,4} → atlas=ingameicons → textures/ingame/icons/age-{1,2,3,4}.png`（**注意不是 `staticons/`**）。

**存在但 `icons.json` 不引用的**（引擎侧/未来用途，工具不应删除）：`StatIconsDamageBleed`、`StatIconsDamageBypass`、`StatIconsPierceAttackBleed`、`StatIconsPierceAttackBypass`、`StatIconsBlastRadius` —— 共 **32 个 `StatIcons*` 材质**。

#### 5.3.2 `Notification` 段 —— 2/2，规则是**硬编码别名映射**
`icons.json` 逐字：`{"000": "wonder_icon", "001": "relic_icon"}`。**值不是材质名，是语义别名**，指向另一族材质：
- `wonder_icon` → 材质 `ScorePanelWonder` → `atlas=defaultwidgets` → **`textures/ingame/icons/indicator_wonder.png`**
- `relic_icon` → 材质 `ScorePanelRelic` → `atlas=defaultwidgets` → **`textures/ingame/icons/indicator_relic.png`**

（反向按 `FileName` 索引恰得唯一命中，无歧义。无关家族：`WonderBanner{0..10}` 13 个、`RelicEvent` 1 个。）

#### 5.3.3 `MenuIcons` 段 —— 3/9 解出，6 条是**真死条目**（**这条修正了此前"9 条全 0 命中"的记录**）

**已解出的 3 条** —— **Return of Rome 政体科技**（`submenu_<X>` → `TechIconsT<id><X>`）：

| 值 | 材质 | 图集 | FileName | 磁盘 |
|---|---|---|---|---|
| `submenu_oligarchy` | `TechIconsT155Oligarchy` | `ingametechs` | `textures/ingame/tech/155_oligarchy.dds` | ✅ |
| `submenu_democracy` | `TechIconsT156Democracy` | `ingametechs` | `textures/ingame/tech/156_democracy.dds` | ✅ |
| `submenu_tyranny` | `TechIconsT154Tyranny` | `ingametechs` | `textures/ingame/tech/154_tyranny.dds` | ✅ |

**发现经过（方法可复用）**：这 3 条在 `materials.json` 里**精确名查不到**（名字带 `TechIconsT<id>` 数字段），所有机械化归一化都失败。**钥匙是 exe 的相邻字符串**：

```
@0x0320FFF0  ...C-Bonus, Lumberjack food + Two-Man Saw\0\0Monoreme\0...Oligarchy\0\0Bireme\0...Democracy\0...Trireme\0Tyranny\0Galley - Antiquity\0\0Reset Oligarchy\0War Galley - Antiquity\0\0Reset Democracy\0Elite Galley\0\0Reset Tyranny\0\0Incendiary Raft...
@0x032101D0  ...Transport Ship (Antiquity)\0...Initial Oligarchy researched\0...
```

`Oligarchy`/`Democracy`/`Tyranny`（政体名）与 `Monoreme`/`Bireme`/`Trireme`（Return of Rome 战船）在串池里相邻，且存在配套的 `Reset Oligarchy/Reset Democracy/Reset Tyranny`（科技重置，就是这 3 个政体互斥的机制）→ 据此到 `materials.json` 里按**尾词匹配** `TechIconsT*<X>` 命中。**若不去 dump exe 上下文，这 3 条会和另外 6 条一起被误判为死条目。**

**判定为死条目的 6 条**：`submenu_button_base`、`submenu_open_arrow_overlay`、`submenu_return_arrow_overlay`、`submenu_open`、`submenu_return`、`mutually_exclusive_tech_unavailable`。**穷举阴性**（8 条独立检查，全部 0 命中）：
1. `materials.json` 的 `Name`/`TextureRef` 精确查：0
2. 任何树内文本文件（含大小写不敏感）：只命中 `icons.json` 自身
3. exe 精确大小写：0
4. exe UTF-16LE：0
5. exe 子 token（`mutually_exclusive` / `tech_unavailable` / `open_arrow` / `return_arrow` / `button_base` / `MenuIcons` / `menu_icon`）：**全部 0**
6. 官方文件名归一化规则 5 种候选形态：全不匹配
7. 磁盘上任何名含 `submenu` / `open_arrow` / `return_arrow` 的 PNG：0 个
8. `wpfg` 树里路径含 `submenu` 的文件：**0 个**

**易混淆项（不是它们的消费者）**：exe 里 `submenu` 有 22 处命中，但全部属于**别的语境** —— `Exit Submenu` / `Open Submenu 0..4`（**这是 AoE1 的购买菜单**）、`Submenu %d button pressed`、`GameScreen::command_build_contexual_buttons_setup_widget (dynamic_submenu)`、以及 WPF 的 `SubmenuHeaderTemplateKey` / `SubmenuItemTemplateKey` / `SubmenuOpened` / `SubmenuClosed` / `IsSubmenuOpen`。**不要把这些当成 `icons.json` 的消费者。**
**相关但不同名的真实材质**：`SubMenu*` 家族 15 个（`SubMenuSmallTabLeftActive`…`SubMenuTabRightNormal`，`atlas=menutabs`，`file=textures/menu/tabs/innertab_*.png`）与 `Menu*` 家族 58 个。

→ **工具应把 `MenuIcons` 段的这 6 条按"无资产"处理（渲染占位符），不要报解析错误。**

#### 5.3.4 ★★ 决策性结论：`icons.json` 不是引擎输入

**证据链**：
- **`icons.json` 在 exe 中精确命中 0 次**；大小写不敏感的 1 次命中是**假阳性** —— 那个字符串是 **`CustomMapIcons.json`**（不同的文件，位于 `ScreenMapSelection`/`custommaps` 上下文，带 `iconRef` 字段）。
- **对照：`materials` 在 exe 里 3 次、`morematerials` 1 次、`buttons.json` 1 次、`CustomMapIcons.json` 1 次、`objreplacement.json` 1 次、`futuravailableunits.json` 1 次** —— 这些都**被引擎点名**。
- **`morematerials` 的 exe 上下文逐字**（@0x0325A618，与 `materials` 紧邻）：
```
CommandPanel\0\0storage_point_list\0\0replace\0use_modes_path_for_mods\0linkedUnits.json\0futuravailableunits.json\0paphosfutureavailableunits.json\0\0morematerials\0\0\0materials\0\0\0\0\0\0TechTreePreviewPanel...
```
  → **`morematerials` 与 `materials` 是同一段代码里紧邻读取的两个 stem（无扩展名）**，这从引擎侧确证了 §5.2 的"同时读、增量合并"结论。
- 没有任何 widgetui 布局 json 直接引用松散徽章贴图；布局里 `Material` 含 `"CivIcon"` 的引用 **0 个**（`CivIcon` 是控件 `Name`，`<Civ>Icon` 是引擎用 `%sIcon` 运行时拼出的材质名）。
- → **`icons.json` 是 UI 编辑器/工具侧的资产清单，不是引擎读取的运行时输入。** 引擎的运行时真相链是 **`材质名 → materials.json → 图集 FileName`**。
- **对工具的决策含义**：可以读 `icons.json` 来获得**人类可读的分类与编号**（它是官方给的"哪张图属于哪个实体"的现成表），但**任何"某贴图是否生效/从哪来"的判断都必须落回 `materials.json` + 磁盘文件 + 图集 DDS**。**不要把 `icons.json` 当作运行时契约。**

#### 5.3.5 `CivHero` 段 —— 0/66，**未使用段**（与其它段同构但不落地）
- 段有 67 槽，**非空 66**，取值形如 `civ_hero_britons`、`civ_hero_franks` … `civ_hero_varangians`、`civ_hero_danes`，末尾 4 个是**非 civ 的特殊槽**：`civ_hero_random`、`civ_hero_mirror`、`civ_hero_fullrandom`、`civ_hero_custom`。
- **它是 `CivEmblem`（`civ_emblems_<civ>` → `wpfg/resources/civ_emblems/`）与 `CivTechTree`（`menu_techtree_<civ>` → `wpfg/resources/civ_techtree/`）的同构兄弟** —— 名字格式完全一致，只是 `<dir>` 段换成 `civ_hero`。
- **但该目录不存在，且没有任何替代位置**：
  - `wpfg/resources/` 下 **78 个子目录**已逐一枚举，**没有 `civ_hero`**（`civ_emblems` 65 文件、`civ_techtree` 232 文件、`history` 94 文件都在）。
  - **全树 `resources\_common\wpfg\` 下名为 `*hero*` 的目录只有 2 个**：`WPFUI\Paphos\Campaign\Resources\Images\Heroes` 与 `WPFUI\Paphos\Campaign\Resources\Images\Providence\Heroes` —— **是 Paphos 战役的插画目录，与 per-civ 菜单图标无关**。
  - `widgetui\textures\menu\` 下 **23 个子目录全部枚举**，无 hero 目录（`civs` 79、`history\civs` 45、`icons` 128、`timeline` 78…）。
  - **全树文件名同时含 `hero` 与任何 civ 词干的文件 = 0**（`drs\graphics\` 里的 `u_*_hero_*` 是**单位动画**，不是 civ 图标）。
  - exe 中 `civ_hero` / `civhero` / `civheroes` **精确与大小写不敏感均 0 命中**（对照：`civ_techtree` **9 命中**）。
  - **`widgetui\` 下全部 json 中，提到 `civ_hero_` 的只有 `icons.json` 自己**。
- 另一条弱线索：`widgetui\textures\ingame\panels\frame_hero.png` 与 `widgetui\textures\ingame\buildings\095_hall_of_heroes.dds` 存在，且布局里有 `HallOfHeroes`（4 次）、`Background/UnitsPanelAnchor/ButtonHeroes`（各 1 次）、控件名 `CivHero`（1 次）—— **说明界面里有"英雄"概念，但用的是 `ButtonHeroes` 控件 + 单位动画，不是这套 per-civ 图标。**
- **判定：`CivHero` 是随游戏一起分发的、从未落地的资产清单段**（很可能对应某个未发布的"文明英雄"菜单）。**工具应把它按"无资产"处理，不要报解析错误，也不要为它生成占位图以外的东西。**

#### 5.3.6 `icons.json` 段行号区间（权威，便于工具按行定位）
`Buildings` 2–120、`Units` 121–1122、`Techs` 1123–1437、`StatIcons` 1438–1463、`CivTechTree` 1464–1532、`CivEmblem` 1533–1601、`InGameCivEmblem` 1602–1666、`CivHero` 1667–1735、`CivUniqueUnit` 1736–1802、`CivSecondaryUniqueUnit` 1803–1869、`MapIcons` 1870–2088、`History` 2089–2177、`Notification` 2178–2181、`MenuIcons` 2182–2193。

**关键细节：**
- **`MapIcons` 已闭合到 `maps.json`**：`maps.json` 有 194 条 `map_list`，每条含 `map_icon_filename`（如 `"rm_arabia"`）；`MapIcons` 段 197 个非空值**全部 197/197 在磁盘命中**，落在 `wpfg/resources/mapicons/`（同时 `mappoolicon/` 也有同名副本）。
  - `maps.json` 条目完整字段池：`const_name / data_name / name_string_id / rollover_string_id / icon_reference / map_icon_filename / script_filename / storage_id / style / land / open / random_map / death_match / regicide / king_of_the_hill / capture_the_relic / sudden_death / defend_the_wonder / wonder_race / empire_wars`。
  - **`maps.json` 可用命令行开关 `+WRITE_MAP_INFO` 从游戏导出**（文件内注释明示）。
- **`Notification` 的规则是硬编码映射**：`wonder_icon` → `ScorePanelWonder`、`relic_icon` → `ScorePanelRelic`（两者都在 `Materials` 里，指向 `defaultwidgets` 图集的 `textures/ingame/icons/indicator_wonder.png` / `indicator_relic.png`）。
- **`MenuIcons` 已部分解出（3/9）**：`submenu_oligarchy` / `submenu_democracy` / `submenu_tyranny` 是 **Return of Rome 政体科技图标**（→ `TechIconsT155Oligarchy` / `T156Democracy` / `T154Tyranny`）；其余 6 条经 8 项独立检查全部阴性，判为**真死条目**。**详见 §5.3.3。**
- **`CivHero` 同理**：段有 66 个非空值（形如 `civ_hero_britons` … `civ_hero_custom`），但 `civ_hero_*` 目录与文件名在磁盘/exe 均 0 命中 → **未使用段**。**详见 §5.3.5。**
- **`StatIcons` 的特殊命名**：**24/24 全解，但必须用"归一化匹配"而非单一推导**（4 种取值形态混用，含材质名内嵌连字符的 `StatIconsRange-Armor`、截断式的 `stat_icon_hpregen` → `StatIconsHpRegeneration`）。引擎侧硬编码 10 个 `<MATERIAL=StatIcons…,1>` 标记可佐证。**详见 §5.3.1。**
- **`Units` 的 206 个缺口是数据本身的稀疏性，不是解析错误**：`icons.json` 有 1000 个槽位，但 `textures/ingame/units/` 只有 **447 个 `%03d_50730.dds`**，缺失从索引 **757** 开始。工具应把无图的槽位渲染为占位符。

### 5.4 图集构建流水线（官方机制，工具可选复用）
`widgetui/build_atlas.ps1` + `build_all_atlases.ps1`（40 个图集名）：
1. 读 `materials.json` → 取 `AtlasDef.MaxWidth/Height` 向上取整到 8 的倍数
2. `texassemble.exe atlas -flist`
3. `texconv.exe` 转 DDS（UHD/HD = `BC7_UNORM -m 1`；SD = `BC3_UNORM -m 1` 且尺寸减半）
4. 回写 `materials.json`

`texturetoatlasjson.ps1` / `texturetotexturejson.ps1` 是**官方给 mod 作者的 JSON 生成器**，硬编码命名规则：
> **`文件名 → ToTitleCase(ToLower()) → 删除 '_' 和 '-' → 加前缀 = RefName`**

**这是"文件名 ↔ RefName"映射的权威规则。** 但 §3 已证明：**工具通常不需要走这条流水线。**

---

## 6. `wpfg/` 菜单层（表层 2）

- **完整 WPF 界面源码随游戏分发，可读可改。**
- 结构：根 57 个 `SystemResources*.xaml` + `screen/` 32 + `dialog/` 30 + `panel/` 5 + `tab/` 28 + `WPFUI/` + `resources/` 2,166 + `fonts/` 13 TTF。
- **mod 覆盖已实测**（`550412` 放了 50 个 wpfg 文件）。
- **XAML 直接按路径加载 PNG**，实证：
  ```
  resources/_common/wpfg/WPFUI/Peru/Campaign/Components/PeruCampaignTimeline.xaml:59
  ImageSource="{Binding Source=resources/civ_emblems/shu.png;
                            Resources/Images/civ_emblems/shu.png,
                            Converter={StaticResource ResolveWPFGAsset}}"
  ```
- **产品含义**：改菜单界面 / 换 logo / 主菜单按钮，**这一层比 `widgetui/` 更好用**（标准 XAML，控件有名字有布局，不是 4K 像素坐标）。
- **`wpfg/resources/` 目录清单（工具的资源浏览器应当内置这份索引）**：
  `Icons` 37 / `battleroyale` 5 / `button_large` 14 / `button_mixer` 4 / `button_player_icon` 4 / `button_small` 94 / `button_xbox` 4 / `campaign` 44（含 22 个子战役目录、`campaign_selection/campaign_icons` 91、`historical_battles` 51、`challenge_missions` 158、`medals` 3）/ `challenges` 7 / `checkbox` 14 / **`civ_emblems` 65** / **`civ_techtree` 232** / `credits` 1 / `dialog` 15 / `empireicons` 36 / `gamemode` 11 / **`history` 94** / `ingame/chat` 10 / `ingame/icons` 19 / `mainmenu` 13 / **`mapicons` 209** / **`mappoolicon` 185** / `news` 11 / `panel` 5 / `preferred_random` 6 / `quickplay` 3 / `rematch` 20 / `ribbon` 17 / `scroll` 13 / `seperator` 2 / `simplemainmenu` 20 / `small_icons` 5 / `tab` 20 / `timeline` 18 / `uniticons` 97 / **`usericons` 433**。

---

## 7. 文案层（表层 3）与官方 mod 字符串通道

- 字符串文件格式：**UTF-8、无 BOM、CRLF**，语法 `id<tab>"value"`，支持 `//` 注释。
- 规模：17 语言 × 13 文件，合并出 **36,351 个数字 ID**。
- **`LanguageDLLName` 不是 DLL 引用**：游戏树内**不存在任何 `language*.dll`**（全树递归 0 命中）→ **DLL 机制已死，本地化 100% 走 key-value 文本文件**。
- **★★ 官方专用的 mod 字符串通道：`key-value-modded-strings-utf8.txt`**
  - 17 个语言目录各一个；游戏侧只有 **605 B 注释头**。
  - 原文说明：*"When you create any mod by creating a directory inside Steam, certain files will automatically copy over… If you want to replace or add any strings, place them in this file and when the mod is enabled, these strings will also be added. The english string file is a global fallback… do not delete them from the original file."*
  - → **改文案只需把要改的行放进该文件，引擎合并。** 实测两个文本 mod 全用这条路，**都没碰** `key-value-strings-utf8.txt`（1,965,572 B）。

---

## 8. mod 的真实机制（工具必须实现的读写面）

### 8.1 mod 根与 `info.json`
- **mod 根 = 含 `info.json` 的那个文件夹**，内部子目录**直接镜像游戏根**（`widgetui/`、`resources/` 与 `info.json` 同级），**不额外包一层 `resources/`**。
- **实测 8/8 个 mod 的键集恒为 `['Author','CacheStatus','Description','Title']`**；同级有 `thumbnail.png` 或 `thumbnail.jpg`。
- **★ 解析必须用 `json.loads(txt, strict=False)`**：`Description` 里含**裸 `\r\n` 控制字符**，严格模式会报 `Invalid control character at: line 1 column 102 (char 101)`。**（曾被误判为"中文乱码"。）**
- **exe 里的可选字段线索**（按相邻顺序）：`info.json` → `Validating '%s'` → `Author` → **`Unpublished`**（可见性私有）→ **`No Description`**（占位默认值）→ `CacheStatus` → **`mainmenu_bg.dds`** → **`previewIcon`** → **`thumbnail`**。
- `requiredMods` 在 exe 中 **0 命中**；`dependencies` 1 命中但与 mod 无关。

### 8.2 `mod-status.json`（工具必须能读写）
官方 schema（exe 逐字确认，按相邻顺序）：
```
mod-status.json → Unsub → local// → subscribed// → local//%s → subscribed//%s
  → WorkshopID → PublishID → LastUpdate → Priority → Enabled → CheckSum
  → creatorName → Update → ModManager::SubscribeToMod
```
- 实测本机 **7 个 mod**，`Priority` 连续 **1..7**，`Unsub = []`，**每条 Path 都存在**。
- **★ 纪律**：`Priority` 是加载优先级（**数值越小越先加载 → 后加载的优先**）。工具**必须对 Path 做存在性校验**（目录可能被用户手动改名），但不应据此宣称游戏自身会失配。

### 8.3 路径与大小写
- **mod 文件夹名是 UTF-8**。
- **文件名大小写是承重的**（音效方向已实测；贴图方向同理）。
- **重命名本地 mod 文件夹触发过 "tampering detected" 锁死** → 工具**不应**替用户改名，只应改 `mod-status.json`。

### 8.4 发布器的官方校验（工具应前置做这些检查）
- **UGC 分类标签（= 发布 tag 枚举）**：`TAG_ANY TAG_AI TAG_CAMPAIGN TAG_DATA TAG_GRAPHIC TAG_MOVIE TAG_MUSIC TAG_RANDOM TAG_SCENARIO TAG_SOUND TAG_SPEECH TAG_TAUNT TAG_TERRAIN TAG_MENUBACKGROUND TAG_UI TAG_TEXT TAG_OFFICIAL TAG_EVENT TAG_GAME_VARIANT_RETURN_OF_ROME`
- **错误枚举**：`ERROR_ZIP ERROR_THUMBNAIL ERROR_MISSING_FILE ERROR_BAD_FILES ERROR_IMAGE_FORMAT ERROR_VIDEO_FORMAT ERROR_MISSING_FIELDS ERROR_NO_TITLE_ID ERROR_PUBLISH_FAILED ERROR_MOD_DB_SAVE_FAILED ERROR_IMAGE_DB_SAVE_FAILED ERROR_DELETED`
- **`IDS_MODMGR_ONLY_PNG`** → 发布器对图片有"只允许 PNG"的校验。
- **`IDS_MODMGR_BANNED_CHARACTERS`** → 文件名/标题有禁用字符集，工具必须在命名时预检。
- **★ `IDS_MODMGR_DATAMOD_SCENARIO_WARNING` / `IDS_MODMGR_DATAMOD_UNEXPECTED_WARNING`** → **官方自己在 UI 上承认"数据 mod 与场景 mod 混用会出问题"**。
- **★ `IDS_MODMGR_VALIDATION_ERROR` / `_DISABLE`** → 校验失败时游戏会**禁用**该 mod（解释了"游戏更新后 mod 被自动禁用"）。
- **官方文档承认的已知缺陷**：① 游戏更新后 mod 会被自动禁用；② 文件夹名/结构不对就静默失效；③ **「把数据 mod 与 UI/内容 mod 合并」的功能"看起来又坏了"** → **工具必须把数据 mod 与贴图/UI mod 拆成两个 mod 交付。**

### 8.5 覆盖的真实语义（没有中心清单）
**Mod 覆盖 = 同名文件按 `Priority` 顺序落在镜像路径上、由本地值覆盖 base 值，没有中心清单。**
- **`replace=false` ≠ mod 不可覆盖**：实测 `DAT` / `WPFG` / `WIDGETUI`（`Pompeii.json` 里均标 `false`）**都被 mod 成功覆盖**。
- **存储点完整枚举 = 47 个**：`LOGS SP_SAVEGAMES MP_SAVEGAMES SCENARIOS CAMPAIGNS AI CREDITS DAT DRS FONTS PALETTES MOVIES SPRITES SPRITES_LOW SLP CURSORS AUDIO_CIVTHEME AUDIO_MUSIC AUDIO_SFX AUDIO_AMBIENT AUDIO_TAUNTS TERRAIN TEXTURES RANDOM_MAPS COMMON_STRINGS STRINGS SHADERS PARTICLES PACKAGES PROFILE ACHIEVEMENTS CAMPAIGN_MOVIES CAMPAIGN_SOUNDS SCENARIO_SOUNDS WIDGETUI WPFG WWISE WWISE_EXTERNALS TESTHARNESS TESTHARNESS_SCRIPTS TESTHARNESS_REPORTS TESTHARNESS_REG_SAVES PERFORMANCE_TEST_GAMES XS TESTHARNESS_XS TELEMETRY SCENARIO_EDITOR`
- **根/来源枚举**：`COUNT NONE NOTFOUND TEMP BASE APPATA USER MODSROOT LOCALMODS SUBSCRIBEDMODS DLC CLOUD` → **mod 覆盖是逐存储点解析，不是简单文件查找**。
- **★ `modes/` 不可被 mod 覆盖**（全盘只有 1 个 `modes` 目录；9/9 已装 mod 无 `modes/`）；"有哪些 mode"**编译进 exe**。`modes/Pompeii/Pompeii.json`（3,205 B，全树唯一）是官方的**存储点注册表**，格式 `{replace?, type, path}` —— **这是官方的"插件清单格式"，我们的插件化内核可直接照抄该 schema。**
- **★ dat 旁路 JSON 也是可覆盖面**：实测真实 mod 覆盖过 `resources/_common/dat/linkedTechs.json`（4,203 B vs 游戏 3,947 B）与 `civilizations.json`（改 1 个字段 + 换 tech id）。Pompeii 的 dat JSON 多为**"官方最小 stub"**（`linkedTechs` 3947→235、`sharedbuildings` 2956→22、`eras` 8978→754）→ **同名 JSON 合并/覆盖，且允许只写需要的部分。**

### 8.6 一个必须实现的工具功能：识别冗余文件
实测 `182654`(prio1) 与 `550412`(prio2) **共享 60 个路径**，其中 59 个 `widgetui/textures/ingame/emblems/*.png` **两侧字节完全相同** → **`550412` 原封不动打包了 `182654` 的整套徽章**。
另有一批 `550412` 的 wpfg 文件（`scroll/knot.png` 3,305 B、`scroll/slider2_panel.png` 37,174 B 等）**与游戏侧字节数完全相同 → 打包了但内容未改**。

→ **工具的增量打包必须能识别"内容未变"的冗余文件**（否则会给用户产出无意义的 diff）。

---

## 9. 离线 HUD 渲染器：**成功**（本节 9a 是失败记录，9b 起是重做后的结果）

> **本轮更新**：9a 的 `❌ 失败` 已被 9b 的**成功**取代，产物在 `_probe\hud_render\`（`HUD_RENDER_REPORT.md`、`HUD_COMPARISON.png`、`HUD_COMPOSITE.png`、`hudrender.py` + 33 个探针脚本）。**9a 保留下来，因为失败机制本身是结论**；但 9a 结尾那句"需要多张不同 HUD 缩放设置的截图 —— 这是唯一缺的输入"被证明是**伪需求**（见 9b①）。

### 9a. 第一版：失败及其原因（保留）

**目标**：证明能否**只用游戏自带文件、在游戏外忠实重绘游戏内 HUD**。
**第一版结果：失败。** 对齐标定一次也没有收敛。

| 探针 | 结果 |
|---|---|
| `align_scale.txt` | 推出三组互不相容的比例：`2.5333` / `0.1190` / `1.0550` |
| `align_art.txt` | `CONSISTENCY delta +0.7660`（不自洽） |
| `cmp_resource.txt` | **GLOBAL MAD 78.55**，只有 **4.2%** 像素每通道差 ≤8 |
| `plank_identity.txt` | 17 个候选面板贴图对同一观察裁切，**最高相关才 +0.39** |

**失败机制已定位（这是有价值的结论）：**
1. **参考分辨率 3840×2160，但截图像素是 2730×1535（比 0.7107），且 HUD 另有自己的缩放设置**（实测有效比例 ~0.598）—— **两者不是简单等比**。
2. **HUD 半透明混合地形**：观察值 = `a·A + (1−a)·T`，其中 `T` 是地形。直接像素比对被地形污染。

**若要重做，必须：**
- ① 先解出**真实 HUD 缩放与锚点**（需要**多张不同 HUD 缩放设置的截图**做标定 —— 这是唯一缺的输入）；
- ② 按 `TextureRef` 反查图集取艺术（不要按 `Name`）；
- ③ 承认观察值 = `a·A + (1−a)·T`，**必须先减掉地形项**。

### 9b. ★★ 重做：**成功**（`_probe\hud_render\HUD_RENDER_REPORT.md`）

**与 9a 的差别不是"再试一次"，而是找回了 9a 自己没有的三个输入。**

**① 真实 HUD 缩放 = `0.5980`，不是 `2730/3840 = 0.7109`。** 游戏在 backbuffer 之上**再乘一次 HUD 缩放**（额外因子 `0.8411`）。标定方法：**只拟合布局自己声明的盒子位置**（`box i = (15+200i, 15, 84, 84)`），5 张截图给出**完全相同**的解、`dx=dy=0`，并用叠加图视觉验证。→ **9a 缺的"多张不同 HUD 缩放设置的截图"其实是伪需求：只要拟合的是布局里写死的几何，单组截图就足够。**

**② 五张参考截图是同一局、相机在移动 → 跨帧标准差 = `(1−alpha)·std(terrain)`，是一个与色调无关的 alpha 直接读数。** 这就消掉了 9a 称为致命的地形项。仪器零点在已知不透明美术上校验为 `std ≈ 1.6`。

**③ 用该探针证明参考截图显示的是 UI 模组而非原版美术。** 在原版声明 `alpha ≥ 250` 的地方（原版预测观测 `std ≈ 0`），实测 `std = 8.11`，而地形是 `14.16`，模组模型预测 `7.05`。启用的 `透明主题整合自用`（WorkshopID **550412**）带 **33 个名字匹配的面板贴图**，其面板与原版 **RGB 逐字节相同、alpha 恰好 ×0.502**。相关性：模组美术 `+0.9083`，原版 `−0.2686`。把渲染器改成模组感知（`--mod`）后：**MAD `50.56 → 23.62`，corr `+0.49 → +0.72`**。
> **★ 这是本节最重要的一条：此前所有"对不上"的测量，都是在拿观察值与原版美术比。**

**④ 美术路径可证精确。** 对全部 4,354 个图集材质，「归一化 UV 范围 × 图集尺寸 = 随游戏发布的松散 PNG 的像素尺寸」：**4,329 项检查、0 处不符** → **HUD 美术 = `crop()` 一张 PNG，任何时候都不需要解码图集 DDS。**

**成绩（诚实的口径）**：

| 项 | 结果 |
|---|---|
| `resourcepanel.json` 保真度 | 面板主体 **MAD 11.21**，而**对照下限是 11.8–14.7**（四个美术已独立验证的图标）→ **在存在地形不确定度的前提下，与原版美术统计上不可区分**。平均色差 Δ≈(9,0,8)/255；叠加图上图标/人口框/空闲徽章/勋章**全部重合** |
| `resourcepanel.json` 控件 | 22 个 widget → **9/10 个美术 widget 解析（90%）**，19/22（86.4%）渲染出正确美术或文本；1 个失败（`AgeUp`），2 个**按设计**无法静态渲染（有字体无 Text 字段，值由游戏给） |
| `scorepanel.json` | **9/9** 九宫格片解析成功，**失败日志为空（0 条）** |
| 渲染器 | **没有灰色占位符路径**：解析不了就是**缺席**，从不伪造 |
| 聚合 MAD | 23.62 —— 但被**不属于美术保真范畴**的控件拉高（`AgeBar`/`AgeTextLabel` 占 `alpha>0.78` 带内的 10,047/10,578 px）。**两个数都要报，并说明构成** |

**⑤ 诚实边界：`scorepanel.json` 没有任何屏幕空间参照物。** 在 `0.598` 比例下它预测 `(2057,837)` 处的 239×239 矩形；把该尺寸窗口全部 2,079 个位置扫过整帧，该位置只排到**第 24 百分位**，而**最静止的窗口（std 2.90）仍远高于已知不透明零点（~1.6）**。看图确认那个窗口是**小地图**，其上方面板是**玩家列表** → **计分面板是一个可开关的浮层，五张截图里都没有。** 因此对 `scorepanel.json` **只声称"9/9 片解析成功、失败日志为空"，不声称任何屏幕空间一致性。**

### 9c. `FontIndex` —— **不是阻塞项**（9a 曾怀疑是）

`FontIndex` 是**引擎已注册字体图集列表的 0 基下标**，按注册顺序 = `["combined", "basic_bold_16", "combined_sansserif"]`。证据：`AoE2DE_s.exe` 在文件偏移 `0x032E6D90–0x032E6DB0` 有恰好这三个 NUL 分隔串（其前 `0x032E6D50` 是 `Setting up UI Widget Manager`）；格式串 `"%s.box..%s_%04d.dds"` @`0x0321969A` 字面构造配对；而**没有任何宽度的指针引用这三个名字** → 由静态初始化表**按位置**注册。

- 全部 133 个文件、**6,203 个 Font 块**的真实用法：下标 `0` → 6,088（98.1%）、`2` → 94、`3` → 8、`−1` → 13。**基数只有 4 个值，其中一个（下标 1 = `basic_bold_16`）从未被使用。**
- **游戏随包发布完整的逐字形度量**：`<name>.box` = 头（ver, glyphCount, pages, sourcePx=64）+ 40 字节记录（`W,H,u0,u1,v0,v1,page,XO,YO,HAdvance`）+ `(u16 码点, u16 字形索引)` cmap。校验：**7,755 glyphs / 6 页**，`16 + 7755·40 = 310,216`，文件 341,236 = 310,216 + **7755·4**，**恰好**。2048² 抗锯齿 PNG 页就是美术来源。
- **基线规则（由测量得出）**：对贴基线字形 **`YO+H` 是常数（43.6±0.1）**（`A` 42.689、`0` 43.689、`a` 43.592、`.` 43.555），只有下伸部更大（`,` 52.581）→ **`YO` 是字形顶部偏移，`YO+H` 就是基线。**
- **这比用随包的 TTF 重排字保真度更高**（TTF 从未被 HUD 路径按名字引用，exe 0 命中）。唯一 caveat：`FontIndex 3`（8 块，0.13%）没有相邻 exe 串，回退到 `combined`，标记 **[I] 非 [V]**。

### 9d. ★ 真正的阻塞项（不是字体，也不是九宫格）

全部 133 个布局 JSON（**133，不是 144**）：6,504 个 widget、31 种 Type。`Base` 1778（27.34%）+ `Label` 1600（24.60%）+ `Anchor` 726（11.16%）= 63.2%，而 **`Surround` 只有 71（1.09%）→ 九宫格是稀有且便宜的，不是大引擎子系统。**

**可扩展性的真实阻塞**：约 **15%** 的 widget（`ListBox` 224、`DropDown` 171、`ScrollBarVertical` 247、`CheckBox` 359、`ProgressBar` 8…）以及**最大文件里的大多数 widget 显示运行时数据**。`editorbottomtriggerspanel.json`（1,241,730 B，482 widget）与 `screenmultiplayerlobbyhost.json`（421 widget）由列表/下拉/文本框行主导，内容无法静态推导 —— **即使美术渲染完美，产物仍是一个空壳。这是内容问题，不是几何问题。**
**可达范围**：约 **10–20 个游戏内面板文件**今天就能很好地渲染；菜单/编辑器只能"刷美术"。

### 9e. 其他已点名的失败，全部计数

- 全语料材质可解析率 **4,514/4,552 = 99.17%**；38 个失败：图集条目未找到 17、全局文件缺失 8、图集未找到 8、`type: Color` 无贴图 5（可实现）。
- 两个目标面板里**恰好只有一个真实失败**：`AgeUp` → `ingamepanels/AgeupCastleAge`，是**随游戏发布的悬空材质引用**（材质存在，但 40 个图集里没有任何匹配的 RefName）。修正后 **UV_OUT_OF_RANGE 为 0、不支持类型为 0**。
- **未实现 `ProgressBar`**（`AgeBar` 是错的：把 284×38 的贴图拉成 378×52），且 **`AlphaPlayerColor`（1,205 个材质，26%）按未着色渲染** —— 两者都已在报告中声明。

### 9f. 后续接手者的坑（全在报告 §7）

- 解开 `{"Widget":{...}}` **以及** `{"MaterialDef":...}`/`{"AtlasDef":...}` —— **层级错就静默返回 None**。
- 图集 UV 矩形是**打包图集里的位置**，对独立 PNG 毫无意义；**只有它的"范围"有意义**（第一版直接裁原始矩形，得到 `17/19` 个 UV_OUT_OF_RANGE）。
- 把材质画进 widget 的 ViewPort **盒子**，**绝不要按贴图分辨率画** —— 单是这个尺寸 bug 就凭空造出 `MAD 45.7`，真值是 `12.1`。
- **字形 alpha = `min(R,G,B)`，不是 `max`**（页里白色拉丁文与高饱和 CJK 混排；取 max 会灌满 255，让所有文字变成实心块）。
- **alpha 量纲陷阱是逐通道的，不是逐块的**（`AgeTextLabel` 在同一个 Font 块里混用 `a:255` 与 `a:1`）。
- **MAD/NCC 在这里是坏仪器**：掩码 MAD 给**错**的木板美术打分**高于对的**。**必须先用已知正确美术建立下限，并且一定要看图。**

**副产品（有独立价值）：**
- **全部 133 个 json 中 116 个含 widget，共 6,504 个 widget**。Type 频次：`Base 1778 (27.34%)`、`Label 1600`、`Button 797`、`Anchor 726`、`CheckBox 359`、`ScrollBarVertical 247`、`ListBox 224`、`DropDown 171`、`TechTreeButton 109`、`TextBoxInput 90`、`TextBox 78`、**`Surround 71 (1.09%)`**、`CampaignTitle 54`、`RotatingImage 53`、`CommandButton 37`、`UserIcon 21`、`OptionsPanel 9`、`ProgressBar 8`、`MapView 2`、`TimeLine 1` → **完整渲染器的真实规模约 6,500 个控件、30 种类型。**
- **字体图集 `combined` 的度量表 = 4 B/字形（`u16` 码点 + `u16` 索引）**，共 **7,755 glyphs / 31,020 B**；字体图集 **6 页，每页 (2048,2048)**。字形按 UV 裁剪（`'A'` W=46 px → 46/2048 = 0.0225 ✓）。
- exe 串池含 **`[icons] [%03d] [StatIcons] [uiwidgetutils SendIconName]`** 与 `[combined] [basic_bold_16] [combined_sansserif]` → **`%03d` 是图标编号格式**（解释 `UnitIcons%03d50730` 命名）。

---

## 10. 一个重要的方法论教训（反复踩过）

### 10.1 MAD/NCC 是坏仪器，视觉才是判据
深色预乘的 V2 与深色背景的 MAD 天然低 → 数值上 V2 赢 5/8，**但视觉上是 V1 在显示**。
玩家列表徽章：NCC 选的 `britons` 是**假赢家**，视觉上观察行 = `lithuanians` 逐像素一致。

**→ 任何"哪个源被渲染了"的判定，必须：(a) 在 alpha>阈值 的 art 像素上算，且 (b) 以并排视觉复核为准。**

### 10.2 必须先测相机位移，再做任何"HUD 是否变化"的判断
第一次跨帧裁决 10 个区域全部报 CHANGING（含理应是静态的 `SCOREPANEL_dark` 0.801）→ **相机在帧间移动了**。
可靠位移（±300 粗搜 + ±4 精修，ncc ≥0.97）：f2 `(0,0)`、f3 `(67,−144)`、f4 `(224,99)`、f5 `(127,115)`。
**搜索半径要足够大**（±80 时 ncc 只有 0.17–0.30，完全不可信）。

### 10.3 "代理带"是无效方法
用紧邻可见地形代替被遮挡地形，会得出**互相矛盾**的结果（alpha≈2 与 alpha≈194），逐列相关只有 r≈0.2–0.5 —— 因为采到的是**不同的世界内容**。
**正确方法 = 面板抵消法**：
`obs_k(x,y) = a·A(x,y) + (1−a)·T_k(x,y)`，取两帧相减消掉 `A`，对已知地形差回归得 `(1−a)`。
对照组（真值 slope=1.0）实测 **0.9944 / r 0.981** → 方法本身正确。

### 10.4 "HUD 是否透明"不能整体回答
同一条底部 HUD 内：y=1250 透传 **0.9628**（alpha 9.5/255），y=1350 只有 **0.3805**（alpha 158）。
**→ 必须逐行/逐控件回答。**

### 10.5 统计文件用 Python `os.walk`，不要用 PowerShell
`Get-ChildItem -Recurse -Filter` 在含中文/长路径的树上输出会被截断，且 `-Include` 与 `-Recurse` 组合行为反直觉。
**`os.path.isdir` 校验路径存在性，而不是肉眼看控制台输出**（GBK 控制台会把中文路径显示成 `????`，这是显示层问题）。

---

## 11. 复现脚本索引（全部在 `_probe\` 下，全部只读）

| 脚本 | 作用 |
|---|---|
| `loose_override_proof.py` | ★ §3 的四步证据链 |
| `size_constraint.py` | §4 的 510 个替换文件尺寸比对 |
| `sections_pin.py` / `sections_pin_all.py` | §5.3 全 14 段解析规则与覆盖率 |
| `sections_resolve.py` / `sections_rest.py` / `sections_residual.py` | 残余项的定性（字面量 `None`、复数文件名、逗号拼接、未使用段） |
| `sections_last3_roles.py` / `sections_last3_pin.py` | §5.3 末三段（`Notification`/`StatIcons`/`MenuIcons`）角色定位 |
| `sections_last3_fix.py` | §5.3.1 `StatIcons` 24/24（**correct `AtlasDef` nesting**） |
| `sections_last3_table.py` | §5.3 逐值五列裁决表（值→规则→材质→图集→FileName→磁盘） |
| `sections_settle.py` | §5.3.3 政体科技规则测试 + §5.3.4 `icons.json` 引擎输入否决 |
| `sections_menuicons_final.py` | §5.3.3 六条死条目的 5 项阴性穷举 |
| `_subctx.py` | §5.3.3 关键：exe 里 `Oligarchy`/`Democracy`/`Tyranny` 的相邻上下文（发现钥匙） |
| `civstem_dirs.py` | §2 三族徽章的目录反查 |
| `v3_provenance.py` | §2 V3 → `defaultwidgets` → `<Civ>Icon` 的引擎链路 |
| `civicon_owner.py` / `civicon_refs.py` | §3.3 `CivIcon` 控件 vs `<Civ>Icon` 材质 |
| `atlas_slice_decide.py` | §2 "图集 DDS 才是事实来源"的判定 |
| `roster_atlas_confirm.py` / `roster_final.py` / `plist_v3.py` | §2 V3 的裁决与并排图 |
| `alpha_solve2.py` / `alpha_exact.py` | §10.3 面板抵消法 |
| `camera_shift.py` / `crossframe.py` / `chibi_track.py` | §10.2 相机位移 |
| `chg_*.py` | §8.6 冗余文件检测 |

**产物图**：`_shots/ui/` 共 70 个文件，关键有
`roster_row1_COMPARE.png`（2800×394，5 列并排裁决）、
`emblem_families_FINAL.png`（528×1328，10 civ × 3 族）、
`family_v3.png`（570×2144，16 civ × [V1|V2|V3]）、
`roster_atlas_confirm.png`、`chibi_vs_candidates.png`、`atlas_vs_src.png`、`v1v2_bgtest.png`、
`bottom_strip_all5.png`、`topbar_x6.png`、`cursors_sheet.png`、`empireicons_sheet.png`。

---

## 12. 诚实边界（本文件未证明的事）

1. **游戏内端到端**：§3 的覆盖链有第三方 mod 的成功实例（且实机截图可见），但**我们没有自己启动游戏、写一个 mod、再截图验证过**。这是唯一剩下的真实未知，**需要用户启动游戏配合**。
2. **V3 能否被松散 PNG 覆盖**：机理与 V1 完全相同（同一条 `materials.json` → `FileName` 路径），但**本机 0 个 mod 提供该目录**，因此无第三方实证。
3. **尺寸不符会怎样**：实测 2 个尺寸不符的样例，但**不知道游戏的实际表现**（可能是拉伸、可能是保持左上角裁切、可能不生效）。因此规则是"保持原尺寸"而非"其他尺寸一定坏"。
4. **`MenuIcons` 的 6 条 / `CivHero` 的 66 条**：判为"死条目/未使用段"，但这只是**磁盘与 exe 双 0 命中**的强推断（`MenuIcons` 另有 8 项独立阴性检查），**不是官方声明的定论**。同一段里另有 3 条（政体科技）已被解出，说明"整段死"的结论必须逐条验证而不能整段推断。
5. **`icons.json` 不是引擎输入**：证据是 exe 精确 0 命中 + 无布局引用 + 运行时名字由 `%sIcon` 拼出。**未在实机验证"删掉 icons.json 游戏仍正常运行"**（这只是不作为引擎输入的必要非充分条件）。
6. **音频方向**：见另一份调研报告 —— **只有 formatTag 1 未压缩 PCM 可行，且仅限 UI 音效**；**不要承诺单位语音替换或自定义音乐**。
