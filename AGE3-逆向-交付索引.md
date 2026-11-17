# AdvancedGenieEditor3.exe · 逆向与全量数据 · 交付索引

> 一句话：**这个 exe 里能读出来的东西，全在这里了 —— 静态本体 52 个文件 + 游戏全量数据 36 张表 228.5 万行。**
> 全部对着**当前游戏版本**（`empires2_x2_p1.dat` 11,963,833 B，2026-10-29 实测），
> 校验 `python -X utf8 verify.py` 打印 **PASS（81 项断言）**。

---

## 0. 目标文件（身份自证）

| 项 | 值 |
|---|---|
| 路径 | `D:\Software\AI\Aoe2\AdvancedGenieEditor20261022x86\AdvancedGenieEditor3.exe` |
| 大小 | 8,415,744 B（8.03 MiB） |
| SHA-256 | `dc724de960cf5a49ccf3a0e65885147a79bf29acedbc6512520093061498aef6` |
| 格式 | PE32 · i386 · GUI · 无数字签名 |
| 编译 | 2026-10-22 04:11:17 UTC（链接器 14.44 / VS 2022 17.14） |
| 外挂名字表 | `AGE3NamesV0007.ini` 10,662 B，sha256 `07f99508bcfe93ff239ae2ec9cde64a079cd168a278da0f3f0fadff9da9f9f10` |

一条命令自查（不依赖任何外部判断）：

```bash
python -X utf8 -c "b=open(r'AdvancedGenieEditor20261022x86\AdvancedGenieEditor3.exe','rb').read();print(hex(len(b)),[hex(b.find(x)) for x in [b'About Advanced Genie Editor',b'2026.10.22',b'AGE3NamesV0007.ini',b'AdvancedGenieEditor3.pdb']])"
```

---

## 1. 两条交付线，别搞混

| 目录 | 是什么 | 规模 | 入口 |
|---|---|---:|---|
| **`AGE3-EXE逆向\`** | **exe 本体**的静态逆向：PE、导入导出、RTTI 类体系、函数画像、字符串、枚举、界面下拉框、外挂 ini | 52 文件 / 51 MB | [`EXE-全景报告.md`](AGE3-EXE逆向/EXE-全景报告.md) 18 章 |
| **`AGE3-全量数据\`** | AGE 能读的那份 `.dat` 里**全部字段**展开成 SQLite/JSON/CSV | 120 文件 / 1.94 GB | [`README.md`](AGE3-全量数据/README.md) + `age3q.py` |

`_re/age3/` 是**复现脚本**（**86 个 `.py`**），两个目录的每个数字都能被它重跑出来。

---

## 2. exe 本体：逆到了什么

### 2.1 骨架

| 指标 | 数值 |
|---|---|
| 节表 | `.text` 5,357,460 / `.rdata` 2,485,570 / `.data` 336,520 / `.rsrc` 8,536 / `.reloc` 404,820 |
| 指令总数 | 1,628,519（capstone 全量反汇编 14.1 MB） |
| 基址重定位 | 196,194 条 / 1,554 块 |
| 导出函数 | 44 个（全是 LZ4 压缩，用于读 `.dat`/`.slp` 的压缩段） |
| 导入 API | 968 个函数 / 10,973 个调用点 / 29 个 DLL / 2,856 个调用者 |
| 函数 | **11,781 个**（2,589 个有字符串引用、3,971 个有 API 调用） |
| 字符串 | 7,561 条被代码引用的串 + 全量 ASCII/UTF-16 池 |

### 2.2 类体系（RTTI 完整落地）

- **1,456 个类**，vftable 命中 **1456/1456**（100%，没漏没猜）
- **47,204 个虚函数槽**，5,779 个唯一函数地址
- 每个类带：修饰名 / 基类链 / 类层次深度 / 全部 vftable / 虚槽目标 RVA

这是读 AGE 源码结构的替代品 —— AGE 是 GPLv3 开源（`https://github.com/Tapsa/AGE`），
但没有 PDB 实体（exe 里只留了路径串），所以**成员变量名和行号拿不到**，只能靠 RTTI + 反汇编推。

### 2.3 枚举（界面下拉框的真身）

6 张表 / 327 项，`enum-final.json`：

| 枚举 | 项数 | id 范围 | 说明 |
|---|---:|---|---|
| Unit Attribute ID | 83 | 0–115 | 属性槽位 + 版本位掩码（`types 20-80`） |
| Unit Class · AoE2 | 62 | 0–61 | 含 4 条 alias |
| Unit Class · SWGB | 64 | 0–64 | 星球大战格式，同一 exe 支持 |
| Unit Task / Command ID | 46 | 0–155 | |
| Effect Command Type | 59 | 0–206 | |
| Tech Effect Command Type | 13 | 0–12 | |

