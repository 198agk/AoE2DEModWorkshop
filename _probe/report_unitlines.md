# unitlines.json 层逆向报告

调查对象：`D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\unitlines.json`
对照物：同目录 `empires2_x2_p1.dat`（gv=54）、`modes\Pompeii\` 同名文件与它自带的 .dat、`resources\_common\ai\**\*.per`、`AoE2DE_s.exe`、玩家 mods 目录。
所有脚本在 `_probe\tmp_ul_*.py`，编号见各条证据。

---

## 0. 事实底数（已实测）

| 项 | 值 | 证据 |
|---|---|---|
| 文件大小 / 行数 | 20,974 B / 1,114 行 | `_probe/tmp_ul_47_linenos.py` |
| 顶层键 | 仅 `Hint` + `UnitLines` | `unitlines.json:2`（Hint）、`:3`（UnitLines） |
| 线条数 | 117 | 同上 |
| 每条键 | `Name / Identifier / LineID / IDChain` 必有；`Building` 只在 2 条出现 | 键频次 `{'Name':117,'Identifier':117,'Building':2,'LineID':117,'IDChain':117}` |
| **`UnitLines` 是数组，不是对象** | `raw["UnitLines"]` 为 list，元素是 dict | 写 `.values()` 会 `AttributeError: 'list' object has no attribute 'values'` |
| `Name` 唯一性 | 117 个，全唯一 | `_probe/tmp_ul_47_linenos.py` |
| `Identifier` 总数 | 125 个（117 条线中 8 条用数组挂 2 个别名），全 distinct | `_probe/tmp_ul_53_ident.py` |
| 链长分布 | `2:96, 3:14, 4:6, 6:1`，无长度 1 | `_probe/tmp_ul_52_direction.py` |
| 链内重复 id | 0 条链有重复 | 同上 |
| 链内混单位类型 | 只有 1 条：`Rocket Cart Line [1904,1906]` = type70 + type60 | 同上 |
| IDChain 成员存在性 | 264 个不同单位，**全部**在 .dat 有 unit 记录（0 缺失） | `_probe/tmp_ul_54_final.py` |
| 单位被命名覆盖率 | 264 / 2693 = **9.8%**；类型构成 `type70:256, type80:7, type60:1` | `_probe/tmp_ul_56_breadth.py` |
| 一个单位属于多条线 | **0 例** | `_probe/tmp_ul_15_edges.py` |

### LineID 空间（已实测，修正了 Hint 的字面读法）
`Hint` 原文 `"LineIDs have to be between (-400, -199)"` 是**开区间**，合法集 = **-399..-200，共 200 个号**。

```
lines: 117   used ids: 117 (distinct)   range: -399 .. -200
legal (-399..-200): 200   free: 83
free contiguous runs:  -397..-316 (82)   -212 (1)
is -400 present: False   is -199 present: False
duplicate ids: none
```
[证据: `_probe/tmp_ul_63_finalids.py` 输出]

- **空号 83 个**，不是 84（-400 与 -199 都在区间外）。
- 出厂文件顺序**不是** id 降序：前 3 条是 `-399 Wall(:5)` / `-398 Tower(:15)` / `-310 Outpost(:26)`，第 4 条 `-300 Sannahya(:35)`，最后一条 `-314`。实际是「主题分组 + 新 DLC 追加到尾部」。完整行号表见 `_probe/tmp_ul_47_linenos.py` 输出（117 行)。
- 全文件仅 2 条带 `Building: true`：`Wall Line`（`:5`，`-399`，`[117,155]`）、`Tower Line`（`:15`，`-398`，`[79,234,235]`）。

---

## 1. 这条线到底控制什么游戏行为？

### 1.1 结论：IDChain 是「族谱」，不是「升级定义」——升级本身在 .dat

IDChain 的相邻对（147 条边）与 .dat 里真正的升级命令（effect 命令类型 3 `Upgrade Unit`，参数 `A:源单位 B:目标单位`）逐对比对：

```
factory:  lines=117  adjacent edges=147  backed by own .dat=139 (94.6%)
    MISSING Militia Line             567 -> 1793
    MISSING Knight Line              569 -> 1813
    MISSING Lembos Line              2124 -> 2125
    MISSING Lembos Line              2125 -> 2126
    MISSING Monoreme Line            2128 -> 2129
    MISSING Ancient Galley Line      2131 -> 2132
    MISSING Incendiary Ship Line     2134 -> 2135
    MISSING Rocket Cart Line         1904 -> 1906
