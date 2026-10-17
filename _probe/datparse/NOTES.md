# 数据模组能力目录 — 实测笔记（NOTES）

本文件只记**实测出来、且会改变产品设计**的事实。每条都附复现脚本。

---

## 0. 环境锚点

| 项 | 值 |
|---|---|
| 游戏根 | `D:\Games\Steam\steamapps\common\AoE2DE` |
| 版本 | `101.103.54800.0`（Steam appid 813780，buildid 25464371） |
| 主数据 | `resources\_common\dat\empires2_x2_p1.dat` |
| 版本串 | `VER 8.9`（→ genieutils `GV_C32` = 54） |
| 压缩后 | 12,023,754 B（raw deflate, `window_bits=-15`） |
| 解压后 | **93,268,152 B** |
| 解析 | `_probe\datparse\parse_dat.py`，逐字节精确，EOF leftover 0，耗时 ~4.7 s |

---

## 1. 内容真值：`displayed_*` 与原始攻防列表是**两份**数据

**实测**：Type50 里同时存有
- 原始 `attacks[]` / `armors[]` 列表（伤害计算使用）
- `displayed_attack` / `displayed_melee_armour` / `displayed_range` / `displayed_reload_time`（**单位面板直接渲染的数字**）

**实测差异率：24 / 1530 个战斗单位（1.6%）两者不一致。**

**产品后果**：`"弓箭手变强"` 至少可拆成 4 个可分别编辑的目标：原始攻击列表、`displayed_attack`、攻击装填/帧延迟、对特定 class 的附加伤害。**只改一个 → 用户会报"你的工具在骗人"。** 每个意图式编辑必须显式声明改哪个（默认：两个都改）。

`screenshot_validate.py` 已用用户实机截图端到端验证：斥候骑兵（id 448）的 6 个面板数字**全部对上**：

| 面板 | dat 字段 | 值 |
|---|---|---|
| 生命 45/45 | `unit.hit_points` | 45 ✓ |
| 攻击 3 | `Type50.displayed_attack` | 3 ✓ |
| 护甲 0/2 (前) | `Type50.displayed_melee_armour` | 0 ✓ |
| 护甲 0/2 (后) | armor 列表 class 3 | 2 ✓ |
| 装填 2 | `displayed_reload_time` | 2.0 ✓ |
| 移速 1.20 | `unit.speed` | 1.2000000476837158 ✓ |

→ 整条链（deflate → 解析 → 字段 → 含义）**对真实游戏**验证完毕。

---

## 2. 攻防语义（权威）

权威类表 = 游戏自带 `Tools_Builds\AGE3NamesV0007.ini` 的 `[AoE2DEArmorNames]`（**37 项，0..36**）。

- `attacks` 里 **class 3 = Base Pierce、class 4 = Base Melee**，其余 class 全是**附加伤害**。
- `armors` 里 **class 3 = 穿刺护甲、class 4 = 近战护甲**。
- `AttackOrArmor` = `int16 Class; int16 Amount;`（各 4 B，Class 在前）。
- **`class` 参数可能超出 0..36**：实测出现 37/38/39/40/41/60 与哨兵 `-1`。→ **ini 不是穷尽表，未知的必须渲染成 `"Class 38"`，不要报错也不要显示 "None"。**
- ⚠ `_probe\schema\armor_classes.json` 的键是**列表索引**不是 class ID，**不可用于显示**；顶层键为 `['source','note','classes']`。
- **10/10 ground truth 复现**（Archer 4 / Knight 10,2,2 / Villager 3 / Spearman 3 且 vs Cavalry +15）。

---

## 3. ★ 效果命令的 count 字段是**几何字段**（血的教训）

`EffectCommand` = `u8 Type; i16 A; i16 B; i16 C; f32 D;`（11 B）。`read_effect()` = `debug_string` + `i16 n` + `n × 11 B`。

Effects **背靠背紧排、无额外长度前缀**。所以：

> **改 `i16 n` 会让后面所有 record 滑移，整个文件崩掉。**

实测后果：我把 `effect[449]` 的 count 从 79 改成 4，重解析在 `UnitHeaders` 处报
`EOFError: read of 4 byte(s) at offset 93268149 would pass end of file (93268152)`。

**正确做法**：**count 必须原样保留**，多余的槽位写成 `Type=255`（no-op 哨兵）填充。
- 哨兵写法：`(255, -1, -1, -1, 0.0)`
- 已在 `reuse_orphan.py` 里实现并验证：effect[449] 的 79 个槽 → 前 4 个改成"资源+2000"，其余 75 个填 255，**count 保持 79**，重解析 EOF 精确 → **PASS**。

**推广**：dat 里所有 `i16 count` + 紧排 record 的容器（Effects、Techs、Units、Graphics…）都有同样约束。**"改值安全、改数量危险"是原地打补丁的总原则。**

---

## 4. ★ 486 个 effect 槽是"无主地产"——不必增长文件就能造新玩法

**实测（`reuse_orphan.py`）**：