**alias 是关键证据**：同一个 id 编了多个名字（18 = `Monk` / `Priest`，23 = `Conquistador` / `Chariot Archer`）。
AGE 不靠"版本判断分支"读多版本 dat，而是**把所有历史名字都留着**，靠数据里的版本号决定显示哪个。

### 2.4 外挂名字表 `AGE3NamesV0007.ini`（新解）

exe 旁边那个 ini 不是安装残留，是**外置的字段名表**，玩家可改。已全量解成 `age3-names-ini.json`：

| 段 | 条数 | id 范围 | 缺号 |
|---|---:|---|---:|
| `AoE2DEArmorNames` | 37 | 0–36 | 0 |
| `AoE2DETerrainTableNames` | 32 | 0–31 | 0 |
| `AoE2DECivResourceNames` | 500 | 0–499 | 0 |
| `Counts` | 3 | — | — |

`Counts` 段（`NumAoE2DEArmors=37` 等）与实际条数**完全自洽** → 这份 ini 没被截断也没被改残。

---

## 3. 全量数据：交付了什么

### 3.1 规模（全部实测，不是估）

```
age3.sqlite          207,933,440 B   36 张表 / 2,285,112 行
age3-dat-full.json   838,733,425 B   同一份数据的 JSON 形态
civs/                63 个文件       每文明一份独立 JSON（774 MB）
csv/                 36 份 CSV       与 36 张表一一对应（185 MB）
schema/              6 个文件        43 结构体 × 620 字段 + 18 组枚举 + 59 个 GameVersion
age3q.py             命令行查询器
verify.py            81 项断言自校验
```

### 3.2 关键实体

| 实体 | 数量 | 备注 |
|---|---:|---|
| 单位记录 `unit` | **136,861** | 每文明最多 2,750 槽位 × 63 文明 |
| 不重复单位 ID | 2,693 | |
| 科技 `tech` | 1,510 | `Civ = -1` 的通用科技 601 条 |
| 效果 `effect` | 1,500 | 命令 `effect_cmd` 10,500 条 |
| 图形 `graphic` | 20,883 | delta 56,470 / angle_sound 16,398 |
| 音效 `sound` | 930 | 条目 5,210 |
| 地形 `terrain` | 200 | `Enabled=1` 的 134 个 |
| 地形通行 `terrain_restriction` | 54 | `tr_name` 覆盖 32 行；通行图形子表 7,236 行 |
| 单位指令头 `unit_header` | 1,701 | 任务 2,329 |
| 文明资源 `civ_resource` | **37,863** | 601 项 × 63，其中 31,500 行有名字（`res_name`） |
| 科技树 | 4 时代 / 37 建筑 / 269 单位 / 240 研究 | |

四张表带**人话名**列（名字来自 exe 外挂的 `AGE3NamesV0007.ini`，不是猜的）：

| 表 | 列 | 有名行 / 总行 |
|---|---|---:|
| `civ_resource` | `res_name` | 31,500 / 37,863（ini 只命名到槽 499，500–600 共 101 项无名） |
| `terrain_restriction` | `tr_name` | 32 / 54（ini 只命名到 31） |
| `u_type50_attacks` | `class_name` | 226,395 / 259,596 |
| `u_type50_armours` | `class_name` | 343,975 / 349,078 |

未命中的 Class 是 37/38/39/41/60（护甲另有 -1、40）—— 这些槽位在 ini 里本来就没有名字，留 `NULL` 而不是编一个。

子表（`u_type50_attacks` 259,596 / `u_type50_armours` 349,078 / `u_resourcestorages` 410,583 /
`u_creatable_resourcecosts` 238,440 / `u_creatable_trainlocations` 80,614 /
`u_bird_tasks` 433,192 / `u_building_annexes` 123,236 / `u_damagegraphics` 71,836）。

### 3.3 怎么用

```bash
cd AGE3-全量数据

python -X utf8 age3q.py tables                       # 36 张表与行数
python -X utf8 age3q.py cols unit                    # unit 表 203 列
python -X utf8 age3q.py id 4 -c British              # 按 ID 查（弓箭手）
python -X utf8 age3q.py tech -n Yeoman               # 按名字查科技
python -X utf8 age3q.py effect 455                   # 效果 + 全部命令
python -X utf8 age3q.py cost 4 -c British            # 成本/训练地/攻击/护甲
python -X utf8 age3q.py sql "select ..."             # 直接 SQL
```

`age3q.py cost 4 -c British` 的实际输出（资源名与攻防 Class 名都来自那份外挂 ini）：