```
[证据: `_probe/tmp_ul_50_coverage.py`；命令类型 3 的语义来自 `aoe2mod/schema/effect_command_types.json`（source: AGE/AGE_Frame/Lists.cpp + Techs.cpp）；全 .dat 扫描得 409 条 type-3 (a,b) 对]

**方向性也是实测的**：把每条边反向也去比对，`same-direction=139  reverse-only=0  neither=8` [证据: `_probe/tmp_ul_52_direction.py`]。IDChain 的顺序就是升级方向，从未反向。

**那 8 条缺边不是「引擎不接受」，而是「.dat 写成跳级」**——查「谁能升级到该目标」：

```
-> 1793  [(74,'Legionary'), (75,'Legionary'), (77,'Legionary')]      # 74/75/77 直达，不经 567
-> 1813  [(38,'Savar'), (283,'Savar')]                              # 38/283 直达，不经 569
-> 2125  [(2123,'Heavy Lembos')]                                     # 首级直达，不经 2124
-> 2126  [(2123,'Elite Lembos')]                                     # 首级直达，不经 2125
-> 2129  [(2127,'Trireme')]                                          # 首级直达
-> 2132  [(2130,'Elite Galley')]                                     # 首级直达
-> 2135  [(2133,'Heavy Incendiary Ship')]                            # 首级直达
-> 1906  NOBODY                                                      # 全 .dat 无人能升级成它
```
[证据: `_probe/tmp_ul_54_final.py`；单位名 `_probe/tmp_ul_55_names2.py`]

即：IDChain 允许「列表里相邻」与「.dat 里父级」不一致 —— 它以**语义顺序**列出整个族，而 .dat 用**多对一**的升级图（可以从第一级直接跳到该级）。8 条里 7 条属于这种「跳级并列」，第 8 条 `1906 Projectile Rocket Cart`（type 60、hp 1）是纯数据异常：它不是可升级单位，却被写进了链尾。

**IDChain 也不校验**：出厂自己就有 8 条边在 .dat 里不存在，Pompeii 还有单元素链 `Bowman Line [4]`（0 条边）[证据: `_probe/tmp_ul_48_pompeii_dat.py`]。所以引擎对「这是不是一条真链」**不做任何检查**——唯一的检查是 exe 里那两句：`Unit line ID is out of bounds (%d)` 与 `Unit type ID is out of bounds (%d)`（见 §4.1）。

### 1.2 `Building: true` 有什么不同

`Building: true` 只出现 2 次（Wall、Tower）。实测三条差异：

**(a) 成员全是建筑。** 对每条线的全部成员查 .dat 的 `type`：`Building:true` 的 2 条成员 type 全 = **80**；115 条 `Building:false` 的成员 type 出现 `{60,70,80}`。唯一不匹配的是 `Outpost Line`（`:26`，-310，`[598,2415]`）——成员全 type 80 却标 `Building: false`，即**出厂值写漏 1 条**，这个字段是手写元数据而不是从 .dat 派生 [证据: `_probe/tmp_ul_56_breadth.py`、`_probe/tmp_ul_41_names.py`]。

**(b) 成员只在 BuildingConnection 里，不在 UnitConnection 里。** .dat 的 TechTree 有 3 张平行连接表（266 unit / 37 building / 241 research）。`[117,155]` 与 `[79,234,235]` 的成员 `inUnitC=[] inBldC=[117,155] / [79,234,235]`，而 `Outpost Line` 的 598 也在 BuildingConnection [证据: `_probe/tmp_ul_3_conn.py`、`_probe/tmp_ul_20_bld.py`]。

**(c) 引擎不读这个键。** exe 里 `"Building"` 作为 JSON 键的近邻字符串 **count=0**，`Building\0` 全 exe 仅 8 次且都在别处（最近 @0x03261A9E 是科技树分类枚举 `UnitUpgrade|Research|BuildingTech|...`）；而同一 JSON 加载器的键块里 `UnitLines / IDChain / LineID / Identifier` 四个是**连续相邻**的（见 §4.1）。同理 `Name` 也不在键块里。
→ **推断（强）**：`Building` 与 `Name` 是编辑器/作者工具侧的元数据，引擎只解析 4 个键。运行时区分建筑还是单位靠 .dat 的 `type == 80`，不靠这个字段。

**(d) 建筑升级与单位升级是同一套 type-3 机制，不是两套。** 全 tech 扫描，墙/塔的升级全走 type-3：
```
tech 194 'Fortified Wall' civ=-1 : 117 -> 155   (effect 187)
tech 140 'Guard Tower'   civ=-1 :  79 -> 234   (effect 139)
tech  63 'Keep'          civ=-1 :  79 -> 235 AND 234 -> 235  (effect 63, 两条同 effect)
tech 525 'Fire Tower'    civ=-1 :  72 -> 119   (effect 580)
```
[证据: `_probe/tmp_ul_21_bldtech.py`、`_probe/tmp_ul_41_names.py`]

以及一个反向的漂亮对照（`_probe/tmp_ul_66_bldsrc.py` 查「谁能升级到该目标」）：
```
-> 155    [(117, tech 194 'Fortified Wall', civ=-1)]
-> 234    [(79,  tech 140 'Guard Tower',    civ=-1)]
-> 235    [(79,  tech  63 'Keep', civ=-1), (234, tech 63 'Keep', civ=-1)]
-> 119    [(72,  tech 525 'Fire Tower (make avail)', civ=-1)]
-> 2415   [(598, tech 1270 'Fortified Outpost', civ=-1)]
-> 236    NOBODY
-> 117    NOBODY          ← 72 Palisade 升不上 117，所以 Wall Line 从 117 起
```
**72 (Palisade) 升不到 117，236 (Ballista Tower) 也没有任何入边** —— 而出厂 `Wall Line = [117,155]` 正好不含 72、`Tower Line = [79,234,235]` 正好不含 236。反过来 `Outpost Line = [598,2415]` 的两端确实由 tech 1270 连着（Pompeii 版 Tower Line 含 236，因为它自带一份把 235→236 写进去的 .dat，见 §2.3）。**线的成员 = 「能被升级进来」的单位集**，这是这一层最可操作的经验规则。

### 1.3 .dat 里没有「升级到我」这个字段
- unit 记录键只有 `_creatable_* / _dll_* / _off* / civ / class / costs / displayed_pierce_armour / garrison_capacity / hit_points / icon_id / id / line_of_sight / name / sort_number / speed / standing_graphic / task_swap_group / train_locations / type / type50`，**没有任何升级指针** [证据: `aoe2mod/dat/parser.py` 的 read_unit + 实测 dump]。
- building 记录里有 `transform / stack / head / tech_id`，但 117/155/79/234/235/236/598/2415 **全为 -1**；`transform != -1` 的只有 65 个建筑且全是双向切换对（城门/垛口 63↔67、78↔64、85↔90、109/141/142→444），与升级链无关 [证据: `_probe/tmp_ul_20_bld.py`]。
- 所以「A 能升级成 B」在 .dat 里的**唯一**表示是某个 tech 的 effect 里的一条 `type 3` 命令（tech 只有 `effect_id`，命令在 `effects[effect_id]["commands"]`）[证据: `aoe2mod/api.py:91 _tech_records()` / `:97 _effect_records()`]。

---

## 2. 引擎读的是 unitlines.json 还是 .dat 里的字段？

### 2.1 两者都读，但分工不同
- **unitlines.json** → 引擎加载它（exe 字符串实证，§4.1），把它变成「命名/抽象层」：AI 常量 + civ 的唯一单位线。
- **.dat** → 真正的升级关系（tech 的 type-3 命令）、真正的位置（TechTree 的 266/37/241 连接表）、真正的数值。
- **不是二选一**：JSON 里的 IDChain **不能**凭空造出升级。决定性对照见 §2.3。

### 2.2 .dat 里有两组结构都与「升级」有关，但都不是 IDChain 的存储
| 结构 | 位置 | 数量 | 字段 | 与 IDChain 的关系 |
|---|---|---|---|---|
| `effect.commands` 里的 `type 3` | Effects 段 | 409 条 (a,b) 对 | `A:源 B:目标 C:范围(-1=全/2=选中/3=含自身母体)` | 96% 覆盖 IDChain 相邻边 |
| `TechTree.UnitConnection` | TechTree 段 | 266 条 | `id/status/upper/vline/group[]/loc/required/line_mode/enabling` | 弱相关：`group`=下一级，77/129 相邻边命中 |
| `TechTree.BuildingConnection` | 同上 | 37 条 | `id/status/enabling/units_techs_total[5]/first[5]` | 只对建筑 |
| `TechTree.ResearchConnection` | 同上 | 241 条 | — | 科技节点 |

`UnitConnection` 的字段语义是实测的（用 monkeypatch 让真 parser 走一遍，`_probe/tmp_ul_3_conn.py`）：`4: upper=87 vline=22 group=[24] required=-1 line_mode=2 enabling=151` / `24: group=[492] required=100 line_mode=3` / `492: group=[] required=237`。
- `group` = 科技树上的**下一级**（不是 IDChain 的相邻边：77 命中 / 52 不命中，不命中的 44 条全是 DLC 线没进 group）[证据: `_probe/tmp_ul_4_vline.py`]
- `required` = 升级到它的 **tech id**（弩手 100），但**只有 2/81 等于「effect 里 type-3 到它」的那个 tech**，因为 tech id 与 effect 宿主不是同一个 id [证据: `_probe/tmp_ul_3_conn.py`]
- `line_mode`：`3` 的 80 个实例**全部 required>=0**，`2` 的 186 个只有 1 个 → `line_mode=3` = 「靠研究解锁这一级」，`2` = 「随时代/开局就有」
- `vline` = 科技树竖排列。120 个单位共用一个「终点列」vline 103；96 条线的成员全共享一个 vline，**5 条跨列**（就是 §1.1 里跳级那几条：Militia→[4,4,4,4,4,**103**]、Knight、ScoutCav、Camel、Bombard Cannon）
- **注意**：`aoe2mod/dat/parser.py:1038` 把 266 条 UnitConnection 读出来**丢弃了**（`for _ in range(unit_count)`），所以项目里 `tt["unit_connections"]` 不存在；要拿只能 monkeypatch。

**结论**：`IDChain` 不是 .dat 任何字段的镜像。它是一份独立维护的「族谱声明」，与 .dat 的 type-3 图 94.6% 重合、方向一致、但不做一致性校验。

### 2.3 ★ 决定性对照：Pompeii 模式自带一份 .dat，两两配对后 100% 覆盖
同一引擎、同一份 JSON 格式、两套规模：

```
factory: size=12023754  techs=1510  effects=1500  type3pairs=409
pompeii: size= 2573146  techs= 191  effects= 228  type3pairs=167
        edge (72,117)   factory present=False   pompeii present=True  (源 [72])
        edge (235,236)  factory present=False   pompeii present=True  (源 [79,234,235])
        edge (13,15)    factory present=False   pompeii present=True  (源 [13])
        edge (545,37)   factory present=False   pompeii present=True  (源 [545])
        edge (17,11)    factory present=False   pompeii present=True  (源 [17])

