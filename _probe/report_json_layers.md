# AoE2 DE 声明式数据层（`resources\_common\dat\*.json`）普查报告

调查日期：2026-10-22　调查对象：`D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\` 下 23 个声明式文件（按要求排除 `unitlines.json`、`linkedTechs.json` 的逐条分析）
方法：① 逐文件 JSON 全量解析（键、条目数、条目内键、空数组、空号段）② 对 `AoE2DE_s.exe`（72,166,200 B）做 NUL 分隔字符串 run 扫描（454,524 个 ≥4 字符 run），用**文件名邻居**与**字段名连续块**判定引擎侧 schema ③ 在 15 个已装模组（共 906 个文件）中反查覆盖 ④ 交叉项目既有文档

**证据分级**（全文统一使用）：
- 已实测 = 本次脚本跑出的数字/结构，可复现
- 文件里写着 = 文件自身内容直接可见（含官方注释）
- EXE = `AoE2DE_s.exe` 字符串实证（字段名 1:1 命中，实测该 EXE 的键名基本不去重，"恰好 1 次"本身就是证据结构）
- 模组 = 已装模组覆盖实证
- 推断 = 有证据链但未闭环
- 未证 = 无证据，不推测成结论

---

## 0. 一句话结论

**本体在这一层给了 3 个完全没被使用的机制**：`objreplacement.json` 的 `replacement_rate`（0/8 条用）、`objreplacement.json` 的 `replacement_attribute` + `required_attribute`（各 1/8 条用）、`buttons.json` 的 `button_shift_action_id`（1/14 条用），以及 **2 个整类空槽**：`unitcategories.json` 的 5 个空类、`airesourcetypes.json` 的 Stone/Gold 各只有 1 条。
**而 906 个已装模组文件里，这 23 个目标文件全被 0 个模组覆盖**（唯一例外 `civilizations.json`，2 个模组）——[证据: 已实测，见 §1 总表「模组」列]。这说明这整层是**玩家社区从未开采的荒地**，不是「试过无效」。

---

## 1. 总表

| 文件名 | 结构 | 引擎是否读（证据） | 空位/余量 | 一个玩法点子 |
|---|---|---|---|---|
| `civilizations.json` | `{"civilization_list":[63]}`，Gaia 6 键 + 62 条各 18 键 | **读**〔EXE: 文件名@0x032900f8 唯一命中；模组: 2 个模组覆盖〕 | 63 vs dat 也是 63，**无空位**；但 `unique_unit_line` 等大量字段对 Gaia 全缺 | 同一份 dat 用两份 civilizations.json 做出「科技树文案两套皮肤」 |
| `eras.json` | **list(2)**：`base`(Ages 5, TechDisplayOverrides 0, EraExclusiveTechs 0) + `antiquity`(Ages 5, TechDisplayOverrides 39, EraExclusiveTechs 50) | **读**〔EXE: 文件名@0x032900e8；字段表 `Ages/TechDisplayOverrides/EraExclusiveTechs`@0x0328fb58；旁邻 `Invalid era name: `@0x0328fe70 + `Game\Dlc\GameDataSet.cpp`〕 | **base 的 TechDisplayOverrides/EraExclusiveTechs 是两个整空槽**；era 总数 2（Pompeii 自带第 3 个 `pompeii`）⇒ era 可加 | 给自定义 DLC 开第 3 个 `era`，整套科技名/图标/前置文本换皮 |
| `linkedUnits.json` | `{"Data":[8]}`，键 `Name`/`Units` | **读**〔EXE: 文件名@0x0325a5c0，与 futuravailableunits/paphos 三连相邻，前邻 `CommandPanel`/`storage_point_list` ⇒ 面板/预览子系统〕 | 8 条；`Villagers` 一条塞 28 个 id | 把「同一单位的两个记录」当**形态切换**用（如攻城/近战双形态） |
| `unitcategories.json` | `dict(7)`：Cavalry/CavalryArchers/SiegeWeapons/Archers/Infantry/Warboats/Monks，条目仅 `Name`+`ID` | **读（推断强度高）**〔EXE: 7 个类名 run 连续块 @0x032e33a0..0x032e33e8，夹在 `GameScreen::score_combat_display` 与 `setup_command_buttons_widget` 之间，前面 22 个 run 是 `ScorePanel`+`stat_icon_infantry/ranged/siege/war_ship/cav_archer/cavalry/monk`〕 | **5/7 类是真空数组**（738 B 文件，官方自己发）；Pompeii 版 7 类全空 | 计分屏「军事」分类修正包：把归错 class 的单位搬进正确桶 |
| `dropsites.json` | `{"drop_site_list":[30]}`，26 个不同建筑；条目 16 键 | **读**〔EXE: 文件名@0x0329e1f0，后接 16 个字段名连续块 + `Game\objects\group.cpp`〕 | 26 建筑 / dat 中 type=80 建筑 **491** ⇒ 覆盖率 5.3%；`attribute_type` 仅用 0,1,2,3,15,16,17 | 让兵营/射箭场成为木头投放点；或按文明限定投放点 |
| `sharedbuildings.json` | `{"Data":[11]}`，条目 `Name`+`Units[]`，元素 4 个 ID 字段 | **读**〔EXE: 文件名@0x03259758，后接恰好 5 个字段名 `Units/FirstUnitID/FirstBuildingID/SecondUnitID/SecondBuildingID`，无 `Name` 键、无条数上限〕 | 11 条每条的 `Units` **恰好 1 个元素**（结构上允许多个，从未用）；Pompeii 版 `{"Data":[]}` 证明空文件合法 | 一个兵种挂 3+ 个建筑；或「城堡出兵→兵营再生产」的降级链 |
| `objreplacement.json` | `{"objects":[8]}`，条目 `name`/`object_id`/`object_override` | **读**〔EXE: 文件名@0x032bf8c0，后接 11 键连续块 + 源码路径 `Game\RandomMap\Modules\ObjectGenerator.cpp` + `RGE_RMM_Object_Generator` + 一串 `(RandSync) Placing …object`〕 | **`replacement_rate` 8/8 条未用 = 最硬的空槽**；`replacement_attribute`/`required_attribute` 各 1/8；`chance` 2/8（值都是 50）；`technology` 4/8 | 「建造物按条件变体」做成通用机制：塔→要塞、磨坊→定居点、任意建筑按科技/属性/概率换皮 |
| `buttons.json` | `{"command_button_list":[14]}`，8 键 | **读**〔EXE: 文件名@0x0325abd0，8 键连续块 + `NotFromGame`；字符串 40231=「打开子菜单」〕 | **`button_shift_action_id` 仅 1/14 用**（`Go Back To Work`↔228）；4 条 `Open Submenu N (debug)` 暴露 4000/4001 动作 | 每个按钮加「Shift+点击」第二行为；给单位命令面板造子菜单 |
| `hotkeys.json` | `shared_hotkey_group_list` 9 组 + `hotkey_group_list` 27 组，634 条 hotkey | **读**〔EXE: 文件名@0x032cad50，旁邻 `shared_hotkey_group_list`@0x032cad60 + `sharedHotkeyGroupsBegin/End`@0x032c8c78〕 | 634 条里 `button_action_list` 66、`unit_list` 56、`sequence_id` 176、`context` 208 ⇒ **4 个未用满的表**；27 组里 24 组无 `group_id` | 给自定义单位补 `unit_list` 让热键生效 |
| `sounds.json` | `{"sound_list":[53]}`，键 `key`+`name` | **读**〔EXE: 文件名@0x0321e610；邻居 `sound_list`/`Play_%s`/`Audio mod file not found: %s`〕；**但 name 具体怎么映射 = 未证** | 53 条；**`name` ≠ `Play_` + `key`（53/53 全部不符）**，两者是两套独立命名（key 小写下划线，name 驼峰）；Pompeii 全套加 `Play_AOE_` 前缀 ⇒ name 可换 | 换音效指向（不是加音效）；做「整套音效换皮」 |
| `maps.json` | `{"default_map_type":13, "default_nomad_map_type":33, "default_battle_royale_map_type":145, "map_list":[194]}`，条目 20 键 | **读**〔EXE: 文件名@0x032cb8d8，37 键连续块 + `maps.txt` + 注释 `// This can be exported from phoenix using …"WRITE_MAP_INFO"`〕 | `storage_id` 区间 9..216 内有 **14 个空号**；`prohibited_game_mode` 仅 1/194；`mappool_icon_filename` 7/194；`scenario_filename` 50/194；`const_name` 160/194 | 用 `scenario_filename` 让地图列表条目直接指向 `.aoe2scenario`（官方已有 50 条先例） |
| `AIConsts.json` | `{"DefConsts":[1], "Defines":[1]}` | **读**〔EXE: 文件名@0x03229d80，后接 `DefConsts`/`Defines`/`AIResourceTypes.json`/`ResourceTypes`/`Types`/`Resource`；前邻一串 AI 错误串〕 | **只有 1 个 const + 1 个 define**，几乎全空 | 自定义 AI 编译期常量（`DE-GAME-AGE2` ↔ `DE-GAME-ROME` 的换法已由 Pompeii 演示） |
| `airesourcetypes.json`（EXE 里叫 `AIResourceTypes.json`） | `{"ResourceTypes":[4]}`：Food 24 条 / Wood 21 条 / **Stone 1 条 / Gold 1 条** | **读**〔EXE: `AIResourceTypes.json`@0x03229da8（磁盘名全小写 = **大小写不匹配**，Windows 不分大小写才读得到，mod 改名会踩坑）〕 | **Stone/Gold 各只有 1 条 = 极端空位**（所有石矿共用一个 id） | 把石矿/金矿细分为多个资源类型，做「富矿/贫矿」 |
| `adapterblacklist.json` | `{"adapters":[39]}`，键 vendorID/deviceID/unsupported/noVideo，值全是字符串 `"true"/"false"` | **未证**〔EXE: `adapterblacklist`(无下划线) **0 命中**；引擎认的是 `adapter_blacklist.json`(带下划线)@1 命中，且有独立实体 `resources\_common\performance\adapter_blacklist.json` 4114 B/38 条，两份 (vendor,device) 集合**零交集**〕 | 39 条 vs performance 版 38 条 | 无玩法价值；仅「伪造显卡绕过黑名单」（不建议） |
| `futuravailableunits.json` | `dict(58)`（57 文明 + `FullTechCiv`），每文明 `{"Buildings":[…]}` | **读**〔EXE: 文件名@0x0325a5d8，三连相邻面板组；`_交接说明.md:75` 记录它**不在 CRC 校验集合里** ⇒ 松散替换合法〕 | **832/1736 个面板 `Units` 与 `Techs` 双空**；`Buildings` 条目只有 6 个必需键，`RequiredAge` 只出现 830/1736 | 建造菜单/科技树预览的「未来物品」文案与图标（**不改变实时可用性**，见 §7 证伪记录） |
| `paphosfutureavailableunits.json` | `dict(12)`：6 真文明 + 4 占位 `Paphos6..9` + Gaia + FullTechCiv | **读**〔EXE: 文件名@0x0325a5f8，同三连组〕 | 4 个占位键（不在 63 文明名单）；`FullTechCiv` 与主文件**不同源**（only-main 31 条 / only-paphos 22 条） | 「第二个 DLC 的面板集」——可照抄这套做自定义模式面板 |
| `selection_group_def.json` | `{"selection_group":[43], "radial_data":[3]}` | **未证，且强反证**〔EXE: `selection_group`/`radial_data`/`item_list`/`is_building`/`group_list` **全部 0 命中**；`modes\Pompeii\…\selection_group_def.json` 是**坏 JSON**（`JSONDecodeError: Expecting ',' delimiter: line 381 column 5`）⇒ 不参与启动路径〕 | 43 组（全列见 §6）；`radial_data` 3 个 category：buildings/units/small | 若能读，则是「找同类」环形菜单的定制入口（未证，先做启动期 A/B 测试） |
| `chronicles_selection_group_def.json` | 同形，43 组 + radial_data items 13/12/12 | **未证**〔同 selection_group 0 命中；`chronicles` 只命中 `chronicles_`(1) 与 `IsChronicles`/`AnyChroniclesOwned`(3)〕 | 与 base 版差异：只 base 有 castle/docks/hulks/monastery/university；只 chronicles 有 **academy/fort/ports/shipyards/temple**；10 组内容不同 | 「两套时代体系的同类选择器」——证明这套结构可换皮 |
| `paphos_campaign.json` | 9 键：CampaignFilePath/MapWidth/MapHeight/TileWidth/TileHeight/TileColumns/TileRows/MapTilePaths[4]/Sections[3] | **读**〔EXE: 文件名@0x031d4c40，`*_campaign.json` 三件套都被点名〕 | MapWidth 8192×8192、Tile 4098×4098、2×2；Sections 3、每 Section 只有 `Scenarios` | 「大地图时间线战役」：一张 8192 大图切 2×2 瓦片，每关是图上一块 |
| `peru_campaign.json` | **完全不同构**：`{PreloadedImages[12], Campaigns[3]}`，Campaign 19 键 | **读**〔EXE: 文件名@0x031e4048〕 | 3 战役 × 5 关；`PreloadedImages` 是 `pack://application:,,,/WPFUI/Peru/…` WPF pack URI | 「三国式战役选择界面」：3 个战役按钮 + 5 关卡片 + 全美术位 |
| `providence_campaign.json` | 同 paphos 9 键 | **读**〔EXE: 文件名@0x031d4c58〕 | MapWidth 16384×8192、Tile 8194×4098、2×2、Sections **5** | 同上，且证明 Sections 数可变（3 vs 5） |
| `UiColors.txt` | `ColorTagName R G B A`，**92 个颜色 tag 行**（90 个 tag 名在 EXE 逐字存在） | **读**〔EXE: 文件名@0x03214690；前邻一串 `PlayerNN…PaletteIndices`/`GaiaHealth`，后邻 `ERROR: sColor map with %zu entries mismatches ColorPreset::NumColors of %d. Did you add a new color definition but forgot to add it to sColor map?`〕 | **注释硬约束**：`ColorTagNames are hard-coded.` ⇒ 只能改数值不能加 tag。EXE 有 `Player9ABCPaletteIndices`/`PlayerDEF0PaletteIndices` 两个 tag 磁盘上没有 | 重绘 UI 全配色（零风险纯数值） |
| `custome_palette_list.txt` | 7 行 `clf_pal - clf` … `pal_7 - unassigned` | **未证，强反证**〔EXE: `custome` 仅 2 命中且都是压缩词典垃圾；`palette_list` 0 命中；文件名 0 命中〕 | `pal_7 - unassigned` = 唯一明确空槽 | 大概率是编辑器/工具用清单，无玩法价值 |

