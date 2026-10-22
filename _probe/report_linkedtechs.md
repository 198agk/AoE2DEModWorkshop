# linkedTechs.json — `Toggleable` / `Cycle` 机制逆向报告

调查对象：`D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\linkedTechs.json`（3947 B，20 组）
数据源：主库 `empires2_x2_p1.dat`（GV=54，1510 条 tech，1500 条 effect，effect 段结束偏移 93202964 / 文件 93268152）
所有探针脚本在 `_probe\`，原始输出在 `_probe\out\p13.txt`…`_probe\out\p37.txt`。

**总纲（一句话）**：`linkedTechs.json` 里的三个 Type **都不是 .dat 里的一个字段**。`.dat` 只提供原料（科技记录的 `civ / required_techs / costs / research_locations` + 效应命令 `101/102/103`），`linkedTechs.json` 提供的是**引擎侧的"这几个科技属于同一个选择器"的分组与循环语义**，而 `Instant` / `Local` / `StartingTech` 是连 `.dat` 都表达不了的纯引擎标志。

---

## 1. `Toggleable` 在数据上怎么表达「可反复研究」

### 1.1 已实测：雅典三科技 vs 织布机 22 的记录差异

| 字段 | 22 Loom（普通一次性） | 1202 Oligarchy | 1203 Democracy | 1204 Tyranny |
|---|---|---|---|---|
| `type` | **0** | **33** | **33** | **33** |
| `civ` | -1（全文明） | **47** | 47 | 47 |
| `required_techs` | `[104]`（黑暗时代） | `[1208]` | `[1208]` | `[1208]` |
| `costs` | `(3,50,1)` = 50 金 | `(3,0,1)` = **0 金** | `(3,0,1)` | `(3,0,1)` |
| `research_locations` | `(109, 25, 6)` = 城镇中心/25 秒/按钮 6 | `(109, **0**, 2)` | `(109, 15, 3)` | `(109, 15, 4)` |
| Repeatable byte | **1** | 1 | 1 | 1 |
| `effect_id` | 22 | 1192 | 1193 | 1194 |

[证据: `_probe\out\p15.txt`（自写 walker 重走全部 1510 条，保留被 `aoe2mod\dat\locate.py:393` 丢弃的 Repeatable 字节）；重复分布 rep=1→1188 条、rep=0→322 条，**没有第三个取值**]

### 1.2 关键结论：`Toggleable` 不是任何一个字段，而是「三个机制叠加」

**（a）Repeatable 字节 = 1 —— 但它不是判据。**
`aoe2mod\dat\locate.py:393` 有 `r.u8()  # Repeatable`，读后丢弃；`aoe2mod\dat\writer.py:826` 写常量 `w.u8(0)`。实测 1188/1510 条科技该字节为 1，包括大量普通一次性科技（如 22 Loom = 1、1195 Satrapy = 1、1275 Doctrine = 1）。**所以 Repeatable=1 是「这条科技的入口可以被再次触发」的引擎级能力，几乎所有科技都是 1，不区分是否 Toggleable。** [证据: p15.txt 全域分布 + `aoe2mod\dat\locate.py:393`]

**（b）`type` 字段 —— 在 shipped 数据里与三种 Type 高度相关，但不是机制本身。**
- 全库 type 分布：`{0: 1488, 2: 3, 32: 6, 33: 13}`（共 1510）。[证据: `_probe\out\p12.txt` / `_probe\out\p33.txt`]
- **所有 8 个 Toggleable 成员（1202/1203/1204/1263/1264/1265/1359/1373）都是 type=33**；**所有 Cycle 成员（1215/1216/1217/1275…1283）都是 type=0**；**所有 MutuallyExclusive 成员是 type=0 或 type=32（1195/1196/1197 是 32）**。
- **但 type=33 不等于 Toggleable**：type=33 的 13 条里有 1205/1206/1207（Reset 三兄弟）、1497/1498（Castle/TC Destroyed/Built），都不在 linkedTechs.json 里。
- **type 也不是「含科技操作命令」的标志**：假设 H1「type==33 ⟺ effect 含 101/102/103」实测 agree=1428 / **mismatch=82**，反例全是 type=0 的 C-Bonus / [FTT] / Shadow 科技（78、79、104、117、298、309、717、785…）。假设 H2「type==32 ⟺ 含 per-instance 命令」agree=1494 / mismatch=16。**两条都证伪。** [证据: `_probe\out\p32.txt`、`_probe\out\p33.txt`]

→ **结论（已实测）**：`type` 是引擎内部的科技分类标签（0=普通、2=时代、32=per-instance 升级、33=可切换型），shipped 数据里三种 linkedTechs Type 与它一一对应得上，但它是**相关性而非定义**。你不能靠把 type 改成 33 就让一条科技变成 Toggleable。

**（c）真正的表达在 effect 命令里 —— `type 102` 互禁 + Reset 科技。**
424009 组三个 effect 每个都带 **3 条 type102**：