factory × factory-unitlines : 147 edges, 139 backed (94.6%)
pompeii × pompeii-unitlines:  26 edges,  26 backed (100.0%)
pompeii-unitlines × factory-dat: 21/26 backed (5 条缺)
```
[证据: `_probe/tmp_ul_49_pompeii_pairs.py`、`_probe/tmp_ul_50_coverage.py`]

`modes\Pompeii\resources\_common\dat\` 里 `empires2_x2_p1.dat` 与 `unitlines.json` **并排存在**，含 14 个同名 JSON 覆盖文件（`AIConsts.json / civilizations.json / eras.json / dropsites.json / buttons.json / futuravailableunits.json / unitcategories.json / ...`）[证据: `_probe/tmp_ul_48_pompeii_dat.py` 目录清单]。

**这就是答案**：`unitlines.json` 提供「名字 + 家族」，**每一条边都必须有 .dat 的 type-3 命令兜底**。官方自己也做不到只改 JSON —— 它换 JSON 的同时必然换 .dat。

---

## 3. 有哪些已安装模组改过这个文件？

### 3.1 结论：**0 个**（已实测）
```
Get-ChildItem -Recurse -Filter unitlines.json  <MODS>   → 0
Get-ChildItem -Recurse -Filter *unitline*       <MODS>   → 0（大小写不敏感）
```
`<MODS>` = `C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods`
mods 树文件类型直方图：`.png 685 / .dds 118 / .wem 36 / .txt 29 / .json 24 / .dat 8 / .jpg 3 / .xs 2`。24 个 .json 逐个打开过：全是 `info.json`、`civilizations.json`、`linkedTechs.json`、`icons.json`、`materials.json`、`objreplacement.json`、`mod-status.json`。

### 3.2 但社区确实在改相邻层
- **8 个数据模组**覆盖 `resources\_common\dat\empires2_x2_p1.dat`（实测路径）：
  `local\dsh 模组工坊 数据\`、`subscribed\297820_10 倍资源文明联盟3倍科技\`、`subscribed\310130_1233 For Stephen Chow (2026.10.8)\`、`subscribed\397366_7V1_三国 ThreeKingdoms_v1.47\`、`subscribed\423821_四月-juntuanzhangtianfumozu军团长天赋模组\`、`subscribed\445153_4X科技 增益科技 大房 小田2026.9.26\`、`subscribed\550749_{2026}1X Civilization Alliance and 3X res 文明联盟 v81\`、`subscribed\551420_2026文明联盟3倍资源2倍科技v10\`
- **2 个模组**覆盖 `civilizations.json`：`297820_`（46 civ）、`310130_`（63 civ）。**逐 civ diff 其 `unique_unit_line` 与出厂：0 差异** [证据: `_probe/tmp_ul_42_loop.py`] —— 连改 .dat 的模组都没动线 ID。
- **mods 树里 `modes\` 目录 0 个**：Pompeii 式「模式模组」在社区尚无先例。
- 注册表 `mods\mod-status.json`：17 条 Mods，**5 条 Enabled=true**（182654 Age of Anime Chibi、550412 透明主题、550009 文本UI、423822 军团天赋文本、482587 兰亭三国地图），**没有一条是数据模组** —— 即 8 个改 .dat 的模组当前全部未启用。

### 3.3 结论（推断，但扫描是实测）
`unitlines.json` 是**社区空白地带**：没有任何已发布模组碰过它，也没有任何模组试过 mode 级替换。同时 §4.4 证明「整文件影子覆盖（loose file shadowing）」是引擎现成机制且已有真实模组在用（那两个 `civilizations.json` / `linkedTechs.json` 覆盖模组）。所以「只改 unitlines.json 的模组」在技术上成立、在市场上有先发空间，但（§2.3）它只能重命名/重分组，不能造升级。

---

## 4. 能不能新增一条线？

### 4.1 引擎侧的合法性检查（exe 实证）
`AoE2DE_s.exe`（72,166,200 B）0x0329E380 起的 NUL 字符串块，原文逐字：
```
s.json || UnitLines || || || || | IDChain | LineID || Unit line ID is out of bounds (%d)
    || || || || Unit type ID is out of bounds (%d)
    || || || || Identifier || || || || Unit line is incorrectly defined and is missing a key variable
    || Unit line data file is missing. This will likely cause some weird behaviour
