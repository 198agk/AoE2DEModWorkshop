# 兵营观察计划（task-3）

> 交付物作者：teammate `observation-planner`
> 写入范围：`_probe/team/observation/`（本文件即其中之一）
> 结论基于对**真实文件与真实字节**的读取，不是推理链。

---

## 0. 一句话结论

**VERDICT: OBSERVABLE AT THE BARRACKS**

蔷琵斥候（unit 2550）**不是**"只在科技树预览里"的东西。它是一个**真实的兵营可训练单位**，理由见第 1 节。
但紧接着必须说清一件事，否则这个结论会被误读：

> 本次 mod 的 A 半（只往 `BRITONS.json` 加了 2550，**没有**动 `futuravailableunits.json`）在兵营里
> **可能完全看不到变化，而这并不代表树文件没被读取**。见第 4 节结果 C 与第 5 节混淆项 #1/#4。

---

## 1. 最重要的答案：蔷琵斥候是不是只在科技树预览里？

**不是。** 四条独立证据：

### 证据 1：`RegionalUnit` 在兵营里本来就是正常排版（13 个先例）

出厂数据里，`.dat` 把**建筑 12（兵营）**登记为其训练地点的单位共有 49 个；其中 `Node Type` 为
`RegionalUnit` 的有 13 个，全部在兵营（建筑 12）：

| 单位 | 行 | 拥有它的文明（出厂即如此） |
|---|---|---|
| 鹰武士 / 精锐鹰武士 / 鹰斥候 | 751 / 752 / 753 | 阿兹特克、玛雅 |
| 火枪骑兵 / 精锐火枪骑兵 | 1901 / 1903 | 中国、女真、契丹、朝鲜、越南 |
| 重装步兵 / 精锐重装步兵 | 2110 / 2111 | 雅典、斯巴达（2110 还有色雷斯） |
| **蔷琵斥候 / 蔷琵战士 / 精锐蔷琵战士 / 蔷琵竞跑者** | **2550 / 2552 / 2554 / 2588** | **印加、马普切、穆伊斯卡、图皮** |
| 瓦兰吉卫队 / 精锐瓦兰吉卫队 | 2703 / 2704 | 拜占庭、丹麦、萨克森、瓦兰吉、维京 |

一个"只在预览里"的类别不可能同时是这 5 个文明家族的主力兵营单位。

### 证据 2：出厂的面板缓存**确实**把 2550 列在兵营下（4 个文明）

`D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\futuravailableunits.json`
里，2550 出现在**建筑 12（兵营）**下，共 4 次：

```
('Incas',   12, 1)   ('Muisca', 12, 1)
('Mapuche', 12, 1)   ('Tupi',   12, 1)
```

（`('ID': 2550, 'Name': 'Champi Scout', 'RequiredAge': 1)`）

### 证据 3：`.dat` 层面，**全部 63 个文明**的 2550 都以兵营 12 为训练建筑

```
British  id=2550 name='CHAMPIR' type=70 class=6 hp=35 train=[(12, 1)]
Incas    id=2550 name='CHAMPIR' type=70 class=6 hp=35 train=[(12, 1)]
```

`type=70` 即 `CREATABLE`。2550 在 63 个文明里各有一条物理记录，训练地点都是 `unit_id=12`。
**所以 .dat 不是"英国能不能造"的那个闸门。**

### 证据 4：`RegionalUnit` 这个字符串在界面层只出现在科技树屏幕，但这**不构成**"只能预览"的证明

- `D:\Games\Steam\steamapps\common\AoE2DE\widgetui\screentechtree.json:1710` = `"Name": "RegionalUnitIcon",`
- 同文件 `:1721` = `"Material": "TTKeyRegionalUnit"`
- `D:\Games\Steam\steamapps\common\AoE2DE\widgetui\materials.json:22940` = `"Name": "TTKeyRegionalUnit",`

