# AoE2 DE 场景文件头部结构研究报告

**任务编号**：m00001
**研究范围**：Windows 本机只读静态分析（未启动游戏，未修改游戏目录任何文件）
**产物目录**：`D:\Software\DeepSeek Harness\工作区2\_probe\scenario_header\`
**标签约定**：**[V]** = 本机实测验证 ｜ **[I]** = 从源码/结构推断 ｜ **[U]** = 未解

---

## 1. 结论速览（TL;DR）

### 1.1 核心算法（一行）

```python
deflate_offset = HEADER_LAYOUT[savable].size(bytes)
```

`savable` 是文件偏移 **8** 处的小端 **s32**。读这**一个 int32** 就唯一确定了头部文法；文法里所有变长字段按声明长度读完，deflate 流从最后一个字段的下一个字节开始。**没有搜索、没有候选循环、没有穷举。** [V]

```
savable  布局        世代                        本机实测出现在
-------  ----------  --------------------------  -------------------
   2     L_SHORT     旧世短头                    1.21
   3     L_LONG_NC   旧世长头，无 creator_name    1.21
   4     L_LONG_C    旧世长头 + creator_name      1.33
   5     M_IVU       现代 + individual_victories  1.35, 1.36, 1.37
   6     M_NOIVU     现代，IVU 已移除             1.40 .. 1.59