```
（`|` = NUL，`s.json` 是前一字符串 `unitlines.json` 的尾巴）
[证据: `_probe/tmp_ul_59_dupstr.py`，同一脚本列出全 exe 只有 3 处 `Unit line` 字面量]

读出的四件事：
1. **引擎确实解析这个文件**，键名连成一串：`UnitLines / IDChain / LineID / Identifier`。`Name` 与 `Building` **不在**其中 → 它们不是引擎键（§1.2c）。
2. 有 `Unit line ID is out of bounds (%d)` → **LineID 范围检查真实存在**（虽然 Hint 文本本身 0 次出现，`LineIDs`/`have to be between` 在 exe 里都找不到 → Hint 纯注释）。
3. 有 `Unit type ID is out of bounds (%d)` → IDChain 里的每个 id 都会被校验，越界即报该错。
4. 有 `Unit line is incorrectly defined and is missing a key variable` → 缺键会被诊断；**但全 exe 没有任何 duplicate-line-id 诊断串**（`duplicate key "` / `duplicate entry for "` 等 30+ 条全属 JSON 库与网络栈，无一条与单位线相关）[证据: `_probe/tmp_ul_60_ctx.py`] → **两条线用同一个 LineID 不会被报错，只会静默撞车**。

### 4.2 结论：**能加，纯 JSON 即可，且不需要碰 .dat**
只要满足：`LineID` 落在 -399..-200 且不与已有 117 个重复；`IDChain` 成员都是 .dat 里存在的 unit id。**新增线不会改变任何游戏行为**（不加升级、不改数值），它只是给一组已有单位起一个名字，并生成一个 AI 常量。

### 4.3 已实测的合成样本
`_probe/tmp_ul_24_synth397.py` 用空号 **-397** 生成 `_probe/out/ul_test397/resources/_common/dat/unitlines.json`：
- 118 条，ids 唯一，min -399 max -200，全在合法区间，重新 json.load 通过；20974 B → 20105 B（仅 indent 差异）
- 成员存在性实测：74 SPRMN / 75 SWDMN / 77 THSWD / 473 HTHSW / 567 HEROI，**type 全 70**
- 相邻已用号 `[-399, -398, -397]`

最小 JSON 片段（直接追加到 `UnitLines` 数组末尾，与相邻 entry 之间加逗号）：
```json
{
  "Name": "Mercenary Line",
  "Identifier": ["mercenary-line", "militia-mercenary-line"],
  "LineID": -397,
  "IDChain": [74, 75, 77, 473, 567]
}
```

字段级说明：
| 字段 | 是否必需 | 说明 |
|---|---|---|
| `LineID` | 必需 | -399..-200 内唯一。越界 → `Unit line ID is out of bounds` |
| `IDChain` | 必需 | 成员必须在 .dat 存在；顺序 = 语义升级方向；不校验链是否连续（§1.1） |
| `Identifier` | 必需 | 字符串或字符串数组；成为 .per 的 DefConst 名（§5） |
| `Name` | 引擎不需要 | 作者工具/UI 元数据，但**出厂与官方 Pompeii 都写**，建议照写 |
| `Building` | 引擎不需要 | `true` 仅用于标记建筑链；出厂 2 条、漏标 Outpost 1 条（§1.2a） |

安装方式（本项目已有先例）：`<mod>\resources\_common\dat\unitlines.json` 整文件替换（引擎逐文件影子覆盖，exe 字面量 `use_modes_path_for_mods`）。**不能**只放增量片段。

### 4.4 「需要同时改什么」——按你想要的效果分三档
**A. 只想让这条线存在（AI 能引用、能被当作单位类）**：只改 `unitlines.json`。零 .dat、零其它 JSON。
> 但要让**自定义 AI** 用得上，还得让 AI 认这个名字：引擎会注入常量，官方 AI 的 `.per` 里也大量直接使用未声明的 line 常量（§5），所以**多数情况下不用写 defconst**；只有在 `#load-if-defined` 分支里需要覆盖时才写。

**B. 想让这条线成为某文明的「唯一单位线」**：+ `civilizations.json` 的 `civilization_list[*].unique_unit_line` 改成该 LineID。
- 实测：63 civ 中 62 个有该字段，**62/62 全部能在出厂 unitlines 的 LineID 里解析**（0 例外）；两个模组版 `civilizations.json` 也是 0 无法解析 [证据: `_probe/tmp_ul_42_loop.py`]
- 该字段会被引擎注入成 AI 常量 `my-unique-unit-line`（exe AIConsts 加载器块含 `my-unique-unit` / `my-unique-unit-upgrade` / `my-elite-unique-unit` / `my-unique-unit-line`），官方 AI 里出现 **494 次**，其中 `(train my-unique-unit-line)` 出现在 `AI (HD version).per:13183 / 13211 / 13295 / 13341 / 13390 / 13447 / 26986 / 26999 / 27028 / 27059 / 27096 / 27120 / 27344 / 27984 / 28041 / 28240 / 28250` 等处 [证据: `_probe/tmp_ul_42_loop.py`]
- → 改这一格，**整套唯一单位 AI 逻辑自动改向**，这是本层最省力的杠杆。