```
effect 1192 "Economic Policy" (tech 1202)  共 10 条
  [0] type102 d=1203        ← 禁用 Democracy
  [1] type102 d=1204        ← 禁用 Tyranny
  [2] type101 a=1205 d=0    ← Reset Oligarchy 成本设 0
  [3] type103 a=1205 d=-1   ← Reset Oligarchy 时间设 -1
  [4] type102 d=1205        ← 禁用 Reset Oligarchy 本身
  [5] type101 a=1214 / [6] type103 a=1214   ← 把"初始 Oligarchy"这条一次性引导科技也归零
  [7] type1 a=234 d=1.0
  [8] type7 a=2229 b=109 c=1                ← 在城镇中心生成单位 2229
  [9] type6 a=502 d=1.5                     ← 资源 502 ×1.5
effect 1193 "Naval Policy" (1203) 共 11 条：102→1202, 102→1204, 101/103/102 对 1206, type5 a=-1 c=105 d=0.8 ×2
effect 1194 "Military Policy" (1204) 共 27 条：102→1202, 102→1203, 101/103/102 对 1207, 101 a=1206 b=1 ×2, 15 条 type4 b=-1 c=104 d=-57.75
effect 1195 "Reset Oligarchy" 仅 3 条：101 a=1205 d=1.0、103 a=1205 d=1.0、type6 a=502 b=4 c=13 d=0.6666667
effect 1196 "Reset Democracy" 仅 4 条：101 a=1206 d=1.0、103 a=1206 d=1.0、type5 a=-1 c=105 d=1.25 ×2
effect 1197 "Reset Tyranny" 18 条：101 a=1207 d=1.0、103 a=1207 d=1.0、type1 a=551 d=0.0、+15 条与 1194 精确镜像的反值
```
[证据: `_probe\out\p11_raw.txt`（逐条四槽原文）、`_probe\out\p18.txt`、`_probe\out\p30.txt`（每组 type 直方图；424009 汇总 `{1:4, 4:15, 5:2, 6:1, 7:3, 101:8, 102:9, 103:6}`）]

**（d）判据总表（20 组逐组实测）**

| 组 | Type | 成员 | 每 effect 的 type102 条数 | 组内 type 直方图 |
|---|---|---|---|---|
| 424009 | Toggleable | 1202,1203,1204 | **3 / 3 / 3** | `{1:4,4:15,5:2,6:1,7:3,101:8,102:9,103:6}` |
| 424011 | Toggleable | 1263,1264,1265,1359,1373 | **4 / 4 / 4 / 4 / 4** | `{1:5,102:20}` |
| 424010 | Cycle | 1215,1216,1217 | **0 / 0 / 0** | `{1:3}` |
| 424012 | Cycle | 1275,1276,1277 | **0 / 0 / 0** | `{0:69}` |
| 424013 | Cycle | 1278–1280 | **0 / 0 / 0** | `{0:81}` |
| 424014 | Cycle | 1281–1283 | **0 / 0 / 0** | `{0:36}` |
| 424001 | MutuallyExclusive | 1195–1197 | 2 / 2 / 2 | `{3:3,102:6}` |
| 其余 13 组 | MutuallyExclusive | — | 各 2 | `{...,102:4}` 等 |
[证据: `_probe\out\p19.txt`、`_probe\out\p30.txt` 全 20 组逐组输出]

→ **`Toggleable` 的数据表达 = 「组内每个科技在 effect 里用 type102 禁掉所有兄弟」+「可以再用 type101/103 把被禁的那个重新放出来」。这是与 `Cycle` 唯一的 .dat 级差别：Cycle 组的 type102 计数全部为 0。**

### 1.3 已实测：Toggleable 与 Cycle 的第二个区分点 —— 按钮槽位

| 组 | 每个成员的 `(location_id, research_time, button_id, hotkey_id)` |
|---|---|
| 424009 Toggleable | 1202 `(109,0,2,418017)`、1203 `(109,15,3,418018)`、1204 `(109,15,4,418019)` → **三个不同按钮并排在 TC** |
| 424011 Toggleable | 1359 `(17,0,1,18446)`、1264 `(17,0,2,18447)`、1373 `(17,15,3,18448)`、1263/1265 `(-1,0,0,16000)` → **多按钮 + 部分成员根本没有按钮** |
| 424010 Cycle | 1215/1216/1217 **全部 `(2172,·,14,418022)`** |
| 424012/013/014 Cycle | 1275–1277 **全部 `(12,1,15,418077)`**；1278–1280 **全部 `(87,1,15,418078)`**；1281–1283 **全部 `(101,1,15,418079)`** |
[证据: `_probe\out\p26.txt`、`_probe\out\p30.txt`]

→ **Cycle 组全体共享同一个 `(location, button, hotkey)` 三元组 = UI 上就是一个按钮；Toggleable 组各成员 button_id 互不相同 = 多个按钮。这是 .dat 里能直接读出来的最稳定判据。** [证据: p26.txt]

---

## 2. `Cycle` + `Instant: true` 是什么行为

### 2.1 已实测：1275/1276/1277 的记录

| 字段 | 1275 Balanced | 1276 Regulars | 1277 Mercenaries |
|---|---|---|---|
| `civ` | 54 | 54 | 54 |
| `required_techs` | **`[]`** | **`[]`** | **`[]`** |
| `costs` | `(-1,0,0),(-1,0,0),(-1,0,0)` **全空** | `(-1,1,0)` | `(-1,1,0)` |
| `research_locations` | `(12, **1**, 15)` | `(12, 1, 15)` | `(12, 1, 15)` |
| `research_time`（API 字段） | `None` | `None` | `None` |
| `type` | 0 | 0 | 0 |
| Repeatable | 1 | 1 | 1 |
[证据: `_probe\out\p15.txt`、`_probe\out\p34.txt`；`location_id=12` = **兵营**（`tk.describe(12,kind="unit")`），1278 组 `87`=靶场、1281 组 `101`=马厩]

**注意两个细节**：
1. **`research_time` 字段在 GV=54 下恒为 `None`** —— 研究时间只在 `research_locations[i].research_time` 里。所以「Instant 是不是 0 秒」要读元组：**三个档位的 time 全是 1 秒，不是 0。** [证据: `aoe2mod\dat\locate.py:394-405`（GV≥GV_C31 时 research_time 改由 research_locations 承载）；p34.txt]
2. `costs` 的 `(-1,1,0)` 是「资源类型 -1、数量 1、**flag=0**」；`aoe2mod\dat\locate.py:353-359` 注释 `1 = paid, 0 = only needed, 2 = seen`。**flag=0 表示「不作为花费扣除，仅作为满足条件计数」**，所以 1276/1277 实际也是免费的。