```

### 1.2 覆盖率（诚实分母）

| 项目 | 数量 |
|---|---|
| 独立场景类文件（递归，`.aoe2scenario` + `.scx`） | **54** |
| 战役容器（`.aoe2campaign`） | **42** |
| 战役内嵌成员（由成员表确定解析，非扫描） | **235** |
| **总实例数** | **289** |
| **成功定位（头部解析成功 且 raw-deflate 到达 eof）** | **289 / 289** |
| **失败** | **0** |

[V] 289/289 全部成功，失败数 0。每个实例在严格验收规则下都只有**唯一**一个可解流，且该流恰好是结构推导出的那一个。

### 1.3 版本直方图（覆盖 289 个实例）

```
1.21 x25, 1.33 x1, 1.35 x6, 1.36 x21, 1.37 x2, 1.40 x1, 1.41 x3,
1.42 x1, 1.43 x3, 1.44 x1, 1.45 x2, 1.46 x4, 1.47 x20, 1.48 x6,
1.49 x10, "1.5\x00" x1, 1.51 x18, 1.52 x1, 1.53 x6, 1.54 x27,
1.55 x90, 1.56 x10, 1.57 x10, 1.58 x16, 1.59 x4
```

[V] 25 个不同版本标签。注意其中有一个**损坏标签 `1.5\x00`**，它照样能用 `savable=6` 正确解析 —— 见 §5.3。

### 1.4 五个最关键的事实

1. **[V]** deflate 起点**不是常量**：同一 `(version, savable)` 组内偏移值就有多个（例：`('1.35',5)` → `[69,73,85]`；`('1.54',6)` → `[81,117,1185]`）。但**算法是常量**，偏移值是头部变长 `str32` 字段长度的函数。
2. **[V]** 任务书里「前 200,000 个偏移 0 命中」是**验收规则造成的假象**，不是文件性质。用正确规则（`d.eof == True` 且输出 ≥ 1000 B）在 1.8 秒内即命中唯一解。
3. **[V]** `savable` 决定布局，**版本标签不行**：`1.21` 同时映射到 `savable=2` 和 `savable=3`；而损坏标签 `1.5\x00` 是 `savable=6`。
4. **[V]** `.aoe2campaign` 成员确实是**背靠背的完整独立场景文件**，并已由**逐字节同一性**证明。成员表可**零扫描**确定解析（成员计数固定在 `8 + 4*amount + 256`）。
5. **[V]** 「64 字节索引表」说法**被证伪**：42 个战役中 `count_field_offset - header_end == 64` 的有 **0/42**，实际恒为 **256**（42/42）。

---

## 2. 语义学：`savable` 到底是什么

必须区分两个同名但**完全不同**的东西，这是整个问题的关键：

| | 库的 `savable` | 磁盘上的 `savable` |
|---|---|---|
| 位置 | `versions/DE/v<ver>/structure.json` 里 `"default": 6` | 文件偏移 **8** 的 s32 |
| 性质 | 每个 schema 的**装饰性默认值** | 游戏写出的**格式世代号** |
| 取值 | v1.36–v1.59 **全部**为 `6` | 本机实测 `2, 3, 4, 5, 6` |
| 作用 | 无（重新保存时写入的常量） | **选择头部文法** |

[I] 库的 `versions/DE/v1.53/structure.json:12` 为 `"savable": {"type": "s32", "default": 6}`，且 v1.36–v1.59 **每一个**版本的默认值都是 `6`。若把它当作判据，则所有版本的头部都会被误判成同一布局 —— 这正是此前走不通的原因。

[V] 磁盘上的 `savable` 在本机 289 个实例中只取 `2..6`，且与文法一一对应，**0 个歧义**。

---

## 3. 确定性算法与验证

### 3.1 公共前缀（所有世代）

| 偏移 | 类型 | 字段 | 说明 |
|---|---|---|---|
| 0 | c4 | `version` | ASCII，如 `"1.53"`。**实测不可靠**，见 §5.3 |
| 4 | u32 | `header_length` | 语义 [U]，见 §8 |
| 8 | **s32** | **`savable`** | **布局选择器** |
| 12 | u32 | `timestamp_of_last_save` | Unix 时间戳 |
| 16 | str32 | `scenario_instructions` | u32 字节长度 + 原始字节 |

**关键**：`str32` 的长度是**字节数**，不是码点数，**不补齐、不 NUL 结尾**。因此**从偏移 4 开始的 u32 对齐遍历对任何 `instructions` 长度非 4 倍数的文件都是错的** —— 它会走偏字段网格并打印垃圾值（实测出现过 `2048, 256000, 512`）。

[V] 极端例子：`default0.aoe2scenario`（1.59）有 **1107 字节**的 UTF-8 中文 instruction 块，所以它的流起点是 **1183**，而不是 80 附近。

### 3.2 五种文法的完整字段序列

[V] 全部从真实字节读出，每种一个代表实例：

**L_SHORT**（`savable=2`）— `real_world_britain.scx` 8557 B / 1.21
```
@4   header_length                        = 20
@8   savable                              = 2
@12  timestamp_of_last_save
@16  scenario_instructions  str32         = 0 B
@20  legacy_unknown_after_instructions
@24  player_count                         = 8
@28  >>> RAW DEFLATE  <<<   输出 187,196 B
```
无 sentinel、无 creator、无 trigger_count、无 `unknown_numbers`。

**L_LONG_NC**（`savable=3`）— `real_world_antarctica.scx` 253333 B / 1.21
```
@16  scenario_instructions  = 1 B
@21  legacy_unknown_after_instructions = 0
@25  player_count           = 8
@29  unknown_value          = 1000      (0x3E8)
@33  unknown_value_2        = 0
@37  amount_of_unknown_numbers = 2
@41  unknown_numbers        = [0, 1]
@49  >>> RAW DEFLATE  <<<   输出 2,333,516 B
```
**无 `creator_name`，无 `trigger_count`。**

**L_LONG_C**（`savable=4`）— `real_world_nippon.scx` 5942 B / 1.33
```
... 同上至 @41
@49  creator_name  str32  = 16 B  → b"TheVeryFish\x00"
@65  >>> RAW DEFLATE  <<<   输出 376,935 B
```
**仍然无 `trigger_count`。**

**M_IVU**（`savable=5`）— `0_E3_Scenario.aoe2scenario` 57070 B / 1.35
```
@16  scenario_instructions  = 1 B
@21  individual_victories_used = 0
@25  player_count           = 8
@29  unknown_value          = 1000
@33  unknown_value_2        = 1
@37  amount_of_unknown_numbers = 6
@41  unknown_numbers        = [2,3,4,5,6,7]
@65  creator_name  str32    = 16 B → b"Freeman1302\x00"
@81  trigger_count          = 71
@85  >>> RAW DEFLATE  <<<   输出 316,584 B
```

**M_NOIVU**（`savable=6`）— `7V1变态山谷-炮塔盛宴-变态难.aoe2scenario` 179824 B / 1.54
```
@16  scenario_instructions  = 1111 B (1107 B 内容 + 长度前缀)
@1127 player_count          = 8
@1131 unknown_value         = 1000
@1135 unknown_value_2       = 1
@1139 amount_of_unknown_numbers = 6
@1143 unknown_numbers       = [2,3,4,5,6,7]
@1167 creator_name  str32   = 14 B → b"lin740807\x00"
@1181 trigger_count         = 704
@1185 >>> RAW DEFLATE  <<<   输出 2,076,786 B
```

### 3.3 偏移值不是常量（实测）

[V] 同一 `(version, savable)` 组内的 deflate 起点集合：

```
('1.21', 2): n=8    offsets = [28]
('1.21', 3): n=17   offsets = [49, 53]
('1.33', 4): n=1    offsets = [65]
('1.35', 5): n=6    offsets = [69, 73, 85]
('1.36', 5): n=15   offsets = [69, 73]
('1.48', 6): n=1    offsets = [79]
('1.51', 6): n=1    offsets = [103]
('1.53', 6): n=1    offsets = [83]
('1.54', 6): n=3    offsets = [81, 117, 1185]
('1.59', 6): n=1    offsets = [1183]
```

全部 289 个实例的偏移谱更宽：`1.47` → `[75,80,84,162,192]`；`1.55` → `[77,79,88,108,168,177,…]`；`1.59` → `[77,88,224,1183]`。

**偏移算法是常量；偏移值是数据相关的**（由 `scenario_instructions` 长度、`amount_of_unknown_numbers`、`creator_name` 长度、`trigger_count` 是否存在共同决定）。这两句话都是实测结论。

### 3.4 与库 oracle 的交叉验证

[V] 在库能工作的版本上，我们**独立推导**的字段序列与库随包分发的 schema **完全相等**：

```
v1.36    ours(M_IVU)   == library(去掉 'version') ? True
v1.37    ours(M_IVU)   == library(去掉 'version') ? True
v1.40    ours(M_NOIVU) == library(去掉 'version') ? True
v1.59    ours(M_NOIVU) == library(去掉 'version') ? True
```

[V] 库全部 20 个已发行版本中只有 **2 种** retriever 顺序：

```
v1.36..v1.37 (n=2):  version, header_length, savable, timestamp_of_last_save,
                     scenario_instructions, individual_victories_used,
                     player_count, unknown_value, unknown_value_2,
                     amount_of_unknown_numbers, unknown_numbers,
                     creator_name, trigger_count