**附：`modes\Pompeii\resources\_common\dat\` 平行副本**（16 个 JSON + `civTechTrees.json` 1,671,526 B）——官方用同一套 schema 做出了一整个「罗马」模式，其中 `sharedbuildings.json` **22 B（空 Data）**、`unitcategories.json` **195 B（7 类全空）**、`eras.json` 754 B（1 个 era `pompeii`，5 个裸 Ages）、`AIConsts.json` 331 B（`DE-GAME-ROME`）。**这四份文件是最强的「空文件也合法」证据。**

---

## 2. `objreplacement.json` —— 你问的第一个问题

### 2.1 8 条配置全文与语义

| # | object_id | 名字 | object_override 内容 | dat 身份 |
|---|---|---|---|---|
| 1 | 83 | Villager | `replacement_object:293, chance:50` | VMBAS(hp25)→VFBAS |
| 2 | 293 | Villager (Female) | `replacement_object:83, chance:50` | VFBAS→VMBAS（**双向**） |
| 3 | 448 | Scout | **无 `replacement_object`**，只有 `replacement_attribute:263` + `attribute_name:"Scout ID"` | SCOUT(hp45) |
| 4 | 109 | Town Center (Base) | `replacement_object:444, required_attribute:82, excluded_computer_players:true` + `attribute_name:"Raider"` | RTWC(hp2400)→PTWC(hp1950) |
| 5 | 562 | Lumbercamp | `replacement_object:1808, technology:[932,940], technology_state:3` | SMIL(hp600)→MULECART |
| 6 | 584 | Mining Camp | 同 #5 | MINE(hp600)→MULECART |
| 7 | 68 | Mill | `replacement_object:2556, technology:[1353], technology_state:**0**` | MILL(hp600)→SETTL1(hp1000) |
| 8 | 45 | Dock | `replacement_object:2172, technology:[1142], technology_state:3` | DOCK(hp1800)→Port 1(hp1800) |

[证据: 已实测，逐字段读出；dat 名与 hp 由 `aoe2mod.dat.parser.Parser` 解析 `empires2_x2_p1.dat` 得到]

### 2.2 这 8 条回答了你的三个子问

**① 还有哪些条目？** 就上面 8 条，没有更多。[证据: 已实测，`{"objects":[8]}`]

**② `chance` 能不能设成别的值？**
- 文件里写着：`chance` 只出现 2 次，值都是 `50`。[证据: 已实测]
- EXE 里 `chance` 是引擎认的键（@0x032bf914，1 次命中，夹在 `replacement_object` 与 `replacement_attribute` 之间）。[证据: EXE]
- **同一张字段表里紧邻还有一个 `replacement_rate`（@0x032bf998），出厂文件 8/8 条一次都没用过。** 这两个键并列存在，最可能是**同一件事的两种表达**（`chance` = 百分比 0–100，`replacement_rate` = 每 N 次一次 / 浮点率）。[推断强度：中]
- **能否取 51？能否取 0？能否取 100？= 未证。** 需要实机 A/B：改 83 的 chance 为 `100`，让村民**全**生成女性；若生效则说明是百分比，再测 `1`/`99` 收敛区间。
- **注意这是最值得早测的一条**：因为它是唯一「不依赖 .dat、不依赖按钮、只要改一个数字」的概率机制。

**③ `replacement_attribute` 是什么？**
- 它出现的唯一一条（#3 Scout 448）**没有 `replacement_object`** —— 说明它是「**按属性替换**」而不是「按对象替换」：把「某单位的某属性」替换成另一个值。`attribute_name:"Scout ID"` 是给这个属性起的**人类可读标签**（`attribute_name` 在 EXE 里 **0 命中**，确认是 shipped-only 的注释键）。[证据: EXE 实测 `attribute_name` 0 命中]
- `replacement_attribute: 263` / `required_attribute: 82` 里的数字是**属性槽索引，不是单位 id**。EXE 里有 `xsGetPlayerAttributeName` / `xsGetObjectAttributeName`（说明属性有名字、能在运行时取到），且 dat 的每个文明都带一长串浮点 `resources`（约 350 项，索引即属性槽）。[证据: 已实测 —— dat `civs[i]['resources']` 长度 350+，含 102.0/103.0/101.0/175.0/178.0/104.0/9466.0/448.0 等]
- **⚠ 口径订正**：本项目早期记录里「263 = dat 单位 COLOSS（hp4800 建筑）」是**误读**——263 作为单位 id 确实存在，但这里语义是属性槽。**82 与 263 各叫什么名字 = 未证**（静态没有枚举表，只能靠 `xsGetPlayerAttributeName` 在运行时反射）。
- #4 的 `required_attribute:82` 配 `excluded_computer_players:true` 是**唯一把属性当开关用**的实例：玩家具备属性 82 时，建 TC 得到「打包 TC」。这是「**玩家级门控**」，不是单位级。

### 2.3 最重要的未解点：它到底在什么时刻生效？

EXE 邻居给出了明确答案，但答案本身矛盾：

```
-4  0x032bf8a0  'RGE_RMM_Object_Generator'
-3  0x032bf8c0  'objreplacement.json'
-2  0x032bf8d8  'objects'
-1  0x032bf8e0  'object_id'
>>  0x032bf8f0  'object_override'
  +1 0x032bf900  'replacement_object'
  …
  +9 0x032bf9b0  '…\Aoc\Source\Game\RandomMap\Modules\ObjectGenerator.cpp'
 +10 0x032bfa20  '(RandomMapSync) create objects: obj-id: %d, group-flag: %d, num-of-groups: %d, land-id: %d'
 +26 0x032bfe60  '(RandSync) Placing second object: obj-id:%d, pos:<%f,%f>, player:%d'