| | 数量 |
|---|---|
| effect 总数 | 1,500 |
| 被某个 tech 引用 | 1,014 |
| **完全无主（无 tech 指向）** | **486** |
| ↳ 其中含真实命令（非 255） | **178** |
| ↳ 纯 255 空操作 | 308 |

样本：`effect[1] 'Hindustanis Tech Tree'`（36 条）、`effect[2] 'Hindustanis Team Bonus'`（14 条）、`effect[3] 'Incas Tech Tree'`（52 条）、`effect[449] 'Mayans Tech Tree'`（79 条）、大量 `'Non-Tech'` 单条项。
完整清单：`_probe\datparse\out_reuse\orphan_effects.json`。

> **注意**：这些"无主"的 effect 里有很多是**文明科技树/团队加成**，它们**靠 TechTree 或别处接线**，不是真的死数据。真正安全的复用对象是 `'Non-Tech'` 与明确废弃的占位。**产品必须在界面上区分"可安全复用"与"连接方式不明"。**

**演示结果**：把 `effect[449]` 改写成"4 项资源各 +2000"（`(1, resource, -1, -1, 2000.0)`，resource 0=Food 1=Wood 2=Stone 3=Gold），
- 改动 **497 字节 / 80 个不连续区域**（因为要把 75 个残留槽填 255）
- 解压后尺寸 **完全不变**（93,268,152）
- 压缩后 11,982,426（**比原文件还小 41,328 B**）
- 未修改的解析器重解析 → **EOF 精确、leftover 0 → PASS**
- 回读确认：`type=1 A=0/1/2/3 B=-1 D=2000.0` + 75 条 `type=255`

---

## 5. ★ 意图编译器已跑通（`intent_patch.py`）

输入一句人话：`INTENT = {"say": "弓箭手攻击力 +2", "unit_id": 4, "field": "attack", "delta": +2}`

输出：

```
RESOLUTION: unit id 4 appears in 63 civs -> 63 physical records
COMPILED: 126 byte edits across 63 civs
   raw attack list edits : 63      (真实伤害计算)
   displayed_attack edits: 63      (面板显示)
BYTE DIFF: 126 changed region(s), 126 bytes total
   every changed region is a claimed edit offset: True
VERIFY: final offset 93268152, leftover 0 -> PASS
   hit_points untouched on all 63 records: PASS
   every record now = 6: PASS
```

**三个必须固化为工具行为的设计点**：

1. **同一单位在每个 civ 有独立副本**。Archer 存在于 **63 个 civ → 63 个物理记录**。只改一个 = 留 62 份过期数据。**必须默认全 civ 应用。**
   - 但**不能假设 63**：2,693 个不同 id 里只有 2,164 个存在于全部 63 civ（Gaia 多 529 个 eyecandy）。**必须按 civ 查成员资格。**
2. **必须同时改两份真值**（原始列表 + `displayed_*`），否则要么 UI 撒谎、要么只是外观。
3. **宽度纪律**：字段是 i16，写入前必须做范围检查（脚本里越界直接 `SystemExit`，不静默截断）。

---

## 6. 可安装 mod 目录已自动生成（`emit_mod.py`）