v1.40..v1.59 (n=18): 同上，去掉 individual_victories_used
```

[V] 库自身的 `changelog.md`（`## Scenario v1.40` → `### Removed` → `FileHeader:`）明确记载：在 `scenario_instructions` 与 `player_count` **之间**移除 `"individual_victories_used": {"type": "u32", "default": 0}`。这是我们 IVU 布局判定的**文档级依据**。

[V] deflate 起点的交叉验证：
```
1.36: our_deflate_offset=73   library_header_len=73   agree=True
1.53: our_deflate_offset=83   library_header_len=83   agree=True
```

### 3.5 `unknown_value_2` 就是 `ScenarioVariant`（已解决，不再是未知项）

[V] 用库的纯字节启发式 `_get_scenario_variant`（`scenarios/aoe2_scenario.py:701`，模块级函数）对全部 46 个含该字段的文件做对照：

```
files where our grammar HAS the field : 46
lib-variant == our unknown_value_2 : 46
lib-variant != our unknown_value_2 : 0
lib-variant is None (b'\xE8\x03\x00\x00' 未找到) : 8
```

那 8 个 `None` 恰好是 `savable=2` / `L_SHORT` 的 `real_world_*.scx` —— **因为 L_SHORT 根本没有 `unknown_value` sentinel 字段**，库找不到 `b"\xE8\x03\x00\x00"` 就返回 `None`。我们的文法对 sentinel **存在与否的预测 100% 正确**。

[I] 库源码本身把 `unknown_value_2` 当作 variant：
- `scenarios/aoe2_scenario.py:486-487`：
  `if self.sections["FileHeader"].unknown_value_2 != self.variant.value: self.variant = self.sections["FileHeader"].unknown_value_2`
- `:519-531` `_update_variant_retrievers` 写入 `unknown_value_2 = variant.value`，并写 `{LEGACY: [], AOE2: [2,3,4,5,6,7,8,9,10,12], ROR: [11]}`。

[V] 枚举（`datasets/scenario_variant.py`）：`LEGACY=0`（AoC & Bare HD）、`AOE2=1`（HD with expansions & DE）、`ROR=2`（Return of Rome）。

[V] 我们实测的 `unknown_numbers` 数组**印证**了这个映射表：
```
M_NOIVU   n=234:  [2,3,4,5,6,7]                       x232   <- 正是 AOE2 列表的前 6 项
                  [2,3,4,...,12,13]                   x1     (real_world_bohemia.scx)
                  [2,3,4,...,12,13,14,15,17,16]       x1     (real_world_world.scx)
L_LONG_NC n=17 :  [0,1] x10 / [2,3,4] x7
M_IVU     n=29 :  [0,1] x16 / [2,3,4,5,6,7] x9 / [2,3,4] x4
L_LONG_C  n=1  :  [0,1] x1
```
搭配 `unknown_value_2` 一起看：`0`（LEGACY）配 `[0,1]`，`1`（AOE2）配 `[2,3,4,…]`。这是一份**已启用扩展/DLC 的 id 列表**，`amount_of_unknown_numbers` 是它的长度。**同一 `amount` 会随 DLC 内容变化**，这正是头部长度可变、deflate 起点不固定的直接原因。

---

## 4. 逐版本头部布局总表

`*` = 该字段在此布局中存在。`off` 是实测 deflate 起点范围（含全部 289 实例）。

| 版本 | savable | 布局 | instr | legacy_unknown | IVU | sentinel 块 | creator | trigger_count | off 实测 |
|---|---|---|---|---|---|---|---|---|---|
| 1.21 (短) | 2 | L_SHORT | * | * | | | | | 28 |
| 1.21 (长) | 3 | L_LONG_NC | * | * | | * | | | 49, 53 |
| 1.33 | 4 | L_LONG_C | * | * | | * | * | | 65 |
| 1.35 | 5 | M_IVU | * | | * | * | * | * | 69, 73, 85 |
| 1.36 | 5 | M_IVU | * | | * | * | * | * | 69, 73, 79, 87, 88 |
| 1.37 | 5 | M_IVU | * | | * | * | * | * | 84, 87 |
| 1.40 | 6 | M_NOIVU | * | | | * | * | * | 84 |
| 1.41 | 6 | M_NOIVU | * | | | * | * | * | 75, 84 |
| 1.42 | 6 | M_NOIVU | * | | | * | * | * | 338 |
| 1.43 | 6 | M_NOIVU | * | | | * | * | * | 80, 84 |
| 1.44 | 6 | M_NOIVU | * | | | * | * | * | 706 |
| 1.45 | 6 | M_NOIVU | * | | | * | * | * | 81, 667 |
| 1.46 | 6 | M_NOIVU | * | | | * | * | * | 81, 84 |
| 1.47 | 6 | M_NOIVU | * | | | * | * | * | 75, 80, 84, 162, 192 |
| 1.48 | 6 | M_NOIVU | * | | | * | * | * | 75, 79, 429 |
| 1.49 | 6 | M_NOIVU | * | | | * | * | * | 75 |
| **1.5\x00** | 6 | M_NOIVU | * | | | * | * | * | 84 |
| 1.51 | 6 | M_NOIVU | * | | | * | * | * | 75, 103, 299, 373 |
| 1.52 | 6 | M_NOIVU | * | | | * | * | * | 75 |
| 1.53 | 6 | M_NOIVU | * | | | * | * | * | 75, 83, 709 |
| 1.54 | 6 | M_NOIVU | * | | | * | * | * | 75, 81, 115, 117, 323, 383, … |
| 1.55 | 6 | M_NOIVU | * | | | * | * | * | 77, 79, 88, 108, 168, 177, … |
| 1.56 | 6 | M_NOIVU | * | | | * | * | * | 75, 77 |
| 1.57 | 6 | M_NOIVU | * | | | * | * | * | 76, 77, 88 |
| 1.58 | 6 | M_NOIVU | * | | | * | * | * | 76, 77, 88, 159, 213 |
| 1.59 | 6 | M_NOIVU | * | | | * | * | * | 77, 88, 224, 1183 |