但是：`widgetui\commandpanel.json` 里 `RegionalUnit` 出现 **0 次**、`futuravailable` 出现 **0 次**。
也就是说**命令面板根本不认识 `RegionalUnit` 这个词**——它只按 ID 画按钮。
"科技树屏幕有 `RegionalUnitIcon`"只说明科技树会给这一个**图标角标**，不说明兵营不画它。

> 因此：**A 半在兵营是可以观察的**。真正的不确定性不是"预览 vs 菜单"，
> 而是"**树文件**驱动按钮格 还是 **面板缓存**驱动按钮格"。见第 4 节。

---

## 2. 开工前的状态（2026-10-15 01:53 实测）

### 2.1 mod 已装好，文件正确

`C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Smoke5 TreeVsPanel\`

| 文件 | 字节 | sha256（前16位） |
|---|---|---|
| `info.json` | 319 | `5c94a49a2a97924b` |
| `resources\_common\dat\empires2_x2_p1.dat` | 11,983,020 | `330665c06b53f033` |
| `resources\_common\dat\futuravailableunits.json` | 1,331,035 | `faeca198b2c17fd3` |
| `resources\_common\dat\CivTechTrees\BRITONS.json` | 74,991 | `6802baf4ecb52fbe` |

### 2.2 两半改动都已按字节核实

**A 半（只加树文件）** —— `BRITONS.json` 出厂 145 行 → mod 146 行，新增 1 行，位于第 2768–2781 行
（`"Name": "Champi Scout"` 在第 2768 行，`"Node ID": 2550` 在第 2778 行）：

```json
{"Age ID": 1, "Building ID": 12, "Draw Node Type": "UnitTech", "Help String ID": 105526,
 "Link Node Type": "Unit", "Name": "Champi Scout", "Name String ID": 14526, "Node ID": 2550,
 "Node Status": "ResearchedCompleted", "Node Type": "RegionalUnit", "Picture Index": 540,
 "Trigger Tech ID": 1350, "Use Type": "Unit"}