产物 `_probe\datparse\out_modtest\ArcherAttackPlus2_probe\`：

```
info.json                                    240 B   (UTF-8, ensure_ascii=False)
thumbnail.png                              1,687 B
resources\_common\dat\empires2_x2_p1.dat  11,982,182 B
```

**两条来自本机真实 mod 的硬规则**（违反则静默失效）：
- **mod 根 = 含 `info.json` 的那个文件夹**；游戏目录树**直接**镜像在其下，**不**包一层额外的 `resources/`。
  （本机 6 个已订阅 mod 全部如此；官方文档亦同。）
- **写盘字符串必须显式 UTF-8**。本机多个中文 mod 的 `info.json` 是 GBK 写的，标题显示成 `閫忔槑涓婚鏁堟暣鍚堣嚜鐢` 这类 mojibake。

目标位置：`C:\Users\26913\Games\Age of Empires 2 DE\<SteamID64>\mods\local\<文件夹名>`。
**脚本未写入任何游戏目录或用户档案目录。**

---

## 7. `.dat` 里的字符串是**原始字节**，编码由写入者决定

- `parse_dat.py:156,172` 用 `b.decode("latin-1")` → 名字字段是**无损字节容器**。
- genieutils `ISerializable::readString/writeString`（`src/file/ISerializable.cpp`）是**纯字节拷贝 + 补 0**，无编码转换。
- **实测**：10× mod 写入的中文是 **GBK/GB18030**，不是 UTF-8（utf-8 解码直接失败）。例：`'¿ª¾Ö×ÊÔ´ÉèÖÃ'` → gb18030 → **`开局资源设置`**；`'¸÷Ïî×ÊÔ´+2000'` → `各项资源+2000`。

**约束**：读写 dat 字符串**必须按原始字节透传**，绝不能擅自 UTF-8 重编码；显示层要做 GB18030→UTF-8 回退嗅探。

---

## 8. 真实数据模组的改动机制（实测，推翻最初猜测）

对比 BASE / `423821` 军团长 / `550749` 10×（脚本 `moddiff.py`、`cmd_diff.py`、`how10x.py`、`autotech.py`）：

| | BASE | 423821 | 550749 10× |
|---|---|---|---|
| effects | 1,500 | 2,028 | 6,053 |
| techs | 1,510 | 1,644 | 5,864 |
| civs | 63 | 63 | 63 |
| graphics 指纹 | — | **完全相同** | **完全相同**（`5439ddf2752d1881603fd3ff`） |
| 跨 civ unit 对象 | 136,861 | 140,389 | 284,344 |
| 解压字节 | 93,268,152 | 94,415,314 | 124,533,358 |

- **前 8 个段（header/TerrainRestrictions/PlayerColours/Sounds/Graphics）逐字节完全相同** → 数据模组只碰后半部分。
- **差异全部从 `0x36B0BE` 开始 —— 正是 `numEffects` 字段位置。**
- **10× 的真相**：**不修改任何已有 unit 属性**（`stat-changed=0` 跨全部 civ）；而是**每 civ 新增 2,341 个空占位 unit**（id 2750+，全 `type=10` EyeCandy、`hp=1`、`class=-1`、空名）+ 新增 4,354 个 tech（多半是空占位）。
  → **"10 倍资源"靠新增 Tech/Effect 包装实现，不是改数值。**
- **civ 的 `resources` 数组（601 项）没有任何差异**；`index 91..94`（Starting Food/Wood/Stone/Gold）全为 0.0 → 也不是靠 civ resources。
- 同一轮修正：**"967 个 effects 不同"全部由名字字段造成**（mod 把英文效果名批量换成中文），**命令内容真正被改的只有 16/1500**。

**产品含义**：一个看似简单的"10 倍资源"实际靠"新增数百个空占位 tech/effect + 少量包装 tech"实现。**UI 必须能把"玩家可见的真实改动"与"引擎内部占位/包装对象"分开**，否则用户打开就看到几千条垃圾项。这是"语义模型层必须存在"最直接的证据。

---

## 9. 原版只用到 27 种 EffectCommand 类型

`template_library.py` → `template_library.json`。**vanilla 全集：27 种类型 / 10,500 条命令**（schema 定义了 59 种）。

频次：Attribute Modifier (+/-) 3026、Attr Mod (Multiply) 2366、Disable Tech 1969、Attr Mod (Set) 1094、Upgrade Unit 434、Tech Cost Modifier 377、Modify Tech 255、Resource Modifier (Set/+/-) 227、Enable/Disable Unit 209、Tech Time Modifier 151、Own Master Objects Attr Mod (+/-) 132、Resource Mod (Multiply) 129、Type 255 哨兵 27、其它…

**产品结论**：这 27 类 + 各自的原版范例 = **意图驱动 UI 的最小完备语法**。模板库可直接变成 UI 卡片——每张卡片背后是一条**已在原版游戏中验证过、保证不会崩**的写法。

---

## 10. 尚未解决 / 尚未验证

| 项 | 状态 |
|---|---|
| **游戏内 smoke test** | **未做**。所有验证都是文件级的（几何完整 + 语义回读）。**唯一剩下的真实未知。** |
| 几何变更（增删对象） | **原地补丁做不到**（见 §3）。需完整重序列化器 → 子代理 `5f280fab` 进行中（`_probe\serializer\write_dat.py` 已 30 KB）。 |
| 引擎是否支持松散 PNG 覆盖图集切片 | 社区证据支持"支持"，**未实机验证**（见 `能力目录v0.md`）。 |
| `Terrain.Phantom` 之外的版本相关歧义 | 已全量重审，确认 Phantom 是 `GV_SWGB` 处唯一行为差异。 |
| 偏移表的版本依赖 | 所有偏移是 **VER 8.9 专属**。工具必须按版本重推并**拒绝未知版本**，不能硬编码。 |
| 联机/成就影响 | 改单个文明建筑外观的 mod **禁用排位与成就**（社区）→ UI 必须警告。 |

---

## 复现脚本索引（全部在 `_probe\datparse\`）

| 脚本 | 作用 |
|---|---|
| `parse_dat.py` | 权威解析器（1,026 行，仅 stdlib） |
| `validate_semantics.py` | 10/10 语义校验 |
| `attack_semantics.py` | 攻防深走查 + ini 类表 + 10/10 ground truth |
| `screenshot_validate.py` | 用实机截图做端到端验证（斥候骑兵 6/6 对上） |
| `intent_patch.py` | **意图 → 字节**编译器（126 处编辑，63 civ） |
| `emit_mod.py` | **意图 → 可安装 mod 目录** |
| `reuse_orphan.py` | 复用 486 个无主 effect 槽（几何不变） |
| `template_library.py` | 27 类命令模板库 |
| `moddiff.py` / `cmd_diff.py` / `how10x.py` / `autotech.py` | 真实 mod 机制逆向 |
| `decode_names.py` | GBK/GB18030 编码探测 |
| `stat_offsets.py` / `stat_offsets.json` | 单位字段字节偏移表 |
| `slot_reuse.py` / `civ_chain.py` | effect 回收与 civ 接线分析 |