[V] **一个版本标签对应多个布局的情况：0 个。** `(version, savable)` 组合映射到多个布局的情况：**0 个**。
[V] **只有 `1.21` 这一个版本标签对应两个 savable（2 和 3）**，所以版本标签单独**不充分**。

---

## 5. 1.35 及更早 vs 1.36+：结构差异与「为什么库不支持」

### 5.1 逐层差异（集合运算，全部读真实字节）

[V] 实测的字段序列差集：

```
1.35/1.36/1.37 (savable=5) vs 1.40–1.59 (savable=6):
    仅存在于 savable=5 : ['individual_victories_used']
1.21 长无creator (savable=3) vs 1.33 长有creator (savable=4):
    仅存在于 savable=4 : ['creator_name']
1.21 短 (savable=2) vs 1.21 长 (savable=3):
    仅存在于 savable=3 : ['unknown_value','unknown_value_2',
                          'amount_of_unknown_numbers','unknown_numbers']
1.33 (savable=4) vs 1.35 (savable=5):
    仅存在于 savable=4 : ['legacy_unknown_after_instructions']
    仅存在于 savable=5 : ['individual_victories_used','trigger_count']
1.21 短 (savable=2) vs 1.59 (savable=6):
    仅存在于 savable=2 : ['legacy_unknown_after_instructions']
    仅存在于 savable=6 : ['unknown_value','unknown_value_2',
                          'amount_of_unknown_numbers','unknown_numbers',
                          'creator_name','trigger_count']
```

**「双重移除」的字段集合（1.36 前存在、1.40+ 消失）**：

```
pre-1.36 专有字段 : ['legacy_unknown_after_instructions']
1.40+ 专有字段    : ['trigger_count']
```

### 5.2 1.35 vs 1.36：**FileHeader 层面完全相同**

[V] 用两个**真实代表文件**实测对比：

```
1.35 rep  0_E3_Scenario.aoe2scenario   savable=5  layout=M_IVU  deflate_offset=85
1.36 rep  real_world_amazon.scx        savable=5  layout=M_IVU  deflate_offset=69
```
（两者 offset 不同只是因为 `creator_name` / `unknown_numbers` 长度不同；**布局相同**。）

```
字段序列 1.35 == 1.36 ? True
  两者均为: header_length, savable, timestamp_of_last_save, scenario_instructions,
            individual_victories_used, player_count, unknown_value, unknown_value_2,
            amount_of_unknown_numbers, unknown_numbers, creator_name, trigger_count
```

**结论**：1.35 与 1.36 在 FileHeader 层面**使用同一套文法**。

### 5.3 为什么库不支持 1.21/1.33/1.35 —— 是版本字符串检查，不是字节不可读

[V] 库的判定逻辑是**目录存在性检查**：

```
_get_structure()  打开  <pkg>/versions/DE/v<ver>/structure.json
versions/DE/ 实际包含: v1.36, v1.37, v1.40…v1.49, v1.51, v1.53…v1.59  (共 20 个)

versions/DE/v1.21 exists = False
versions/DE/v1.33 exists = False
versions/DE/v1.35 exists = False
versions/DE/v1.36 exists = True
```
报错原文：
```
UnknownScenarioStructureError: The version DE:1.21 is not supported by AoE2ScenarioParser. :(
(versions/DE/v1.21 exists=False)
```
[V] 库的 `changelog.md` 称 v1.36 是 *"First DE scenario file version"*。**[I] 所以库拒绝这三个版本，唯一原因是它没有为它们分发 schema 目录 —— 在任何字段被读取之前就拒绝了。它们的字节完全可读。**

### 5.4 版本标签不可靠（实测反例）

[V] 真实发行的战役成员 `K1_Tamerlane_5.aoe2scenario`（在 `kcam1.aoe2campaign` 内）的版本标签是 **`b'1.5\x00'`** —— 末尾是**裸 NUL**，而非法 ASCII 数字。它的 `savable=6`，用 M_NOIVU 文法**正确解析**（deflate_offset=84，输出 426,987 B）。