```

这一行与出厂 **INCAS.json 里的那一行逐字节相同**（13 个键全部一致），所以它不是手写的近似品，
而是把一个**已经在游戏里正常工作的行**原样搬过来。

配套的科技 1350 也存在且形状正确：

```
tech 1350 = 'Champi Scout (make avail)'  civ=-1  loc=[12]  btn=[6]
effect 1350 = 'Champi Scout (make avail)'  n_cmd=1  cmds=[(type=2, a=2550, b=1, c=-1)]
```

与图皮的"可造"科技形状完全一样（`453 'Tarkan (make avail)' cmds=[(2, 755, 1, -1, ...)]`）。

**B 半（只减面板）** —— mod 的 `futuravailableunits.json` 与出厂相比，**整个英国只有一处不同**：

```
block 12 (Barracks/兵营)  units removed=[74]  added=[]
```

出厂英国的兵营块有 8 项，mod 里是 7 项，少了 74（民兵）。其余 30 个建筑块逐字节相同。

### 2.3 对照（村民血量）确实生效

出厂 `British` 村民（83）`hit_points = 25` → mod 里 `= 1000`。
两份 `.dat` 解压后都是 93,268,152 字节，差异 **3,402 字节，恰好 1,701 段、每段 2 字节**，
每段都是 `1900` → `e803`（int16 25 → 1000）。1,701 正好等于出厂 `unit_header_count`。
**这是"mod 已装且只动了该动的东西"的最强证明。**

### 2.4 ⚠ 阻塞项：这个 mod **还没有被游戏注册**

`C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\mod-status.json`
（2,204 字节，mtime 2026-10-15 00:54:44）里只有 9 个 Mods 条目：

```
Enabled=False Prio=1  local//aoe2mod Bundle VillagerHP plus Britons HandCannon
Enabled=True  Prio=2  subscribed//182654_Age of Anime (Chibi Edition)
Enabled=True  Prio=3  subscribed//550412_透明主题整合自用
Enabled=True  Prio=4  subscribed//550009_2026 Civilization Alliance 文明联盟  文本UI(v20)
Enabled=True  Prio=5  subscribed//423822_四月-juntuanzhangtianfuwenben军团长天赋文本
Enabled=False Prio=6  subscribed//297820_10 倍资源文明联盟3倍科技
Enabled=False Prio=7  subscribed//550749_{2026}1X Civilization Alliance and 3X res 文明联盟 v57
Enabled=False Prio=8  subscribed//551103_10xResources 2xTech  CivilizationAlliance
Enabled=False Prio=9  subscribed//423821_四月-juntuanzhangtianfumozu军团长天赋模组
>>> Smoke5 present: False
```

**`aoe2mod Smoke5 TreeVsPanel` 完全不在列表里。**
它已在磁盘上，但游戏还没扫描到；在它出现之前**无法勾选**。
注意 `mod-status.json` 读取时要用 UTF-8 BOM（`encoding="utf-8-sig"`），PowerShell 的
`ConvertFrom-Json` 会报 `传入的对象无效`。

---

## 3. 上机观察步骤（中文界面逐字）

### 3.0 开打前必须确认（不确认就不用打了）

1. 打开 **模组**（模组管理器），确认列表里**出现** `aoe2mod Smoke5 TreeVsPanel` 并且**已勾选**。
   - 若列表里没有它：先**退出游戏重开一次**让游戏扫描 `mods\local`，再看。
   - 若仍未出现：**实验作废**，回来告诉我，我改注册方式。
2. 确认 `aoe2mod Bundle - Villager HP + Britons Hand Cannoneer` **未勾选**。它装了同样的三个文件，
   其中 `.dat` 是 11,983,020 字节的**旧版/外来基线**，一旦启用会污染本次观察。
3. 记住 **选项 → 界面** 里 `显示未来的物品`（字符串 ID 8898）的开关状态，**记录下来**。
   相关文件位置：`D:\Games\Steam\steamapps\common\AoE2DE\widgetui\screenoptions.json:1565`
   （`"Name": "EnableFutureItemsDisplay"`），它的说明文字（ID 98877）是：
   > 「点击启用只可通过达成升级到下一个时代等特定条件，而开放使用之建筑、单位和科技的预览图标。」

   注意它和另一个**独立的**选项 `TechTreePreview`（`screenoptions.json:1601`）不是一回事。

### 3.1 快速开一局不列颠黑暗时代

| 步骤 | 中文界面 | 字符串 ID |
|---|---|---|
| 1 | 主菜单 → **单人游戏** | 9202 / 9500 / 9679 |
| 2 | **标准游戏** | 9226 / 9239 |
| 3 | **文明** → **不列颠** | 9681 / 10271 / 13545 / 62001 |
| 4 | **起始时代** → **黑暗时代** | 9734 / 10261 / 4201 / 7104 / 20110 / 20385 |
| 5 | **地图** → **阿拉伯半岛**（无海，方便造兵营） | 10010 / 10875 |
| 6 | **开始游戏** | 9472 / 9710 / 170023 |

（`不列颠` 就是 Britons；`兵营` = 5135 / 13004；`民兵` = 5079 / 14079。）

**最快看到兵营格子的办法**：黑暗时代开局后，把资源/人口调到最高（或用修改器/场景），
立刻用村民造一个**兵营**——但**起始时代必须保持黑暗时代**，因为换成后帝王时代会让
`RequiredAge` 过滤失效，第 5 节 #1 那个时代门就测不出来了。

### 3.2 看哪里（关键：两个屏幕不要混淆）

- **兵营建造菜单** = 选中**兵营**后，**屏幕右下角**的命令面板里那一排**训练按钮**。
  光标悬停会显示 `生产民兵`（6079）、`生产长枪兵`（6408）之类的提示。
- **科技树预览** = **另一个屏幕**，要用菜单里的 **科技树**（9799 / 40101）或 **完整科技树**
  （9732 / 13524）打开。

> ⚠ 在**科技树**里看到「蔷琵斥候」/「蔷琵\n斥候」（ID 14526）**完全不能**证明兵营里有它。
> 本次要看的**只有右下角命令面板**。

### 3.3 具体记什么（4 个数）

1. 命令面板里**一共几个**单位训练格？（不是几个可点，是**一共画了几个**）
2. 其中**有没有**「蔷琵」相关的一个（图标 540，名字 `蔷琵\n斥候`，鼠标悬停出现"生产…"提示）？
3. **民兵**（5079 / 14079）**还在不在**？
4. **村民**选中时血量是不是 **1000**？（对照，先看这个）

---

## 4. 四种结果的预判表（**先写死，再看盘**）

前置：**先看村民血量**。不是 1000 → mod 没加载 → 后面全部作废，直接结束。

| # | 观察（黑暗时代兵营） | **证明什么** | **不证明什么** |
|---|---|---|---|
| **A** | 蔷琵斥候**在** + 民兵**在** | 树文件和面板文件**都不是**实时按钮来源（两者都只是元数据）；按钮来自别的机制 | ✗ 不证明 mod 没加载（村民血量已排除）<br>✗ 不证明树文件不被读取（科技树屏幕仍可能读它）<br>✗ 不证明"任何数据 mod 都改不了"（只证明这两个文件不是来源） |
| **B** | 蔷琵斥候**在** + 民兵**消失** | **最强结论**：树文件能"加"、面板文件能"减"，两个文件**都**实时参与按钮生成 | ✗ 不能区分"树单独驱动"还是"树+面板联合驱动"<br>✗ 不能证明面板能"加"（本次没测面板加法） |
| **C** | 蔷琵斥候**不在** + 民兵**消失** | 面板缓存是实时来源（减法生效）；**只加树文件不够**，树不是（单独的）杠杆 | ✗ **不证明**"蔷琵斥候不可在兵营观察"——只证明"只改树不够"<br>✗ 不证明树文件语法错（该行与印加出厂行逐字节相同）<br>✗ 不证明调度问题（本次调度的只是这一行） |
| **D** | 蔷琵斥候**不在** + 民兵**在** | **两处改动都没生效** → mod 未加载 / 未启用 / 被覆盖 / 看错界面 | ✗ 得不出任何关于"树 vs 面板"的结论<br>✗ 不能据此判定设计失败<br>→ 先查最新 `MainLog.txt` 里有没有 `Enabling mod #0 (aoe2mod Smoke5 TreeVsPanel)` |