### 2.2 「空 required_techs + 有 cost」意味着什么

- `.dat` 的 `required_techs` 是**硬门**（研究前置科技）。空数组 = 无科技前置，只要玩家达到该建筑/时代就能点。
- 全库「`req==[]` 且 cost 槽 0 非空」共 **41 条**，包括 1210/1211/1212/1213（第 1–4 次更换政府，`costs=(1,0,0)`）、1138 Paphos Shadow Tech `(0,1,1)`、1141 Shipyard built、1222 Port built、555–558 Enable animals、968–977 Placeholder 1–10、737–747 Resources last +N%。[证据: `_probe\out\p19.txt`]
- **所以「空 req + 有 cost」是普通写法，不是 Cycle 的特效。** Cycle 组的特殊性只体现在：三档共享一个按钮、effect 是**绝对赋值**而不是增减。

### 2.3 已实测：Cycle 的 effect 是纯绝对设置，因此天然幂等

```
effect 1223 "Regulars Recruitment (Barracks)"  23 条，全部 type0（设置属性）
  a=74,75,77,567  c=103(食物成本) d=50.0 ；a=93,358,359 c=103 d=35.0 ；a=2384,2385,882 c=103 d=50.0
  a=93,358,359    c=104(木材成本) d=25.0
  a=74,75,77,567  c=101(训练时间) d=21.0 ；93,358,359 d=22.0 ；2384 d=19.0 ；2385 d=15.0 ；882 d=18.0
effect 1224 "Mercenary Recruitment" 23 条：食物 42.5 / 29.75、木材 21.25、时间 31.5 / 33.0 / 28.5 / 22.5 / 27.0
effect 1225 "Balanced Recruitment" 23 条：食物 55.0 / 38.5、木材 27.5、时间 10.5 / 11.0 / 9.5 / 7.5 / 9.0
```
[证据: `_probe\out\p11_raw.txt`、`_probe\out\p23.txt`；目标单位 74 民兵/75 武士/77 长剑士/93 长矛兵/358 长枪兵/359 长戟兵/567 冠军剑士/882 意大利佣兵/2384 方阵步兵/2385 精锐方阵步兵]

→ **三档都是「把成本/时间设成这个绝对值」，不是 `type4`（增减属性）。所以 A→B→C→A 循环不需要任何撤销命令，也不需要 Reset 科技。** 这就是为什么 4 个 Cycle 组的 type102 计数全是 0。

### 2.4 关于 `Instant: true` 本身 —— 已实测：`.dat` 里没有它的痕迹

- `Instant` 是引擎硬编码键：[证据: `AoE2DE_s.exe`（72166200 B）偏移 53053056..53053170 的可打印串按地址升序正好是 `Comment, Techs, Instant, Local, StartingTech, LinkedTechs, linkedTechs.json, MutuallyExclusive, Toggleable, Cycle`]
- 4 个 Cycle 组都带 `Instant:true`，但它们成员的 `research_time` 分别是 `1`（424012/013/014）和 `0/1/1`（424010），**没有一组是 0**。而 Toggleable 组的 1202 也是 `0`、1359 也是 `0`。
- → **已实测**：`Instant` 无法由 `.dat` 的 research_time 推断，它是引擎侧的「点了就直接生效、不进入研究队列/不显示进度条」标志。
- → **推断（未游戏内验证）**：`Instant:true` 的效果是「跳过研究动画与计时，点击立刻应用 effect，按钮立即变成下一档」。对照组 424011（Toggleable，无 Instant）的 1373 研究时间是 15 秒 —— 同样是贸易比例，Toggleable 版本要等 15 秒，Cycle 版本是 1 秒。

---

## 3. 切换时旧效果怎么撤销（最关键）

### 3.1 `type 102` = 禁用科技 —— 这就是「撤销」原语

全部命令类型中文名（`C.load_effect_tables()["zh"]["types"]`，55 项，已实测）：

```
0=设置属性   1=设置/增减资源   2=启用/禁用单位   3=升级单位   4=增减属性   5=乘算属性
6=乘算资源   7=生成单位        8=修改科技        10-18=队伍:同八种  20-28=敌方:同八种
30-38=中立:同八种  40-48=盖亚:同八种
101=修改科技成本   102=禁用科技   103=修改科技研究时间
200-202=主人单位:设置/增减/乘算属性   203-205=选中单位:设置/增减/乘算属性   206=转化选中单位
```
[证据: `from aoe2mod.intent import compiler as C; C.load_effect_tables()["zh"]["types"]`；中文输出落在 `_probe\out\p10.txt`（Windows 控制台会乱码，必须写 UTF-8 文件）]

`type 102` 的 schema 定义：
```
{"raw": 102, "label": "Disable Tech", "params": ["D:tech id (via D)"], "summary": "Remove a tech from the tree"}
```
[证据: `schema\effect_command_types.json:516-524`]

**全库 type102 普查（已实测）**：
- 共 **1969 条**，分布在 **128 个 effect / 64 个 tech** 里。
- 槽形状：`a=-1 b=-1 c=-1` 占 **1951 条**（压倒性主流），只有 18 条有别的形状（`a=1795 b=0` 10 条、`a=1104 b=1`、`a=1206 b=-1 d=1206`、`a=1231/1233/1236/1238/1250 b=-1 c=0`、`a=535 b=1`）。
- → **真正的作用对象只在 D 槽（= 科技 id）。**

### 3.2 有没有「专门做禁用/启用另一科技」的类型？两个候选