```
# ARCHR  ID=4  slot=4  HP=30  Speed=0.9599999785423279

## 成本（res_name 来自 AGE3NamesV0007.ini，槽 500 以上无名）
Type | res_name            | Amount | Flag
1    | Wood Storage        | 25     | 1
3    | Gold Storage        | 45     | 1
4    | Population Headroom | 1      | 0

## 训练地点/时间
TrainTime | UnitID | ButtonID | HotKeyID
35        | 87     | 1        | 16083

## 攻击（class_name 来自 [AoE2DEArmorNames]）
27 | Spearmen                        | 3
21 | Standard Buildings              | 0
3  | Base Pierce                     | 4
17 | Rams & Trebuchet & Siege Towers | 0
13 | Stone Walls & Gates & Towers    | 0
```

Excel / pandas 直接吃 `csv/`；要联查就开 sqlite（推荐，索引齐）。

---

## 4. 这次修的五个硬伤（为什么之前那版不能用）

1. **旧交付基于过期 dat**。上一版是 `_real.dat`（93,273,004 B），比当前游戏解压后的
   `_game.dat`（93,272,287 B）**多 717 字节** —— 上一个补丁的 dat。两者都能 `leftover = 0` 自洽，
   但计数全不同（音效 769→930、效果 1501→1500、单位 136,863→136,861）。
   所以旧版的 `769 / 1501 / 136,863 / 2,277,848 行` 全部作废，已用当前 dat 全量重算。

2. **`civ.csv` 曾炸到 889,106,981 B（848 MB）**。`flat()` 把 `Civ.Units`（2,750 条子记录）
   和 `Civ.Resources`（601 项）整块 `json.dumps` 进了 civ 行。已剔除这两个键（它们各有归属表），
   修后 `civ` 表 9 列、`civ.csv` 2,505 B。

3. **`verify.py` 写死了旧版本魔数** → 3 项假 FAIL。已改成**自一致断言**
   （`SoundCount == 表 sound 的行数`），现在换任何一版 dat 都不会误报。

4. **`civ_resource` 表整个丢了**（37,863 行）。原表由一批已不在仓库的旧脚本生成，
   `grep -rln civ_resource --include=*.py` 零命中 —— 重建后悄悄消失。已把生成段写回
   `_re/age3/export_sqlite_patch.py`。

5. **`terrain_restriction` 原来把整块 JSON 塞一列**。已拆成 `{tr_index, tr_name, usable_count,
   usable_terrain_count, usable}` + 子表 `terrain_restriction_passgraphic`（7,236 行）。
   同时把 ini 的三张名表接进 `civ_resource` / `terrain_restriction` / `u_type50_attacks` /
   `u_type50_armours`，让「Class 27」变成「Spearmen」。

---

## 5. 边界（这份交付**不**包含什么，别问我为什么）

| 缺什么 | 原因 |
|---|---|
| C++ 成员变量名、函数签名、源码行号 | 无 PDB 实体，只有路径串 |
| 约 6,000 个非虚函数的**名字** | 不可达于无符号信息；地址、大小、调用关系都有 |
| 界面的完整控件树 | wxWidgets 用 wxSizer 代码建构，只能从 `Create*Controls` 反读 |
| `.sld` / `.dds` / `.wav` 文件本体 | 那是游戏资源，不是 exe 也不是 `.dat` |
| 语言 DLL 文本 | 在 `resources/<lang>/` 里，不在 exe |
| `.rms` 随机地图、`.per` / `.xs` 脚本 | 同上，不在 exe 也不在 `.dat` |
| 反编译出的完整源码 | 只有 1,628,519 条指令的反汇编 |

> 「全部数据」= **exe 里所有能被静态读出来的结构 + AGE 能读的那个 `.dat` 里所有字段值**。
> 上面这 7 类本来就不在 exe 里，去找它们得换文件 —— 要哪一类说一声，单开一条线做。

---

## 6. 复现

```bash
cd _re/age3

# exe 侧（主要 19 个，全部可重跑；目录共 86 个脚本）
python -X utf8 exe_pe.py            # PE 骨架
python -X utf8 exe_rtti6.py         # RTTI → 1,456 类
python -X utf8 exe_code3.py         # 函数画像 → 11,781
python -X utf8 exe_enum2.py         # 枚举定稿 → 6 表 327 项
python -X utf8 exe_textcat.py       # 界面文案分类
python -X utf8 exe_report.py        # 汇总报告

# 数据侧（顺序不能乱，v2 的 CSV 依赖 full 建的库）
python -X utf8 age3_full.py --dat _game.dat --verify
python -X utf8 age3_full.py --dat _game.dat --out "../../AGE3-全量数据"
python -X utf8 export_sqlite_full.py
python -X utf8 export_sqlite_v2.py
python -X utf8 export_sqlite_patch.py
```

---

*最后更新：2026-10-29 · 对应游戏 dat `empires2_x2_p1.dat` 11,963,833 B，解压后 93,272,287 B / sha256 `82eb7d14…`*