### 两个"伪装成结论"的特殊情形

| 情形 | 真相 | 证明什么 / 不证明什么 |
|---|---|---|
| 蔷琵斥候**出现但是灰色、点不动** | 那是 **`显示未来的物品` 的画法**（预览图标），不是可训练按钮 | 证明这一行被当成"尚未开放"的预览项；**不证明**它可训练。请务必同时记录该选项的开关状态 |
| 兵营单位格**全空**，但右边还有"设置聚集点"等按钮 | 这是**被过滤后的空面板**，不是坏掉的 UI | 证明"面板里没有符合当前时代条件的单位"；**不证明**界面崩了。`buttons.json` 里的 `设置聚集点`/`城镇钟` 等上下文按钮来自**另一个文件**，与本次改动无关 |

---

## 5. 混淆项清单（每条都带 文件+行号 证据）

### #1 【最危险】时代门（Age gate）把"缺少"伪装成"失败"

出厂英国兵营块在缓存里列了**全部四个时代**的单位：

```
74 民兵           RequiredAge=1
93 长枪兵         RequiredAge=2    75 长剑士      RequiredAge=2
77 双手剑士       RequiredAge=3    358 长枪兵     RequiredAge=3
473 冠军剑士      RequiredAge=4    567 冠军        RequiredAge=4   359 长枪兵 4
```