```

⇒ **实现在「随机地图模块 ObjectGenerator」，带 RandSync 同步**。[证据: EXE]
这完美解释了 #1/#2（村民生成时一半概率给女性）——那是**地图生成阶段**的对象放置。

**但 #5–#8 四条（伐木场→骡车、矿场→骡车、磨坊→定居点、船坞→港口）在语义上不可能发生在开局地图生成时**，它们必须发生在**建造落成时**。两者共用同一个 `ObjectGenerator` 类，说明该类同时承担「开局对象生成」与「建造落成定型」两条路径。

**这是本次普查最重要的未解点，也是最大的机会点**：如果 ObjectGenerator 真的在建造落成时也查这张表，那么 `objreplacement.json` 就是一个**通用的「建筑形态演化引擎」**，其能力边界远大于官方展示的 4 个例子。需要实机验证（见 §8 玩法 #10）。

---

## 3. `unitcategories.json` —— 你问的第二个问题

### 3.1 现状

```json
{ "Cavalry": [ ], "CavalryArchers": [ ], "SiegeWeapons": [7 条],
  "Archers": [ ], "Infantry": [ ], "Warboats": [ ], "Monks": [2 条] }
```
文件仅 738 B。5 个空类是**真正的空数组**（原文 `"Cavalry": [\n\n\n   ],`），不是 null、不缺键。Pompeii 版 7 类**全空**（195 B）。[证据: 已实测]

有内容的 9 条：

| 类 | 单位 (Name, ID) | dat class | dat hp |
|---|---|---|---|
| SiegeWeapons | Ballista Elephant 1120 / Elite Ballista Elephant 1122 / Armored Elephant 1744 / Siege Elephant 1746 / Mounted Trebuchet 1923 / War Chariot (Focus Fire) 1962 / War Chariot (Barrage) 1980 | **全部 class=12** | 250/280/180/220/75/65/65 |
| Monks | Warrior Priest 1811 / Zakare 1826 | **class=6** | 80/250 |

对照：真正的攻城器 MANGO 280 / ONAGR 550 / SNAGR 588 是 **class=13**；CNGAU 691 / TURTL 831 是 **class=22**；FCAMEL 1263 是 **class=35**。同为 class=12 的还有 KNGHT 38 / LANCE 37 / CATAP 40 / TARKAN 755 等 **189 个单位**。[证据: 已实测，dat 全量解析]

### 3.2 空的意味着什么？能填吗？填了影响什么？

**空 = 「无覆盖」，不是「空槽位」。** 推断链如下：

1. 9 个已列单位里，7 个在 dat 里 class=12（= 骑兵），2 个 class=6（= 僧侣）。
2. 所以这 7 个「攻城象/战车」会被引擎按 class 归进骑兵，2 个武僧归进僧侣。
3. `unitcategories.json` 做的事就是**把这 9 个「归错了」的单位手工搬到正确桶里**（攻城象→SiegeWeapons，武僧→Monks）。
4. 所以：**绝大多数单位靠 class 自动归类，只有少数例外需要这份文件纠正**。5 类留空是因为「没有需要纠正的单位」，不是「槽位空着等你填」。

**引擎侧证据（决定性）**：7 个类名在 EXE 里是一块**连续的 run 块** @0x032e33a0..0x032e33e8：

```
-1  0x032e3378  'GameScreen::score_combat_display'
>>  0x032e33a0  'Infantry'
  +1 0x032e33b0  'Cavalry'
  +2 0x032e33b8  'Archers'
  +3 0x032e33c0  'CavalryArchers'
  +4 0x032e33d0  'Monks'
  +5 0x032e33d8  'Warboats'
  +6 0x032e33e8  'SiegeWeapons'
  +7 0x032e33f8  'GameScreen::setup_command_buttons_widget'
