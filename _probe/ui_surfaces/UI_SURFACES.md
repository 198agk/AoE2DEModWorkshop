# 三个 UI 表层（实测，本机 101.103.54800.0 / appid 813780 / buildid 25464371）

我此前只记录了 `widgetui/`，实际上游戏有**三个**互相独立的 UI 表层，各自的文件格式、目录、可覆盖性都不同。
本文件是对「能力目录v0.md」的补正。

---

## 表层 1：游戏内 HUD —— `widgetui/`（JSON + 图集贴图）

* 位置：`D:\Games\Steam\steamapps\common\AoE2DE\widgetui\`
* 144 个 `.json` + 7,840 个贴图（5,977 `.png` / 1,655 `.dds` / 206 `.jpg`）
* 坐标系：**参考分辨率 3840×2160 的整数像素** + `alignment` 锚点（`TopLeft` / `CentreCentre` / `BottomRight` / …），**没有** CSS 式比例坐标
* 面板九宫格：`Type:"Surround"` + `Box{gridstep:32, drawbox:true}` + 9 个方向的 `StateTL/TC/TR/CL/CC/CR/BL/BC/BR × Normal/Disabled`
* 材质抽象：`materials.json` 顶层三键 `Materials`(4555) / `AtlasTextures`(40) / `GlobalTextures`(202)
  * `Materials[]` 元素是 `{"MaterialDef": {...}}` 包装（直接取 `["Name"]` 会 `KeyError`）
  * `AtlasTextures[]` 元素是 `{"AtlasDef": {...}}` 包装
  * `MaterialDef.Type` 实测 `Atlas` / `Texture` / `Color`；`Blend` 实测 `InverseAlpha`(3081+124+3) / `AlphaPlayerColor`(1205) / `None`(71+69+1) / `Null`(1)
  * **`AlphaPlayerColor` 共 1,205 个，是玩家色染色类换肤的核心机制**
* mod 覆盖方式：**丢同名同尺寸的松散贴图到 `widgetui/textures/...`**，引擎优先取松散文件、回落图集切片。
  * **已成定论**（实机视觉证据 + alpha 直方图 + 社区 `topic_91310`）：`widgetui/textures/atlas/*.dds` 打包图集整体替换**不生效**，单张源贴图**生效**
  * 因此：**烘烤器 = 复制文件，不需要重打图集**（这是最大的架构利好）
* mod 也可覆盖 `widgetui/*.json`（2019 年官方修复过，见 `topic_65172`）

---

## 表层 2：菜单层 —— `resources/_common/wpfg/`（XAML + PNG）★本轮新发现

* 位置：`D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\wpfg\`
* **3,039 个文件**：`.png` 2,708 / **`.xaml` 233** / `.dds` 28 / `.ttf` 24 / `.jpg` 22 / `.ps` 10 / `.dx11` 10 / `.txt` 4
* **这是完整的 WPF 界面源码，随游戏分发。** 不是生成的，是可读可改的 XAML。
* 结构：
  * 根：57 个 `SystemResources*.xaml`（按钮/滚动条/复选框/字体/树/通知/径向菜单/进度条… 全控件样式）+ `app.xaml` / `systemresources.xaml` / `applicationwindow.xaml` / `screenwindow.xaml` / `backgroundwindow.xaml` / `overlaywindow.xaml` / `fadewindow.xaml` / `emberwindow.xaml` / `sttwindowoverlay.xaml` / `PersistentOverlayWindow.xaml`
  * `screen/` 32 个：`screensimplemainmenu.xaml`、`screenoptions.xaml`、`screengame.xaml`、`screenmultiplayermatchmaking.xaml`、`screeninstalledmods.xaml`、`screencredits.xaml`、`screenachievements.xaml`、`screenmapselection.xaml`、`screensavegame.xaml` …
  * `dialog/` 30 个：`dialogdiplomacy.xaml`、`dialogendgame.xaml`、`dialogingamemenu.xaml`、`dialogobjectives.xaml`、`dialogmixer.xaml`、`dialogmultiplayerchat.xaml`、`dialogprofilehub.xaml`、`dialogsimplesettingsmenu.xaml` …
  * `panel/` 5 个：`paneltopnavigation.xaml`、`panelnotification.xaml`、`pannelevents.xaml`、`panelplayerlogin.xaml`、`panelrematch.xaml`
  * `tab/` 28 个：`taboptions{audio,game,graphics,hotkeys,interface}.xaml`、`tabprofilehub{mods,player,statistics,icons,mute,offline,playerlookup,block}.xaml`、`tabLoadGame{Saves,Replays}.xaml`、`tabsingleplayercreate{game,lobby,map}settings.xaml`、`tabDebugAI*.xaml`（含 AI 脚本调试面板！）
  * `WPFUI/` 子目录（Common/Components、Common/Resources、Palm、Paphos…）
  * `resources/` 2,166 个：`.png` 2,117 / `.dds` 28 / `.ps` 10 / `.dx11` 10 / `.jpg` 1
    * 含 `aoe_logo.png`、`button_{large,small,mixer}/{active,disabled,hover,normal}.png`、`scroll/*`、`simplemainmenu/button_image_*.png`、`civ_emblems/`、`civ_techtree/`、`loading_slash*.png` …
  * `fonts/` 13 个 TTF：BKANT、Georgia、MalgunGothic、MicrosoftYaHei、Nirmala、PalatinoLinotype、SegoeUI、**TrajanPro-Bold/Regular**、`XBOX LOGO`、arial、micross、timesbd
  * `.ps` + `.ps.dx11` 是 D3D11 像素着色器源码对（`blur.ps` 等）
* **mod 覆盖已实测**：`550412_透明主题整合自用` 在 `resources/_common/wpfg/resources/` 下放了 50 个文件（49 个游戏侧同名存在、1 个 `_aoe_logo.png` 是新增）。
  * 尺寸差异举例：`loading_slash.png` mod 2,964,320 vs game 7,561,402；`simplemainmenu/button_image_ranked.png` mod 1,061,579 vs game 2,088,251；`aoe_logo.png` mod 61,869 vs game 113,767
  * 部分文件**尺寸完全相同**（`scroll/knot.png` 3,305 / `slider2_panel.png` 37,174 / `simplemainmenu/ant_button_image_editor.png` 213,784）→ 内容改过但字节数巧合相同，或只是无损重存
* **产品含义（重要）**：想做「改菜单界面/换 logo/换主菜单按钮」这类 mod，**这一层比 `widgetui/` 更好用**——它是标准 XAML，控件有名字、有布局，不是 4K 像素坐标。**这是此前完全漏掉的一整块能力面。**

---

## 表层 3：文案层 —— `resources/<lang>/strings/key-value/`

* 17 种语言目录：`br de en es fr hi it jp ko ms mx pl ru tr tw vi zh`
* 每语言 13 个 key-value 文件，合并出 36,351 个数字 ID
* 格式：**UTF-8、无 BOM、CRLF**，`id<tab>"value"`，支持 `//` 注释
* **★★ 官方专用的 mod 字符串通道（本轮新发现，重大）：`key-value-modded-strings-utf8.txt`**
  * 17 个语言目录**各有一个**，游戏侧内容只有 605 B 的注释头，原文逐字：
    ```
    //INSTRUCTIONS:
    //When you create any mod by creating a directory inside Steam,
    //certain files will automatically copy over, including this
    //file when you run the game. If you want to replace or add any
    //strings, place them in this file and when the mod is enabled,
    //these strings will also be added. The english string file is
    //a global fallback when a string cannot be found in the
    //desired native language file.
    //
    //If you would like to modify an existing string, copy only
    //the strings you wish to modify into this file, and do not
    //delete them from the original file.
    ```
  * **含义**：改文案**不需要覆盖整个 1.9 MB 的 `key-value-strings-utf8.txt`**，只把要改的行放进 `key-value-modded-strings-utf8.txt` 即可，引擎会合并（en 作为全局回落）。
  * 实测三个文本 mod 全都用这条路：
    * `423822_...军团长天赋文本`：`resources/{en,tw,zh}/strings/key-value/key-value-modded-strings-utf8.txt`（17,458 / 14,503 / 14,503 B）
    * `550009_...文明联盟 文本UI(v19)`：`resources/{en,zh}/.../key-value-modded-strings-utf8.txt`（20,884 / 23,558 B）
  * 对比：三个 mod 都**没有**碰 `key-value-strings-utf8.txt`（游戏侧 1,965,572 B）→ **官方推荐的增量方式是 mod 作者的实际做法。**
* 另有赛事专用文件 `tournament-key-value-strings-utf8.txt`（718 B，含 `IDS_MATCHMAKING_RED_BULL` 等赞助商条目）与各 DLC 战役文件（`PDLC2/3/4/6-*`、`*-campaign-*`、`paphos-*`）。
* **dat 里的 `LanguageDLLName` 字段就是这张表的数字键**（不是 DLL 引用；游戏树内不存在任何 `language*.dll`）。

---

## ★★★ 表层 0（新发现，最底层）：`modes/<Name>/<Name>.json` = 引擎的"存储点注册表"

* 位置：`D:\Games\Steam\steamapps\common\AoE2DE\modes\Pompeii\Pompeii.json`（3,205 B，**全树唯一一个**，`storage_point_list` 在 exe 里只出现 1 次）
* **28 条存储点**，这是引擎**自己声明的"我能从哪些目录读什么"的权威清单**，也是"mod 能不能覆盖这个目录"的官方答案：

| type | path | replace |
|---|---|---|
| `SP_SAVEGAMES` | `savegame` | ✅ |
| `MP_SAVEGAMES` | `savegame\multi` | ✅ |
| `SCENARIOS` | `resources\_common\scenario` | ✅ |
| `CAMPAIGNS` | `resources\_common\campaign` | ✅ |
| `AI` | `resources\_common\ai` | ✅ |
| `DAT` | `resources\_common\dat` | ❌ **+ `use_modes_path_for_mods: true`** |
| `DRS` | `resources\_common\drs` | ❌ |
| `SPRITES` | `resources\_common\drs\graphics` | ❌ |
| `RANDOM_MAPS` | `resources\_common\random-map-scripts` | ✅ |
| `COMMON_STRINGS` | `resources\_common\strings` | ❌ |
| `STRINGS` | `resources\<locale>\strings` | ❌ |
| `ACHIEVEMENTS` | `resources\_common\achievements` | ✅ |
| `CAMPAIGN_MOVIES` | `resources\<locale>\campaign\movies` | ✅ |
| `CAMPAIGN_SOUNDS` | `resources\<locale>\campaign\sounds` | ✅ |
| `SCENARIO_SOUNDS` | `resources\<locale>\scenario\sounds` | ✅ |
| `WIDGETUI` | `widgetui` | ❌ |
| `WPFG` | `resources\_common\wpfg` | ❌ |
| `PALETTES` | `resources\_common\palettes` | ❌ |
| `TERRAIN` | `resources\_common\terrain` | ❌ |
| `PARTICLES` | `resources\_common\particles` | ❌ |
| `WWISE_EXTERNALS` | `resources\_common\drs\sounds` | ❌ |
| `AUDIO_MUSIC` | `resources\_common\sound\music` | ❌ |
| `AUDIO_SFX` | `resources\_common\sound\stream` | ❌ |
| `AUDIO_AMBIENT` | `resources\_common\sound\terrain` | ❌ |
| `AUDIO_TAUNTS` | `resources\<locale>\sound\taunt` | ❌ |
| `TESTHARNESS_REG_SAVES` | `testharness\regressionsaves` | ✅ |
| `PERFORMANCE_TEST_GAMES` | `resources\_common\performance` | ✅ |
| `XS` | `resources\_common\xs` | ❌ |

* `replace:true`（12 条）语义待考：可能是"mod 以整目录替换而非逐文件合并"，也可能是"这个存储点不是游戏必需、可以被 mode 整体换掉"。**注意它与实际可覆盖性不冲突**：已实测 `DAT`（replace=false）被 2 个 mod 覆盖成功、`WPFG`（replace=false）被 1 个 mod 覆盖成功、`WIDGETUI`（replace=false）被 2 个 mod 覆盖成功 → **`replace=false` 不等于"mod 不可覆盖"。**

### 完整的存储点枚举（从 exe 提取，共 46 个，`Pompeii.json` 只用了 28 个）

`Pompeii.json` 定义 28 条，但 exe 里的枚举串更长。原始串（NUL 分隔，从 `LOGS` 起）逐字：

```
LOGS SP_SAVEGAMES MP_SAVEGAMES SCENARIOS CAMPAIGNS AI CREDITS DAT DRS FONTS
PALETTES MOVIES SPRITES SPRITES_LOW SLP CURSORS AUDIO_CIVTHEME AUDIO_MUSIC
AUDIO_SFX AUDIO_AMBIENT AUDIO_TAUNTS TERRAIN TEXTURES RANDOM_MAPS COMMON_STRINGS
STRINGS SHADERS PARTICLES PACKAGES PROFILE ACHIEVEMENTS CAMPAIGN_MOVIES
CAMPAIGN_SOUNDS SCENARIO_SOUNDS WIDGETUI WPFG WWISE WWISE_EXTERNALS TESTHARNESS
TESTHARNESS_SCRIPTS TESTHARNESS_REPORTS TESTHARNESS_REG_SAVES
PERFORMANCE_TEST_GAMES XS TESTHARNESS_XS TELEMETRY SCENARIO_EDITOR
```

紧随其后是**根/来源枚举**（第二条串）：

```
COUNT NONE NOTFOUND TEMP BASE APPATA USER MODSROOT LOCALMODS SUBSCRIBEDMODS DLC CLOUD
```

→ **每个存储点都会被解析到一个"根"**（`BASE` = 游戏安装目录、`USER` = `C:\Users\<u>\Games\Age of Empires 2 DE\<id>`、`LOCALMODS` / `SUBSCRIBEDMODS` = mod 目录、`DLC`、`CLOUD`…）。这解释了 `use_modes_path_for_mods` 的作用，也说明**mod 覆盖是逐存储点解析的，不是简单文件查找**。

**`Pompeii.json` 未定义、但引擎认识的 19 个存储点**（工具可据此推断落点）：
`LOGS`、`CREDITS`、`FONTS`、`MOVIES`、`SPRITES_LOW`、`SLP`、`CURSORS`、`AUDIO_CIVTHEME`、`TEXTURES`、`SHADERS`、`PACKAGES`、`PROFILE`、`WWISE`、`TESTHARNESS`、`TESTHARNESS_SCRIPTS`、`TESTHARNESS_REPORTS`、`TESTHARNESS_XS`、`TELEMETRY`、`SCENARIO_EDITOR`。

### `modes/<Name>/` 实测规模（Pompeii）

| 子树 | 文件数 |
|---|---|
| 总计 | 3,351 |
| `widgetui/` | 988 |
| `resources/` | 2,362 |
| `Pompeii.json` | 1（3,205 B） |

`resources/_common/` 下的子目录实测：`achievements`(2) / `ai`(2 文件 + 3 目录) / `campaign`(21) / `dat`(16 文件 + `CivTechTrees/`) / `drs`(0 文件 + 2 目录) / `palettes`(7) / `particles`(2 + 1 目录) / `strings`(0 + 1) / `terrain`(0 + 3) / `wpfg`(0 + 3)；外加 17 个 `resources/<locale>/strings/`。

`modes/Pompeii/resources/_common/dat/` 的 16 个文件：`AIConsts.json`(331) / `buttons.json`(1,738) / `civTechTrees.json`(1,671,526) / `civilizations.json`(9,720) / `dropsites.json`(10,066) / **`empires2_x2_p1.dat`(2,573,146)** / `eras.json`(754) / `futuravailableunits.json`(277,960) / `hotkeys.json`(108,606) / `linkedTechs.json`(235) / `maps.json`(18,580) / `selection_group_def.json`(17,510) / `sharedbuildings.json`(22) / `sounds.json`(5,048) / `unitcategories.json`(195) / `unitlines.json`(3,261) + `CivTechTrees/` 目录。
* **★ 一个 mode = `modes/<Name>/` 下的完整平行游戏树 + 一份 `<Name>.json`**。`modes\Pompeii\` 实测有 **3,351 个文件**，包含**自己的一整套**：
  * `empires2_x2_p1.dat`（2,573,146 B，与主 dat 12,023,754 B 完全不同 → **mode 可以整换数据集**）
  * 全套 dat-adjacent JSON：`civTechTrees.json`(1,671,526) / `futuravailableunits.json`(277,960) / `AIConsts.json` / `buttons.json` / `civilizations.json` / `dropsites.json` / `eras.json` / `hotkeys.json` / `linkedTechs.json` / `maps.json` / `sounds.json` / `unitcategories.json` / `unitlines.json` / `sharedbuildings.json` / `selection_group_def.json` + `CivTechTrees/`
  * `widgetui/` 988 个文件：`commandpanel.json`(311,623) / `icons.json`(18,107) / `menupanel.json` / `campaignselection.json` / `techtreepreviewpanel.json` / **`morematerials.json`** / `textures/` + 两个 build 脚本
  * `resources/{17 个语言}/strings/` + `resources/_common/{achievements,ai,campaign,dat,drs,palettes,particles,strings,terrain,wpfg}/`
* `Pompeii` = 罗马归来（Return of Rome）模式；其图集为 `CivEgypt` / `CivGreek` / `CivBabyl` / `CivRome` / `campaignicons_p`（`_p` 后缀），与主树 40 图集不同。
* **产品含义（重要）**：`modes/<Name>.json` 就是**官方的"插件清单格式"**——一份声明式 JSON，列出这个包会接管哪些存储点及其路径。我们的"插件化内核"可以直接照抄这个 schema，而不需要自己发明。它同时也是"某个目录到底属于哪个子系统"的权威答案（例如 `AI` 存储点 = `resources\_common\ai`，可以直接印证 AI 脚本 mod 的落点）。

---

## ★★ 表层 1 补充：`morematerials.json` = 官方的**增量**材质通道

* **引擎同时读 `materials.json` 与 `morematerials.json`**。exe 里这两个字符串**紧挨**在一起（偏移 52799000 附近，上下文：`storage_point_list\0replace\0use_modes_path_for_mods\0linkedUnits.json\0futuravailableunits.json\0paphosfutureavailableunits.json\0morematerials\0materials\0TechTreePreviewPanel\0MenuPanel\0`）。
* 全树只有 1 个 `morematerials.json`：`modes\Pompeii\widgetui\morematerials.json`（990,932 B），顶层键与 `materials.json` **完全相同**：`Materials`(799) / `AtlasTextures`(14) / `GlobalTextures`(13)。
* **官方 `modes\Pompeii\widgetui\build_atlas.ps1`（173 行，已完整读取）明确以 `morematerials.json` 为读写目标**，而不是 `materials.json`：
  * 第 19 行 `Get-Content -Path "morematerials.json"`，第 147-148 行 `Clear-Content -Path "morematerials.json"` / `Add-Content -Encoding ASCII`
  * 顶部注释逐字：`# atlasname - name of the atlas to generate as it appears in "morematerials.json"`
  * 流程与主树 `build_atlas.ps1` 一致（`texassemble.exe atlas -flist` → `texconv.exe`），但**少了 `OrderBy/StringComparer::Ordinal` 的去重排序**（只用 `Sort-Object | Get-Unique`），**少了 8 倍数取整**（直接取 `MaxWidth/MaxHeight`），且 `atlasWidth/Height` 默认 1024 而非从 0 起算
* **叠加语义（实测）**：`more` 与 `main` 的 `Materials` 名字**重叠 199 个**（如 `Age2Event` / `BackgroundMainMenu` / `BigButtonActive` / `ButtonAddActive` …），`AtlasTextures` 重叠 2 个（`CivAsia` / `CivGreek`），`GlobalTextures` 重叠 3 个 → **`more` 既能新增也能覆盖单条定义**（同名即覆盖），是"合并两份字典"而非"整文件替换"。
* **★ 抵消了本项目最大的一个顾虑**：做贴图 mod 时**不需要重写 2.5 MB 的 `materials.json`**（主树 4,552 个材质），只要写一个小得多的 `morematerials.json` 追加条目即可。这是"格式描述外置 + 增量而非替换"架构的**官方先例**。

---

## 覆盖性的四条硬规则（实测汇总）

1. **mod 根 = 含 `info.json` 的那个文件夹**，游戏目录树**直接**镜像在其下，**不**额外包一层 `resources/`
2. 19 个已装文件（含 `.dat`、`.json`、`.txt`、`.png`、`.dds`）全部走「同名同路径覆盖/新增」，**没有任何 mod 提供一个声明式的"我要改什么"清单** → 工具必须**自己算路径**
3. **文案用 `key-value-modded-strings-utf8.txt`（增量合并）**，不要去覆盖完整语言文件
4. **贴图用松散同名文件**，不要去重打 `atlas/*.dds`

## mod 文件类型实盘（6 个已订阅 mod）

| mod | 非贴图文件 | 类型 |
|---|---|---|
| `182654_Age of Anime (Chibi Edition)` | 仅 `info.json` | 纯 UI 贴图（62 个 `widgetui/textures/ingame/emblems/*.png`） |
| `423821_...军团长天赋模组` | `resources/_common/dat/empires2_x2_p1.dat` | 数据 mod |
| `423822_...军团长天赋文本` | `resources/{en,tw,zh}/strings/key-value/key-value-modded-strings-utf8.txt` | 文本 mod |
| `550009_...文明联盟 文本UI(v19)` | `resources/{en,zh}/.../key-value-modded-strings-utf8.txt` | 文本 mod |
| `550412_透明主题整合自用` | 50 个 `resources/_common/wpfg/resources/**` + 533 png + 2 dds | **菜单层 UI mod（跨层整合包）** |
| `550749_{2026}10倍资源文明联盟2倍科技 北欧dlc可用 v48` | `resources/_common/dat/empires2_x2_p1.dat` + `resources/_common/dat/linkedTechs.json` | 数据 mod（**额外覆盖了一个 dat-adjacent JSON**） |

* `550749` 同时覆盖 `linkedTechs.json`（mod 4,203 B vs game 3,947 B）→ **dat-adjacent JSON 也是可覆盖面**，此前未记录。
* **没有任何 mod 使用 `widgetui/*.json` 覆盖**（除了早前记录的社区帖所述能力）→ 该能力存在但本机无样本。
* **官方文档承认的已知缺陷**：① 游戏更新后 mod 会被自动禁用；② 文件夹名/结构不对就静默失效；③ **「把数据 mod 与 UI/内容 mod 合并」的功能"看起来又坏了"** → **工具必须把数据 mod 与贴图/UI mod 拆成两个 mod 交付**（与 `topic_231422`、`topic_245850` 的社区实测一致：数据 mod 里的自定义图标长期不生效）。

## 待验证（需用户配合一次实机）
* `widgetui/*.json` 覆盖是否真的生效（本机无样本，社区证据说 2019 年已修）
* `wpfg` 的 XAML 能否被 mod 覆盖（本机只有 PNG 样本）
* 松散 PNG 覆盖图集切片：已由 alpha + 视觉双重支持，但缺一次「只启用单一 mod」的受控 A/B