直方图 `{1:1, 2:2, 3:2, 4:3}`。也就是说**只有"民兵"是黑暗时代能出的**。
**上一个把"靶场没有火枪手"当成失败读数的实验，就是被这个门骗的**（火枪手 RequiredAge=4）。
→ 所以第 3.3 节的第 1 问（**一共画了几个格**）就是用来识别这个门的：
如果只画 1 个 → 游戏在按时代过滤；如果画了 8 个（还带灰） → 它画的是整张表。

### #2 mod 的 B 半**恰好删掉了黑暗时代唯一的那个格**

mod 的英国兵营块 = 出厂 8 项 **减 74**，剩 7 项，`RequiredAge` 全部 ≥ 2。
所以在"按时代过滤"的读法下，**mod 的黑暗时代英国兵营应该是 0 个单位格**。
这是**设计上就会出现的空面板**，而不是加载失败。
→ 判断标准：**单位格全空，但右下角上下文按钮（设置聚集点等）仍在** = 过滤后的空，不是崩溃。

### #3 mod 尚未被游戏注册

见 §2.4。`mods\mod-status.json` 里 9 个条目全无 Smoke5。
在它出现并被勾选之前，任何观察都是空转。

### #4 本地 mod 只在日志的**第二遍**才出现

最新日志 `C:\Users\26913\Games\Age of Empires 2 DE\logs\2026.10.14-2339.53\MainLog.txt`：

```
232: Setup mod manager
233-240: Enabling mod #0 (四个订阅 mod)   ← 每个出现两次
259: Setup post mod manager
265: Opening resource packages
292: Loading player profile
324: Running Game
897: Closing video
922: Enabling mod #0 (aoe2mod Bundle - Villager HP + Britons Hand Cannoneer)
931: Enabling mod #0 (aoe2mod Bundle - Villager HP + Britons Hand Cannoneer)
2132: Terminating Mod Manager
```

订阅 mod 只出现在**第一遍**；本地 mod 只在 `Running Game` **之后**的第二遍出现。
→ **事后校验**：在新日志里搜 `aoe2mod Smoke5 TreeVsPanel`。搜不到 = mod 从未加载 = 作废。

### #5 日志**无法**证明哪个文件赢了

对同一份日志全文搜 `futuravailable` / `CivTechTrees` / `commandpanel` / `linkedUnits` /
`DisplayFutureItems` / `.json`：**全部 0 次**。游戏不打印它读了哪些数据文件。
→ 日志只能证明"mod 被启用"，不能证明"树赢了还是面板赢了"。

### #6 "显示未来的物品"开关会改变你看到的东西

`screenoptions.json:1565` = `EnableFutureItemsDisplay`（字符串 8898 =「显示未来的物品」）；
`screenoptions.json:1601` = `TechTreePreview`（**另一个独立选项**）；
`stringreference.json:394` = `"IDS_OPT_DISPLAY_FUTURE_ITEMS": 8898,`。
说明文字（ID 98877）明说它画的是**预览图标**。
→ 开/关会直接改变"灰格是否出现"。**必须记录开关状态**，否则灰色与可点是分不清的。

### #7 别改错文件：`widgetui\futuravailableunits.json` 是 81 字节的跳转桩