**因此：任何以版本字符串为判据的解析器都会在这个文件上失败或走错分支。`savable` 才是可靠判据。**

### 5.5 未解：`savable=2` 与 `savable=3` 的语义差别

[U] 两者都出现在 1.21，都是 `real_world_*.scx`。实测差别：
- `savable=2` → L_SHORT，`header_length=20`，无 sentinel 块，`player_count=8`
- `savable=3` → L_LONG_NC，`header_length=0`，有 sentinel 块，`player_count=8`

两者的**语义理由不明**（可能是编辑器的一次性迁移遗留）。已知的是本机 8 个 `savable=2` 全部来自 `real_world_*` 系列。**不给猜测。**

---

## 6. `.aoe2campaign`：成员表确定解析

### 6.1 结论：**证实**「成员是背靠背的独立场景文件」

[V] **逐字节同一性证明**：`dcam0.aoe2campaign` 内的成员 `The Siege.aoe2scenario` 是 **209,143 B**，sha1 = `a4cbb05098a18f36c7ff1be9a7ca7429da480f70` —— 与用户档案目录下的**独立** `The Siege.aoe2scenario` **完全相同**（`identical=True`）。

[V] **完整消费证明**：**235/235** 个成员的 deflate 流恰好消费完该成员的全部字节（不多不少），且 **235/235** 拥有合法的 4 字节版本标签。**失败 0 个。**

### 6.2 成员表确定解析（零扫描）

[V] 解析规则，全部**推导**、无搜索：

```
@0                    c4      version tag ("2.00")
@4                    u32     amount_of_unknown_numbers   (42 个战役中恒为 6)
@8                    u32[amount]  unknown_numbers
@8 + 4*amount          u8[256] fixed 256-byte prologue
@8 + 4*amount + 256    u32     member_count
                      然后 member_count 条变长成员记录
                      然后 member_count 个成员场景文件，背靠背，精确铺满到 EOF
```

成员记录（变长，`record_size = 16 + 2 * len(name)`）：
```
u32 member_size
u32 member_offset          (相对战役文件起点的绝对偏移)
u16 0x0A60                 (常量 sentinel)
u16 name_len
char name[name_len]        e.g. b"A1_Tariq1.aoe2scenario"
u16 0x0A60                 (同一 sentinel 重复)
u16 name_len               (重复)
char name[name_len]        (重复)
```

[V] 实测（全部 42 个战役）：

```
campaigns parsed with ZERO search               : 42/42
header_end      (== 8 + 4*amount) 直方图        : {32: 42}
count_field_offset          直方图              : {288: 42}
gap (count_field_offset - header_end) 直方图    : {256: 42}
members tile exactly to EOF                     : 42/42
member_count 直方图                             : {5: 25, 6: 15, 4: 1, 16: 1}
total members                                   : 235
distinct record sizes (16 + 2*len(name))        : [58,60,62,64,66,68,70,72,74,76,
                                                    78,80,82,84,86,90,92,94,98]
```

**成员表是变长的**（步长取决于每个成员的**文件名长度**），这就是为什么从来找不到一个固定步长的索引表。

### 6.3 「64 字节索引表」说法：**证伪**

[V]
```
campaigns where (count_field_offset - header_end) == 64 :  0/42
campaigns where (count_field_offset - header_end) == 256: 42/42
```
**42 个战役中 0 个符合 64 字节的说法**，实测恒为 **256**。之前那份报告声称的「64 字节索引表」在**本机 42 个战役中的 0 个**成立。（未照抄该说法。）

### 6.4 那 256 字节序幕到底是什么（实测分布）

[V] 42 个战役，共检视 1344 个 64-bit 字：

```
 704  52.4%  other
             e.g. acam1  0x316d616361          <- 这其实是 ASCII "acam1" 的字节
             e.g. acam1  0x1f424ddf938        <- 堆区间地址
             e.g. acam1  0x1f43008bab0
 299  22.2%  user-space pointer range [0x00007FF0_00000000, 0x00008000_00000000)
             e.g. acam1  0x7ff66d50d010
             e.g. acam1  0x7ff99f1888b0
 226  16.8%  small integer 1..0xFFFF
             e.g. acam1  0x30
             e.g. acam2  0x30
 110   8.2%  zero
   5   0.4%  0x10000 .. 0xFFFFF
             e.g. coop9  0x228c4
             e.g. incam2 0xa584b
```

[V] 序幕总是以 **NUL 结尾的可打印 ASCII 战役名**开头：**42/42**，**42 个互不相同**（`acam1, acam2, acam3, acam4, cam2, cam3, cam4, cam5, coop10, coop17, coop22, coop25, …`）。

[V] 非零字节数：**最少 112 / 最多 166**（共 256 字节）。

[I] 其中 22.2% 的字落在 **Windows 用户态指针区间**，另有大量堆区间值 —— 这与「编辑器把未初始化内存 / 运行时指针写进了文件」的解释一致。

[U] **这 256 字节没有可用的固定语义表结构。** 这是「64 字节索引表」说法不可能成立的**结构性原因**：该区域的内容按战役而异（非零字节 112–166 浮动、混有指针值），**不存在固定布局的字段**。它的**存在与长度（恒 256）是确定的，内容语义是未解的。**