**候选 A：`type 8`（修改科技），B 码 12 = 0 禁用 / 1 启用。**
- schema：`type 8` 的 B 码族（`schema\effect_command_types.json:108-122`，注释 source = `AGE/AGE_Frame/Lists.cpp + Techs.cpp`）：`-1`=设研究时间、`-2`=加研究时间、`0..3`=设第 N 种成本、`4`=设研究地点、`5`=设按钮、`6`=设图标、`7`=设名字、`8`=设描述、`9`=启停叠加、`10`=叠加上限、`11`=设热键、**`12` = 0=disable / 1=enable tech**、`16384..16387`=加第 N 种成本。
- 实测 B 码分布：`{-1:3, 0:2, 1:1, 3:2, 4:4, 5:19, 7:2, 8:6, 11:6, **12:204**, 18:6}`。
- **关键：b==12 的 204 条，D 值全部是 1.0，没有一个 0。** 也就是说 shipped 数据里**只用过「启用」，从未用过「禁用」**。[证据: `_probe\out\p28.txt`]
- 这 204 条的目标科技全是「enable X」型（235/236 Camels、272/372 Longship、378/384/433/434 Eagle、528 Slinger、630/631 Battle Elephant、714/715 Steppe Lancer、886 Dromon、913 Catapult Galleon、979/980 Rocket Cart、1025/1032/1033/1034、1350-1353/1402 Champi …）。
- **全部指向 1205/1206/1207 的命令里没有一条 type8；全部指向 1195–1211 这些 linkedTechs 成员的 type8 也是 0 条**（唯一例外是 424015 的 1284/1285 组里 1284 带 12 条 type8，但那与切换机制无关）。[证据: p28.txt "NONE"]

→ **已实测结论**：`type 8 / b=12 / d=0` 在理论上能做「禁用科技」，但在本体 204 次使用中一次都没用过，行为未经游戏验证。**Toggleable/Cycle 的互禁一律用 `type 102`。**

**候选 B：`type 101` + `type 103` = 把被禁的选项「重新放出来」。**
```
effect 1195 "Reset Oligarchy"：type101 a=1205 b=0 c=0 d=1.0 ; type103 a=1205 b=-1 c=0 d=1.0 ; type6 a=502 b=4 c=13 d=0.6666667
effect 1196 "Reset Democracy"：type101 a=1206 d=1.0 ; type103 a=1206 b=-1 d=1.0 ; type5 a=-1 c=105 d=1.25 ×2
effect 1197 "Reset Tyranny"  ：type101 a=1207 d=1.0 ; type103 a=1207 b=-1 d=1.0 ; type1 a=551 d=0.0 ; +15 条镜像反值
```
[证据: `_probe\out\p18.txt`、`_probe\out\p11_raw.txt`]

配套：1202/1203/1204 三兄弟各自在 effect 里对「自己那个 Reset」下 `101(b=0,c=0,d=0)` + `103(b=-1,c=0,d=-1)` + `102(d=<reset id>)`；Reset 被研究后又把 `101(d=1.0)` + `103(d=1.0)` 设回去。**这就是「点一次进入该选项 → 该选项的撤销按钮被解锁 → 点撤销按钮回来」的三件套。**

**「谁碰 Reset 三兄弟」全表（已实测）**：指向 1205/1206/1207 的命令只有 1192/1193/1194 里的 `101+103+102` 三条，加上 1195/1196/1197 自己。**没有任何其它科技（包括 type8）能恢复它们** → 撤销链完全闭合在这 6 个 effect 里。[证据: `_probe\out\p28.txt` 尾段、`_probe\out\p18.txt` 尾段]

**未解决点（如实标注）**：1205/1206/1207 的三条命令是 `101(成本→0)` → `103(时间→-1)` → `102(禁用自己)` 的顺序，若按「同一目标后发命令覆盖先前」的直觉，结果是「被禁用」。但 1195/1196/1197 自己又把 `101/103` 设回 1.0。**1205–1207 究竟由谁触发（它们的 `required_techs` 是 `[1203,1204]` 这种"两个都要"的组合，且 `research_locations=(-1,1,0)` 没有建筑入口）无法从 .dat 静态判定，属未实测**。三个可能：①引擎在 linkedTechs 切换时自动研究；②`102` 只影响科技树显示而非可研究性；③`required_techs` 在此为「或」语义。**必须在游戏内验证，不要按静态顺序下结论。**

### 3.3 为什么 Cycle 组完全不需要撤销

| 组 | 主 effect 的命令族 | 是否幂等 |
|---|---|---|
| 424009 Toggleable | `type1/4/5/6/7` **增减类** + `101/102/103` | **否** —— 必须靠 102+Reset 反值 |
| 424011 Toggleable | `type1 a=503 d=0/0.25/0.5/0.75/1.0` **设值** + 4 条 `102` | 值是绝对的，但仍用 102 互禁（因为要保证"当前只有一档生效"） |
| 424010 Cycle | `type1 a=503 b=0 c=504 d=0.25/0.5/0.75` 单条 | **是** |
| 424012/013/014 Cycle | 全 `type0` 绝对赋值 | **是** |

→ **判据：effect 是「增减/乘算」就必须配 type102 + Reset 反值；effect 是「绝对设置」就不需要。** 雅典的 1194（Military Policy）用了 15 条 `type4 d=-57.75` 这种增减，所以 1197（Reset Tyranny）必须写 15 条 `+57.75` 精确镜像 —— 实测逐条对上（`-50.0`↔`+50.0`、`-66.66670227050781`↔`+66.66670227050781`）。[证据: p11_raw.txt effect 1194 vs 1197]

### 3.4 已实测：资源 id 交叉验证（证明上面读法正确）

外部权威表 `https://ugc.aoe2.rocks/general/resources/resources/` 给出：
`502 = Athenian Chopping Food Productivity`、`503 = Wood Trade Ratio`、`506 = Achaemenid Town Center Local Upgrade`、`508 = Fortified Outpost Local Upgrade`、`513 = Emplacement Local Upgrade`、`551 = Tyranny Productivity`、`85 = Research Cost Modifier`、`86 = Research Time Modifier`、`269 = Technology Reward Effect`。