它的全部内容是：
`This file has been moved to Game/resources/_common/dat/futuravailableunits.json`。
真正生效的是 `resources\_common\dat\futuravailableunits.json`。（网上那两个"这些文件放在 mod 里不生效"的帖子
说的都是旧的 `widgetui\` 位置，对本次布局不适用。）

### #8 竞争 mod

`aoe2mod Bundle VillagerHP plus Britons HandCannon`（`mod-status.json` 里 `Enabled=False Prio=1`）
装了**同样三个文件**，且它的 `.dat` 是 **11,983,020 字节**，而出厂 `.dat` 是 **12,023,754 字节**
——它是**过期的外来基线**。启用它会整体覆盖。**必须保持未勾选。**

四个已启用的订阅 mod（P2–P5）经扫描**各自携带 0 个相关文件**，不构成文件级冲突。

### #9 两份缓存**分治**文明名单（别去错的文件里找）

- `futuravailableunits.json`：**58** 个文明键（基础/DE 文明，含 `Britons`）
- `paphosfutureavailableunits.json`：**12** 个文明键（`Achaemenids / Athenians / FullTechCiv / Gaia /
  Macedonians / Paphos6-9 / Puru / Spartans / Thracians`）

英国在**第一份**里。另外**没有任何一份缓存覆盖 `MAGYAR`**（已知的 `CIV_FILE_OVERRIDES` 映射条目）。

### #10 树文件路径/大小写

必须是 `resources\_common\dat\CivTechTrees\BRITONS.json`（大写）。少一层 `CivTechTrees` 会直接
`FileNotFoundError`。出厂目录 `D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\CivTechTrees`
是安装里**唯一**这类目录，含 **62** 个文件。

### #11 选错建筑 / 建筑未建成

选中**靶场**（87）会看到弓箭手（4），选中**马厩**（101）会看到斥候骑兵（5326），
都不在本次观察范围。兵营必须在**建成后**再选中（在建中的建筑不画训练格）。

### #12 名字混淆

黑暗时代兵营里正常只有 **民兵**（5079 / 14079）。
**长枪兵**（5408）是封建时代（RequiredAge=2）——如果只看到"少了长枪兵"，那不是本次改动造成的。

### #13 `Use Type: "Tech"` 的行会混进单位空间

树的 `civ_techs_units` 数组里，兵营下还有 3 行是**科技**不是单位：
`602 火焰箭`(age2)、`875 Gambesons`(age3)、`215 方阵`(age3)。
如果只按 `Node ID` 数数，会把它们误算成"要显示的单位"。

---

## 6. 本次实验的预测矩阵（对上就是结论）

| 模型 | 黑暗时代英国兵营**应该**画几个格 | 具体是哪些 |
|---|---|---|
| 出厂，按时代过滤 | **1** | 民兵 |
| 出厂，不作时代过滤（画全表） | **8** | 上表 8 个 |
| mod，**树驱动** + 按时代过滤 | **2** | 民兵、**蔷琵斥候** |
| mod，**面板驱动** + 按时代过滤 | **0** | （空） |
| mod，**面板驱动** + 不按时代过滤 | **7** | 75/77/473/567/93/358/359（全部 RequiredAge≥2，应显示为灰或不可点） |

> 关键：**"画了几个"这个数字本身就能分辨模型**，不需要猜。

---

## 7. 事后校验（三步，2 分钟）

1. 在**最新**的 `C:\Users\26913\Games\Age of Empires 2 DE\logs\<最新目录>\MainLog.txt` 里搜
   `aoe2mod Smoke5 TreeVsPanel`。**没有 → mod 未加载 → 结论作废。**
2. 复查 `mods\mod-status.json` 里 Smoke5 是否变成 `"Enabled": true`。
3. 复查 mod 目录里 4 个文件的字节数与 sha256（§2.1）——确认游戏没有改写它们。

---

## 8. 诚实边界（我没能证明的东西）

1. **我无法从文件判定"树驱动还是面板驱动"**。出厂数据里两者在无条件行上重合
   **2,667 / 2,673 = 99.78%**；真正缺失的只有 6 条，且其中 5 条是**带前置条件**的行
   （哥特兵营 759/761 哈斯卡尔前置科技 16、匈奴 886/887 前置 483、图皮 532 前置 35）。
   两个模型在出厂数据上**预测完全相同**——正因如此这个实验才有意义，也正因如此**只能靠上机分辨**。
2. **"面板缓存 = 显示未来的物品"是强推断，不是证明**。证据是文件名（`futuravailableunits.json`）
   + 官方选项名（`EnableFutureItemsDisplay` / `DisplayFutureItems`，字符串 8898）
   + 官方说明文字（"预览图标"，字符串 98877）。但 `commandpanel.json` 与
   `techtreepreviewpanel.json` 里**都没有** `futuravailable` 字符串，
   所以**界面层没有任何一条线把这份缓存接到命令面板上**。
3. **`.dat` 里的科技名**要按**列表下标**取（记录里没有 `id` 键）。
   `tech 16 = 'Gothic Anarchy'` 是按下标查出来的；不要反过来说"16 号科技是 Anarchy"以外的推断。
4. **外部印证不足**：格鲁吉亚"攻城巨投"、斯巴达"渔船"这 6 条判别行
   在搜索结果里找不到可信页面，所以**我没有**用外部知识来判定这 6 条的归属。
   （能查到的只有社区对**著名负面**的记载——保加利亚没有冠军/强弩/火枪/游侠、女真科技树
   到不了冠军/强弩/火枪——这些都与**树**一致、与**缓存**矛盾，但两条互相抵消的偏差不足以定案。）
5. **面板缓存存在 66 个"孤儿"条目**（缓存列了、`.dat` 里没有对应训练建筑）：
   61 个集中在**建筑 118（村民建造菜单）**（那里用的是另一套约定：`.dat` 把"村民可造"编码成训练建筑 `-1`），
   另 5 个在**建筑 2556**。**建筑 12（兵营）的孤儿数 = 0**，所以兵营这一块是干净的、可解释的。

---

## 附：本次为得出结论而写的探针（均在 `_probe/team/observation/`）

| 脚本 | 用途 |
|---|---|
| `probe_dat_train.py` / `probe_dat_train2.py` | 走 .dat 训练地点；**第一版有方法学假象**（见下） |
| `probe_regional_at_barracks.py` | 13 个"兵营 RegionalUnit"三证人核对 |
| `probe_mod_vs_shipped.py` | mod 与出厂逐文件 sha256/尺寸/时间 |
| `probe_direction.py` | 村民血量对照 + 全量字节差（1,701 段） |
| `probe_direction2.py` / `probe_cache_shape.py` | 缓存结构（顶层是文明表、`Buildings` 是**数组**） |
| `probe_crosstable2.py` | 缓存 vs 树 全量交叉表 + 外部事实裁判表 |
| `probe_prediction.py` | **决定性计数**：2,673 条无条件行只缺 6 条 |
| `probe_hoplite_case.py` / `probe_huskarl_decision.py` | 兵营可训练但缓存从未列出的 22 个单位 |
| `probe_goths_huskarl.py` | 哥特兵营哈斯卡尔在缓存里完全不存在 |
| `probe_anarchy.py` | 哥特树兵营块逐行 + 缓存 `PrereqTech` 全集 |
| `probe_techshape.py` / `probe_techid.py` | 科技记录形状（**下标即 ID**）；`tech 16 = Gothic Anarchy` |
| `probe_trigger.py` | `Trigger Tech ID 1350` 机制 + mod 行与印加行逐字节比对 |
| `probe_effect1350.py` | 效果 1350 = `(type 2, a=2550, b=1)`，与图皮"可造"同形 |
| `probe_conflict_scan.py` | 所有已启用 mod 的相关文件扫描；Smoke5 未注册 |
| `probe_preflight_final.py` | 最终状态 + 本报告引用的全部行号 |
| `probe_log_final.py` | 日志两遍 mod 管理器 + 日志不含任何 `.json` 字符串 |
| `probe_zh_labels.py` / `probe_zh_labels2.py` | 中文界面字符串 |

> **方法学教训（写给下一个做同类探针的人）**：`train_locations` 是
> `aoe2mod/dat/locate.py:85 walk_unit` 挂上去的，**不是** `parser.py:761 read_unit` 挂的。
> 用 `Parser(...).parse()` 再取 `u["train_locations"]` 会得到**每个单位都是空表**，
> 于是"证明"了"没有任何单位在兵营可造"——一次纯粹的测量假象（缺键与空表长得一样）。
> 同类陷阱还有两处：缓存的顶层**就是**文明表、`Buildings` 是**数组**不是字典；
> 以及 `CT.load_trees` 签名用错时返回 `{}`，看起来像"这个文明没有单位"。
> **先打印非零计数，再下结论。**