```

而它前面的 22 个 run 是：`GameScreen::score_normal_display` / `ScorePanel` / `stat_icon_fishing_ship` / `stat_icon_miner` / `stat_icon_lumberjack` / `stat_icon_hunter` / `stat_icon_forager` / `stat_icon_farmer` / `stat_icon_builder` / `stat_icon_villagers` / `stat_icon_fisherman` / `stat_icon_shepherd` / `stat_icon_transport_units` / `GameScreen::score_resource_display` / `stat_icon_infantry` / `stat_icon_ranged` / `stat_icon_siege` / `stat_icon_war_ship` / `stat_icon_cav_archer` / `stat_icon_cavalry` / `stat_icon_monk` / `GameScreen::score_combat_display`。（[证据: 已实测，第 33 轮复核]）

**7 个图标名与 7 个类名一一对上**（infantry↔Infantry、ranged↔Archers、siege↔SiegeWeapons、war_ship↔Warboats、cav_archer↔CavalryArchers、cavalry↔Cavalry、monk↔Monks）。

⇒ **这是计分屏（Score Panel）「战斗」分类的枚举。** 不是 AI 分类，不是特效作用范围。[推断强度：高；仍需实机截图确认]

**⚠ 一处必须说清的细节**：`unitcategories.json` 这个**文件名本身的邻居**与计分屏无关（它的前邻是 `morematerials`/`materials`/`TechTreePreviewPanel`/`MenuPanel`/`Game::onPlayerDropped`，后邻是 `TournamentMode`/`BaseGame::HandleTournamentModeState()`/`ScreenMultiplayerMatchmaking`）。证据来自**7 个类名的独立 run 块**，不是来自文件名邻居。这两条证据必须分开引用，否则证据链会被误读。

**能填吗？** 结构上完全能填（`{"Name": "...", "ID": 数字}`），且答案只有「填了之后计分屏是否真的改分类」这一个待验点。

**填了影响什么？** 按目前的证据：**只影响计分屏的战斗分类显示**（也就是「军事分数」那一栏的构成明细）。不影响 AI、不影响伤害、不影响特效。填错不会崩，但会让计分屏统计错乱。

**玩法的真正价值**：这是**唯一一个「改一个数字就能验证引擎行为」的 JSON**（填一个步兵 id 到 Cavalry，进游戏看计分屏）。**它是最好的探针文件。**

---

## 4. `sharedbuildings.json` —— 你问的第三个问题

### 4.1 11 条全表

| # | Name | 第一组 | 第二组 | 语义 |
|---|---|---|---|---|
| 1 | Huskarl | 41 @ **82**(Castle) | 759 @ **12**(Barracks) | 哥特：城堡→兵营 |
| 2 | Elite Huskarl | 555 @ 82 | 761 @ 12 | 同上 |
| 3 | Tarkan | 755 @ 82 | 886 @ **101**(Stable) | 匈奴：城堡→马厩 |
| 4 | Elite Tarkan | 757 @ 82 | 887 @ 101 | 同上 |
| 5 | Konnik | 1225 @ 82 | 1254 @ **1251**(Krepost) | 保加利亚：城堡→要塞 |
| 6 | Elite Konnik | 1227 @ 82 | 1255 @ 1251 | 同上 |
| 7 | Serjeant | 1658 @ 82 | 1660 @ **1665**(Donjon) | 西西里：城堡→塔楼 |
| 8 | Elite Serjeant | 1659 @ 82 | 1661 @ 1665 | 同上 |
| 9 | Spearman | 93 @ **12**(Barracks) | 1786 @ **1665**(Donjon) | 条顿：兵营→塔楼 |
| 10 | Pikeman | 358 @ 12 | 1787 @ 1665 | 同上 |
| 11 | Halberdier | 359 @ 12 | 1788 @ 1665 | 同上 |

[证据: 已实测，全部 11 条 id 在 dat 中存在且 class 为 70/80]

### 4.2 能新增吗？

- **结构上可以**：EXE 只认 5 个字段（`Units`/`FirstUnitID`/`FirstBuildingID`/`SecondUnitID`/`SecondBuildingID`），**没有条数上限，没有 `Name` 要求**（`Name` 在 EXE 里 0 命中，纯注释）。[证据: EXE —— `sharedbuildings.json` 后的 5 个 run 恰好是这 5 个键，后面直接跳到 `IDS_TEXT_CHAT_MESSAGE_LIMIT_REACHED`]
- **`Units` 是数组套数组**：11 条里每条 `Units` **恰好 1 个元素**，但结构上允许多个 ⇒ **一个兵种理论上能挂 3 个以上建筑**。[证据: 已实测结构]
- **空文件合法**：Pompeii 版就是 `{"Data":[]}`（22 B）。[证据: 文件里写着]
- **但有一个硬门槛未证**：目标建筑在 **.dat 里必须有对应的训练按钮位**。`sharedbuildings` 提供的是「同一兵种的第二个训练入口」，不是「凭空多一个按钮」。需要实机验证（见 §8 玩法 #9）。

---

## 5. `dropsites.json` —— 能不能让兵营收木头？

### 5.1 现状：30 条 / 26 个建筑

覆盖的建筑：TC 109、TC Foundation 621、Mill 68、Saw Mill 562、Mining Camp 584、Farm 50、Rice Farm 1187、Mule Cart 1808、Dock 45(×3)、Port 2172(×3)、Settlement 2556、Pasture 1897 / Pasture Annex 1890 / Pasture Foundation 1889 / Pasture Mangrove 1893、Greek Command Tent Dropsite 2405，以及**10 座塔**（Watch 79 / Guard 234 / Keep 235 / Fort 82 / Fire 190 / Bombard 236 / Accursed 684 / Tower of Flies 685 / Sea 785 / Fortified 1102）。

**同一个建筑可以有多条投放入口**：Dock 45 出现 3 次（`worker_object_group` = 无 / 4 / 21，分别只收 Oysters / Shore Fish+Fish / 三者全收），Port 2172 同构。⇒ **投放点由「建筑 + 工人组」共同定义，不是建筑唯一键**。[证据: 已实测]

### 5.2 能让兵营收木头吗？

**结构上：能，而且不需要改代码。** 只要往 `drop_site_list` 里加一条 `building_id: 12`（Barracks）+ `target_list` 含 `{object_group: 15, attribute_type: 1}`（Trees → 木头）即可。

**但有三个真实门槛**：
1. **`object_group` 就是 DAT 的 unit class**（已实测对拍：Trees→class 15 有 54 个、Stone Mines→8 只有 STONM 102 + ROCKSX 839、Gold Mines→32 只有 GOLDM 66 + ROCKGX 841、Shore Fish→33、Fish→5、Forage→7、Farms/Pasture Livestock→49、Sheep→58、Oysters→63、Hunted Animals→9、Hunting Animals→10）。⇒ **想新增一类可投放资源，必须让该类在 dat 里成为一个独立 class。**
2. **.dat 里建筑本身可能有「是不是投放点」的属性位**（未证）。这一条是最大的不确定性。
3. **`worker_object_group` 只有 {4, 21, None} 三个取值**（4=村民、21=渔船），引擎是否接受别的值未证。

### 5.3 三个反直觉的发现

**A. `target_civs` 不是空槽，它被 10 座塔用着。**
`target_civs` 在出厂文件里出现 **10 次，全部是那 10 座塔，值全部是 `[55]`**。dat 文明索引 **55 = Thracians（色雷斯人）**。[证据: 已实测 —— dat `civs[55]['name']`]
⇒ **「色雷斯人可以把木头/石头/黄金交进塔里」是整份文件里唯一按文明分支的机制。** 这也纠正了「`target_civs` 是引擎认但没人用的键」这个错误假设——**16 个 EXE 字段全部在出厂文件里被用过，dropsites.json 没有空槽**。

**B. `worker_object_list` 精确到男女农民。**
4 次使用：Farm 50 / Rice Farm 1187 → `[214, 259]`；Dock 45 / Port 2172 → `[2333, 2334]`。dat 解析：214=VFFAR(女农民)、259=VMFAR(男农民)、2333=VMGLD、2334=VFGLD。[证据: 已实测]
⇒ **这是「由哪几个具体工种执行投放」的字段**，粒度比 `worker_object_group` 细一级。

**C. `object_state_forced_return_state: 2` 只用了 1 次。**
108 个 `target_list` 元素里，`object_state` 只有值 5（17 次），`object_state_forced_return_state` 只有值 2（**仅 TC 的 Hunted Animals 一条**）。[证据: 已实测]
⇒ 语义未证（推断：交完资源后强制让动物进入某个状态）。**这是「打完猎尸体怎么处理」的可调项，官方只在一个地方用过。**

### 5.4 容量

26 个建筑 / dat 中 `type=80` 的建筑 **491** 个 ⇒ **覆盖率 5.3%，余量 465 栋建筑**。[证据: 已实测]
`attribute_type` 只用了 7 个值（0,1,2,3,15,16,17），105+ 个槽里有 91 个没写 `object_state`。

**Pompeii 证明这套东西能整族换皮**：它的 13 条把 Mill 换成 `Granary 68`、Saw Mill 换成 `Storage Pit 562`、加了 `Pasture` 系列 ⇒ 同一套 schema 就是「罗马/希腊经济体系」。

---

## 6. 其余文件的关键余量

### `eras.json` —— 能不能加第六个时代？

**不能，至少不能只靠这个文件。**

- 文件里写着：`Ages` 数组 **5 项**。base 的 5 条是 `NameId 4201..4205`，第 5 条**只有 `NameId` 一个键**（无 `TechTreeIconMaterialName`、无 `ShieldMaterialName`）。
- 字符串解析（`resources/zh/strings/key-value/key-value-strings-utf8.txt`，19,677 条）：**4201=黑暗时代、4202=封建时代、4203=城堡时代、4204=帝王时代、4205=后帝王时代**。[证据: 已实测]
- ⇒ **Ages 数组第 5 项是 UI 上的「后帝王时代」标签，不是第 5 个可研究时代。**
- dat 侧：`tech_tree = {'total_unit_tech_groups': 116, 'ages': **4**, 'buildings': 37, 'units': 266, 'research': 241}`；`RequiredAge` 在面板文件里的取值直方图只有 {1,2,3,4}（没有 0、没有 5）。[证据: 已实测 —— dat 解析 + futuravailableunits 全量统计]
- EXE 里 `numAges` / `MAX_AGE` / `POST_IMPERIAL` **全 0 命中**。[证据: EXE]
- ⇒ **真正的时代数由 .dat 的 `tech_tree.ages=4` 决定，JSON 只是标签表。加第六时代必须动 .dat 的 techtree ages（还要接受 CRC 破坏的代价，见下）。**

**但 `eras.json` 有两个真正的空槽**：
1. **`base` 的 `TechDisplayOverrides` 与 `EraExclusiveTechs` 都为空数组**，而 `antiquity` 有 39 + 50 条。⇒ 「同一科技在不同时代体系里换名/换图标/换前置文本」这套机制，**基础游戏一次都没用**。
2. **era 可以加第三个**：本体有 `base` + `antiquity`，Pompeii 自己加了 `pompeii`（Ages 逐字节照抄 base）。EXE 有 `Invalid era name: `（@0x0328fe70）说明按名字查表，**名字不对会报错**，但加新名字是合法路径。

**加时代的代价**：`empires2_x2_p1.dat` 在 CRC 校验集合里（`_交接说明.md:75`，crc=0x59fab71f），改它会触发 `IDS_WARN_USER_FILE_CRC_BREAK` 弹窗让玩家「验证游戏文件」；而 `futuravailableunits.json`（0xa22a47d8）与 `paphosfutureavailableunits.json`（0xff46b0dc）**不在**集合里 ⇒ 松散的 JSON 替换合法，.dat 不合法。[证据: 项目文档]

### `maps.json`

194 条；`storage_id` 区间 9..216 内有 **14 个空号**：`[24, 30, 45, 48, 59, 60, 61, 62, 63, 64, 65, 66, 137, 138]`。[证据: 已实测]
EXE 认而稀用：`prohibited_game_mode`(1/194)、`mappool_icon_filename`(7/194)、`scenario_filename`(50/194)、`cm_generic`(0)、`IconGeneric`(0)。
**`scenario_filename` 已有 50 条先例** ⇒ 「用地图列表条目直接指向 `.aoe2scenario`」是官方支持的替代路径。[证据: EXE 字段表 @0x032cb8d8 + 已实测 50 条使用]

### `airesourcetypes.json`（EXE 名 `AIResourceTypes.json`）

`{"ResourceTypes":[4]}`：Food **24** 条、Wood **21** 条、Stone **1** 条（STONM 102）、Gold **1** 条（GOLDM 66）。
⇒ **Stone 与 Gold 各只有 1 条，是整层里最不对称的空位**：AI 无法区分「石矿 A / 石矿 B」。
⚠ 磁盘名全小写，EXE 里是 `AIResourceTypes.json` —— **Windows 不分大小写才读得到；写 mod 时改名会静默失效。** [证据: EXE 0x03229da8]

### `buttons.json`

14 条里 **只有 1 条用了 `button_shift_action_id`**（`Go Back To Work` 171 ↔ shift 228）。[证据: 已实测]
4 条 `Open Submenu 0..3 (debug)` 暴露了 `button_action_id` 4000 / 4001 这个「打开子菜单」动作；字符串 40231 = 「打开子菜单」。[证据: 已实测 + 字符串解析]
**没有证据表明模组能新增 `button_action_id`**（引擎侧是 enum）；能改的只有图标 / 文案 / sequence / shift 行为。

### `hotkeys.json`

634 条 hotkey；可选键使用率：`data_name` 634、`name_string_id` 634、`defaults_list` 630、`string_index_list` 369、`context` 208、`sequence_id` 176、`button_action_list` 66、`unit_list` 56。
⇒ **`unit_list`(56/634) 与 `button_action_list`(66/634) 是最大的两个空位**——绝大多数热键没有绑定到具体单位或按钮。
`hotkey_group_list` 27 组里 **24 组没有 `group_id`**。[证据: 已实测]

### `futuravailableunits.json` / `paphosfutureavailableunits.json`

- 58 个键 = 57 个 base 文明 + `FullTechCiv`；**6 个 antiquity 文明完全缺席**（走 paphos 那份）。
- 1736 个面板，3984 个 Units 条目，4994 个 Techs 条目。
- **832 / 1736 个面板 `Units` 与 `Techs` 双空**（如 Britons 的 TC 621、Watch Tower 79、House 70、Farm 50、Wonder 276、Fish Trap 199、Outpost 598、各类墙/门）。[证据: 已实测]
- 关键机制原文：同一兵种在 `Units` 与 `Techs` 里**各出现一次、ID 不同**（Militia 74 在 Units，升 Man-at-Arms 的科技 222 在 Techs）。`Builder` 面板（ID 118）的 `Units` 装的是**可建造的建筑** ⇒ **建造菜单也用同一套面板表**。
- EXE 里 8 个键连续成表：`FullTechCiv` / `PaphosFullTechCiv` / `RequiredAge` / `RequiredTechID` / `RequiredUnitID` / `PrereqTech` / `PrereqIconSet` / `PrereqIconIndex` / `PrereqStringID` / `PrereqStyle` @0x032e5ec8 附近。**前两项是 `FullTechCiv` 与 `PaphosFullTechCiv`** ⇒ 解释了为什么这两个「非文明名」会出现在面板文件里（引擎侧的特殊面板集）。[证据: EXE]

### `selection_group_def.json` / `chronicles_selection_group_def.json`

`{"selection_group":[43], "radial_data":[3]}`；43 个组名全列：
`all_land_military`(18 items) / `non_siege_land_military`(14) / `siege`(4) / `warships`(1) / `cavalry`(2) / `archers`(2) / `infantry` / `monks` / `warrior_priests` / `trade` / `villagers` / `fishing_ships` / `transport_ships` / `resource_buildings` / `market` / `university` / `blacksmith` / `monastery` / `docks` / `town_centre` / `barracks` / `archery_range` / `castle` / `stable` / `seige_workshop`（**原文拼错 seige**） / `military_buildings` / `economic_buildings` / `all_military` / `civilians` / `all_military_no_monks` / `all_land_military_with_monk` / `naval` / `king` / `support` / `livestock` / `ranged` / `melee_military` / `galleys` / `fireships` / `hulks` / `demolition_ships` / `ranged_ships` / `unique_ships`。
`radial_data` 3 条：id=6 category=`buildings`(12 items) / id=5 `units`(12) / id=7 `small`(13)。item 形如 `{"icon":19,"title":"IDS_FINDMENU_RESOURCEBUILDINGS_TITLE","desc":"…","group":"resource_buildings","is_building":true}` ⇒ **这是「找同类」环形菜单的定义**。

**但：`selection_group` / `radial_data` / `item_list` / `is_building` / `group_list` 在 EXE 中全部 0 命中；且 `modes\Pompeii\…\selection_group_def.json` 是坏 JSON（`JSONDecodeError: Expecting ',' delimiter: line 381 column 5 (char 5807)`）—— 官方自己发了一份解析不了的文件，说明它不参与启动路径。** ⇒ **未证，且反证强。** 玩法上先不做依赖。

`chronicles` 版与 base 版差异：只 base 有 `castle`/`docks`/`hulks`/`monastery`/`university`；只 chronicles 有 `academy`/`fort`/`ports`/`shipyards`/`temple`；10 组内容不同。⇒ **两份文件是「两套时代体系的同类选择器」**，证明这套结构可换皮（前提是它能被读）。

### `UiColors.txt`

92 个颜色 tag 行，**90 个 tag 名在 EXE 中逐字存在**（只有 `Red` / `Pink` 不在）。文件注释原文：

```
//Format: ColorTagName Red Green Blue Alpha (RBGA) - valid ran 0
//ColorTagNames are hard-coded.
//Lower UI only. Does not affect in game healthbars.
//Game setup screen score colors achievements
//minimap/radar map dots
```

EXE 后邻是 **`ERROR: sColor map with %zu entries mismatches ColorPreset::NumColors of %d. Did you add a new color definition but forgot to add it to sColor map?`**（@0x032146a0）。[证据: EXE + 文件里写着]
⇒ **引擎读它，且「tag 名硬编码 + 行数必须与代码里的 `ColorPreset::NumColors` 完全一致」是官方自己写明的硬约束**：**只能改 RGB 值，不能加 tag，不能删行**。这是全层里限制写得最死的一个。
另：EXE 有 `Player9ABCPaletteIndices` / `PlayerDEF0PaletteIndices` 两个 tag，磁盘上没有 ⇒ 缺的用默认值（推断）。

### `custome_palette_list.txt`

125 B，7 行：`clf_pal - clf` / `pal_2 - foak_nn` / `pal_3 - fpal_nn` / `pal_4 - fpin_nn` / `pal_5 - fsno_nn` / `pal_6 - fire effects` / `pal_7 - unassigned`。
**未证，强反证**：EXE 里 `custome` 仅 2 命中（压缩词典垃圾）、`palette_list` 0 命中、文件名 0 命中。[证据: EXE]

### 三个战役文件

| 文件 | 结构 | 参数 |
|---|---|---|
| `paphos_campaign.json` | CampaignFilePath / MapWidth / MapHeight / TileWidth / TileHeight / TileColumns / TileRows / MapTilePaths[4] / Sections[3] | `pacam1.aoe2campaign`, 8192×8192, Tile 4098×4098, 2×2 |
| `providence_campaign.json` | 同上 9 键 | `PRCAM Build1.aoe2campaign`, 16384×8192, Tile 8194×4098, 2×2, **Sections[5]** |
| `peru_campaign.json` | **完全不同构**：`{PreloadedImages[12], Campaigns[3]}`，Campaign 19 键 | 3 战役 × 5 关；`PreloadedImages` 是 `pack://application:,,,/WPFUI/Peru/Campaign/Resources/Images/map.jpg` WPF pack URI |