- 1202 的 tooltip 是 `408051: Change Current Policy to Economic Policy (Lumberjacks gather food 50% faster)`，effect 1192 里正是 `type6 a=502 d=1.5`（资源 502 ×1.5）；Reset Oligarchy 里是 `type6 a=502 b=4 c=13 d=0.6666667`（×1/1.5 撤销）。**完全对上。**
- `408052: Foot Archers and Warships cost -20% gold` ↔ 1193 的 `type5 a=-1 c=105 d=0.8 ×2`（属性 105 = 黄金成本，×0.8），Reset Democracy 用 `×1.25`。**完全对上。**
- 1215 的 tooltip `408048: Merchant ships currently return 25% wood and 75% gold from trading. Click to toggle 50%/50%` ↔ effect 1203 的 `type1 a=503 b=0 c=504 d=0.25`。**完全对上，且 tooltip 原文就写着 "Click to toggle"，直接证明 Cycle 是同一按钮循环。**
- 1275/1276/1277 的 tooltip 分别是 `408156/408157/408155`，每条都以 `Toggle to: ...` 结尾（如 `Balanced Training: Barracks units cost and train normally. Toggle to: Barracks units cost -15% Food/Wood, but train 50% slower.`）。

[证据: `_probe\out\p25.txt`（自写 walker 保留被 API 丢弃的 DLL id；`tk._tech_records()` 字段里**没有** LanguageDLLName，只能重走记录）]

**注意名字陷阱（已实测）**：tech 名与 effect 名错位严重，**绝对不能按名字推断**：
- tech 1275 `Barracks Balanced Doctrine` → effect 1223 名 `Regulars Recruitment (Barracks)`；1276 Regulars → 1224 `Mercenary`；1277 Mercenaries → 1225 `Balanced`（完全是轮转错位）。
- tech 1202 `Oligarchy` → effect 1192 `Economic Policy`；1203 Democracy → 1193 `Naval Policy`；1204 Tyranny → 1194 `Military Policy`。
- tech 1120 `Dekate` → effect 1124 `Taxiarchs`；1121 `Taxiarchs` → 1123 `Trierarchies`。

---

## 4. `Local: true` 是什么意思

### 4.1 已实测：只有 424001 有，且它的成员形态独一无二

```
424001  "Satrapies"  Type: MutuallyExclusive  Local: true  Techs: [1195, 1196, 1197]
1195 Economic Satrapy  type=32  civ=46  req=[1138,1209,1103]  costs=(1,125,1),(506,1,2),(0,75,1)  locs=(109,50,2)
1196 Military Satrapy  type=32  civ=46  同 req           costs=(1,125,1),(506,1,2),(3,75,1)  locs=(109,35,3)
1197 Defensive Satrapy type=32  civ=46  同 req           costs=(2,50,1),(506,1,2),(1,100,1)  locs=(109,15,4)
effect 1185/1186/1187 各 3 条：
  type3 a=109 b=2275/2277/2276 c=2 d=0     ← 把「城镇中心(109)」升级成经济/军事/防御城镇中心
  type102 d=<同组另两个 tech>
```
[证据: `_probe\out\p34.txt`、`_probe\out\p30.txt`、`_probe\out\p18.txt`]

### 4.2 三个独立证据指向同一结论

**证据一：成本槽里挂着「Local Upgrade」资源。** `costs` 的第二槽是 `(506, 1, flag=2)`，而资源 506 的官方名是 **`Achaemenid Town Center Local Upgrade`**（UGC Guide）。翻遍全库，`506` 只出现在这三条科技里；`508 = Fortified Outpost Local Upgrade` 只出现在 1270；`513 = Emplacement Local Upgrade` 只出现在 1323/1324 —— **这三个都是「同一条科技可以在一座建筑上反复做、每座建筑单独记账」的升级**。[证据: `https://ugc.aoe2.rocks/general/resources/resources/`；`_probe\out\p34.txt`、`_probe\out\p30.txt`]

**证据二：effect 用 `type3 c=2` —— 全库只有 4 条。** `type 3`（升级单位）的 C 槽分布是 `c=-1 : 404 条、c=1 : 26 条、c=2 : 只有 4 条`，而这 4 条正是 `effect 1185(c=2, 109→2275)`、`1186(→2277)`、`1187(→2276)` 和 `1221(598→2415 强化哨站)`。**`c=2` 是「升级这一座具体建筑（per-instance）」的槽位取值**，与「全局升级某单位类型」的 `c=-1` 相对。[证据: `_probe\out\p32.txt`]

**证据三：成员的 civ 是单一文明。** 1195/1196/1197 全部 `civ=46`（Achaemenids），而其它 MutuallyExclusive 组的成员也多是 `civ=46`/`47`/`48`/`54`/`56` —— 所以 civ 本身不区分。**真正区分的是「这个升级是作用于单位类型（全局）还是作用于具体实例（本地）」。** [证据: p34.txt]

### 4.3 结论

- **`Local: true`（推断，但有上述三条强证据）= 「该组的互斥选择是 per-instance 的：每座符合条件的建筑各自选一个，互斥只在同一座建筑内部成立，而不是整个文明只能选一个」。**
- 与其它组对比：其它组的 effect 用 `type4 a=-1`（全单位/全文明属性增减）或 `type0 a=<unit id>`（单位类型级绝对赋值），是全局生效；只有 424001 用 `type3 c=2` + `Local Upgrade` 资源位。
- **已实测的边界**：`.dat` 里没有 "Local" 这个字段的任何痕迹；`type 32` 与 `Local: true` 在 shipped 数据里完全重合（type=32 的 6 条里 3 条是 1195–1197，另 3 条 1270/1323/1324 也都是 `*_Local Upgrade` 资源的 per-instance 升级，只是不在 linkedTechs 里）。**所以「type=32 ⟺ per-instance」比「type=32 ⟺ Local」更准确。** [证据: p34.txt]