**C. 想让这条线真的「能升级」**：必须改 `.dat`，具体是**某个 tech 的 effect 里加一条命令类型 3**：`A = 源单位 id, B = 目标单位 id`（类型 3 参数表：`A:from unit / B:to unit / C:-1 全部 / 2 选中 / 3 含自身母体`）。只改 JSON 不会产生任何升级入口。证据即 §2.3 的 8 条缺边与 Pompeii 的 100% vs 21/26 对照。

**D. 想让这条线出现在科技树里**：+.dat 的 `TechTree.UnitConnection`（或建筑用 `BuildingConnection`），字段 `id / status / upper / vline / group / loc / required / line_mode / enabling`。出厂这些是排版数据，JSON 层完全没有对应物。

---

## 5. `Identifier` 是干什么的？

### 5.1 结论：它是 **AI 脚本的 DefConst 名字空间**，由引擎在运行时注入，XML/其它 JSON 都不消费

**(a) 名字形状**：125 个 identifier，**全部**匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`，**全部**以 `-line` 结尾，最长 26 字符（`pattiyodha-longbowman-line`）；全 distinct [证据: `_probe/tmp_ul_53_ident.py`]。这是 AI 词法器的合法标识符形状，不是文件路径也不是 key。

**(b) 不跨 JSON 传播**：`dat` 目录下除 unitlines.json 外，**没有任何 JSON 出现这些字符串**（0 命中）；`civilizations.json` 用整数 LineID 而不是 identifier。
**(c) 不服务 XS**：全游戏 7 个 `.xs`，**0 个**引用任何 identifier [证据: `_probe/tmp_ul_9_per.py` + `_probe/tmp_ul_58_sweep.py`]。
**(d) 只在 .per 里出现**：以「独立标识符」口径（`(?<![A-Za-z0-9_-])name(?![A-Za-z0-9_-])`，52 个 .per）统计：`militiaman-line` **520 次**、`spearman-line` 378、`knight-line` 290、`scout-cavalry-line` 232、`battering-ram-line` 228、`galley-line` 218、`scorpion-line` 215、`mangonel-line` 195、`archer-line` 181、`eagle-warrior-line` 179、`skirmisher-line` 163、`stone-wall-line` 128、`bombard-cannon-line` 105、`camel-line` 97、`champi-line` 31、`mounted-crossbowman-line` 13、`fire-lancer-line` 13、`watch-tower-line` 10 [证据: `_probe/tmp_ul_58_sweep.py`。注意：子串口径会把 `archer-line` 虚高到 316（`crossbowman-line`/`longbowman-line`/`rattan-archer-line`/`fire-archer-line` 等包含它）。我最初用 `.count()` 得到 372，属子串误计；上表是 `_probe/tmp_ul_64_exact.py` 词边界口径的更正数字。全条线名字在 `.json` 里除 `unitlines.json` 自身外 0 命中。

### 5.2 决定性：这些名字在 .per 里**根本没被定义**却到处在用
52 个 `.per` 全扫：
- identifier 共 125 个，其中 **只有 50 个**在 .per 里被 `(defconst ...)` 显式定义；**75 个从未定义**
- 75 个里 **47 个被 .per 直接引用** → 只能由引擎注入
- 剩 28 个无人引用 = 纯同义别名

`stone-wall-line` 就是最干净的样本：`(defconst stone-wall-line ...)` **一次都没有**，而它在 `.per` 里被引用 **128 次**：
```
AI (HD version).per:5393   (and (nand (building-type-count stone-wall-line >= 10)
AI (HD version).per:6492   (building-type-count stone-wall-line < 9)
AI (HD version).per:9043   (building-type-count-total stone-wall-line > 15)
AI (HD version).per:23953  (build-wall 2 stone-wall-line)
Promisory\buildings.per:10129  (not (can-build-wall 2 stone-wall-line))
Promisory\init.per:283     (up-set-defense-priority c: stone-wall-line c: 1)
```
[证据: `_probe/tmp_ul_46_bldctx.py` 全量分类统计]

47 个「引擎注入且被引用」的首个引用点（抽样）：
| identifier | LineID | 引用次数 | 首个引用 |
|---|---|---|---|
| `militiaman-line` | -296 | 520 | `AI (HD version).per:787` |
| `spearman-line` | -295 | 378 | `AI (HD version).per:4990 (defconst extra-anti-cav-unit spearman-line)` |
| `archer-line` | -299 | 181 | `AI (HD version).per` |
| `scout-cavalry-line` | -286 | 232 | `AI (HD version).per:680 (defconst scout-unit scout-cavalry-line)` |
| `battering-ram-line` | -291 | 228 | `AI (HD version).per:5385 (nor (unit-available battering-ram-line)` |
| `scorpion-line` | -289 | 215 | `AI (HD version).per:7179 (unit-type-count scorpion-line >= 18)` |
| `stone-wall-line` | -399 | 128 | `AI (HD version).per:5393` |
| `champi-line` | -301 | 31 | `AI (HD version).per:1922 (defconst militiaman-line champi-line)` |
| `watch-tower-line` | -398 | 10 | `AI (HD version).per:15202 (building-type-count watch-tower-line > 3)` |
| `mounted-crossbowman-line` | -315 | 13 | `Promisory\merge.per:125` |
| `fire-lancer-line` | -207 | 13 | `AI (HD version).per:26854 (can-train fire-lancer-line)` |

28 个「引擎注入但无人引用」全是同义别名，正因为有它们才需要 `Identifier` 支持**数组**：`Eagle Warrior Line` = `["eagle-warrior-line","eagle-scout-line"]`、`Militia Line` = `["militiaman-line","militia-line"]`、`Ratha Melee Line` / `Ratha Ranged Line` 各挂自己那份。**数组 = 一条线挂多个 AI 常量名。**

### 5.3 .per 里能拿它做什么（实测形态）
line 常量在 .per 里的调用形状统计：
```
unit-type-count-total 1273 | players-unit-type-count 1050 | defconst 646 | unit-type-count 392
train 256 | can-train 255 | set-goal unit-goal 227 | up-compare-goal 128
up-find-remote 109 | up-find-local 99 | up-get-focus-fact 97 | unit-available 68
building-type-count 48 | building-type-count-total 36 | players-building-type-count 28
build 0 | research 0 | up-build 0 | up-train 0
```
[证据: `_probe/tmp_ul_10_ai.py` + `_probe/tmp_ul_58_sweep.py`]

- **能当「单位类」直接喂给 `train` / `can-train` / `unit-type-count*`**，例：`AI (HD version).per:13149 (train rocket-cart-line)`、`:13183 (train my-unique-unit-line)`
- **不能当 id 喂给 `research` / `build`**（0 次）——那些要具体 tech id / building id
- 建筑类线（-399 / -398）**只被 building-* 事实消费**，实测 128 次 `stone-wall-line` 全部落在 `building-type-count*` / `players-building-type-count` / `can-build-wall` / `build-wall` / `delete-building` / `up-set-*-priority` / `up-pending-objects`，**0 次**落进 `unit-type-count` [证据: `_probe/tmp_ul_46_bldctx.py`] —— 这正好解释 `Building:true` 的用途：**提示作者这条线该配 building-* 事实**，引擎侧则用 exe 里的 `Resolved unit type is not a building (%d)` / `Resolved unit type is a building which cannot be trained (%d)` 在使用时校验（这两条错误串与 `Invalid unit line type ID (%d)`、`Invalid unit line type (%d)` 同处 AI VM 错误表 @0x03221400 区）。

### 5.4 引擎注入 vs .per 遮蔽：写模组时必须知道的坑
- **50 个 identifier 在 .per 里也被声明**，其中只有 32 个值恰好等于 LineID；另 18 个是过时值/别名/越界值。
- 系统性 **-3 偏移**的一整组（`.per` 里的值比文件 LineID 大 3）：`genitour-line` .per `-250` vs 文件 `-253`、`caravel-line` `-254` vs `-257`、`shotel-line` `-251` vs `-254` …… 共 10 个 [证据: `_probe/tmp_ul_23_order.py`]。这 10 行位于 `AI (HD version).per:526` 附近的 `; unit lines` 注释块（`:527-531`），**且不在任何 `#load-if` 分支内** → 在 DE 上实际生效并覆盖引擎值。
- 另一组同值错位在 `Promisory\const.per:986-996` / `:1295-1304`，但整块被 `Promisory\const.per:905 #load-if-not-defined DE-AVAILABLE` … `:1312 #end-if` 包住，**DE 上被跳过**，不影响正式版。
- 还有直接把**单位 id**写成 line 常量的：`Promisory\customConstants.per:60 (defconst sannahya-line -199)`（越界，文件里是 -300）、`finalingConstants.per` 里 `#load-if-defined ATHENIANS-CIV` 分支把 `galley-line -215;2130 / demolition-ship-line 2133 / fire-ship-line 2127 / cannon-galleon-line 2140` 覆盖成单位 id（注释自述 `;These must be exclusive to Paphos`）。
- 条件重映射：`AI (HD version).per:1917 #load-if-defined INCAN-CIV` → `:1922 (defconst militiaman-line champi-line)`、`:1923 (defconst eagle-warrior-line champi-line)`；`:2172 #load-if-defined JURCHENS-CIV` → `:2173 (defconst knight-line steppe-lancer-line)`、`:2174 (defconst mangonel-line rocket-cart-line)`。**文明的「等价单位」是靠 .per 常量重映射实现的，不是靠 JSON。**
- `ERR2012: Constant Already Defined` 这个错误串存在于 AI 词法器（@0x03227CC0 区），但游戏不报错 → **重复 defconst 是「合法覆盖」，后者胜**（推断；错误串存在是实测）。
- → **对模组作者的实践含义**：如果你新增一条线并希望 AI 用新名字，同名 identifier 若已存在于某个 `.per` 里，**那个 .per 的值会盖掉引擎注入**。要么用全新名字，要么自己写 defconst。

### 5.5 官方自己怎么用这一层（Pompeii 范式，最强的「用法说明书」）
`modes\Pompeii\resources\_common\dat\unitlines.json`：3,261 B / **18 条**，`Hint` 措辞都不同（`"LineIDs have to be in a range of -400 and - 199"`）。18 条全表：

| Name | LineID | IDChain | Building |
|---|---|---|---|
| Wall Line | -399 | [72,117,155] | true |
| Tower Line | -398 | [79,234,235,236] | true |
| Bowman Line | -299 | **[4]** | |
| Improved Bowman Line | -298 | [24,492] | |
| Clubman Line | -266 | [281,531] | |
| Cavalry Line | -295 | [38,283,569] | |
| Swordsman Line | -294 | [74,75,77,473] | |
| Horse Archer Line | -293 | [39,474] | |
| War Elephant Line | -292 | [1132,1134] | |
| Chariot Line | -291 | [1370,1372] | |
| Hoplite Line | -290 | [93,358,359] | |
| Ballista Line | -289 | [279,542] | |
| Stone Thrower Line | -288 | [280,550,588] | |
| Fishing Ship Line | -287 | [13,15] | |
| Transport Ship Line | -286 | [545,37] | |
| Scout Ship Line | -285 | [539,21,442] | |
| Catapult Trireme Line | -284 | [420,691] | |
| Trade Boat Line | -283 | [17,11] | |

[证据: `_probe/tmp_ul_48_pompeii_dat.py`]

四个可复制的做法：
1. **与出厂撞号 17 个**（-399/-398/-299/-298/-295/-294/-293/-292/-291/-290/-289/-288/-287/-286/-285/-284/-283/-266）—— **撞号无害**，因为一个 mode 只加载自己那份。
2. **允许单元素链**（`Bowman Line [4]`）—— 引擎不校验，只是「0 条边」。
3. **允许把出厂没连上的档位塞进去**（`Tower Line` 含 236 Ballista Tower、`Wall Line` 前面加 72 Palisade）—— 但那**同时要求它自带 .dat**（§2.3，出厂 .dat 里 72→117 与 235→236 都不存在）。
4. **自带一份 `.per` 把常量重定义一遍**：`modes\Pompeii\resources\_common\ai\default\alternateConstants.per:234-269` 与 `AiBuilder_p\alternateConstants.per:197-226`，13/18 个 line 常量显式写出，**值全部精确等于该 mode 的 LineID**（如 `:234 (defconst bowman-line -299)`、`:245 (defconst hoplite-line -290)`、`:269 (defconst tower-line -398)`），另有额外别名 `:240 (defconst clubber-line -266)`、`:243 (defconst elephant-line -292)`、`:252/:253` 两个名字同值 -285。5 个（`fishing-ship-line / stone-wall-line / transport-ship-line / war-elephant-line / watch-tower-line`）未声明，且在这 35 个 .per 里 0 次引用。
   → **官方不依赖引擎注入，宁可自己写常量**。这与 §5.4 的遮蔽机制自洽。

---

## 6. 项目现状（供工具开发参考）

- `aoe2mod/dat/parser.py:1122-1132`：stage 6 UnitLines 明确跳过，`stats["unit_lines"] = None`，注释写「`DatFile.cpp:214` guards UnitLines with `gv >= GV_SWGB`」，实测 gv=54 (GV_C32) < GV_SWGB → **.dat 里确实没有 UnitLines 数组，这一层的唯一数据源就是 JSON**。
- `aoe2mod/dat/writer.py:994`：写出时同样把 stage 6 留空。
- `aoe2mod/game/buttons.py:33`：注释承认「Twelve slots mix `unitlines.json` line ids, and all twelve are ONE line reachable at two buildings（`Huskarl 41@Castle` / `759@Barracks`）」——这是本层在**生产面板/按钮槽**上的唯一已知耦合，结论是「出厂从没把两条无关链塞进同一个可用槽」。
- 项目里**没有任何读写 unitlines.json 的代码**（全项目 grep：只有上面 3 处注释/统计）[证据: `_probe/tmp_ul_53_ident.py`]。
  现有产物：`_probe/out/ul_test/`（117 条 roundtrip 副本）、`_probe/out/ul_test397/`（+1 条合成线）。

---

## 7. 明确区分：已实测 vs 推断

**已实测（可直接引用）**
1. 117 条线 / 1114 行 / 20,974 B；`UnitLines` 是数组；键频次 `Name/Identifier/LineID/IDChain` 各 117、`Building` 2
2. 合法 LineID = -399..-200（200 个）；已用 117 无重复；空号 83（-397..-316 共 82，-212 共 1）
3. IDChain 相邻边 147 条，139 条有对应 .dat type-3（94.6%）；8 条缺边清单及「谁能升级到该目标」的来源清单
4. 方向一致：同向 139 / 反向 0 / 皆无 8
5. 全 .dat type-3 pair 共 409 条；tech 1510 / effect 1500 / 命令 10500；type-3 = `Upgrade Unit (A:from B:to C:range)`
6. .dat 无 UnitLines 段（parser stage 6 跳过）、unit 记录无升级字段、building 的 `transform` 对墙塔全为 -1
7. TechTree 连接表 266 unit / 37 building / 241 research；UnitConnection 字段语义（`group`=下一级、`required`=解锁 tech、`line_mode` 2/3 的 required 相关性、vline 103 终点列、5 条跨列线）
8. `Building:true` 2 条且成员全 type 80；Outpost Line 漏标；成员只在 BuildingConnection
9. exe 键块 @0x0329E380 四键连续、`Building`/`Name` 不在其中、3 条 `Unit line ...` 错误串、无 duplicate-line-id 诊断
10. 125 个 identifier 形状合规且 distinct；不在任何其它 JSON；.xs 0 引用
11. 50 个 identifier 在 .per 有 defconst、75 个没有、47 个被引用、28 个孤儿；`stone-wall-line` 0 定义 128 引用
12. .per 里 line 常量的调用形状统计（`train` 256 / `can-train` 255 / `build` 0 / `research` 0）
13. 建筑线常量 128 次全部落在 building-* 事实
14. -3 偏移 10 个 identifier；`const.per:905-1312` 整块被 `#load-if-not-defined DE-AVAILABLE` 跳过；INCAN/JURCHENS 条件重映射行号
15. mods 树 `unitlines.json` 命中 0；8 个 .dat 模组路径；2 个 civilizations.json 模组、unique_unit_line 0 差异；17 条注册模组、5 条启用、0 条数据模组
16. 出厂 `civilizations.json` 62 个 unique_unit_line，62/62 可解析；`my-unique-unit-line` 在官方 AI 里 494 次
17. Pompeii 版 unitlines.json：18 条、撞号 17、单元素链 1 条、`alternateConstants.per` 13 个常量值精确等于 LineID
18. Pompeii 自带 .dat：2,573,146 B / 191 tech / 228 effect / 167 type-3；26/26 边全覆盖；同 5 条边在出厂 .dat 里全部缺失
19. 合成 -397 线可写入、可 reload、118 条、ids 合法唯一

**推断（有证据支撑但未直接观测）**
- `Name` 与 `Building` 引擎完全不解析（依据：字符串缺失；官方两份文件都照写，说明作者工具会写）
- `line_mode=3` = 「靠研究解锁」、`2` = 「随时代/开局」（依据：required 与 mode 的 80/80 vs 1/186 相关性，非直接观测）
- 重复 defconst 是「允许覆盖、后者胜」（依据：`ERR2012` 存在但游戏不报错）
- 引擎注入发生在 .per 解析之前（依据：`AI (HD version).per:526-531` 的过时值在 DE 上生效，只能是与注入值冲突后 .per 胜）
- `unit-type-count-total <line>` 会把整条链求和（依据：命令名 + 官方 AI 用 `(unit-type-count-total archer-line > 10)` 的语义意图，未在游戏内验证）
- 新增一条线对**游戏平衡零影响**（依据：JSON 里没有数值；但未在游戏内跑过「新增线后是否触发 UI 变化」）
- 「社区空白地带」的判断（依据：本机 mods 扫描实测；不能代表全 Steam Workshop）

**没做到 / 无法验证**
- 没有在游戏内启动验证（不能确认新增线是否出现在任何 UI 上）
- 不能确认引擎是否把 LineID 用于科技树高亮（`unique_unit_line` 的消费者没找到，exe 里只见 civ schema 键）
- 没有反编译，键块相邻性只是编译器字符串池布局的强推断

---

## 8. 这一层能做出本体没有的玩法

前提：**unitlines.json 只做「命名 + 分组 + 唯一线指向」，加不了升级也改不了数值**。以下 5 条都只靠这层字段（B 档以上需配合标注的文件）。

**① 佣兵池 / 雇佣兵市场（只改 JSON）**
新增线 `LineID: -397`，`IDChain: [74,75,77,473,567]`（民兵→剑士→长剑→双手→冠军，截断在冠军之前），`Identifier: ["mercenary-line","militia-mercenary-line"]`。
AI 侧 `(train mercenary-line)` 与 `(unit-type-count-total mercenary-line)` 直接可用；再把该线的成员在 .dat 里设为「多个建筑可造」即在 Castle/Barracks 双点开放。
用到字段：`LineID` + `IDChain` + `Identifier`（数组形式两个名字，一个给战术判断、一个给生产）。
为什么本体没有：本体从不给同一批单位挂第二个名字，也不存在「按族谱批量计数」的入口。

**② 跨文明共享升级链（`Identifier` 数组 + 撞号复用）**
出厂 117 条线**零撞号**、264 个单位**零重叠**。模组可以故意让 `archer-line` 这条线在某文明上指向 `[4,24,492]`、在另一个文明上指向同一组但另立 `LineID` 与 `Identifier: ["archer-line","auxiliary-archer-line"]`，再用 `civilizations.json` 的 `unique_unit_line` 把某文明的「唯一单位线」指过去。
效果：官方 AI 里 494 处 `my-unique-unit-line` **自动改向**新线，不用改一行 .per。
用到字段：`LineID` + `Identifier` + `civilizations.json` 的 `unique_unit_line`。
为什么本体没有：本体的唯一单位线永远是你自己的独特单位，无法把「通用兵种」伪装成某文明的唯一线来驱动 AI 逻辑。

**③ 把「海战时代」压成一条线，做古代海军模式（mode 级）**
照 Pompeii 范式：新目录 `modes\<你的模式>\resources\_common\dat\` 放自己的 `unitlines.json` + `empires2_x2_p1.dat` + `alternateConstants.per`。
在其 unitlines 里把 `[2123,2124,2125,2126]` 写成一条 `lembos-line`，把 `[2130,2131,2132]` 写成一条 `antiquity-galley-line`，然后**在同一套 .dat 里把 type-3 升级补成真正的 3 档**（出厂 .dat 里 2124→2125、2125→2126 都不存在，全是 2123 直达）。
用到字段：整个 `IDChain` + `.dat` 的 `effect.commands type 3`。
为什么本体没有：本体把 DLC 新船写成「首级直达」的跳级，玩家看到三个名字却没有中间升级；补成真三档是本体没有的手感。

**④ 让「塔」真正四档（`Building: true` + `.dat` 配合，最能说明边界）**
出厂 `Tower Line = [79,234,235]`，**236 Ballista Tower 被排除**，因为出厂 .dat 里 236 没有任何 type-3 入边。模组把它写成 `[79,234,235,236]` 并 `Building: true`，然后在 .dat 里给 `tech 63 'Keep'` 的 effect 追加一条 `type 3, A=235, B=236, C=-1`，即可让 Keep 之后还能再升一档弩炮塔。
用到字段：`IDChain` + `Building` + `.dat` 的 tech/effect type-3。
为什么本体没有：本体故意让 236 游离在链外（它只能作为独立建筑出现）。这条同时也是**「只改 JSON 不行」的最佳反例**。

**⑤ 用「假链」做 AI 的复合资源计数器（`IDChain` 不校验）**
IDChain 不做连续性校验（出厂自己 8 条边无 .dat 支撑，Pompeii 还有 1 元素链）。因此可以造一条 `LineID: -396`、`IDChain: [83,93,7,530,1258]`（长枪→戟→民兵系混编，语义上不是链）的 `trash-group-line`，然后在 AI 里用 `(unit-type-count-total trash-group-line)` 一次拿到「垃圾兵总量」再触发 `(train ...)`。
用到字段：`IDChain`（无需真实升级关系）+ `Identifier`。
为什么本体没有：本体每条线都是真族谱，AI 想统计跨兵种总量必须写 5 个 `unit-type-count` 再相加。
风险标注：这条依赖「`unit-type-count-total` 对整条链求和」这一**推断**（§7），需要游戏内验证一次再落库。

---

## 9. 一页速查

```
unitlines.json  ── 独立于 .dat 的「命名层」，不存升级、不存数值
   UnitLines[]  ← 引擎真正解析的 4 个键：LineID / IDChain / Identifier (+UnitLines 容器)
   LineID       ← -399..-200 唯一；越界报 "Unit line ID is out of bounds"；重复不报
   IDChain      ← 语义族谱，顺序=升级方向，不校验连续性，成员须为存在的 unit id
   Identifier   ← 引擎注入的 AI DefConst 名，可数组（一条线多个别名），.per 里可直接
                  当单位类喂 train/can-train/unit-type-count*；建筑线只喂 building-*
   真升级        ← 只在 .dat：某 tech 的 effect 里 command type=3 (A=from, B=to)
   真排版        ← 只在 .dat：TechTree.UnitConnection/BuildingConnection 的 vline/group/required
   Name/Building← 作者工具元数据，引擎不读（Building:true 仅 2 条，Outpost 漏标）
   唯一消费者    ← civilizations.json 的 unique_unit_line → AI 的 my-unique-unit-line（494 次）
   已有模组改动  ← 0 个；社区全部在改 .dat（8 个）与 civilizations.json（2 个）
   可新增线      ← 能，纯 JSON；空号 83 个（-397..-316 共 82、-212）；要能升级则必须改 .dat
```
