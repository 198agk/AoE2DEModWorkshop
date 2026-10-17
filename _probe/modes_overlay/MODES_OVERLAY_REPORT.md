# modes/ 覆盖层研究报告 — AoE2DE 静态分析

- 目标安装：`D:\Games\Steam\steamapps\common\AoE2DE`
- 分析对象：`AoE2DE_s.exe`（72,166,200 B）、`modes\Pompeii\`（3,351 文件 / 3,234,991,267 B）、主树（31,484 文件 / 56,325,414,475 B）、用户数据 `C:\Users\26913\Games\Age of Empires 2 DE`
- 方法：**纯只读静态分析**。未启动任何游戏可执行文件，未修改游戏目录任何文件。所有脚本与中间数据落盘于 `D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay\`
- 标注约定：**[V] 实测** / **[I] 推断** / **[U] 未解**

---

## 0. 一页结论

1. **`modes/` 不是可被 mod 声明的覆盖层。** 它是**安装根（BASE）私有**的一层。全盘只有 1 个 `modes` 目录（安装根，唯一子目录 `Pompeii`），用户数据/mod 根下 **0 个**；9 个已安装 mod 的顶层目录中 **0 个**含 `modes/`。[V]
2. **"有哪些 mode"是编译进 exe 的，不是扫描目录发现的。** 引擎里有一张 **DLC/内容模式名表**（rva `0x321efe0`），逐字为 `Base, DLC1, DLC2, DLC3, Pompeii, DLC4, DLCVV, DLC6, DLC7, DLCProvidence, DLCParis, DLCPortland` —— **`Pompeii` 就是该表的第 5 项**。全 exe **没有** `modes\`、`/modes`、`modes%s`、`%s\modes`、`ModesPath`、`ModesPathForMods` 之类"遍历 modes 目录"的字面量。[V]
3. **mod 无法自建新 mode**，因为 `MODE`/`MODES` **不在 47 个存储点枚举里**（枚举里只有 `DAT DRS WIDGETUI WPFG …` 与根来源 `BASE APPATA USER MODSROOT LOCALMODS SUBSCRIBEDMODS DLC CLOUD`）；mod 只能按**已声明的存储点**逐点镜像覆盖，而"模式注册表"没有任何存储点可挂。[V]
   > ⚠️ **对任务书的更正**：任务书称存储点枚举为"完整 46 个"。实测（`p32_enum2.py`，逐字节解析 rva `0x31f8cc4`–`0x31f8f36`）为 **47 个**；任务书自己列出的那份名单数一遍也是 **47** 个名字。属原任务书的 off-by-one，非本报告口径问题。
4. **`use_modes_path_for_mods: true` 无法从二进制定论。** 该字符串在 exe 中 **0 次被直接代码引用**（且它与 `replace`、`storage_point_list` 一样，在 .rdata 字符串池中属于**无引用区**）。已排除的解释见 §4。倾向性 [I]：它改变 **DAT 存储点在 mod 覆盖时的查找路径**（把 mod 的 dat 解析到当前 mode 的路径下），而非"是否可覆盖"。[U]
5. **`Pompeii` 是"第一方内容模式/DLC 变体"**：它复用了与普通 mod **完全相同的三件套原语**（镜像树 + 同名覆盖 + 逐存储点解析），但多出一条 **mod 拿不到的私有声明通道**——编译进 exe 的内容模式名表 + `modes\Pompeii\` 硬编码前缀 + 自带的存储点注册表 `Pompeii.json`。[V]+[I]
6. **对模组工具的后果（明确倾向）**：**"整套游戏变体"必须靠"镜像 47 个存储点"来实现，"丢一个 `modes/<Name>/` 进去"这条路对第三方 mod 关闭。** 工具应实现为普通 mod 文件夹内的多存储点镜像树。证据强度：**强**（3 项独立证据：编译期名表、无 MODES 存储点、9/9 已装 mod 无 `modes/`）。[V]

---

## 1. 关键前提与告诫（务必先读）

- **⚠️ 本机是注入/破解版，不是干净 Steam 安装。** 游戏根含 `Juij_Steam.dll`、`version.dll`、`winmm.dll`、`Juij_Steam.json` 及 `Juij_*.txt/.html`。**exe 本身可能被打过补丁**，因此所有"代码引用"结论都带此告诫；但全部字符串与目录证据不受影响。
- **⚠️ 重要方法学限定：本 exe 中"某字面量 0 次代码引用"**不能**证明"该文件/键未被使用。** 反例控制：`hotkeys.json`、`maps.json`、`civilizations.json`、`dropsites.json`、`unitlines.json` 这些**必然被加载**的核心 dat 数据文件，其文件名字面量在 `.text` 中的严格引用数**同样为 0**（见 §6-D）。因此引擎对 `.json` 文件名的获取**不是**通过代码字面量，而是**数据驱动**（目录枚举或名单文件）——exe 确实导入了 `FindFirstFileW / FindFirstFileExW / FindNextFileW / FindClose`（§6-B）。**故 `Pompeii.json` 的 0 命中，只说明"名字不是硬编码在代码里"，不说明"文件没被读"。**
- 逐条结论都给了分母（检查了多少文件、多少命中）。

---

## 2. 环境与可复现命令

```powershell
$py = "C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$env:PYTHONIOENCODING="utf-8"
$d  = "D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
# 按顺序：PE/字符串 → 清单 → 引用 → 对比 → 权威结论 → 控制实验 → 严格引用
& $py "$d\p01_exe_index.py"   # PE 节表、版本资源、PDB 路径
& $py "$d\p02_inventory.py"   # os.walk 全量清单（base + pompeii）
& $py "$d\p10_compare.py"     # 逐存储点文件数/字节/差异分类
& $py "$d\p11_deep_cmp.py"    # 同名文件 SHA-256 + 大小复核
& $py "$d\p13_truth.py"       # PE 地面真值映射 + 原始字节 dump
& $py "$d\p15_authority.py"   # 决定性：全 .text 暴力 disp32 扫描
& $py "$d\p16_fs.py"          # 全树关键字扫描 + mod 根实地结构
& $py "$d\p22_control.py"     # 控制实验：同池字符串引用普查 + 导入表
& $py "$d\p26_ranges.py"      # 区块引用测试 + mod 顶层形态
& $py "$d\p27_strict.py"      # ModRM 校验的严格 RIP 引用测试
& $py "$d\p28_json.py"        # JSON 加载器指纹
& $py "$d\p29_modepaths.py"   # 五个内容模式名的宿主函数解码
& $py "$d\p32_enum2.py"       # 存储点枚举精确计数（最大可打印游程解析）
& $py "$d\p33_artifact.py"    # 落盘 storage_points.json / content_modes.json
```

### 诚实的分母

| 检查项 | 规模 | 命中 | 失败 |
|---|---|---|---|
| 主树 `os.walk` | 31,484 文件 / 56,325,414,475 B | — | 0 walk 错误 |
| `modes\Pompeii` `os.walk` | 3,351 文件 / 3,234,991,267 B | — | 0 walk 错误 |
| 双树关键字字节扫描（p16） | 38,008 文件（含用户数据） | 见 §3 | 0 不可读 |
| 双树标记扫描（p24） | 34,835 文件 / 59,560,405,742 B | 见 §5 | 0 不可读 |
| 逐存储点对比 | 48,916 行文件级记录 | — | 0 |
| exe `.text` 暴力 disp32 扫描 | 51,879,936 B（0x3195400），逐字节 | 见 §6 | — |
| `.pdata` 函数表 | 169,274 个 RUNTIME_FUNCTION | — | — |

---

## 3. 问题 1：`modes/` 是不是可被 mod 覆盖的一层？

### 3.1 目录事实（[V]，全盘枚举）

| 位置 | `modes` 目录数 | 子项 |
|---|---|---|
| `D:\Games\Steam\steamapps\common\AoE2DE` | **1** | `['Pompeii']` |
| `C:\Users\26913\Games\Age of Empires 2 DE`（全部 profile / 用户数据） | **0** | — |
| 9 个已安装 mod 的顶层目录 | **0** | 见 §5.2 |

### 3.2 引擎侧证据（[V]）

- `storage_point_list` 在 exe 中**只出现 1 次**（rva `0x325c588`），在 `Pompeii.json` 中出现 1 次。**全树仅这两个文件**。
- `use_modes_path_for_mods` 同样**只在这两个"同一文件的两个视图"**里出现。**除此之外全盘无第三处。**
- `Pompeii.json` 文件名在 `AoE2DE_s.exe` 中 **0 次**出现。
- **"扫描 modes 目录"的字面量全部为 0 命中**：`/modes`、`\modes`、`modes\`（作为独立前缀）、`modes%s`、`%s\modes`、`%s/modes`、`ModesPath`、`ModsPath`、`Pompeii.json`、`return_of_rome`、`morematerials.json`、`build_atlas.ps1`、`AoE2DE.dat`。
- `modes` 的全部 8 处大小写敏感出现，**除 OpenSSL 内部**（`crypto\modes\ocb128.c`、`tls_construct_ctos_psk_kex_modes`、`tls_parse_ctos_psk_kex_modes`）与**回归测试工具**（`game\modes\Pompeii\resources\` 等）外，唯一真实通路字面量是 **`modes\Pompeii\`**。

### 3.3 决定"用哪个 mode"的机制：编译期名表（[V]）

rva `0x321efe0` 起是一张 **8 字节绝对 VA 指针表**，逐字指向：

```
0x321efc0 -> 0x31fb1a4  'Base'
0x321efc8 -> 0x321eec0  'DLC1'
0x321efd0 -> 0x321eec8  'DLC2'
0x321efd8 -> 0x321eed0  'DLC3'
0x321efe0 -> 0x31f7480  'Pompeii'      <-- 第 5 项
0x321efe8 -> 0x321eed8  'DLC4'
0x321eff0 -> 0x321eee0  'DLCVV'
0x321eff8 -> 0x321eee8  'DLC6'
0x321f000 -> 0x321eef0  'DLC7'
0x321f008 -> 0x321eef8  'DLCProvidence'
0x321f010 -> 0x321ef08  'DLCParis'
0x321f018 -> 0x321ef18  'DLCPortland'
```
其后是打包 u32 索引对 `(1,4) (5,6) (7,8) (13,14) (15,17) (16,18)`。

- **`Pompeii` 在引擎里的身份 = 内容模式/DLC 名表的一个条目**，与 `Base` / `DLC1..DLC7` 并列。**[V]**
- 5 个内容模式名 `Pompeii / Philadelphia / Paphos / Paris / Providence` 位于 rva `0x31f7480 / 0x31f7488 / 0x31f7498 / 0x31f74a0 / 0x31f74a8`（8 字节步长），同属 `cloudfilesystem.cpp` 的字符串簇。
- **绝对值指针普查**：`Pompeii`(0x31f7480) 有 **恰好 1** 个绝对 VA 指针（就在上表 `0x321cfe0`）；`Philadelphia/Paphos/Paris/Providence` **各 0 个** → 只有 `Pompeii`（及 Base/DLC 标签）进了绝对指针表，其余 4 个仅由 RIP 相对代码到达。**[V]**
- 5 个名字都被**同一个 1845 字节函数**引用（rva `0x27e7c0-0x27eef5`），该函数是"按内容模式取名字"的分发器（内部 17 次调用 `0x2a9630` = 字符串比较/赋值，末尾 17 次调用 `0x2a88a0`）。**[V]**

### 3.4 结论（问题 1）

> **[V]** mode 集合是**编译期固定**的（DLC/内容模式名表），引擎**不存在**"扫描 `modes\` 目录并注册新 mode"的代码字面量；`modes/` 只存在于安装根（BASE）。
> **[V]** 一个 mod **无法**通过自建 `modes/<SomeName>/` 让引擎加载一个新模式：`MODE`/`MODES` **不在 47 个存储点枚举中**，且已安装的 9 个 mod **无一**含 `modes/` 目录。
> **[U]** `Pompeii.json` 这个注册表文件**如何被定位**（0 次字面量命中）未能定论。但它不能作为"未加载"的证据——见 §1 的 `.json` 反例控制：核心 dat 文件名（`hotkeys.json` 等）同样是 0 次严格引用而必然被加载。最可能：**目录枚举 + 名单文件**驱动。

---

## 4. 问题 2：`use_modes_path_for_mods: true` 改变了什么？

### 4.1 已知事实（[V]）

| 事实 | 值 |
|---|---|
| 出现次数（exe） | 1（rva `0x325c5a8`，`.rdata` 字符串池） |
| 严格 RIP 相对代码引用（ModRM 校验） | **0** |
| 绝对 VA 指针 / 4 字节 RVA 引用 | **0 / 0** |
| 出现次数（全盘 34,835 文件） | 2（= `Pompeii.json` 的两个根视图） |
| 携带它的存储点 | **只有 `DAT`**（`resources\_common\dat`），且该条 **没有 `replace`** |
| 伴生字段 | 其邻域只有 `storage_point_list`(0x325c588)、`replace`(0x325c5a0)；三者相邻，**仅此两个 per-entry 字段名** |

### 4.2 判据：这是**数据驱动**的键，不是硬编码分支（[V]）

严格引用测试（要求 disp32 前一字节 ModRM 的 mod=00、rm=101，即真 RIP 相对寻址的**必要条件**）：

| 字面量 | 严格引用数 | 被拒绝的"伪命中" |
|---|---|---|
| `storage_point_list` | **0** | 1（若只看 disp32 值会误判为命中） |
| `replace` | **0** | 0 |
| `use_modes_path_for_mods` | **0** | 0 |
| `morematerials` / `materials` | 0 / 0 | 0 / 0 |
| `linkedUnits.json` / `futuravailableunits.json` / `paphosfutureavailableunits.json` | 0 / 0 / 0 | 0 |
| **对照：`Pompeii`** | **4** | 1 |
| **对照：`Philadelphia` / `Paphos` / `Paris` / `Providence`** | **4 / 4 / 4 / 4** | 0 |
| **对照：`modes\Pompeii\`** | **1** | 0 |
| **对照：`pompeii-strings`** | **1** | 0 |
| **对照：`UNIQUE_TEMP_FOLDER`** | **1** | 0 |
| `mod-status.json` / `info.json` | 0 / 0 | 0 |

→ **方法不是瞎的**（同池的 `ScreenTechTree` 2、`DialogIngameMenu` 2、`MenuPanel` 2、`unitcategories.json` 2、`ScreenMultiplayerMatchmaking` 16 都有引用；寄存器名/REPLAY 格式串也都有）。而 **`storage_point_list` / `replace` / `use_modes_path_for_mods` 三者精确为 0**。
→ 说明这三个键**由通用字符串键 JSON 查表消费**（或由 exe 之外的消费者处理），**语义无法从引用分析读出**。

**伪命中率量化**（证明只看 disp32 值会严重高估）：对内容模式名区块 `0x31f7460–0x31f7520`，原始 disp32 落点 204 个，其中 **恰好落在字符串起始 174 个**、**落在字符串中间/填充 30 个（14.7% 纯巧合）**。因此上文一律采用 ModRM 校验后的严格计数。

### 4.3 已排除的解释（[V] 排除）

1. ~~"`replace=false` 所以 mod 不能覆盖 DAT"~~ —— **排除**：实地证据显示已装 mod 确实覆盖了 DAT：`297820_…` 提供 `resources\_common\dat\{civilizations.json, empires2_x2_p1.dat}`；`423821_…` 提供 `empires2_x2_p1.dat`；`550749_…` 提供 `empires2_x2_p1.dat, linkedTechs.json`。**[V]**
2. ~~"`replace` 是控制同名覆盖的开关"~~ —— **排除**：同名覆盖 **418/420 发生在 `replace` 缺省（false）的存储点上**；12 个 `replace=true` 的存储点合计只贡献 2 个同名文件。见 §5.3。
3. ~~"该标志控制是否允许 mod 修改 DAT"~~ —— 与事实 1 矛盾；且 DAT 无 `replace` 却仍被 mod 覆盖。

### 4.4 倾向性结论（[I] + [U]）

> **[I] 最强解释**：`use_modes_path_for_mods` 改变的是 **mod 侧 DAT 文件的查找根**——当 `DAT` 存储点被激活模式覆盖时，mod 提供的 dat 不再只按 `MODSROOT/LOCALMODS/SUBSCRIBEDMODS` 镜像路径解析，而**同时/优先按当前模式的路径（`modes\<Mode>\<path>`）解析**。即"让 mod 也能落到模式路径下"。
> **[U] 未定论**：无法从二进制证明。**该字段是纯数据驱动的键**（0 引用），其语义由消费 `Pompeii.json` 的代码决定，而该消费点未能在本 exe 中定位（且本机为破解版，不排除该代码段被改动）。**不要基于此字段做逆向断言。**

---

## 5. 问题 3：`modes/Pompeii/` 逐存储点量化对比

### 5.1 权威对比表（[V]，双侧重新实测大小；同名文件用 SHA-256 判定）

格式：`主树 文件数|字节 → Pompeii 文件数|字节 ; Pompeii独有 / 完全相同 / 同名不同 / 仅主树`

| 存储点 | `replace` | path | 主树 | Pompeii | 独有/相同/不同/仅主树 |
|---|---|---|---|---|---|
| SP_SAVEGAMES | true | savegame | 0\|0 | 0\|0 | 0/0/0/0 |
| MP_SAVEGAMES | true | savegame/multi | 0\|0 | 0\|0 | 0/0/0/0 |
| SCENARIOS | true | resources/_common/scenario | 0\|0 | 0\|0 | 0/0/0/0 |
| CAMPAIGNS | true | resources/_common/campaign | 156\|53,637,216 | 21\|2,912,975 | **21**/0/0/156 |
| AI | true | resources/_common/ai | 55\|5,325,646 | 36\|1,053,073 | **36**/0/0/55 |
| **DAT** | 缺省 | resources/_common/dat | 106\|21,211,973 | 33\|5,606,631 | 15/0/**18**/88 |
| DRS | 缺省 | resources/_common/drs | 16,329\|38,581,975,555 | 2,118\|2,477,850,641 | 2,031/1/**86**/16,242 |
| SPRITES | 缺省 | resources/_common/drs/graphics | 15,559\|38,500,804,322 | 2,082\|2,477,003,524 | 2,002/0/**80**/15,479 |
| RANDOM_MAPS | true | resources/_common/random-map-scripts | 0\|0 | 0\|0 | 0/0/0/0 |
| COMMON_STRINGS | 缺省 | resources/_common/strings | 1\|6,735 | 1\|19 | 0/0/**1**/0 |
| STRINGS | 缺省 | resources/<locale>/strings | 0\|0 | 0\|0 | 0/0/0/0 |
| ACHIEVEMENTS | true | resources/_common/achievements | 2\|52,872 | 2\|5,127 | 0/0/**2**/0 |
| CAMPAIGN_MOVIES | true | resources/<locale>/campaign/movies | 0\|0 | 0\|0 | 0/0/0/0 |
| CAMPAIGN_SOUNDS | true | resources/<locale>/campaign/sounds | 0\|0 | 0\|0 | 0/0/0/0 |
| SCENARIO_SOUNDS | true | resources/<locale>/scenario/sounds | 0\|0 | 0\|0 | 0/0/0/0 |
| **WIDGETUI** | 缺省 | widgetui | 7,975\|3,994,185,738 | 988\|636,647,550 | 799/0/**189**/7,786 |
| WPFG | 缺省 | resources/_common/wpfg | 3,039\|1,264,036,257 | 104\|32,410,345 | 79/0/**25**/3,014 |
| PALETTES | 缺省 | resources/_common/palettes | 80\|434,449 | 7\|98,195 | 6/0/**1**/79 |
| TERRAIN | 缺省 | resources/_common/terrain | 158\|236,069,154 | 17\|51,749,709 | 0/0/**17**/141 |
| PARTICLES | 缺省 | resources/_common/particles | 451\|312,079,974 | 6\|21,095,662 | **6**/0/0/451 |
| WWISE_EXTERNALS | 缺省 | resources/_common/drs/sounds | 0\|0 | 0\|0 | 0/0/0/0 |
| AUDIO_MUSIC | 缺省 | resources/_common/sound/music | 0\|0 | 0\|0 | 0/0/0/0 |
| AUDIO_SFX | 缺省 | resources/_common/sound/stream | 0\|0 | 0\|0 | 0/0/0/0 |
| AUDIO_AMBIENT | 缺省 | resources/_common/sound/terrain | 0\|0 | 0\|0 | 0/0/0/0 |
| AUDIO_TAUNTS | 缺省 | resources/<locale>/sound/taunt | 0\|0 | 0\|0 | 0/0/0/0 |
| TESTHARNESS_REG_SAVES | true | testharness/regressionsaves | 0\|0 | 0\|0 | 0/0/0/0 |
| PERFORMANCE_TEST_GAMES | true | resources/_common/performance | 3\|2,983,997 | 0\|0 | 0/0/0/3 |
| XS | 缺省 | resources/_common/xs | 8\|126,847 | 0\|0 | 0/0/0/8 |

**覆盖度自查**：`modes/Pompeii` 的 3,351 个文件中，**未被这 28 条存储点 + 注册表自身覆盖的只有 1 个文件：`Pompeii.json`(3,205 B)**。→ 该模式树**完全由自己的存储点注册表解释**。[V]

### 5.2 `widgetui/`（最大 UI 增量）

- Pompeii 独有 **799** = 449 `.png` + 349 `.dds` + 1 `.json`
- 同名不同 **189** = **DIFF_SIZE 188**（177 `.png` + 5 `.json` + 4 `.dds` + 2 `.ps1`）+ **DIFF_CONTENT 1**（`.dds`，等大小不同哈希）
- 仅主树 7,786 = 5,800 `.png` + 1,650 `.dds` + 206 `.jpg` + 128 `.json` + 2 `.ps1`
- 最大的独有文件：`widgetui/textures/atlas/{HD,UHD}/campaignicons_p.dds` 各 26,112,148 B；`map_aoe.png` 13,257,769；`map_pompeii.png` 9,363,133；`{HD,UHD}/ingametechs_p.dds` 6,553,7xx；`campaign/pcam1/sargon.dds`、`pcam2/pyrrhus.dds`、`pcam3/trajan.dds` 及各自 `_background.dds` 各 6,125,888；`campaign/aoecam{1..4}/*.dds` 各 5,529,728。
- 最大的同名差异（Pompeii → 主树）：`atlas/HD/CivAsia.dds` 4,309,120→4,718,740；`atlas/UHD/CivGreek.dds` 4,309,140→4,718,740；`ingame/panels/GREEK/command-panel_collapsed.png` 300,358→593,469；`GREEK/topbar.png` 69,511→294,448；**`widgetui/campaignselection.json` 127,213→306,128**；**`widgetui/techtreepreviewpanel.json` 100,944→207,261**；**`widgetui/icons.json` 18,107→75,114**。
- **`widgetui/morematerials.json`：主树不存在（0 文件），Pompeii 990,932 B。** 且 `morematerials` 这个字面量**只在 `widgetui\build_atlas.ps1` 里被提到**（各 6 次），**没有任何游戏 JSON 引用它**。[V]

### 5.3 `replace` 与"同名覆盖"的相关性（**重要**，[V]）

| 组 | 存储点数 | Pompeii 文件 | 同名文件 | 独有文件 |
|---|---|---|---|---|
| `replace=true` | 12 | 59 | **2** | 57 |
| `replace` 缺省（false） | 16 | 5,356 | **418** | 4,938 |

→ **[I]** `replace` **不是**同名覆盖的开关。语义更可能是：`true` = 该存储点被模式目录**整体接管**（子目录级替换，几乎不与 base 发生同名交集）；缺省/false = 模式目录**叠加**在 base 之上，允许同名逐文件覆盖。Pompeii **刻意没在它要覆盖内容的存储点上设 `replace`**。

### 5.4 `resources/_common/drs/graphics/`（美术）

- Pompeii 独有 **2,002** 个 `.sld`；同名不同 **80** 个 `.sld`（**全部变小**，如 `n_tree_rainforest_x2.sld` 1,480,128 vs 2,493,184；`n_tree_birch_x2.sld` 1,242,932 vs 2,076,648；`n_tree_oak_x2.sld` 995,220 vs 1,644,080）。
- 最大的独有 `.sld` 是**古代兵种/建筑全套**：`u_all_trade_cart_deathA_x2.sld` 27,862,028；`b_bab_wonder_destruction_x2.sld` 23,583,108；`b_gre_wonder_destruction_x2.sld` 23,193,000；`b_rom_wonder_destruction_x2.sld` 22,024,924；`u_all_juggernaut_walkA_x2.sld` 15,796,860；`u_all_{heavy_,}catapult_attackA_x2.sld` 14,858,940 / 14,436,432 等。
- → [I] Pompeii **新增了一整套古代纪元单位/建筑精灵集，并裁剪了树木美术**。

### 5.5 `resources/_common/dat/`

- `empires2_x2_p1.dat`：主树 **12,023,754 B** sha256 前缀 `4aa2f0a719e88e5f1502517e…` vs Pompeii **2,573,146 B** sha256 前缀 `fe4d566b98b0e40b05af749f…` → **确为两个不同文件**（非截断关系）。[V]
- Pompeii 独有 15：`CivTechTrees/{ASSYRIANS,BABYLONIANS,CARTHAGIANS,CHOSON,EGYPTIANS,GREEKS,HITTITES,LACVIET,MINOANS,PALMYRANS,PHOENICIANS,SHANG,SUMERIANS,YAMATO}.json`（各 ≈53.4 KB）+ `civTechTrees.json` 1,671,526。
- 同名不同 18：`civilizations.json` 9,720 vs 58,763；`hotkeys.json` 108,606 vs 490,546；`maps.json` 18,580 vs 128,394；`dropsites.json` 10,066 vs 31,606；`eras.json` 754 vs 8,978；`futuravailableunits.json` 277,960 vs 1,331,147；`unitlines.json` 3,261 vs 20,974；`linkedTechs.json` 235 vs 3,947；`sharedbuildings.json` 22 vs 2,956；`sounds.json` 5,048 vs 4,881；`AIConsts.json` 331 vs 334；`CivTechTrees/{MACEDONIANS,PERSIANS,ROMANS}.json`；`buttons.json` 1,738 vs 3,160；`selection_group_def.json` 17,510 vs 23,890；`unitcategories.json` 195 vs 738。
- 仅主树 88：62 个 AoE2 文明科技树 JSON（ACHAEMENIDS…WU）+ `BlkEdge.Dat`、`loQMaps.dat`、`STemplet.dat`、`TileEdge.Dat`、`blendomatic_x1.dat`、`lightMaps.dat`、`view_icm.dat`、`FilterMaps.dat`、`PatternMasks.dat`、`InterfaceData.pbin`、`UiColors.txt`、`adapterblacklist.json`、`airesourcetypes.json`、`linkedUnits.json`、`objreplacement.json`、`paphos_campaign.json`、`peru_campaign.json`、`providence_campaign.json` 等。

### 5.6 `resources/{17 语言}/strings/`

Pompeii 为 **17 个语言** 各带 `resources/<L>/strings/key-value/key-value-pompeii-strings-utf8.txt`：`br` 289,290 / `de` 309,208 / `en` 261,754 / `es` 296,627 / `fr` 316,619 / `hi` 640,265 / `it` 299,614 / `jp` 329,397 / `ko` 317,065 / `ms` 291,483 / `mx` 295,048 / `pl` 290,967 / `ru` 447,724 / `tr` 289,900 / `tw` 258,589 / `vi` 364,995 / `zh` 259,590。**[V]**
另有 `resources/_common/strings/key-value/non-localized-key-value-strings-utf8.txt`：主树 6,735 B vs Pompeii **19 B**（同名不同，Pompeii 侧几乎清空）。**[V]**

### 5.7 统计口径

- `STRINGS` 存储点 path 是 `resources\<locale>\strings`（**`<locale>` 是占位符，不是真实目录**），故按字面 path 统计为 0；实际 17 语言文件已在上表按 §5.6 列出。
- `SP_SAVEGAMES / MP_SAVEGAMES / SCENARIOS / RANDOM_MAPS / WWISE_EXTERNALS / AUDIO_* / TESTHARNESS_REG_SAVES / CAMPAIGN_*` 在两侧**均为空**（运行时目录或本机无内容）。

---

## 6. 问题 4：`Pompeii` 是不是"开发者在游戏内做的大型 mod"？

### 6.1 与普通 mod **同源**的部分（[V]）

| 原语 | 普通 mod（实地验证） | `modes/Pompeii` |
|---|---|---|
| 文件夹顶层镜像游戏根路径（不额外包 `resources/`） | ✅ `info.json`+`resources`/`widgetui` | ✅ 同样的镜像布局 |
| 同名文件覆盖 base | ✅ 3 个 mod 覆盖 `empires2_x2_p1.dat` 等 | ✅ 418 个同名文件 |
| 无中心清单，按文件解析 | ✅ 无清单，仅 `info.json`+`mod-status.json` | ✅ 无清单，仅 `Pompeii.json` |
| `info.json` 存在 | ✅ 9/9 | ❌ **无** `info.json` |

### 6.2 `Pompeii` **私有**的部分（mod 拿不到）（[V]）

1. **声明通道**：`Pompeii.json` 存储点注册表（`storage_point_list` + 28 条 + `replace`/`use_modes_path_for_mods`）。**全盘唯一**，无任何 mod 有等价物。
2. **编译期身份**：`Pompeii` 是 exe 内 DLC/内容模式名表的一个条目（§3.3）。
3. **硬编码路径前缀**：`modes\Pompeii\` 是 `filesystem.cpp` 中的**字面量前缀**（位于临时/虚拟路径区段，紧邻 `UNIQUE_TEMP_FOLDER`/`AOE2DE_Temp_`/`mods`/`subscribed`/`preview`），**而不是**"枚举 `modes/` 得到的目录名"。
4. **专用本地化表**：`pompeii-strings` 是 `LocalizationManager` 的硬编码字符串表名（配合 `resources\%s\strings\%s`）。
5. **专用音频库**：`Pompeii_Campaign.bnk / Pompeii_Music.bnk / Pompeii_SFX.bnk / Pompeii_Campaign_VO.bnk / Pompeii_Scenario_VO.bnk / Pompeii_Taunts.bnk`，与 `Base_*`、`Palermo_*`、`Paphos_*`、`Providence_*` 等并列，各 1 处 `LEA rax,[rip+disp32]` 装入栈结构。
6. **`modes\Pompeii\` 初始化的性质**：承载它的函数 rva `0xbdb50-0xbdc93`（323 B）**同时是 exe 内 639 条"静态初始化/全局构造"函数指针表（rva `0x319c008` 起）的第 117 项**，其唯一字符串引用就是 `modes\Pompeii\`，体内 3 次调用字符串构造器 `0xa1a660` 并把结果存入 `.data` 全局。→ **它是把该路径注册进全局的静态初始化器**，不是"扫描目录"的函数。[V]

### 6.3 结论（问题 4）

> **`Pompeii` 不是"开发者用 mod 工具做的大型 mod"，而是"第一方内容模式/DLC 变体"**：它**复用**了与普通 mod 完全相同的三件套覆盖原语，但通过一条 **mod 无法触及的私有声明通道**（编译期内容模式表 + 硬编码 `modes\Pompeii\` 前缀 + 自带的存储点注册表 + 专用本地化/音频库）挂载。[V] + [I]

---

## 7. 问题 5：对做模组工具的后果（明确倾向）

### 倾向性结论

> **"整套游戏变体"（换一整套 dat + UI + 美术）对第三方 mod 而言，必须靠"镜像 47 个存储点"实现；"丢一个 `modes/<Name>/` 进 mod 让引擎加载"这条路关闭。**

### 证据强度：**强（3 项独立证据）**

1. `MODE`/`MODES` **不在 47 个存储点枚举中**，也不在根/来源枚举（`COUNT NONE NOTFOUND TEMP BASE APPATA USER MODSROOT LOCALMODS SUBSCRIBEDMODS DLC CLOUD`）中 → mod 的覆盖解析**没有可以指向 `modes/` 的存储点**。[V]
2. mode 集合是 **exe 编译期固定的** DLC/内容模式名表；不存在"枚举 `modes/` 注册新 mode"的代码字面量；`modes\Pompeii\` 是硬编码前缀。[V]
3. **实地反证**：9 个已安装 mod，**0 个**含 `modes/` 目录；**全盘**只有安装根 1 个 `modes/` 目录（唯一子项 `Pompeii`），用户数据下 0 个。[V]

### 工具实现建议

- **可行交付形态**：普通 mod 文件夹（`info.json` + 镜像存储点子路径），逐存储点覆盖 —— 这正是现有 9 个 mod 的做法（如 `resources\_common\dat\empires2_x2_p1.dat`、`widgetui\`）。
- **不可行**：让 mod 自带 `modes/<Name>/` 来注册新模式。
- **唯一的灰色地带（[U]）**：`DAT` 存储点带 `use_modes_path_for_mods: true`，**可能**允许 mod 的 dat 文件按 `modes\<Mode>\…` 路径参与解析（§4.4）。若成立，则"换一整套 dat"在**激活模式存在时**可能有第二条通路；但**仅限 DAT 一个存储点**，且未证实。**不要把它当作通用机制来实现工具。**

---

## 8. 未解项（明确列出，不做编造）

1. **[U] `Pompeii.json` 如何被定位与解析**：`Pompeii.json` 0 次字面量命中；`storage_point_list`/`replace`/`use_modes_path_for_mods` 三者**严格代码引用均为 0**。候选解释（未区分）：(a) 目录枚举 `modes\` + 名单；(b) 由 exe 之外的消费者（启动器/构建脚本/打包工具）读取后注入；(c) 该段代码在本机破解版中被改动。**注意**：`.json` 文件名普遍 0 引用（核心 dat 文件亦然），故此项**不能**被解读为"文件未使用"。
2. **[U] `use_modes_path_for_mods` 的确切语义**：见 §4.4；只能给出 [I] 级最强解释，不能给出 [V] 级定论。
3. **[U] `replace` 的确切语义**：只能由 §5.3 的相关性给出 [I] 级解释（整体接管 vs 叠加），无法从二进制读出。
4. **[U] 47 个存储点中 19 个未被 `Pompeii.json` 使用的点**（`LOGS CREDITS FONTS MOVIES SPRITES_LOW SLP CURSORS AUDIO_CIVTHEME TEXTURES SHADERS PACKAGES PROFILE WWISE TESTHARNESS TESTHARNESS_SCRIPTS TESTHARNESS_REPORTS TESTHARNESS_XS TELEMETRY SCENARIO_EDITOR`）在模式化时如何处理：本机无 DLC 内容可观测，未解。
5. **[U] 破解版影响面**：`Juij_Steam.dll` / `version.dll` / `winmm.dll` 的注入是否改写了 exe 的模式装载路径，无法在不运行游戏的前提下判定。
6. **[U] 多模式共存**：名表含 5 个内容模式名 + 11 个 DLC 标签，但磁盘上只有 `Pompeii` 一个 `modes/` 子目录；其余模式的文件来自何处（DLC 包 / `_packages` / 云）未解。

---

## 9. 自我更正章节

1. **【已更正】"未覆盖文件"误报**：早期脚本未展开 `path` 中的 `<locale>` 占位符，错误报告有 18 个文件不属于任何存储点（17 个本地化 `key-value-pompeii-strings-utf8.txt` + `Pompeii.json`）。展开为 17 个语言代码（`br de en es fr it hi jp ko ms mx pl ru tr tw vi zh`）后，**真正未覆盖的只有 1 个文件：`Pompeii.json`(3,205 B)**。
2. **【已更正】fileoff ↔ VA 换算错误**：早期把 `.rdata` 的 `fileoff = VA − 0x2000` 与 `.text` 的 `fileoff = VA − 0xC00` 混用过，导致 `storage_point_list` 的代码命中位置算错，一度得出"1 处代码引用"的结论。更正为逐节 `fileoff = rawptr + (RVA − section.rva)` 后**推翻**该结论。
3. **【方法学更正 — 最重要】"0 引用 ⇒ 未被使用"是错的**。`storage_point_list` 一度被认为有 1 处代码引用（rva `0x1ee15ba`），经 ModRM 校验后判定该处**不是合法 RIP 相对寻址指令**（该区域字节不构成指令），故**撤销**。但更重要的是反向教训：核心 dat 文件名（`hotkeys.json`、`maps.json`、`civilizations.json`、`dropsites.json`、`unitlines.json`）**严格引用也是 0** 却必然被加载 → **本报告的"0 引用"结论一律只用于说明"名字不是代码字面量"，绝不用于断言"未被使用"。** §1 与 §8.1 已按此限定。
4. **【已更正】熵不能证明是数据**：`.text` 平均熵 7.2179 b/B（12,693 窗口，7,630 个 >7.5），故不能靠熵判定某区域是数据；`storage_point_list` 的伪引用点已改由 ModRM 校验处理。
5. **【已更正】误把回归测试工具当模式加载器**：rva `0x334f510` 簇（`game\modes\Pompeii\resources\`、`Checking Pompeii language:`、`key-value-pompeii-strings-utf8`）属于 `Source\Tools\Regression\RegressionLocale.cpp`/`RegressionStringList.cpp` 的**回归测试工具**，**不是**游戏模式加载器，已从证据链中剔除。
6. **【已更正】存储点枚举计数 47 而非 46**：任务书称"完整 46 个"。逐字节解析 rva `0x31f8cc4`–`0x31f8f36`（`p32_enum2.py`）得 **47** 个名字；任务书自己给出的名单数一遍也是 47 个。未使用集为 **19** 个（非 18）。`47 − 28 = 19` 自洽。已全文更正。
7. **【方法学更正】NUL 分隔不可直接按单字节切分**：该枚举的成员间用**不等长 NUL 填充**（0–7 字节）对齐到 4/8 字节边界，早期脚本按"单个 `\0`"切分只得 1 个成员（`p30_out.txt` 的错误输出即为证据）。正确方法是提取**最大可打印游程**（`p31`/`p32`）。
8. **【已更正】`widgetui/` 同名差异的扩展名拆分**：早期按各扩展名计数时把 `DIFF_CONTENT` 的 1 个 `.dds` 与 `DIFF_SIZE` 的 4 个 `.dds` 合并，写成"5 个 `.dds`"、且漏掉 2 个 `.ps1`。以 `cmp_filelevel.tsv` 的 8,774 行 widgetui 记录复核（`p34_verify.py`）后更正为：**同名不同 189 = DIFF_SIZE 188（177 `.png` + 5 `.json` + 4 `.dds` + 2 `.ps1`）+ DIFF_CONTENT 1（`.dds`）**。并顺带核对全表：`POMPEII_ONLY 4,995 / BASE_ONLY 43,502 / DIFF_SIZE 408 / DIFF_CONTENT 11`（合计 48,916，与 `.tsv` 行数一致）。
9. **【已更正】`.rdata` 绝对指针表偏移**：`content_modes.json` 首版把 RVA `0x321efc0` 当作文件偏移读取，得到空表。更正为 `fileoff = RVA − 0x2000` → `0x321cfc0`，读出 12 项（`Base, DLC1..DLC3, Pompeii, DLC4, DLCVV, DLC6, DLC7, DLCProvidence, DLCParis, DLCPortland`）。

---

## 10. 附录：落盘产物

| 文件 | 内容 |
|---|---|
| `p01_exe_index.py` … `p33_artifact.py` | 34 个分析脚本（PE/字符串/引用/对比/控制实验/枚举核验） |
| `p13_out.txt` … `p32_out.txt` | 各脚本的完整输出 |
| `inv_base.tsv` / `inv_pompeii.tsv` | 双侧全量文件清单（路径/大小） |
| `inv_topdirs.json` | 顶层目录文件数/字节汇总 |
| `cmp_storagepoints.{json,tsv}` | **28 个存储点的权威对比表** |
| `cmp_filelevel.tsv` | 48,916 行文件级差异记录（分类 + 大小） |
| **`storage_points.json`** | **47 个存储点枚举 + 28 条声明 + 19 未用（机器可读）** |
| **`content_modes.json`** | **内容模式/DLC 名表（`Base,DLC1..DLC3,Pompeii,DLC4,DLCVV,...`）** |
| `exe_sections.json` | PE 节表（rva/vsize/rawptr/rawsize） |
| `exe_needle_hits.json` | 关键字命中位置与上下文 |
| `exe_funcmap.json` | 169,274 条 `.pdata` RUNTIME_FUNCTION |
| `exe_rtti.json` | 5,291 个 RTTI 名 |
| `exe_code_refs.json` / `exe_brute_disp.json` | 引用分析结果 |
| `p24_markers.json` | 全盘标记扫描结果 |
| `pompeii_uncovered.json` | 覆盖度自查（最终仅 `Pompeii.json` 一个文件） |

### 复核入口

- 存储点计数：`p32_enum2.py`（严格解析）/ `p30_out.txt`（**错误示范**：按单 `\0` 切分只得 1 个成员）
- 决定性引用测试：`p27_strict.py`（ModRM 校验）/ `p22_control.py`（同池对照，证明方法不瞎）
- 内容模式名表：`p25_out.txt` / `p29_out.txt`（五个模式名的宿主函数 `0x27e7c0`）
- 逐存储点对比：`cmp_storagepoints.tsv`（28 行）/ `cmp_filelevel.tsv`（48,916 行）