---

## 7. 被证伪的说法（含任务书中的）

### 7.1 「前 200,000 个偏移 0 命中」——**证伪**

[V] 对 `The Siege.aoe2scenario`（209,143 B，ver `1.53`，savable=6）实测：

```
布局推导  : layout=M_NOIVU  deflate_offset=83  body_bytes=1,453,615

偏移 4 处直接解压:
   wbits=-12 -> zlib.error   eof=False
   wbits= 15 -> zlib.error
   wbits= 47 -> zlib.error
   wbits= 31 -> zlib.error
   wbits=-15 在真实偏移 83 处 -> OK   eof=True

穷举扫描偏移 0..200000:
   zlib.error 的偏移数                               : 199,003
   能解出点什么（宽松规则）的偏移数                   :     997
   eof==True 且输出 >= 1000B（严格规则）的偏移数      :       1  -> [(83, 1453615)]
   用时                                              : 1.8 秒
```

**结论：任务书里「0 命中」是验收规则的假象，不是文件的性质。** 正确规则下唯一解在 1.8 秒内出现。

### 7.2 「default0 在偏移 39,939 有流（解出 4,741 B）」——**是假阳性**

[V] `default0.aoe2scenario`（175,001 B，1.59）在整个文件上的严格命中：

```
offset=1183   out=2,525,710   <-- 真实
offset=39939  out=4,741       <-- 伪流（spurious）
```
**真实起点是 1183（结构推导），body 2,525,710 B。** 39,939 处确实能解出 4,741 B 并 `eof=True`，但那是一个偶然的伪流，**不是场景正文**。

### 7.3 「穷举偏移是已证伪的策略」

[V] **更精确的说法**：穷举**能**找到真实偏移，但**必须**同时满足两个条件 ——（a）正确的验收规则（raw `-15` 流上 `d.eof == True`），（b）一个量级规则（取输出最大的那个）。实测：

| | 找到真实偏移 | 唯一命中 | 输出最大者即真实 | 首个命中即真实 |
|---|---|---|---|---|
| 54 个独立文件 | 54/54 | 41/54 | **54/54** | **54/54** |
| 235 个战役成员 | 235/235 | 191/235 | **235/235** | **235/235** |
| **合计 289** | **289/289** | **232/289** | **289/289** | **289/289** |

[V] 含糊（≥2 个严格命中）的实例：独立 13/54，成员 44/235，**合计 57/289**。单个实例最多命中 **10** 个（`special_map_swirlingriver.scx`）。最典型的多命中例子：

```
0_September_Event_Scenario.aoe2scenario  真实=84
   严格命中 7 个: [(84, 27137282), (848165, 18568), (1328991, 40142),
                   (2020612, 34767), (2165733, 42186), (2303482, 44214),
                   (2337679, 23784)]
```
其中真实流输出 **27,137,282 B**，其余最大者 44,214 B —— 差了 **约 600 倍**。

**所以正确的表述是**：穷举在 232/289 的情况下就能得到唯一解，但在 57/289 的情况下需要「取输出最大者」这个额外规则才能定夺；而**结构推导在 289/289 的情况下一次给出唯一、无需任何量级规则**。后者才是**确定性算法**。任务书要求「不要以穷举作为答案」是对的，但理由不是「穷举找不到」，而是「穷举在 57/289 上需要额外的量级启发式，且它不是推导」。

### 7.4 「229 个内嵌场景」——**是我自己早期的错误**

[V] 之前的魔数扫描（正则 `rb"1\.\d\d\x00\x00\x00\x00"` + header length 24..400）得到 **229**，而**成员表**得到 **235**。差值原因：**魔数扫描漏掉了 6 个成员**，因为它们的 `scenario_instructions` 太长，把头部推出了 24..400 的窗口上界（最长漏掉的 `instr_len = 635`）：

- `coop3` → `3_Saladin_1 CO-OP.aoe2scenario`（instr_len=355）
- `coop6` → `C1_Attila_1..4 CO-OP.aoe2scenario`（instr_len 588/615/627/635）
- `kcam1` → `K1_Tamerlane_5.aoe2scenario`（版本标签损坏 `1.5\x00`）

**235 才是正确数字**，且它由**确定性的成员表**给出，不依赖任何窗口启发式。

---

## 8. 仍然未解的问题