Section 内只有一个键 `Scenarios`；Scenario 元素键（paphos）：`CutsceneFilePath`('pa-00.webm')、`ScenarioFilePath`、`ScenarioNameLocId`(**字符串型数字** "444040")、`LocationNameLocId`、`HeroNameLocId`、`HeroIconFilePath`("Heroes/artaphernes.png")、`HeroCivId`("ACHAEMENIDS-CIV")、`DescriptionLocId`、`HeroPortraitImagePath`、`ScenarioIconFilePath`("Timeline/scenario_icon_0.png")。
⇒ **两代不同的战役 UI 数据格式**：paphos/providence 是「一张大图切瓦片 + 若干 Section」，peru 是「3 战役 × 5 关 + 切换按钮美术」。三者都被 EXE 点名。[证据: EXE —— `paphos_campaign.json`@0x031d4c40 / `providence_campaign.json`@0x031d4c58 / `peru_campaign.json`@0x031e4048]

---

## 7. 口径订正（项目文档里错的或过时的）

| # | 原记录 | 实测更正 |
|---|---|---|
| 1 | `数据模组能力目录v1.md:736`「`linkedUnits.json` 是 UTF-8 **带 BOM**」 | **错**。实测 linkedUnits.json 809 B、`bom=none`、CRLF。全部 25 个目标文件都是 **bom=none + 纯 CRLF + 零 LF**。[证据: 已实测] |
| 2 | 早期记录「263 = dat 单位 COLOSS」 | 263 作为 dat 单位 id 确实是 COLOSS，**但在 `objreplacement.json` 里 `replacement_attribute:263` 的语义是属性槽索引，不是单位 id**。[证据: EXE —— `xsGetPlayerAttributeName`/`xsGetObjectAttributeName` 存在；`attribute_name` 键 0 命中] |
| 3 | 「`target_civs` 是引擎认但出厂未使用的键」 | **错**。它被 10 座塔使用 10 次，值全为 `[55]`（Thracians）。**dropsites.json 的 16 个 EXE 字段全部被用过，没有空槽。** [证据: 已实测] |
| 4 | 「`adapterblacklist.json` 是 GPU 黑名单」 | 引擎认的文件名是 `adapter_blacklist.json`（**带下划线**），实体在 `resources\_common\performance\`（4114 B / 38 条）。dat 下这份 `adapterblacklist.json`（4418 B / 39 条）与它 (vendor,device) **零交集**，引擎读取**未证**。[证据: EXE + 已实测] |
| 5 | 「`unitcategories.json` 是 AI 分类 / 特效作用范围」 | **不是**。EXE 里 7 个类名夹在 `GameScreen::score_combat_display` 与 `setup_command_buttons_widget` 之间，前有 7 个 `stat_icon_*` ⇒ **计分屏战斗分类**。[证据: EXE] |
| 6 | 「`futuravailableunits.json` 驱动建造菜单」（已证伪过） | 部分对：面板表的 `Builder` 面板确实用 `Units` 数组承载可建造建筑，**但它只是「未来物品/预览」描述，实时可用性由 .dat 决定**。[证据: 项目文档 §3518/3637 的证伪 + 本报告 §6 的正面解释] |

**方法论钉子（本次确立，以后可复用）**：`AoE2DE_s.exe` 里的键名字符串**基本不去重**。实测 `chance`/`replacement_rate`/`technology_state`/`object_state`/`worker_num`/`target_civs`/`allow_resource_distance_update`/`auto_work`/`worker_object_list`/`button_shift_action_id`/`NotFromGame`/`mappool_icon_filename`/`scenario_filename`/`prohibited_game_mode`/`RequiredAge`/`PrerequisiteStringId` 等**全部各 1 次命中**；`Name` 3 次；`attribute_name`/`selection_group`/`radial_data`/`item_list`/`is_building`/`group_list` **0 次**。
⇒ **「恰好 1 次命中」不是巧合，是 1:1 的证据结构；0 命中就是真缺席。** 这比「在字节窗里找邻居」可靠得多——用字节窗会把二进制垃圾当邻居。

---

## 8. 按可行性排序的 10 个新玩法

排序依据：改动面（几个文件）→ 是否需要动 .dat（动 .dat 触发 CRC 弹窗）→ 是否有官方先例 → 待验点数。

| 排序 | 玩法 | 依赖文件 | 改动量 | 需要实机验证什么 |
|---|---|---|---|---|
| **1** | **UI 全局换色**：把 8 个玩家色 + 血条 + 小地图点 + 聊天色全换一套（如「暗色低对比」主题） | `UiColors.txt` | 1 个纯文本，92 行数值 | **零待验**（官方注释写明只能改值；行数不能变——改完直接看 UI）。风险点：行数与 `ColorPreset::NumColors` 不一致会报 ERROR，所以**只能改数值不能增删行**。 |
| **2** | **计分屏分类修正包**：把归错 class 的单位（攻城象/战车等）搬进正确桶，让「军事分数」明细分类正确 | `unitcategories.json` | 1 个 JSON，7 类 | 填 1 个步兵 id 到 `Cavalry`，进游戏看计分屏「军事」栏是否出现该单位。**这是最好的引擎探针**（改一个数字即可）。同时确认：计分屏是否只在 `score_combat_display` 生效、是否影响观战/复盘。 |
| **3** | **热键补全**：给自定义单位补 `unit_list`、给未绑定按钮补 `button_action_list`，让 634 条热键里未用满的 4 个表填满 | `hotkeys.json` | 1 个 JSON | `unit_list` 的 id 是单位 id 还是 unit group？补 `context` 后是否在对应面板生效？27 组里 24 组缺 `group_id` 是否有影响？ |
| **4** | **AI 资源细分**：把 Stone/Gold 各 1 条的桶细分成「近矿/远矿/富矿」，让自定义 AI 能按距离选矿 | `airesourcetypes.json`（+ 自定义 `.per`） | 1 个 JSON + AI 脚本 | ⚠ **必须保持文件名 `AIResourceTypes.json` 的大小写语义**（磁盘小写能读，mod 里改名会失效）。验证：`.per` 里用新资源类型能否编译并通过。 |
| **5** | **按钮 Shift 二段行为**：给每个命令按钮配「Shift+点击」的第二行为（本体 14 条里只用了 1 条） | `buttons.json` | 1 个 JSON | `button_action_id` 是 enum，**不能新增动作值**，只能把已有 action 挂到 shift 槽。验证：给定居点按钮加 shift 行为，看是否触发。 |
| **6** | **地图列表当情景入口**：用 `scenario_filename` 让「地图列表条目」直接指向 `.aoe2scenario`，把战役/情景塞进标准地图选择器 | `maps.json` | 1 个 JSON + 1 个 .aoe2scenario | 官方已有 50 条先例。验证：`storage_id` 用空号（24/30/45/48/59–66/137/138 共 14 个）会不会与存档/回放冲突。 |
| **7** | **文明限定投放点**：只让某几个文明能把资源交进塔（本体只有 Thracians `[55]` 用着），做成「游牧文明靠塔当仓库」 | `dropsites.json` | 1 个 JSON | `target_civs` 的值是 dat civ 索引（0=Gaia…62=Danes）还是别的编码？改成两个文明是否两者都能用？ |
| **8** | **让非经济建筑成为投放点**：兵营收木头、射箭场收金（投放点只覆盖 26/491 栋建筑） | `dropsites.json` | 1 个 JSON | **关键未知**：.dat 里建筑是否有「是不是投放点」的属性位（若有，纯 JSON 改不动）。先试 Barracks(12) + Trees(class 15 / attribute_type 1)。 |
| **9** | **跨建筑出兵桥**：用 `sharedbuildings.json` 让一个兵种挂 3 个以上建筑（本体每条 `Units` 只放 1 个元素），或做「城堡→兵营→塔楼」降级链 | `sharedbuildings.json`（+ .dat 按钮位） | 1 个 JSON（可能 + .dat） | 目标建筑在 .dat 里是否必须有空按钮位？`Units` 数组放 2 个元素是否生效？Pompeii 证明 `{"Data":[]}` 空文件合法，可先做空文件 A/B。 |
| **10** | **通用「建筑形态演化引擎」**：把 `objreplacement.json` 的 `technology` + `technology_state` + `replacement_object` 当通用机制——任意建筑按任意科技变成另一个建筑（塔→要塞、房屋→庄园、伐木场→锯木厂），再用 `chance` 做概率变体、用 `required_attribute` 做玩家级门控 | `objreplacement.json`（+ .dat 目标建筑） | 1 个 JSON | **三个必须先钉死的点**：① `chance` 的取值域（改 83 为 100 测是否全变女性）② `replacement_rate` 到底是不是 `chance` 的另一种表达（它 8/8 条未用，是最大的空槽）③ **`technology_state` 的 0 与 3 谁代表「未研究」**——本体 #7 磨坊用的是 0，其余用 3，这直接决定「科技前变」还是「科技后变」④ **最关键**：ObjectGenerator 是否在「建造落成」时也查这张表（#5–#8 四条语义上必须是，但 EXE 邻居全指向随机地图生成阶段） |

**不建议做的 3 个**（明确了「给不了」就不该承诺）：
- `eras.json` 加第六时代 —— 时代数由 .dat `tech_tree.ages=4` 决定，JSON 只是标签表；且改 .dat 触发 CRC 弹窗。**能做的是**给一个自定义 DLC 开第 3 个 `era`（换名/换图标/换前置文本），这是合法的。
- `selection_group_def.json` / `chronicles_selection_group_def.json` —— 引擎侧 0 命中 + 官方自己发了一份坏 JSON。要做得先做启动期 A/B 测试证明它被读。
- `adapterblacklist.json` / `custome_palette_list.txt` —— 与玩法无关 / 未证且反证强。

---

## 9. 遗留待验清单（给实机阶段）

1. `objreplacement.json` 的 `chance` 取值域（测 100 / 1 / 0）
2. `objreplacement.json` 的 `replacement_rate` 语义（8/8 条未用，最硬空槽）
3. `objreplacement.json` 的 `technology_state` 0 vs 3（磨坊 0，其余 3）
4. `objreplacement.json` 是否在建造落成时生效（ObjectGenerator 双职责）
5. `replacement_attribute` / `required_attribute` 的 82 / 263 各是什么属性（用 `xsGetPlayerAttributeName` 反射）
6. `unitcategories.json` 填了之后计分屏是否真改分类（截图）
7. `sharedbuildings.json` 新增条目是否自动出按钮（还是仍需 .dat 空按钮位）
8. `dropsites.json` 新增建筑为投放点是否被 .dat 属性位拦住
9. `target_civs` 的编码（dat civ 索引还是别的）
10. `selection_group_def.json` 是否真的被读（启动期 A/B）