---

## 5. 能不能新增一组 Toggleable

### 5.1 NameId 段：424xxx 已满，但 NameId 根本不是注册表

**已实测字符串表**：`D:\Games\Steam\steamapps\common\AoE2DE\resources\en\strings\key-value\` 下 13 个 txt，其中
- `key-value-strings-utf8.txt`（2012476 B，max_id = 30030001）→ **424xxx 段 0 条**
- `key-value-paphos-strings-utf8.txt`（132444 B，max_id = 428194）→ **424001..424020 恰好 20 条，全满，无空缺**
- 其余 11 个文件 0 条

20 条原文：424001 Satrapies / 424002 Sparabaras/Reed Arrows / 424003 Scythed Chariots/Sagaris / 424004 Taxiarchs/Trierarchies / 424005 Eispohora/Delian League / 424006 Ephorate/Morai / 424007 Helot Levies/Xyphos / 424008 Agoge/Peloponnesian League / 424009 **Athenian Policies** / 424010 **Merchant Trade Rates** / 424011 **Antiquity Mode Merchant Trade Rates** / 424012 **Barracks Normal Doctrines** / 424013 Archery Range Normal Doctrines / 424014 Stable Normal Doctrines / 424015 Veteran Chiliarchs/Ends of the World / 424016 Pezhetairoi/Sarissophoroi / 424017 Odomantian Raiders/Dii Plunderers / 424018 Bessian Metalworking/Peltasts / 424019 Vadhavadha/Leaf-Headed Shafts / 424020 Vedic Teachings/Skandhavaras

→ **424021 起是空号。** [证据: `_probe\out\p21.txt`、`_probe\out\p22.txt`]

**但 NameId 不参与机制（三重实测）**：
1. 全库扫描：**tech 记录里没有任何 420000..429999 的整数（total = 0）**；effect 命令里只有 4 条落在该段（effect 750 `Rename Units` 的 `type0 d=421049/421096/421096/421088`，是显示文本不是科技引用）。→ **424xxx 与 .dat 完全无联系。** [证据: `_probe\out\p31.txt`]
2. 模组 `397366 三国` 用 `NameId 30101001 / 30101002`，**完全跳出现有段**，且**该模组没有提供任何 strings 文件**，照样能加载。`550749`/`551420` 用 `NameId 666666`，同样无 strings。→ **NameId 没有文案也能跑（UI 显示为数字或缺省）。** [证据: `_probe\out\p20.txt`]
3. 本体自带的 `modes\Pompeii\resources\_common\dat\linkedTechs.json` **把 424010 复用给了完全不同的组**（`Comment: "Trade Boat Rates"`, `Type: Toggleable`, `StartingTech: 184`, `Techs: [184,185,186]`）。→ **NameId 只是 UI 文案的键，引擎不校验唯一性。** [证据: 该文件全文 235 B；`_probe\out\p13.txt`]

### 5.2 最小 JSON 片段

```json
{
  "LinkedTechs": [
    {
      "NameId": 424021,
      "Comment": "Barracks Doctrine (3-state cycle)",
      "Type": "Cycle",
      "StartingTech": 2001,
      "Instant": true,
      "Techs": [ 2001, 2002, 2003 ]
    },
    {
      "NameId": 424022,
      "Comment": "Town Center Policy (toggleable, needs reset)",
      "Type": "Toggleable",
      "StartingTech": 2011,
      "Techs": [ 2010, 2011, 2012, 2020, 2021, 2022 ]
    }
  ]
}
```

字段合法性：`LinkedTechs / NameId / Comment / Type / Techs / StartingTech / Instant / Local` 这 8 个键名全部硬编码在 `AoE2DE_s.exe` 偏移 53053056..53053170（按地址升序：`Comment, Techs, Instant, Local, StartingTech, LinkedTechs, linkedTechs.json, MutuallyExclusive, Toggleable, Cycle`），**Type 的合法值只有这三个**。[证据: `_probe\out\p13.txt`]

### 5.3 还需要在 .dat 里造哪些科技

**Cycle 组（推荐先做，成本最低）—— 造 3 条科技：**

| 字段 | 值 | 依据 |
|---|---|---|
| `civ` | 目标文明 id（如 54） | 1275 组 civ=54 |
| `required_techs` | `[]` | 1275/1276/1277 实测全空 |
| `costs` | 三槽全 `(-1,0,0)`（free） | 1275 实测 |
| `research_locations` | **三条完全相同的 `(location_id, 1, button_id, hotkey_id)`** | 1275/1276/1277 实测全为 `(12,1,15,418077)` |
| `type` | 0 | Cycle 成员实测全 0 |
| Repeatable | 1 | 实测 |
| `effect_id` | 各一条 effect，每条**只含绝对赋值命令**（`type0` 设成本/时间、或 `type1` 设资源比例） | 1223/1224/1225 实测 |

**Toggleable 组 —— 造 2 个选项 ×2 + 2 个 Reset：**

| 需要 | 关键字段 |
|---|---|
| 选项 A / B | `civ`=目标文明、`required_techs`=[门科技]、`costs` 可 free、`research_locations` **各自不同的 button_id**（如 2/3）、`type`=33（与本体一致，非必需） |
| A 的 effect | 增量效果（`type4`/`type5`/`type6` 增减）**＋ `type102 d=<B 的 id>` ＋ `type102 d=<ResetA 的 id>` ＋ `type101 a=<ResetA> d=1` ＋ `type103 a=<ResetA> d=1`** |
| B 的 effect | 对称写一份 |
| Reset A / Reset B（可选） | `required_techs` 设成对方、`costs=(0,1,1)`、`research_locations=(-1,1,0)`（无建筑入口）、effect 里用**精确反值**（乘算写倒数、增减写相反数）＋ `type101 a=<自己> d=1.0` ＋ `type103 a=<自己> d=1.0` |

文案（可选）：`<mod>\resources\<lang>\strings\key-value\key-value-modded-strings-utf8.txt`，一行 `424021 "你的组名"`。同机其它模组（310130 / 411309 / 423822 / 445153 / 550009）都这么干，实测有内容。[证据: `_probe\out\p35.txt`]

**必读的坑**：
- `.dat` 写入必须走 `aoe2mod\dat\writer.py`，`writer.py:826` 会把 Repeatable 写成常量 `0`、`writer.py:852` 写 `w.op(1)` —— **如果你的科技依赖 Repeatable=1，注意 writer 的常量行为。** [证据: `aoe2mod\dat\writer.py:826`]
- `research_time` 在 GV=54 下**不写在标量位置**，必须写进 `research_locations[i].research_time`（`aoe2mod\dat\locate.py:394-405`）。只改标量会被读成 `None`。
- 新科技在科技树 JSON（`CivTechTrees\<CIV>.json`）里没有节点 → 玩家在树里看不到它，只有 `research_locations` 给的那个建筑按钮。**这正是 Cycle/Toggleable 组成员（1275–1283、1215–1217、1263–1373、1359）在本体的真实处境：62 个 civ 树 JSON 里一个都没有。** [证据: `_probe\out\p36.txt`、`_probe\out\p17.txt`]
- 反过来，1202/1203/1204 与 1195–1197 **在树里有节点**（`Node Type: UniqueTech`，`Name String ID` 407051–407053 / 407045–407047）——**想让玩家在树里看见，就要补一条 civ 树节点**。

---

## 6. 哪些已装模组改过 linkedTechs.json

扫描根：`C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\`（`local\` 空，`subscribed\` 13 个目录）。**只有 3 个模组带这个文件**：[证据: `_probe\out\p20.txt`]

| # | 模组 | 字节 | 组数 | 与本体关系 | 特殊处 |
|---|---|---|---|---|---|
| 1 | `subscribed\397366_7V1_三国 ThreeKingdoms_v1.47 (...)` | 379 | **2** | **替换式覆盖：本体 20 组全部丢失** | `NameId 30101001` MutuallyExclusive `[4044,4045,4046]`；`NameId 30101002` MutuallyExclusive `[4084,4085,4086]`；**无 strings 文件** |
| 2 | `subscribed\550749_{2026}1X Civilization Alliance and 3X res 文明联盟 v81` | 4203 | **21** | **增量：本体 20 组原样保留（含 424001 的 `Local: true`）** | 追加 `NameId 666666` **Cycle** `Instant: true` `StartingTech 4666` `Techs [4666,4667,4668,4669,4670]`；**无 strings** |
| 3 | `subscribed\551420_2026文明联盟3倍资源2倍科技v10` | 4203 | **21** | 与 #2 **逐字节相同** | 同上 |

**可操作结论**：
- **覆盖 vs 合并是一个真实的坑**：#1 用 2 组替换掉整个文件 → 玩家失去所有本体可选政策（雅典政体、贸易比例、兵役政策全部消失）。做模组时应像 #2/#3 那样**读本体 20 组再追加**。
- **NameId 完全自由**：30101001 / 666666 都不在任何字符串表里，游戏照样跑。想有文案就自己加 `key-value-modded-strings-utf8.txt`。
- 同机另有 8 个 `empires2_x2_p1.dat`：`local\dsh 模组工坊 数据`、`subscribed\297820_10 倍资源文明联盟3倍科技`、`310130`、`397366`、`423821`、`445153`、`550749`、`551420` —— **改 linkedTechs.json 的 3 个模组里有两个也换了 .dat**（397366、550749/551420），说明"分组 + 新科技"必须成对下发。

---

## 7. 这一层能做出什么本体没有的玩法

前提：本体已经用掉了「政策切换（Toggleable）」「比例循环（Cycle）」「互斥二选一（MutuallyExclusive）」三种基础形态。**剩下没被用掉的是"可组合性"** —— 因为分组完全由 JSON 定义，不与 .dat 的 civ/树绑定。

### 点子 1：同一座建筑多套「产线风格」滑杆（Type: `Cycle` + `Instant` + `StartingTech`）
- 一组 4 档，全部共享 `(location_id=12, button_id=15, hotkey_id)`，`required_techs=[]`，`costs` 全 `(-1,0,0)`，`research_time=1`。
- 每档 effect 只用 `type0`：`c=101`（训练时间）、`c=103`（食物成本）、`c=104`（木材成本）绝对赋值到该兵营全部兵种。
- 与本体 424012 的区别：本体只有「正常/征召/雇佣」三档且是固定数值；你可以做**四档且跨建筑联动**（步/弓/马三个 Cycle 组共享同一个 `NameId` 与同一套数值表），做出「全军风格滑杆」而不是单建筑滑杆。
- 为什么本体做不到：本体 424012/013/014 是三组独立 `NameId`，UI 上是三个互不相干的按钮。

### 点子 2：可反复切换的「文明姿态」+ 自动反值撤销（Type: `Toggleable` + Reset 科技）
- `Techs: [姿态A, 姿态B, ResetA, ResetB]`，`StartingTech: 姿态A`。
- 姿态 A 的 effect：`type4 a=-1 c=9(攻击力) d=+2`、`type4 a=-1 c=0(生命值) d=+10`，再 `type102 d=<姿态B>`；姿态 B 反向。
- **关键**：因为用 `type4`（增减属性）不幂等，必须造 Reset 科技做 `d=-2/-10` 精确镜像，并让 A/B 的 effect 用 `type101 a=<ResetB> d=0` + `type103 a=<ResetB> d=-1` 解锁对应 Reset。
- 与本体 424009 的区别：本体的政策是「一次选定、靠 Reset 按钮回退」，你可以做成**任意次往返**（每次切换都重新解锁对方的 Reset），得到真正的"姿态滑块"。

### 点子 3：把「Local」用满 —— 逐建筑形态切换（Type: `MutuallyExclusive` + `Local: true`）
- `Techs: [形态1, 形态2, 形态3]`，`Local: true`，成员 `type`=32，`costs` 第二槽塞 `(506, 1, 2)` 这类 `*_Local Upgrade` 资源位。
- effect 用 `type3 a=<建筑id> b=<新建筑id> c=2 d=0`（per-instance 升级）+ `type102` 禁同组另两个。
- 本体只用它做了「城镇中心 → 经济/军事/防御城镇中心」和「哨站 → 强化哨站」。**没被用的空间**：同一套机制可以做「城门 → 三种箭塔」「市场 → 木材/黄金专营市场」「船坞 → 战舰/商船坞」，每座建筑各自选择，同文明内混搭。
- 为什么本体做不到：没有第二组用 `Local: true`，`508`/`513` 这两个 Local Upgrade 资源位只被 1270/1323/1324 用过一次，**剩余 3 个组的槽位是空的**。

### 点子 4：经济比例的多资源滑杆（Type: `Cycle` + `type1` 设资源）
- 一组 5 档，`Techs: [档0..档4]`，共享 `(2172, ?, 14, 418022)` 那个港口按钮；每档 effect 只有一条 `type1 a=503 b=0 c=504 d=0/0.25/0.5/0.75/1.0`。
- 本体只在**贸易**上用了 `503`（Wood Trade Ratio）；资源表里同类还有 `102 Naval Trade Wood`、`251/252/253 Trade Food/Wood/Stone Percent`、`9 Trade Goods`。**这些资源位至今只有本体内部在用，没有任何 linkedTechs 组碰过。**
- 玩法：一个港口按钮循环「食物/木材/石料/黄金」四档贸易产出，或一个市场按钮循环销售税档位。

### 点子 5：用「涨价阶梯」做局内政体演进（Type: `Toggleable` + `type0 c=57` 计数器）
- 完全照抄雅典链：造一条 `initial_<政体>` 引导科技（`req=[<门科技>]`, `costs=(0,1,1)`, `research_locations=(-1,1,0)`），effect 里对每个政体下 `type101 b=3 c=0 d=0`（成本归零）+ `type103 b=3 d=15`（时间 15）+ **`type0 a=2229 b=-1 c=57 d=<string-id>`** 推进计数器；
- 再造 3 条「第 N 次更换」隐藏科技（`req=[]`, `costs=(1,0,0)`, `dll_name=7000`），每次把政体成本 `type101 b=3 c=0 d=25/50` 抬一档。
- 本体做到的是"每次换政府涨价 25 金"（1199–1207 实测 `d=25/50`），**你可以把它变成「换一次解锁一个新档位」的科技树前置链**，做出本体没有的"改革次数 = 解锁深度"。
- 需要的前提：`type0 a=2229 c=57` 那族的语义（2229 = 单位 `Government cost change`）**尚未游戏内验证**，这是唯一需要实验确认的点。

---

## 8. 已实测 / 推断 / 未验证 一览

**已实测（数字可复现）**
1. `type` 字段分布 `{0:1488, 2:3, 32:6, 33:13}`；Repeatable 分布 `{1:1188, 0:322}`；两者都不编码 Toggleable/Cycle。
2. Toggleable 组每 effect 的 `type102` 条数为 3（424009）/ 4（424011）；Cycle 组为 0（四个组全部）。
3. Cycle 组全体共享同一 `(location_id, button_id, hotkey_id)`；Toggleable 组 button_id 各不相同。
4. 1275/1276/1277：`civ=54`、`req=[]`、`locs=(12,1,15)`、`time=1s`、`type=0`、effect 全 `type0` 绝对赋值。
5. `type 102` 共 1969 条 / 128 effect / 64 tech，D 槽即科技 id；`type 8 b=12` 共 204 条，D 全部 = 1.0。
6. 424xxx 段 20 条全在 `key-value-paphos-strings-utf8.txt`，424021 起空号；`.dat` 里没有任何 42xxxx 整数。
7. 引擎二进制硬编码 8 个 JSON 键名 + 3 个 Type 值 + `Instant`/`Local`/`StartingTech`。
8. 3 个模组改了 linkedTechs.json，其中 1 个是替换式覆盖（丢 20 组）。

**推断（证据强但未游戏内验证）**
- `Local: true` = per-instance 选择（三条证据：`506 Achaemenid Town Center Local Upgrade` 成本槽、`type3 c=2` 全库仅 4 条、`508/513` 同构）。
- `Instant: true` = 跳过研究计时/队列直接应用（对照：Toggleable 版同类科技 15 秒，Cycle 版 1 秒）。
- 雅典 "Reset" 三兄弟由引擎在切换时自动研究（静态数据无法解释其 `req=[1203,1204]` 与无建筑入口）。
- `type0 a=2229 c=57 d=2230/2231/2232/2233` = 政府涨价阶梯的第 1–4 态。

**未验证 / 未做**
- 1205/1206/1207 的触发路径（见 3.2 未解决点）——**必须在游戏内验证，不要按静态顺序下结论。**
- `Instant` 是否真 0 时间、Cycle 点击是否真的同按钮循环（只从 tooltip 的 "Click to toggle" 文案佐证）。
- `modes\Pompeii` 自己的 `empires2_x2_p1.dat` 里 184/185/186 的真实记录（主库里 184/185 是 `New Research` 占位）。
- `type 8 / b=12 / d=0`（禁用科技）的行为 —— shipped 数据里 0 次使用。
- `type 101` 的 B 码（`-1/0/1/3`）与 C 码（`-1/0/1/2`）中 24 行未定码（见 `aoe2mod\intent\compiler.py:97-100`）。