| # | 未解项 | 实测到的证据 | 缺什么 |
|---|---|---|---|
| U1 | `header_length`（偏移 4 的 u32）的语义 | [V] 8 个 L_SHORT 文件恒为 **20**；其余 **281/289** 恒为 **0**。在 L_SHORT 中恰好等于 `deflate_offset - 8`。库源码中 `grep header_length` **无任何匹配** —— 库从不以编程方式读它 | 无语义定义；只有 1 个非零取值，无法判定公式 |
| U2 | `legacy_unknown_after_instructions` 的语义 | [V] 存在于所有旧世布局；全部 26 个旧世实例中**恒为 0** | 取值无变化 → 无法推断含义 |
| U3 | `individual_victories_used` 的语义（名字来自库） | [V] 存在于全部 29 个 `savable=5` 实例，**恒为 0** | 名字是库给的；本机取值全 0 |
| U4 | 战役序幕 256 字节区域的**布局** | [V] 长度恒 256（42/42）；22.2% 的字像用户态指针；非零字节 112–166 浮动 | 无固定字段结构，内容按战役而异 → 见 §6.4 |
| U5 | `unknown_numbers` 的**精确语义** | [V] 与库的 `{LEGACY:[], AOE2:[2..12], ROR:[11]}` 映射一致；取值是 `[0,1]` / `[2,3,4]` / `[2,3,4,5,6,7]` / 更长的 DLC id 列表 | `[I]` 是 DLC/扩展 id 列表，但无第一方文档确认 |
| U6 | `trigger_count` 是否真的等于场景内触发器数量 | [V] 存在于现代布局；范围 0..704（M_NOIVU）、0..89（M_IVU） | 未解析解压后正文的 triggers 段做数量核对 |
| U7 | `savable=2` 与 `savable=3` 的语义差别（均在 1.21） | 见 §5.5 | 本机样本只有 `real_world_*` 系列，区分理由不明 |
| U8 | 1.21/1.33/1.35 的**第一方 schema** | 库无 v1.21/v1.33/v1.35 目录 | 我们的旧世文法只有 `[I]` 推断 + `[V]` 289/289 验证，**没有官方文档来源** |
| U9 | `.aoe2campaign` 的**独立格式文档** | [V] 成员表规则在 42/42 上成立 | AoE2ScenarioParser **完全没有** `.aoe2campaign` 支持，无 oracle 可对照 |

---

## 9. 自我更正

本节记录此前**错误的假设**及修正理由。任务要求「宁可写未解，也不要给一个看起来合理但没验证的答案」——因此这里逐条列出实际发生过的错误。

### 9.1 我曾假设「从偏移 4 开始的 u32 对齐遍历可以走出头部字段」

**错误原因**：忽略了 `scenario_instructions` / `creator_name` 是 **str32 变长字段**，其长度是**字节数且不补齐**。当长度为奇数（如 1、5、13）时，后续所有字段都落在**非 4 字节对齐**的位置上，u32 遍历会走偏字段网格。

**修正**：实测 `real_world_antarctica.scx`（instr_len=1）与 `real_world_nippon.scx`（instr_len=1）后，改为**严格按声明长度推进字节指针**。此前 u32 遍历打印出 `2048, 256000, 512` 等垃圾值即是该错误的症状。

### 9.2 我曾用错误的 `structure.json` 解析方式，导致字段顺序看起来是**字母序**

**错误原因**：把 `structure.json` 当成「带 `name`/`id` 键的 section 列表」，并用会排序键的 pprint 输出。结果 retriever 顺序**看起来是字母序**（`amount_of_unknown_numbers` 排在 `player_count` 前面等），这会让「两种顺序」的结论变得毫无意义。

**修正**：`structure.json` 实际是**以 section 名为键的 dict**，`structure["FileHeader"]["retrievers"]` 的**插入顺序**就是库的二进制读取顺序（`json.load` 保留文件顺序；是 `pprint` 默认排序键造成了假象）。改用 `json.load` 直接读后，才得到正确的两种顺序（§3.4），并且与我们的独立推导**完全相等**。

### 9.3 我早期采纳过任务书中的两个数字，后来都**实测推翻**

- 「`default0.aoe2scenario` 在偏移 39,939 有可解流」→ [V] 那是一个**伪流**（4,741 B）；真实结构偏移是 **1183**（2,525,710 B）。见 §7.2。
- 「前 200,000 个偏移 0 命中 → 穷举不可能」→ [V] 那是**验收规则**的问题；严格规则下唯一解 1.8 秒命中。见 §7.1。

### 9.4 我早期的「229 个内嵌成员」是**我自己引入的错误**

**错误原因**：用窗口启发式（header length ∈ 24..400）扫描，窗口上界截断了 `scenario_instructions` 很长的成员。

**修正**：改用**确定性的成员表**（成员计数固定在 `8 + 4*amount + 256`），得到 **235**。见 §7.4。

### 9.5 我曾把「64 字节索引表」作为待验证的说法

**修正**：实测 42 个战役，符合 64 的 **0/42**，实际恒为 256。已按任务要求给出**实测结论**而非照抄。见 §6.3。

### 9.6 `open_questions.py` 中的 `PROFILE` 路径表达式曾被写坏

**错误原因**：写了一个无意义的 `.replace("98406248", … .zfill(0) or …)` 表达式，路径被毁。

**修正**：改为字面量 `C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario`。该 bug 在脚本运行前被发现并修复。

### 9.7 `field_offsets()` 的调用签名错误

**错误原因**：在 `layout_diff.py` 中按 `field_offsets(b)` 调用，而该函数需要 `(b, layout)`，第一次运行抛 `TypeError: field_offsets() missing 1 required positional argument: 'layout'`。

**修正**：改为 `field_offsets(b, locate(b)[1])`。

### 9.8 `brute_force_audit.py` 的枚举 bug（曾静默丢弃 50 个文件）

**错误原因**：用 `os.listdir(DRS)`，但 50 个 `.scx` 位于 `drs\` 的**子目录**中，导致首次审计只覆盖 239 个实例而非 289 个。

**修正**：改用 `os.walk` 递归枚举。这是本次审计中最严重的一个 bug —— 它会让分母静默偏小。

---

## 10. 可复现脚本与运行命令

所有脚本位于 `D:\Software\DeepSeek Harness\工作区2\_probe\scenario_header\`。
统一执行方式（PowerShell）：

```powershell
$env:PYTHONIOENCODING="utf-8"
$py="C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $py "D:\Software\DeepSeek Harness\工作区2\_probe\scenario_header\<脚本>.py"
```

### 10.1 核心交付脚本

| 脚本 | 作用 |
|---|---|
| **`header_layout.py`** | **核心交付物**。纯 stdlib（`struct`+`zlib`），**不导入 AoE2ScenarioParser**。导出 `SAVABLE_LAYOUT`、`read_version`、`read_savable`、`field_offsets(b, layout)`、`parse_header`、`inflate_body(b, offset)`、`locate(b)`。**无任何搜索/候选循环。** |
| `campaign_deterministic.py` | 零扫描战役解析器，导出 `parse_campaign_deterministic(b)` 与 `PROLOGUE_LEN = 256`；含 `if __name__ == "__main__"` 保护 |
| `campaign.py` | 早期基于窗口搜索的战役解析器（**已被 `campaign_deterministic.py` 取代**，保留作对照）；导出 `SENTINEL = 0x0A60`、`_try_record` |

### 10.2 验证脚本

| 脚本 | 运行命令 | 关键产出 |
|---|---|---|
| `dispatch_verify.py` | 同上下 | `dispatch_verify_output.txt` / `.json` — 289 实例纯 dispatch 验证 + 3 个文件在 4..3000 的偏移唯一性反证 |
| `report_facts.py` | 同上 | `report_facts_output.txt` / `.json` — 本报告引用的**全部数字**一次生成 |
| `layout_diff.py` | 同上 | `layout_diff_output.txt` / `.json` — 结构差集 + 与库 schema 的交叉验证 |
| `open_questions.py` | 同上 | `open_questions_output.txt` / `.json` — 未解字段的取值直方图 |
| `variant_check.py` | 同上 | `variant_check_output.txt` / `.json` — `unknown_value_2` vs 库 variant oracle（46/46 一致）+ 序幕分布 |
| `member_rule_check.py` | 同上 | `member_rule_check.json` — savable 规则在 235 成员上的验证 |
| `member_completeness.py` | 同上 | `member_completeness_output.txt` — 成员字节同一性 + 精确消费 |
| `final_verify.py` | 同上 | `final_verify_output.txt` / `.json` — 289 实例单一候选确认 |
| `oracle_check.py` | 同上 | `oracle_check_output.txt` — 库拒绝 1.21/1.33/1.35 的原始报错 + schema 顺序 |
| `refute_bruteforce.py` | 同上 | `refute_bruteforce_output.txt` — §7.1 的实测数据 |
| `spurious_hits.py` | 同上 | `spurious_hits_output.txt` — 全文件严格命中（发现 39,939 伪流） |

### 10.3 穷举审计（耗时较长，合计约 30 分钟）

```powershell
& $py "...\brute_force_audit.py" singles    # 54 独立文件, 876.6 s, 15,092,753 个偏移
& $py "...\brute_force_audit.py" members    # 235 成员,   888.9 s, 28,714,100 个偏移
```
产出 `brute_force_audit_singles_output.txt` / `brute_force_audit_members_output.txt`（互相不覆盖）。

### 10.4 一个最小的独立复现（无需读本报告）

```python
import sys, struct, zlib
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\scenario_header")
from header_layout import locate, read_savable

b = open(r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
         r"\resources\_common\scenario\The Siege.aoe2scenario", "rb").read()
off, layout, body, diag = locate(b)
print(read_savable(b), layout, off, len(body))   # -> 6 M_NOIVU 83 1453615
```

---

## 11. 交付清单对照

| 任务书要求 | 状态 | 位置 |
|---|---|---|
| 1. 逐版本头部布局，覆盖本机所有版本 | 完成（25 个版本标签 / 289 实例） | §4 |
| 2. 以库源码为 oracle，写独立定位函数并在所有可读场景验证 | 完成（`header_layout.py`，**不导入库**；289/289；与库在 v1.36/v1.37/v1.40/v1.59 上序列完全相同） | §3.2–3.4 |
| 3. 1.35 及更早 vs 1.36+ 的差异及原因 | 完成（差集已实测；原因是**目录存在性检查**） | §5 |
| 4. `.aoe2campaign`：证实/证伪 + 成员表确定解析 | 完成（**证实**，byte-identical；零扫描解析 42/42；64 字节说法**证伪**） | §6 |
| 5. 报告含诚实分母、[V]/[I]/[U] 标签、可复现脚本、未解清单、自我更正 | 完成 | 全文 / §8 / §10 / §9 |
| 6. 最终紧凑中文要点摘要 | 完成 | 交付回复 |

**结论：核心问题已解决。** deflate 流起点可由 `savable`（偏移 8 的 s32）唯一确定文法后**确定性推导**，无需任何搜索；在 289/289 个实例上验证成功，失败 0 个。
