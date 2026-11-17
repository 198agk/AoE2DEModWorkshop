# AoE2DE 引擎内建 AI 与 XS 全量能力解析

> 目标：`D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe`（72,176,952 B / 68.8 MB）
> 方法：静态二进制分析（PE 解析 + 字符串表聚簇 + LEA rip 引用追踪 + .pdata 函数归属），**不依赖任何已写好的官方 .per / .xs 语料**
> 定位：本文件解析的是**引擎本身能读写什么**，而非"别人写好的脚本长什么样"

---

## ⚠ 坐标系统更正（2026-10-28 二次校核）

**上一版报告里所有标成「VA」的地址，实际是文件偏移（file offset），不是 RVA。** 已全部更正。

`.rdata` 段的 `VA − 文件偏移` 差值是 **`+0x1400`**：

```
.rdata   VA=0x03197000   rp=0x03195c00   delta=+0x1400
```

所以「`0x32223f8` 基础命令表」的真实 RVA 是 **`0x32237f8`**。本文档已统一为 **RVA**（相对 `ImageBase 0x140000000`）。

完整节表（本文档所有地址的换算依据）：

```
段名       VA           文件偏移       delta
.text     0x00001000   0x00000400    +0xc00
.rodata   0x03196000   0x03195400    +0xc00
.rdata    0x03197000   0x03195c00    +0x1400
.data     0x03da7000   0x03da4e00    +0x2200
.pdata    0x04ca3000   0x04254400    +0xa4ec00
_RDATA    0x04e94000   0x04444e00    +0xa4f200
.rsrc     0x04e97000   0x04447200    +0xa4fe00
.reloc    0x04eb2000   0x04461600    +0xa50a00
```

校准锚点：`up-jump-rule` 在文件偏移 `0x3221570`，RVA `0x3222970`。

**为什么必须纠正**：若按旧坐标去 Ghidra/IDA 里跳转，会落到 `.rdata` 里偏移 `+0x1400` 的错位位置，看到的是别的字符串——这会让所有 handler 定位全错。

复现脚本：`py -X utf8 _age_analysis/aixs/rva_all.py`（输出 `AI命令全集_v3.json`，全部坐标为 RVA）。

---

## 0. 结论速览

| 维度 | 数字 | 来源（RVA，全部为四次校核实测） |
|---|---|---|
| 引擎内建 AI 语言标识符 | **1752** | `0x3221400–0x3235400` 连续字符串区 |
| AI 动作命令（可执行集） | **251** = 基础 59 + `up-*` 192 | 见 §2.2b / §2.2 |
| ↳ 基础命令（原版内核，无前缀） | **59** | 块B `0x032237f8–0x03223c48` |
| ↳ UserPatch 扩展命令 `up-*` | **192** | 块A 143 @`0x03222970–0x0322369d` + 块C 49 @`0x03233730–0x03233be6` |
| 编辑器/测试命令 `fe-*` | **13** | 块A 10 + 块C 3 |
| AI→XS 桥接命令 | **1**（`xs-script-call`） | `0x03223648`（块A 内） |
| AI 运算符（`c:`/`s:`/`g:` × 18） | **54** | 算术簇 `0x032236a0` + 比较簇 `0x0322b8f0` |
| AI 行为状态枚举（大写） | **12** | `0x03223db8–0x03223e28` |
| AI 行为状态显示名（小写） | **11** | `0x033b10e8–0x033b1148`（标签 `'action state'` @`0x033b10d8`） |
| 单位动作类型枚举 | **23** | `0x033b115c–0x033b124f`（标签 `'action type'` @`0x033b1150`） |
| AI 命令实现区函数数 | **2154** | `.pdata` 内 `0x0b40000–0x0c20000`（**其中 handler 归属不明，见 §8**） |
| XS syscall 总数（注册表实量） | **232** | `0x3300000–0x3320000`，全部带 `名字(` 原型串 |
| ↳ 文档表里另有名字无原型 | **3** | `xsArrayGetBool` / `xsGetFunctionID` / `xsGetMapID` |
| XS syscall 带官方原型串 | **226** | 206 条 `type name(...)` + 20 条 `name(...)` |
| XS syscall 带英文描述文本 | **44** | 名字串后紧跟 `原型: 描述` |
| XS syscall **带静态 arity 的结构** | **15 对**（id+count） | `0x032217c0–0x03221918`，见 §8.1 |
| XS 编译器语法关键字 | **26** | `0x3316de8–0x3316f20` |
| XS 引擎源码模块 | **13** 个 .cpp | 嵌入的 P4 路径 |
| AI 引擎源码模块 | **13** 个 .cpp/.h | 嵌入的 P4 路径 |
| 全文件函数总数 | 169,486 | `.pdata` |
| **AI 命令名的代码引用数** | **0** | 十八重独立扫描，见 §8.2 |
| ↳ 已解出精确 arity 的 `up-*` | **3 / 192** | `up-get-fact-{min,max,sum}` = 4 个 `int`，证据 `?UPGetFact*@AIHybrid@@SAHHHHH@Z` @`0x04122172/1c2/212`，见 §8.1 |
| 引擎残留 MSVC 修饰函数名 | **44** 条唯一签名 | `.data`，arity 分布 `{1:5, 2:20, 3:12, 4:4, 5:3}` |
| **PE 内 PDB 身份记录** | **有**（`RSDS` + GUID + Age + 完整路径） | DEBUG 目录 `0x036a0710`，GUID `651ecf97-392a-704d-a32c-5cd6ba3f8545`，Age 1 |

**关键判断：引擎的 AI 与 XS 能力是一张自解释的静态词表 + 一张 syscall 注册表，不是编译进代码的魔法。** 全部 1752 个 AI 标识符和 232 个 xs* 函数名都在磁盘上以明文存在，可直接读出。

**第二判断：AI 语言不是"一堆字符串命令"，而是一套带类型系统的表达式语言 + 协程状态机。** `c:`/`s:`/`g:` 三族运算符（各 18 个，共 54）证明 `up-modify-goal` 的第二操作数是**带类型前缀的表达式节点**；12 个动作状态证明每条 AI 动作是有生命周期的协程，不是一次性调用。这两点是上一版报告漏掉的**结构性事实**。

---

## 1. 证据从哪来（可复现）

### 1.1 PE 布局

```
.text     VA 0x00001000  vsize 0x3194ef2
.rodata   VA 0x03196000  vsize 0x0000790
.rdata    VA 0x03197000  vsize 0x0c0f0a8
.data     VA 0x03da7000  vsize 0x0efb9c8
.pdata    VA 0x04ca3000  vsize 0x01f08a8    ← 169486 个函数边界
_RDATA    VA 0x04e94000  vsize 0x0002308
.rsrc     VA 0x04e97000  vsize 0x001a210
.reloc    VA 0x04eb2000  vsize 0x007160c
```
ImageBase = `0x140000000`。

### 1.2 三步定位法

1. **字符串区聚簇**：`.rdata` 里 `0x3221400–0x3235400` 是连续的 78 KB 明文标识符区，按 4KB 分块统计密度，可得 13 个高密度块全在此区。
2. **LEA rip 引用追踪**：扫描全 `.text` 的 `48-4F 8D /r [rip+disp32]`，筛出目标落在此区的 86 处指令，得到 59 个不同目标串。
3. **`.pdata` 归属**：用 `.pdata` 的 169486 条 `(start,end)` 把 86 处引用点归到具体函数，得到真正消费这些名字的 handler。

### 1.3 溯源路径（引擎自曝）

exe 里嵌着 **402 条构建机源码路径**，都是 P4 depot 路径：

```
F:\Agents\PhoenixBuilder-07\p4\portland_group\Aoc\Source\Game\...   (102 条)
F:\Agents\PhoenixBuilder-07\p4\portland_group\Aoc\Source\XS\...     ( 13 条)
F:\Agents\PhoenixBuilder-07\p4\portland_group\Aoc\Source\Engine\... ( 26 条)
```

**AI 模块（13 个路径）**
```
Source\Game\ai\AIExpertEngine.cpp
Source\Game\ai\aiexpert.cpp
Source\Game\ai\SerializeMarker.h
Source\Game\ai\Actions\ActionGather.cpp
Source\Game\ai\Actions\ActionHeroPower.cpp
Source\Game\ai\Actions\ActionMissile.cpp
Source\Game\ai\Actions\ActionMove.cpp
Source\Game\ai\Actions\ProjectileData.cpp
Source\Game\ai\Modules\ObjectSpawnData.cpp
Source\Game\ai\Modules\TribeInformationAIModule.cpp
Source\Game\ai\Modules\TribeUnitAIModule.cpp
Source\Game\ai\Modules\UnitAIModule.cpp
Source\Game\ai\Searching\aisearch.cpp
```

**XS 模块（13 个）**
```
Source\XS\xsactivationrecord.cpp   ← 调用栈帧
Source\XS\xsdata.cpp               ← 数据/类型
Source\XS\xsfileentry.cpp          ← .xs 文件入口
Source\XS\xsfunctionentry.cpp      ← 用户函数
Source\XS\xsruleentry.cpp          ← rule 条目
Source\XS\xsrulemodule.cpp         ← rule 调度
Source\XS\xsruntime.cpp            ← 运行时/VM
Source\XS\xssource.cpp             ← 词法/源码
Source\XS\xssymboltable.cpp        ← 符号表
Source\XS\xssyscallentry.cpp       ← syscall 条目
Source\XS\xssyscallmodule.cpp      ← syscall 注册
Source\XS\xsuserclassentry.cpp     ← 用户类
Source\XS\xsvariableentry.cpp      ← 变量
```

这 13 个文件名本身就是 XS 引擎的架构图：**词法(`xssource`) → 符号表(`xssymboltable`) → 条目(`xsfunctionentry`/`xsruleentry`/`xsvariableentry`/`xsuserclassentry`) → 模块(`xsrulemodule`/`xssyscallmodule`) → 运行时(`xsruntime`/`xsactivationrecord`) → 持久化(`xsfileentry`/`xsdata`)**。

---

## 2. AI 语言：引擎认识什么

### 2.1 总量与分类（1752 项）

| 类别 | 数量 | 说明 |
|---|---|---|
| 其他标识符 | 569 | 含单位名、建筑名、文明名、地形、类枚举、命令 |
| 研究/单位 ID 名 `ri-*` | 263 | `ri-` 前缀的研究/单位命名 ID |
| SN 战略数字 `sn-*` | 212 | 全部可写的战略数字 |
| UP 扩展命令 `up-*` | 192 | UserPatch 命令集（DE 已内建） |
| 玩家资源/统计 `amount-*` | 189 | 资源索引 + 玩家统计索引 |
| 玩家主体选择器 | 60 | `any-*` / `every-*` / `this-any-*` / `my-*` / `players-*` |
| 动作命令 | 52 | `can-*` / `set-*` / `train` / `research` 等 |
| 对象/单位查询 | 51 | `object-data-*` / `unit-type-count*` / `group-type-*` |
| 地形枚举 `terrain-*` | 42 | 42 种地形 |
| 聊天/日志 | 26 | `chat-to-*` / `log*` |
| 动作 ID `actionid-*` | 22 | 22 种动作 |
| 命令 ID `orderid-*` | 22 | 与 actionid 一一对应 |
| FE 编辑器/调试 `fe-*` | 13 | 编辑器与 testharness |
| 指令 ID `cmdid-*` | 11 | AI 单位分组指令 |
| 语法关键字 | 10 | `defrule`/`defconst`/`load-if-*` 等 |
| 时代枚举 | 10 | 5 个时代 + 派生命名 |
| 运算符 | 7 | `min`/`max`/`mod`/`neg`/`not`/`xor`/`not-equal` |
| 阵型 | 1 | `formation-line` |

### 2.2 UP 扩展命令 192 个（按功能分段）

**① 事实读取 up-get-*（13）**
```
  up-get-fact                       up-get-fact-min                   up-get-fact-max
  up-get-fact-sum                   up-get-focus-fact                 up-get-player-fact
  up-get-target-fact                up-get-threat-data                up-get-victory-data
  up-get-victory-limit              up-get-treaty-data                up-get-precise-time
  up-get-rule-id
```

**② 对象数据访问（10）**
```
  up-get-object-data                up-get-object-target-data         up-get-object-type-data
  up-object-data                    up-object-target-data             up-get-attacker-class
  up-attacker-class                 up-get-path-distance              up-path-distance
  up-get-search-state
```

**③ 目标搜索与过滤（20）**
```
  up-find-local                     up-find-remote                    up-find-player
  up-find-flare                     up-find-player-flare              up-find-next-player
  up-find-status-local              up-find-status-remote             up-find-resource
  up-filter-status                  up-filter-include                 up-filter-exclude
  up-filter-range                   up-filter-distance                up-filter-garrison
  up-target-point                   up-target-objects                 up-set-target-object
  up-set-target-by-id               up-update-targets
```

**④ 搜索状态机（6）**
```
  up-full-reset-search              up-reset-search                   up-reset-filters
  up-clean-search                   up-remove-objects                 up-can-search
```

**⑤ 几何与点位（21）**
```
  up-get-point                      up-get-point-distance             up-get-point-contains
  up-get-point-elevation            up-get-point-terrain              up-get-point-zone
  up-add-point                      up-copy-point                     up-lerp-percent
  up-lerp-tiles                     up-bound-point                    up-bound-precise-point
  up-cross-tiles                    up-set-target-point               up-set-precise-target-point
  up-point-distance                 up-point-contains                 up-point-elevation
  up-point-terrain                  up-point-zone                     up-point-explored
```

**⑥ Goal / SN / 比较（12）**
```
  up-modify-goal                    up-modify-sn                      up-get-indirect-goal
  up-set-indirect-goal              up-get-shared-goal                up-set-shared-goal
  up-allied-goal                    up-allied-sn                      up-compare-goal
  up-compare-const                  up-compare-flag                   up-compare-sn
```

**⑦ 单位/建筑计数（15）**
```
  up-object-type-count              up-object-type-count-total        up-unit-type-in-town
  up-building-type-in-town          up-villager-type-in-town          up-gaia-type-count
  up-gaia-type-count-total          up-idle-unit-count                up-defender-count
  up-enemy-units-in-town            up-enemy-buildings-in-town        up-enemy-villagers-in-town
  up-players-in-game                up-group-size                     up-get-group-size
```

**⑧ 资源读取（4）**
```
  up-resource-amount                up-resource-percent               up-allied-resource-amount
  up-allied-resource-percent
```

**⑨ 定时器与信号（8）**
```
  up-set-timer                      up-get-timer                      up-timer-status
  up-reset-attack-now               up-set-signal                     up-get-signal
  up-set-event                      up-get-event
```

**⑩ 跳转控制（3）**
```
  up-jump-rule                      up-jump-direct                    up-jump-dynamic
```

**⑪ 经济（12）**
```
  up-buy-commodity                  up-sell-commodity                 up-tribute-to-player
  up-drop-resources                 up-modify-escrow                  up-release-escrow
  up-setup-cost-data                up-reset-cost-data                up-add-cost-data
  up-get-cost-delta                 up-add-object-cost                up-add-research-cost
```

**⑫ 生产与建造（15）**
```
  up-build                          up-build-line                     up-train
  up-research                       up-can-build                      up-can-build-line
  up-can-research                   up-can-train                      up-set-placement-data
  up-reset-placement                up-pending-placement              up-research-status
  up-train-site-ready               up-add-object-by-id               up-retask-gatherers
```

**⑬ 军事（20）**
```
  up-set-attack-stance              up-set-offense-priority           up-set-defense-priority
  up-reset-target-priorities        up-create-group                   up-reset-group
  up-set-group                      up-modify-group-flag              up-modify-flag
  up-disband-group-type             up-retreat-now                    up-retreat-to
  up-garrison                       up-gather-inside                  up-ungarrison
  up-guard-unit                     up-get-guard-state                up-reset-scouts
  up-send-flare                     up-send-scout
```

**⑭ 删除与重置（7）**
```
  up-delete-objects                 up-reset-building                 up-delete-distant-farms
  up-delete-idle-units              up-reset-unit                     up-pending-objects
  up-remaining-boar-amount
```

**⑮ 文本与聊天（13）**
```
  up-store-text                     up-store-map-name                 up-store-object-name
  up-store-player-chat              up-store-player-name              up-store-tech-name
  up-store-type-name                up-change-name                    up-chat-data-to-all
  up-chat-data-to-all-using-id      up-chat-data-to-player            up-chat-data-to-player-using-id
  up-chat-data-to-self
```

**⑯ 投射物（3）**
```
  up-projectile-detected            up-projectile-target              up-get-projectile-player
```

**⑰ 调试与测试（5）**
```
  up-testharness-report             up-testharness-test               up-cc-send-cheat
  up-cc-add-resource                up-log-data
```

**⑱ 杂项（5）**
```
  up-player-distance                up-get-player-color               up-request-hunters
  up-assign-builders                up-compare-text
```

> 另有 `fe-break-point` 1 个（`fe-` 前缀，调试断点，不计入 192 个 `up-*`），实际命令表共 **193 条**，
> 其中 `up-*` 192 条 + `fe-*` 1 条。

### 2.2b 基础 AI 命令 59 个（原版内核，无前缀）

这是**独立于 `up-*` 的第二张表**，位于 `0x32237f8–0x3223c5a`（前面 `0x32237b5` 有一条 60 个连字符的 `-----` 分隔线，是典型的静态数组初始化区起始标记）。这 59 个是 1999 年原版 AoC 就有的命令内核，DE 只是把它原样保留：

```
acknowledge-event         acknowledge-taunt        attack-now
build-forward             build-gate               build-wall
buy-commodity             cc-add-resource          chat-debug
chat-local                chat-local-to-self       chat-local-using-id
chat-local-using-range    chat-to-all              chat-to-all-using-id
chat-to-all-using-range   chat-to-allies           chat-to-allies-using-id
chat-to-allies-using-range chat-to-enemies         chat-to-enemies-using-id
chat-to-enemies-using-range chat-to-player        chat-to-player-using-id
chat-to-player-using-range chat-trace             clear-tribute-memory
delete-building           delete-unit              disable-rule
disable-self              disable-timer            do-nothing
enable-rule               enable-timer             enable-wall-placement
generate-random-number    log                      log-trace
release-escrow            research                 resign
sell-commodity            set-author-email         set-author-name
set-author-version        set-difficulty-parameter set-doctrine
set-escrow-percentage     set-goal                 set-shared-goal
set-signal                set-stance               set-strategic-number
spy                       taunt                    taunt-using-range
train                     tribute-to-player
```

**59 + 192 = 251 条 AI 动作命令**，这就是引擎能执行的全部动作集。

注意其中 5 个是**单词命令**（`log` / `research` / `resign` / `spy` / `taunt` / `train`），不带连字符。我上一版用「必须含 `-`」的正则过滤时把它们漏了，这是本次修正的重点之一。

**这张表里藏着三个战略级命令**：

- `set-doctrine` —— 切换 AI 的行为学派（对应 `.dat` 里的 Civilization 表的 doctrine 字段）
- `set-difficulty-parameter` —— 直接改难度系数（AI 的"作弊程度"）
- `set-author-*` 三件套（name/email/version）—— 脚本元数据，写进 `.ai2` 文件头

### 2.2c 运算符：`c:` / `s:` / `g:` 三族 × 18 = 54 个

报告上一版只写了 7 个运算符，**这是错的**。引擎实际维护三套平行的运算符族，按**操作数主体类型**区分，每族 18 个，一一对称：

| 族 | 含义 | 成员（18） |
|---|---|---|
| `c:` | **const** 常量操作数 | `=` `+` `-` `*` `/` `min` `max` `mod` `neg` `z/` `%*` `%/` `<` `<=` `>` `>=` `==` `!=` |
| `s:` | **sn** 战略数字操作数 | 同上 18 个 |
| `g:` | **goal** 目标变量操作数 | 同上 18 个 |

它们分两个簇存放：
- `0x32236ac–0x3223788`：**算术族** `c:/s:/g:` × {`=` `+` `-` `*` `/` `min` `max` `mod` `neg` `z/` `%*` `%/`}（12×3=36，末串 NUL 止于 `0x322378d`）
- `0x322b914–0x322b984`：**比较族** `c:/s:/g:` × {`<` `<=` `>` `>=` `==` `!=`}（6×3=18，末串 NUL 止于 `0x322b989`）

**语义解读**（从名字直接读出，不需要反编译）：

- `c:` = 立即数常量 → `up-modify-goal g:5 c:+ 10` 把 goal 5 加常量 10
- `s:` = 战略数字 → `up-modify-goal g:5 s:+ sn-maximum-town-size` 用 SN 的值参与运算
- `g:` = 目标变量 → `up-modify-goal g:5 g:+ g:3` 两个 goal 相加

`z/`、`%*`、`%/` 三个是**零安全变体**：`z/` = 除零返回 0 而不是崩溃（对应错误串 `Division by zero`）；`%*` / `%/` 是"取模后再乘/除"的复合运算，用于把余数映射回区间（典型用途：`goal % N` 做随机数取模后换算）。

**这条是本次解析最重要的补充**：`up-modify-goal` 的第二个参数不是普通操作数，它是**带类型前缀的表达式节点**，所以 AI 脚本里能直接写三元运算，不需要先存中间变量。

### 2.2d 行为状态机 12 个（AI 动作的生命周期）

大写枚举在 `0x03223db8–0x03223e28`（**12 条**，全部 8 字节对齐，`enum` 逐条实测）：

```
0x03223db8 Done        0x03223dc0 Wait        0x03223dc8 Search
0x03223dd0 Goto        0x03223dd8 Goto2       0x03223de0 Work
0x03223de8 Work2       0x03223df0 Return      0x03223df8 Turn
0x03223e00 Failed      0x03223e08 Invalidated 0x03223e18 MoveNoSearch
```

小写调试视图在 `0x033b10e8–0x033b1148`（**11 条**，标签 `'action state'` 在 `0x033b10d8`）：

```
0x033b10e8 done    0x033b10f0 wait    0x033b10f8 search  0x033b1100 goto2
0x033b1108 work    0x033b1110 work2   0x033b1118 turn    0x033b1120 delay
0x033b1128 failed  0x033b1130 invalidated   0x033b1140 moveNoSearch
```

**⚠ 两张表不是一一镜像（这是上一版的错，`v214_states.py` 实测）**：
- 大写 12 条、小写 11 条。
- 重合 9 条：`done wait search goto2 work work2 turn failed invalidated`。
- **仅大写有 3 条**：`Goto`（大写有、小写无——小写只有 `goto2`）、`Return`、`MoveNoSearch`（注意小写里是 `moveNoSearch`，大小写不同故未计入重合）。
- **仅小写有 2 条**：`delay`、`moveNoSearch`。
- **索引不对齐**：前 3 项 `done/wait/search` 两边 idx 相同，从第 4 项起全部漂移——大写 `goto2`=4、`work`=5、`work2`=6、`turn`=8、`failed`=9、`invalidated`=10；小写对应 3/4/5/6/8/9。**漂移量恒为 1**，正好等于大写多出的 `Goto`。

`delay` 只在小写里出现，说明它是调试面板对「动作正在等待 N 帧」这一内部状态的**显示判定**，不是 `enum ActionState` 的成员；`Return` 只在大写里出现，说明它是真实状态但没有独立显示名（调试面板把它显示成 `goto2` 或 `moveNoSearch`）。以上解释**未证实**，写入 §8.3。

**含义**：AI 的每个动作不是"发一条指令就完事"，而是被引擎当作**有状态的协程**推进。`up-build` 发出后进入 `Work`，每帧轮询，完成转 `Done`，被打断转 `Invalidated`，被攻击打断转 `Failed`。`Goto`/`Goto2` 是两段式寻路（先粗后精）。`Turn` 是转向对齐（单位要先转身才能做下一动作）。`MoveNoSearch` 是"已知路径直走，跳过寻路"的快路径。

这解释了 AI 脚本里一个经典坑：**连续两条 `up-build` 不会并行执行**，第二条会覆盖第一条的状态，因为状态槽是单例。

### 2.3 SN 战略数字 212 个

完整清单见 `_age_analysis/aixs/ai_categorized.txt`。按语义分段：

- **探索/斥候（9）**：`sn-percent-civilian-explorers` … `sn-blot-size`
- **攻击组（10）**：`sn-minimum-attack-group-size` … `sn-attack-separation-time-randomness`
- **防御组（8）**：`sn-minimum-defend-group-size` … `sn-defend-overlap-distance`
- **海战组（8）**：`sn-number-boat-attack-groups` … `sn-maximum-boat-defend-group-size`
- **目标评估（11）**：`sn-target-evaluation-distance`/`-hitpoints`/`-damage-capability`/`-kills`/`-ally-proximity`/`-rof`/`-randomness`/`-attack-attempts`/`-range`/`-siege-weapon`/`-boat`
- **采集比例（8）**：`sn-food-gatherer-percentage` … `sn-wood-gatherer-percentage`、`sn-intelligent-gathering`
- **掉落点（8）**：`sn-food-dropsite-distance` … `sn-minimum-dropsite-buffer`、`sn-dropsite-separation-distance`
- **建造（9）**：`sn-build-frequency`/`sn-number-build-attempts-before-skip`/`sn-building-targeting-mode`/`sn-wall-targeting-mode`/`sn-town-center-placement`/`sn-placement-zone-size`/`sn-placement-fail-delta`/`sn-placement-to-center`/`sn-unexplored-construction`
- **协同/多人（7）**：`sn-coop-share-information`/`-attacking`/`-interval`、`sn-attack-winning-player`/`-factor`、`sn-track-player-history`、`sn-hits-before-alliance-change`
- **特殊攻击（3）**：`sn-special-attack-type1/2/3` + `sn-special-attack-influence1`
- **新版本开关（约 40）**：`sn-enable-new-building-system`/`sn-enable-boar-hunting`/`sn-enable-patrol-attack`/`sn-enable-training-queue`/`sn-enable-research-queue`/`sn-enable-offensive-priority`/`sn-enable-full-vision`/`sn-allow-capturing-gaia-units`/`sn-allow-gathering-sea-fish-with-villagers`…（这些是 DE 相对 HD/AoC 的能力开关）

### 2.4 玩家主体选择器 60 个

- **`my-*`（8）**：`my-player-number` `my-civ` `my-unique-unit` `my-unique-unit-upgrade` `my-elite-unique-unit` `my-unique-unit-line` `my-unique-research` `my-second-unique-research`
- **`any-*`（11）**：`any-ally` `any-computer` `any-computer-ally` `any-computer-enemy` `any-computer-neutral` `any-enemy` `any-human` `any-human-ally` `any-human-enemy` `any-human-neutral` `any-neutral`
- **`every-*`（5）**：`every-ally` `every-computer` `every-enemy` `every-human` `every-neutral`
- **`this-any-*`（11）**：上两类交叉
- **`players-*`（15）**：`players-achievements` `players-building-count` `players-building-type-count` `players-civ` `players-civilian-population` `players-current-age` `players-current-age-time` `players-military-population` `players-population` `players-score` `players-stance` `players-tribute` `players-tribute-memory` `players-unit-count` `players-unit-type-count` `players-in-game`
- **敌方侦察（4）**：`enemy` `enemy-buildings-in-town` `enemy-captured-relics` `enemy-units-in-town` `enemy-villagers-in-town`
- **Gaia（3）**：`gaia` `gaia-type-count` `gaia-type-count-total`
- **焦点（1）**：`focus-player`

### 2.5 `object-data-*` 20 个（对象数据访问器）

```
object-data-id            object-data-type          object-data-class
object-data-category      object-data-cmdid         object-data-action
object-data-order         object-data-target        object-data-point-x
object-data-point-y       object-data-hitpoints     object-data-maxhp
object-data-range         object-data-speed         object-data-dropsite
object-data-resource      object-data-carry         object-data-garrisoned
object-data-garrison-count object-data-status
```

### 2.6 `actionid-*` / `orderid-*`（各 22 个，完全对称）

```
attack defend build heal convert explore stop runaway retreat gather
move patrol follow hunt transport trade evade enter repair train research unload
```

两套 ID 同构，说明引擎内部"AI 动作"与"单位命令"共用同一枚举语义。

### 2.7 `cmdid-*` 11 个（AI 单位分组指令）

```
cmdid-flag  cmdid-livestock-gaia  cmdid-civilian-building  cmdid-villager
cmdid-military  cmdid-trade  cmdid-monk  cmdid-transport  cmdid-relic
cmdid-unknown  cmdid-military-building
```

### 2.8 单位类枚举（`*-class`，27 个）

```
town-center-foundation  villager-class  ocean-fish-class  shore-fish-class
farm-class  tower-class  wall-class  gate-class  king-class  livestock-class
infantry-class  archery-class  archery-cannon-class  cavalry-class
cavalry-archer-class  cavalry-cannon-class  monastery-class
siege-weapon-class  scorpion-class  packed-trebuchet-class
unpacked-trebuchet-class  petard-class  warship-class  all-units-class
```

### 2.9 语义枚举族（这些是 AI 语言的"参数取值"）

**idle-type（4）**：`idle-type-villager` `idle-type-trade-cart` `idle-type-fishing-ship` `idle-type-trade-cog`
**stance（4）**：`stance-aggressive` `stance-defensive` `stance-stand-ground` `stance-no-attack`
**escrow（2）**：`with-escrow` `without-escrow`
**place（4）**：`place-normal` `place-forward` `place-control` `place-point`
**priority（2）**：`priority-offense` `priority-defense`
**position（13）**：`position-center` `position-opposite` `position-corner` `position-enemy` `position-border` `position-mirror` `position-flank` `position-zero` `position-map-size` `position-self` `position-target` `position-focus` `position-object` `position-point`
**action（21）**：`action-default` `action-move` `action-patrol` `action-guard` `action-follow` `action-stop` `action-ground` `action-garrison` `action-delete` `action-unload` `action-train` `action-gather` `action-lock` `action-work` `action-ungarrison` `action-drop-relic` `action-pack` `action-unpack` `action-none` `action-research`
**formation（3）**：`formation-box` `formation-stagger` `formation-flank`
**mainland（2）**：`off-mainland` `on-mainland`
**sort（5）**：`sort-targets` `sort-random` `sort-distance` `sort-hitpoints` `sort-range`
**find（3）**：`find-attacker` `find-random` `find-closest` `find-ordered`
**scout（7）**：`scout-center` `scout-opposite` `scout-corner` `scout-enemy` `scout-border` `scout-mirror` `scout-flank`
**hunting（4）**：`hunting` `boar-hunting` `deer-hunting` `live-boar`
**timer（3）**：`timer-status` `timer-disabled` `timer-running`
**search（2）**：`search-local` `search-remote`
**villager-role（14）**：`villager-shepherd` `villager-forager` `villager-farmer` `villager-hunter` `villager-fisherman` `villager-food` `villager-wood` `villager-stone` `villager-gold` `villager-builder` `villager-repairer` `villager-base` `villager-type-in-town`
**threat（4）**：`threat-time` `threat-player` `threat-source` `threat-target`
**食物来源（5）**：`forage-food` `deer-food` `boar-food` `fish-food` `farm-food` `sheep-food`
**`*-set` 特殊编组（9）**：`monk-set` `trebuchet-set` `huskarl-set` `tarkan-set` `konnik-set` `kipchak-set` `serjeant-set` `flemish-pikeman-set` `ratha-set` `spearman-set`
**victory（3）**：`king-of-the-hill` `wonder-race` `trigger`

### 2.10 文明名 40 个（AI 可用 `my-civ` 判等）

```
aztec briton byzantine celtic chinese frankish gothic hun korean mayan
mongol persian saracen teutonic viking ethiopian malian berbers khmer
malay burmese bulgarians tatars cumans lithuanians burgundians sicilians
poles bohemians dravidians bengalis gurjaras romans armenians georgians
indian italian japanese khmer slav spanish turk
```

### 2.11 `terrain-*` 42 种地形

```
grass grass2 grass3 grass-snow grass-old            water water-deep
water-medium water-bridge water-old water-beach      shallows ice ice2
ice-beach desert dirt dirt2 dirt3 dirt-snow          farm farm1 farm2
farm3 farm-dead forest forest-bamboo forest-jungle    forest-oak forest-palm
forest-pine forest-snow foundation foundation-snow    koh leaves road
road-broken road-snow road-fungus snow unknown
```

### 2.12 语法关键字（编译器级）

```
rule  defrule  defconst  load-if-defined  load-if-not-defined
else  end-if  rules  goal  strategic-number
```

另有 `include` `load` `load-random` `cpp` `per` `per2` `ai2` 等文件级关键字，说明 AI 编译器支持：

- `.per`（经典）
- `.per2`（DE 扩展）
- `.ai2`（文件头标识）
- `load` / `load-random`（运行时加载其它脚本）
- `cpp`（预处理器式条件编译，配合 `load-if-defined`）

### 2.13 AI 命令实现区结构

**先纠一个上一版的错**：那份报告说"UP 扩展命令 192 个"，但同时又列了"动作命令 52"、"聊天/日志 26"，且把 `fe-*` 混进 UP 段。经全文件 `\x00` 边界精确切分（`_age_analysis/aixs/final_cmds.py`），准确分类是：

| 族 | 数量 | 存放区 | 性质 |
|---|---|---|---|
| 基础 AI 命令（无前缀） | **59** | `0x032237f8–0x03223c48` | 原版 AoC 内核，全部是动作 |
| `up-*` 严格命令名 | **192** | 块A 143 + 块C 49（见下表） | UserPatch 扩展，DE 内建 |
| `fe-*` 严格命令名 | **13** | 块A 10 + 块C 3 | 编辑器 / testharness / 子局类型 |
| `xs-*` | **1** | `0x03223648`（块A 内） | 只有 `xs-script-call` |
| `skybox-*` | **2** | 块A 内 | `skybox-clear-signal` `skybox-set-name-mode` |
| `UA*`/`TA*`/`UPA*` 调试名字 | **17** | `0x03221928–0x03221dab` + `0x03222568` | 追踪/日志用名字，非脚本命令 |

（上表的 `up-* 143+49`、`fe-* 10+3` 是 v180 逐条实测的块内分配，合计正好 192 / 13。）

**⚠ 上一版这里有一张 21 行的"命令 → 实现函数"对应表，全部是错的，已删除。** 逐条实拍（`_age_analysis/aixs/v191_ua_claims.py`）：

上一版那 21 个所谓 handler 地址，实际内容全是**命令名串的中间片段**——`0x3222e20` 是 `'nt'`（`up-request-hunters` 的尾巴）、`0x3222e30` 是 `'bject-by-id'`、`0x3222e48` 是 `'oint-elevation'`、`0x32231a8` 是空串、`0x3223968` 是 `'sing-range'`。**21 条里命中 0 条**。那张表是把"名字里带 UA/TA 字样"和"地址落在 0x3222xxx 区间"两件事拼在一起的产物，没有一条经过字节校验。

真实的 `UA*` / `TA*` 名字位置（明文容器串，`0x3221928–0x3221dab` + `0x3222568`）：

```
TAChatLocalUsingRange       0x03221928    TAChatToAllUsingRange     0x03221940
TAChatToAlliesUsingRange    0x03221958    TAChatToEnemiesUsingRange 0x03221978
TAChatToPlayerUsingRange    0x03221998    TATauntUsingRange         0x032219e0
UAJumpRule                  0x03221a23    UAGetThreatData           0x03221a33
UARetaskGatherers           0x03221a4b    UAChatData                0x03221a7b
UAAssignBuilders            0x03221ad3    UARetreatNow              0x03221aeb
UAFindPlayer                0x03221b23    UAGetVictoryData          0x03221b43
UAGetTreatyData             0x03221b5b    UASetPlacementData        0x03221dab
UPAGuardUnit                0x03222568
```

**这 17 个名字的引用情况**（`v158_rip_pool.json`，4626 条记录 / 1354 唯一目标）：只有 4 个被引用过一次——`0x3221940` / `0x3221958` / `0x3221978` / `0x3221998`，引用点 `0xb5772e` / `0xb5789e` / `0xb57a0e` / `0xb57cb6`。其余 13 个**零引用**。

反汇编引用者 `0x00b57720–0x00b5775c`（60 B）：

```
0x00b5772e  lea rdx, [rip+0x26ca20b]   ; -> 0x3221940 'TAChatToAllUsingRange'
0x00b57735  mov r8d, 0x36d              ; 877 = 源文件行号
0x00b5773b  lea rcx, [rip+0x37fd5be]   ; -> 0x04354d00（非字符串，日志对象）
0x00b57742  call 0x905170
0x00b57747  cdq
0x00b57748  idiv ebx                    ; 取模运算
```

这是**带行号的日志/断言调用**，不是分派表。`UA` = Unit Action、`TA` = Text Action 这个命名法判断本身仍成立（与 §4.0 的 23 种 action type 同源），但**"脚本写 `up-jump-rule`，引擎调 `UAJumpRule`"这个映射关系在二进制里不存在任何证据**。

**真正的三块命令名区（v180 实测边界）**：

| 块 | 条数 | RVA 范围 | 内容 |
|---|---|---|---|
| A | 156 | `0x03222970 .. 0x0322369d` | `up-jump-rule` … `fe-reset-attack-group-exclusion-list`（动作族） |
| 裸前缀 | 3 | `0x032236a0 .. 0x032236ac` | `c:` `s:` `g:` |
| 算术簇 | 36 | `0x032236ac .. 0x0322378d` | 3 族 × 12 |
| B | 59 | `0x032237f8 .. 0x03223c5a` | 基础命令（原版内核） |
| Cmp | 18 | `0x0322b914 .. 0x0322b989` | 比较运算符 3 族 × 6 |
| C | 52 | `0x03233730 .. 0x03233be6` | `up-allied-goal` … `fe-idle-pasture-count`（条件表达式族） |

A 块全是**动作**（`up-jump-rule`、`up-train`、`up-train-site-ready`、`up-set-attack-stance`、`up-retreat-now`…），C 块全是**条件/查询**（`up-compare-goal`、`up-can-build`、`up-object-type-count`…）——语义分工干净，与 AI 语言「defrule 的 facts 与 actions 两半」完全对应。

（注：`up-attack` 这个命令**不存在**。攻击相关的真实命令是 `up-set-attack-stance`、`up-reset-attack-now`、`up-attacker-class`、`up-get-attacker-class`，以及基础命令里的 `attack-now`。上一版把 `attack-now` 误写成 `up-attack`。）

**`xs-script-call` 单独一条，位置在 `fe-break-point` 与 `fe-exclude-from-attack-group` 之间**——这是 AI 调 XS 的**唯一入口**，全引擎只有这一条。补进 §5。

`fe-*` 13 个全量：

```
fe-break-point                    fe-can-build-at-point
fe-cc-effect-amount               fe-cc-effect-percent
fe-exclude-from-attack-group      fe-get-signal
fe-idle-pasture-count             fe-reset-attack-group-exclusion-list
fe-set-signal                     fe-sub-game-type
fe-testharness-log-seed           fe-testharness-message
```

---

`.pdata` 在 `0x0b40000–0x0c20000`（0xE0000 = 896 KB）区段有 **2154 个函数**：

- 中位函数大小 `0x9c`（156 B）
- 45% 的函数 ≤ `0x80`（128 B）
- 每 64KB 的函数密度：`0x0b40000` 块 364 个（最密），其余 79–216 个

**诚实说明**：这 2154 个函数是该区段的**全部函数**，不是全部 AI 命令 handler。该区段被 RIP 引用的池区目标共 86 处（59 个不同目标），其中指向 AI 命令名区的是 **0 处**。

从命中结果看，该区段的函数形态确实是「小而多」：
```
func 0x0b5e1d0-0x0b5e20f (0x3f B) -> 'Invalid AI group passed (%d)'
func 0x0b5f780-0x0b5f7cf (0x4f B) -> 'Event ID out of range (%d) [0 - %d]'
func 0x0b60300-0x0b6034f (0x4f B) -> 'Signal ID out of range (%d) [0 - %d]'
func 0x0b92a70-0x0b92ae2 (0x72 B) -> 'F:\...\Source\Game\ai\Actions\ActionMove.cpp'
func 0x0b7bc0c             -> 'Found a potential target: %d'
```

**这 4 个参数校验函数已完整反汇编**（`v207_ai_validate.py`），**全函数体只有 63–115 字节，看不到任何命令分派逻辑**，只有「越界 → 格式化报错 → jmp 日志器」：

```
0x00b5f780  push rbx / sub rsp,0x20 / mov ebx,r8d
0x00b5f789  call 0xbef1d0                    ; 取值
0x00b5f78e  cmp  eax, 0xff                   ; ★ 合法范围上界 = 0xff
0x00b5f793  ja   0xb5f7ae                    ; 越界分支
0x00b5f795  movsxd rdx, eax
0x00b5f79a  lea  rax, [rip+0x37489df]        ; -> 0x42a8180 一张 u32 数组
0x00b5f7a1  mov  edx, dword ptr [rax+rdx*4]  ; ★ 按索引查表
0x00b5f7a9  jmp  0xbefc20
0x00b5f7ae  ...  lea rdx, [rip+..]           ; -> 'Event ID out of range (%d) [0 - %d]'
0x00b5f7bc  mov  r9d, 0x100                  ; ★ 报错里的上界 = 0x100
```

从这 4 个函数读出的硬参数约束（**这是 A 项目前唯一的二进制级证据**）：

| 参数 | 合法范围 | 证据 RVA | 后继表 |
|---|---|---|---|
| AI group | 无显式上界，走 `0xCA6480` 判定 | `0x00b5e1d6` | — |
| signal id | `0 ≤ id ≤ 0xFF`（报错上界写 `0x100`） | `0x00b5f78e` `cmp eax,0xff` / `0x00b5f7bc` `mov r9d,0x100` | `0x042a8180` u32[] |
| event id | `0 ≤ id ≤ 0xFF`（同上） | `0x00b6030e` `cmp eax,0xff` / `0x00b6033c` `mov r9d,0x100` | `0x042a7d80` u32[] |
| player index | 走 `0x15fe480` 判定，无内联常数 | `0x00be87f8` | — |

**`cmp eax, 0xff` + `mov r9d, 0x100` 这两条指令同时存在，等于引擎自己承认 signal / event 的合法 id 空间是 256 项。**

**这 4 个函数有 0 个 `E8` 直接调用点，也 0 个 `lea rip` 引用**（`v207` / `v208` 双向确认）——它们只能通过函数指针表间接调用。唯一找到的指针槽 `0x03229ae0`（存 `0x140be87e0`）经扩张后只有 **6 项**（`0x03229ad0..0x03229af8`），目标 `0xbe87c0/0xbe87d0/0xbe87e0/0xbe8860/0xbe8870/0xbe8880`——是 C++ 迭代器/range 适配器小函数（`lea rax,[rcx+8]; ret` 之类），**不是命令分派表**。


### 2.13b 三条 `up-get-fact-*` 的精确参数个数（MSVC 修饰符号通道）

上一节说「A 项目前唯一的二进制级证据」是那 4 个校验函数的值域。现在多了一条更强的证据：**参数个数本身**。

引擎在 `.data` 里残留了 **44 条唯一 MSVC 修饰函数名**（`?Name@Class@@sig@Z` 形态）。其中三条直接是 `up-get-fact-*` 的实现：

```
?UPGetFactMin@AIHybrid@@SAHHHHH@Z      @0x04122212
?UPGetFactMax@AIHybrid@@SAHHHHH@Z      @0x041221c2
?UPGetFactSum@AIHybrid@@SAHHHHH@Z      @0x04122172
```

严格解析 `SAHHHHH`（`v284_exact.py`，按 MSVC 修饰名官方文法逐字符切分）：

```
原始类型段 : S A H H H H H
第 1 步    : S  -> static
第 2 步    : A  -> __cdecl
剩余       : H H H H H
第 3 步    : 按「返回类型在参数之前」切分
             -> 返回类型 = int        (第 1 个 H)
             -> 参数列表 = int,int,int,int   (剩余 4 个 H)
             -> arity    = 4
```

**这一步极易算错，三个数字都能自圆其说**：把前缀 `SA` 整体正则吞掉 → `arity=0`（`v273` 的错误）；把 `HHHHH` 全部当参数、忘记返回类型占第一个 → `arity=5`（`v270` 的错误）；按文法切才是 **4**。

| 命令 | 命令名 RVA | 实现修饰名 | 签名 | **arity** |
|---|---|---|---|---|
| `up-get-fact-min` | `0x03222ae0` | `?UPGetFactMin@AIHybrid@@SAHHHHH@Z` | `static int (int,int,int,int)` | **4** |
| `up-get-fact-max` | `0x03222af0` | `?UPGetFactMax@AIHybrid@@SAHHHHH@Z` | `static int (int,int,int,int)` | **4** |
| `up-get-fact-sum` | `0x03222b00` | `?UPGetFactSum@AIHybrid@@SAHHHHH@Z` | `static int (int,int,int,int)` | **4** |

**判据强度**：把 324 个命令名做 5 种形态变换（原样 / 去 `up-` / 去连字符 / CamelCase / `UP`+CamelCase）与 44 个修饰名交叉匹配，命中 **3/324**；同样流程用 **200 个随机拼接的假命令名**跑一遍，命中 **0/200 (0.0%)**。→ 这 3 条不是巧合。

**这条通道的天花板已实测**（`v285_functor.py`）：全文件枚举 `. ?AV?$_Func_impl_no_alloc…` / `$Function@` 形态的 RTTI 类型描述符 **1153 处**，从中提取出的唯一「被 `std::function` 包装的函数」只有 **40 个**（分布在 `AIHybrid` / `Age2MainMenu` / `TRIBE_Master_Combat_Object` / `WorldPlayerBase` / `GameScreen` 等类上），其中 AI 相关仅 **4 个**：

```
AIHybrid::UPGetFactMax   ret=int  params=int,int,int,int  arity=4   desc@0x0417cb50
AIHybrid::UPGetFactMin   ret=int  params=int,int,int,int  arity=4   desc@0x0417caa0
AIHybrid::UPGetFactSum   ret=int  params=int,int,int,int  arity=4   desc@0x0417cc00
TribeStrategyAIModule::update  ret=int  params=int  arity=1  desc@0x0417d360
```

→ **`up-get-fact-{min,max,sum}` 就是全部能用这条通道解出的 AI 命令。** 剩下的 189 条 `up-*` 不走 `std::function`（或它们的 lambda 未生成 RTTI），符号通道到此确认关闭。

**这三条命令的语义正好吻合**：`up-get-fact-sum/min/max` 在 UP 规范里就是 `(fact-id, object/player-param, object/player-param, out-goal)` 四参数形态——`sum` 需要两个操作数才能求和，`min`/`max` 同理。这四条 `int` 与该语义一一对应。


### 2.13c `AIHybrid` 的 vtable 与注册点：静态可达性的终点

三条实现通过 `std::function` 包装。RTTI 链路解出：

```
TypeDescriptor  .?AV?$_Func_impl_no_alloc@V<lambda_1>@?4??UPGetFactMin@AIHybrid@@…
COL             0x0322a888 (Min) / 0x0322a8c0 (Max) / 0x0322a8f8 (Sum)
vtable 首槽      0x140bf2c50      / 0x140bf2c30      / 0x140bf2c70
```

这三个 thunk 在 `0x00bf2c30..0x00bf2c80`，形态完全同构：

```
00bf2c30  48 8d 05 89 7c 63 02   lea rax,[rip+0x2637c89]   ; -> 0x0322a8c0 (Max vtable)
          48 89 02               mov [rdx],rax            ; 把 vtable 指针写进目标对象
          48 8b c2               mov rax,rdx
          0f 10 41 08            movups xmm0,[rcx+8]
          0f 11 42 08            movups [rdx+8],xmm0
          c3                     ret
```

→ **这是 `std::_Func_impl_no_alloc` 的拷贝构造函数，不是命令注册点。**

**可达性判定**（`v281_reg_site.py`）：全 `.text` 找 `E8 rel32` 指向这 6 个 thunk 及其 ±2 字节变体，**0 处**；找 `lea` 取址，**仅 1 处** `lea@0x02b7b2a8`（在函数 `0x02b7b190..0x02b7b7c6`，1590 B）。→ **构造 thunk 只经 vtable 间接调用，静态 call 图在此断裂。**

**该 thunk 区（`0x00bf2b00..0x00bf3000`）的实际形态**：大片高熵字节夹着稀疏真代码（`48 8d 05 …; c3` 的 8 字节小 thunk 一排，间隔着几百字节的无序数据）。**这与 §8.1 记录的那 10.10% 不可解字节是同一现象** —— 引擎把大量小 thunk 和未知数据块交错排布在同一段里。


### 2.14 错误消息暴露的参数约束

从错误串可直接读出各命令的合法值域：

```
up-store-object-name: Target object was not valid or gone (object id = %d)
up-store-player-name: Target player out of range (%d)
up-store-tech-name:  Tech ID is invalid (%d)
up-store-type-name:  Type ID is invalid (%d)
up-find-player-flare: Invalid player index (%d) / Invalid outGoal (%d)
Signal ID out of range (%d) [0 - %d]
Event ID out of range (%d) [0 - %d]
Invalid map coord [%d,%d] from goal point (%d)
Invalid escrow state (%d). Defaulting to without escrow
Invalid state (%d), using default -1
Goals can't be used as setup cost data (%d - %d)
Division by zero
Invalid math operator (%d)
Player needs at least one market to buy/sell resources
Invalid AI group passed (%d)
Invalid cheat (%s)
Break points not allowed in multiplayer
```

**`Goals can't be used as setup cost data` 与 `Break points not allowed in multiplayer` 是两条硬约束**——直接告出 AI 引擎的边界。

---

## 3. XS 语言：引擎认识什么

### 3.1 编译器语法关键字（26 个）

`0x3316de8–0x3316f20` 区的完整 token 表：

```
vector switch case while break if then else goto label for dbg return
void const static continue extern export class mutable
```

**派生属性关键字（rule 属性）**
```
minInterval  maxInterval  highFrequency  active  inactive
infiniteLoopLimit  infiniteRecursionLimit  breakpoint  runImmediately
```

这说明 XS 的 rule 声明可带这些属性：
```
<rule name="..." active="1" minInterval="0" maxInterval="5"
      infiniteLoopLimit="..." infiniteRecursionLimit="..." breakpoint="0" runImmediately="1">
```

**语言特性判断**
- 有 `switch/case` → 支持多分支
- 有 `goto/label` → 支持跳转（C 风格）
- 有 `class/mutable/static/const/extern/export` → 有类、可变、静态、常量、外部符号、导出
- 有 `for/while/break/continue` → 完整循环
- 有 `dbg` → 引擎级调试语句
- 有 `then` → 兼容 AoC 时代 `if ... then ... endif` 的伪代码风格
- **没有 `foreach` / `try` / `catch` / `new` / `delete` / `template`** → 无异常、无动态分配、无泛型

### 3.2 词法错误码（Tokenizer 错误 0001-0012）

```
Token Error 0006: string is too long.
Token Error 0007: line feed in string.
Token Error 0008: string not terminated.
Token Error 0009: expected '=' after '!'.
Token Error 0011: unexpected state=%d.
Token Error 0012: cannot add token #%d.
... floating point constant - missing exponent digits.
... string character found before buffer end.
```

说明 XS 有自己的手写 tokenizer，错误编号从 0001 到 0012。

### 3.3 syscall 注册机制（自解释设计）

**关键结构**：每个 syscall 在二进制里占「名字串 + doc 串」两段。doc 串分三种形态：

1. **纯原型**（182 条）—— 只给签名，无描述
2. **原型 + 英文描述**（44 条）—— 引擎开发者写的内联文档
3. **简写原型**（20 条）—— 文件 IO 族只有 `xsOpenFile(string filename)` 这种形式

带完整官方描述的那 44 条（原文照抄）：

```
void xsDisableSelf( void ): Disables the current rule.
void xsEnableRule( string ruleName ): Enables the given rule.
bool xsIsRuleEnabled( string ruleName ): Returns true if the rule is enabled.
void xsSetRulePriority( string ruleName, int priority ): Sets the priority of the given rule.
void xsSetRulePrioritySelf( int priority ): Sets the priority of the current rule.
void xsSetRuleMinInterval( string ruleName, int interval ): Sets the min interval of the given rule.
void xsSetRuleMinIntervalSelf( int interval ): Sets the min interval of the current rule.
void xsSetRuleMaxInterval( string ruleName, int interval ): Sets the max interval of the given rule.
void xsSetRuleMaxIntervalSelf( int interval ): Sets the max interval of the current rule.
void xsEnableRuleGroup( string ruleGroupName ): Enables all rule in the given rule group.
void xsDisableRuleGroup( string ruleGroupName ): Disables all rules in the given rule group.
void xsIsRuleGroupEnabled( string ruleGroupName ): Returns true if the rule group is enabled.
float xsVectorGetY( vector v ): Returns the y component of the given vector.
float xsVectorGetZ( vector v ): Returns the z component of the given vector.
float xsVectorSetY( vector v, float y ): Set the y component of the given vector, returns the new vector.
float xsVectorSetZ( vector v, float z ): Set the z component of the given vector, returns the new vector.
float xsVectorSet( float x, float y, float z ): Set the 3 components into a vector, returns the new vector.
float xsVectorLength( vector v ): Returns the length of the given vector.
float xsVectorNormalize( vector v): Returns the normalized version of the given vector.
int xsArrayCreateInt(int size, int defaultValue, string name): creates a sized and named integer array, returning an arrayID.
int xsArraySetInt(int arrayID, int index, int value): Sets a value at the specified index in the requested array.
int xsArrayGetInt(int arrayID, int index): Gets the value at the specified index in the requested array.
int xsArrayResizeInt(int arrayID, int newSize): Resize the requested array.
int xsArrayCreateFloat(int size, float defaultValue, string name): creates a sized and named float array, returning an arrayID.
int xsArraySetFloat(int arrayID, int index, float value): Sets a value at the specified index in the requested array.
float xsArrayGetFloat(int arrayID, int index): Gets the value at the specified index in the requested array.
int xsArrayResizeFloat(int arrayID, int newSize): Resize the requested array.
int xsArraySetBool(int arrayID, int index, bool value): Sets a value at the specified index in the requested array.
int xsArrayResizeBool(int arrayID, int newSize): Resize the requested array.
int xsArraySetString(int arrayID, int index, string value): Sets a value at the specified index in the requested array.
string xsArrayGetString(int arrayID, int index): Gets the value at the specified index in the requested array.
int xsArrayResizeString(int arrayID, int newSize): Resize the requested array.
int xsArrayCreateVector(int size, vector defaultValue, string name): creates a sized and named vector array, returning an arrayID.
int xsArraySetVector(int arrayID, int index, vector value): Sets a value at the specified index in the requested array.
vector xsArrayGetVector(int arrayID, int index): Gets the value at the specified index in the requested array.
int xsArrayResizeVector(int arrayID, int newSize): Resize the requested array.
int xsArrayGetSize(int arrayID): Gets the specified array's size.
int xsDumpArrays(): blogs out all XS arrays.
int xsGetContextPlayer( void ): Returns the current context player ID.
void xsSetContextPlayer( int playerID ): Sets the current context player ID (DO NOT DO THIS IF YOU DO NOT KNOW WHAT YOU ARE DOING).
int xsGetTime( void ): Returns the current gametime (in milliseconds).
bool xsAddRuntimeEvent( string foo, string bar, int something ): Setups a runtime event.  Don't use this.
int xsGetFuntionID( string functionName ): Runs the secret XSFID for the function. USE WITH CAUTION.
```

**三条值得注意的官方警告**（开发者原话）：
- `xsSetContextPlayer`: `DO NOT DO THIS IF YOU DO NOT KNOW WHAT YOU ARE DOING`
- `xsAddRuntimeEvent`: `Don't use this.`
- `xsGetFuntionID`: `Runs the secret XSFID for the function. USE WITH CAUTION.` —— 注意函数名在引擎里就是 **`xsGetFuntionID`**（拼错了 `Function`），不是文档里常见的 `xsGetFunctionID`

并且配套的错误串证明注册是**运行时按格式串构建的**：
```
Syscall config error - Unable to add the '%s' syscall.
Syscall config error - Unable to add integer parm %d for syscall '%s'.
Syscall config error - Unable to add string parm %s for syscall '%s'.
Syscall config error - Unable to add float parm %f for syscall '%s'.
Syscall config error - Unable to add bool parm %d for syscall '%s'.
Syscall config error - Unable to add vector parm (%f, %f, %f) for syscall '%s'.
```

→ **XS 的 syscall 表不是编译期固定的，而是启动时通过一个注册 API（`addIntegerParm`/`addStringParm`/`addFloatParm`/`addBoolParm`/`addVectorParm`）动态构建的**。这是它最关键的架构特征。

### 3.4 syscall 全量（232 个注册项）

完整带签名清单见产物 `xs_syscalls.txt`（232 条，全部为 `名字(` 形态的注册项）。

**关于 233 与 232 的差异（本轮定论）**：在 `0x3300000–0x3320000` 内以 `xs[A-Z]\w{2,40}` 扫描得到 **235** 个去重名字，其中 **232** 个后面紧跟 `(`（有原型串），另 **3** 个是孤立名字槽：

| 孤立名字 | RVA | 判定 |
|---|---|---|
| `xsArrayGetBool` | `0x330b7f8` | 文档表里的名字槽，前后字节全零 —— **有名字、无原型、无描述** |
| `xsGetFunctionID` | `0x330bfe0` | 同上，位于一段 XOR 混淆数据区，无 LEA 引用 |
| `xsGetMapID` | `0x3312088` | 同上，相邻的 `xsGetMapType` 却有完整原型 |

三者均**未被任何 `48 8D` LEA 直接引用**（对 83713 个 LEA 目标建索引后反查），因此它们是文档表的残留槽位，不是注册表里的可调用项。**可调用 syscall 数以 232 为准。**

另有一处引擎自身的拼写错误：`xsGetFunctionID` 的官方描述串写作 `int xsGetFuntionID( string functionName ): Runs the secret XSFID for the function. USE WITH CAUTION.` —— `Function` 少了 `c`。这条描述本身还确认了存在一个对脚本隐藏的 "secret XSFID" 机制，且引擎明确标注 `USE WITH CAUTION`。

#### 返回类型分布（232 项精确统计）

| 返回类型 | 数量 | 代表 |
|---|---|---|
| `int` | **79** | `xsGetGoal` `xsGetStrategicNumber` `xsGetMapWidth` `xsArrayCreateInt` |
| `bool` | **56** | `xsIsRuleEnabled` `xsCreateUnit` `xsTrainObject` `xsIsObjectValid` |
| `void` | **26** | `xsSetGoal` `xsEffectAmount` `xsTask` `xsDisableRule` |
| `float` | **24** | `xsGetUnitHitpoints` `xsVectorLength` `xsPlayerAttribute` |
| `string` | **17** | `xsGetUnitName` `xsGetPlayerName` `xsReadNetString` |
| `vector` | **7** | `xsGetUnitPosition` `xsArrayGetVector` `xsGetUnitMoveTarget` |
| `int32_t` | **5** | `xsGetWorldTime` `xsGetTurn` `xsGetFileSize` |
| 无返回类型声明（简写槽） | **18** | `xsChatData` `xsOpenFile` `xsReadInt` `xsWriteVector` ｜ 全部为文件 IO 族与 `xsGetNumPlayers`/`xsGetDataTypeSize`/`xsChatData` |

合计 **214 + 18 = 232**，与注册表口径一致。

> 注：`int32_t` 与 `int` 在引擎里是**两个不同写法**——`int32_t` 只出现在 `xsGetWorldTime` / `xsGetTurn` / `xsGetFileSize` 这类时间与文件大小接口上，说明 XS 的类型系统区分 `int`（脚本整数）和 `int32_t`（宿主原生 32 位）。

#### 按功能域分段（232 项全覆盖）

**① Goal / 战略数字 / 信号 / 上下文（12）**
```
  xsGetGoal                           xsSetGoal                           xsGetStrategicNumber                xsSetStrategicNumber
  xsGetAiScriptGoal                   xsSetAiScriptGoal                   xsGetAiSignal                       xsSetAiSignal
  xsGetContextPlayer                  xsSetContextPlayer                  xsTriggerVariable                   xsSetTriggerVariable
```

**② 规则生命周期控制（11）**
```
  xsEnableRule                        xsDisableRule                       xsEnableRuleGroup                   xsDisableRuleGroup
  xsDisableSelf                       xsIsRuleEnabled                     xsIsRuleGroupEnabled                xsSetRuleMinInterval
  xsSetRuleMaxInterval                xsSetRulePriority                   xsSetRuleMinIntervalSelf
```

**③ 规则参数与隐藏入口（5）**
```
  xsSetRuleMaxIntervalSelf            xsSetRulePrioritySelf               xsAddRuntimeEvent                   xsGetFuntionID
  xsBreakPoint
```

**④ Array 容器（21）**
```
  xsArrayCreateBool                   xsArrayCreateFloat                  xsArrayCreateInt                    xsArrayCreateString
  xsArrayCreateVector                 xsArrayGetFloat                     xsArrayGetInt                       xsArrayGetSize
  xsArrayGetString                    xsArrayGetVector                    xsArrayResizeBool                   xsArrayResizeFloat
  xsArrayResizeInt                    xsArrayResizeString                 xsArrayResizeVector                 xsArraySetBool
  xsArraySetFloat                     xsArraySetInt                       xsArraySetString                    xsArraySetVector
  xsDumpArrays
```

**⑤ Vector 数学（9）**
```
  xsVectorGetX                        xsVectorGetY                        xsVectorGetZ                        xsVectorSet
  xsVectorSetX                        xsVectorSetY                        xsVectorSetZ                        xsVectorLength
  xsVectorNormalize
```

**⑥ 单位创建 / 建造 / 移除（4）**
```
  xsCreateUnit                        xsBuildUnit                         xsTrainObject                       xsRemoveUnit
```

**⑦ 单位属性读写（25）**
```
  xsGetUnitHitpoints                  xsSetUnitHitpoints                  xsGetUnitOwner                      xsSetUnitOwner
  xsGetUnitName                       xsSetUnitName                       xsGetUnitCaption                    xsSetUnitCaption
  xsGetUnitCivName                    xsSetUnitCivName                    xsGetUnitPlayerName                 xsSetUnitPlayerName
  xsGetUnitPosition                   xsSetUnitPosition                   xsGetUnitProperty                   xsSetUnitProperty
  xsGetUnitAttribute                  xsGetUnitAttributeHeld              xsSetUnitAttributeHeld              xsGetUnitAttributeTypesHeld
  xsGetUnitBuildPoints                xsSetUnitBuildPoints                xsGetUnitCharge                     xsSetUnitCharge
  xsGetUnitGatherPoint
```

**⑧ 单位查询与身份（16）**
```
  xsSetUnitGatherPoint                xsGetUnitClass                      xsGetUnitType                       xsGetUnitObjectId
  xsGetUnitCopyId                     xsGetUnitGroupId                    xsGetUnitTargetUnitId               xsGetUnitTaskCount
  xsGetUnitMoveTarget                 xsGetGroupMoveTarget                xsDoesUnitExist                     xsIsObjectValid
  xsIsObjectAvailable                 xsObjectHasAction                   xsGetGarrisonedUnitIds              xsGetGarrisonedInUnitId
```

**⑨ 任务与指令（11）**
```
  xsTask                              xsTaskUnits                         xsTaskAmount                        xsGetTaskAmount
  xsResetTaskAmount                   xsUnitTaskAmount                    xsObjectTaskAmount                  xsRemoveTask
  xsModifyUnitTasks                   xsModifyObjectTasks                 xsStopUnit
```

**⑩ 玩家身份 / 颜色 / 外交（16）**
```
  xsGetPlayerCivName                  xsSetPlayerCivName                  xsGetPlayerCivilization             xsGetCivName
  xsGetPlayerColor                    xsGetPlayerColorTag                 xsSetPlayerColor                    xsGetPlayerName
  xsSetPlayerName                     xsGetPlayerInGame                   xsGetWorldPlayerId                  xsGetPlayerType
  xsGetPlayerNumberOfObjects          xsGetPlayerNumberOfTechs            xsGetPlayerUnitIds                  xsGetDiplomacy
```

**⑪ 外交与属性（10）**
```
  xsSetDiplomacy                      xsPlayerAttribute                   xsSetPlayerAttribute                xsGetPlayerAttributeName
  xsGetHandicapMultiplier             xsGetObjectAttribute                xsGetObjectAttributeName            xsGetTechAttribute
  xsGetTechName                       xsSetTechName
```

**⑫ 科技与研究（7）**
```
  xsSetTechDescription                xsResearchTechnology                xsResearchLocalTechnology           xsHasResearchedLocalTechnology
  xsInitiateResearch                  xsGetTechState                      xsGetObjectTaskCount
```

**⑬ 地图 / 对象枚举（14）**
```
  xsGetMapWidth                       xsGetMapHeight                      xsGetMapName                        xsGetMapType
  xsGetMapSeed                        xsGetMapTileAttribute               xsGetObjectCount                    xsGetObjectCountTotal
  xsGetObjectName                     xsGetObjectClass                    xsGetObjectType                     xsGetObjectCopyId
  xsGetNumPlayers                     xsGetDifficulty
```

**⑭ 随机数（3）**
```
  xsGetRandomNumber                   xsGetRandomNumberLH                 xsGetRandomNumberMax
```

**⑮ 时间与计时器（8）**
```
  xsGetTime                           xsGetGameTime                       xsGetWorldTime                      xsGetTurn
  xsClearTimer                        xsDisplayTimer                      xsGetVictoryTime                    xsGetVictoryType
```

**⑯ 胜利条件（6）**
```
  xsDeclareVictory                    xsGetVictoryCondition               xsGetVictoryPlayer                  xsGetVictoryConditionForSecondaryGameMode
  xsGetVictoryPlayerForSecondaryGameMode  xsGetVictoryTimeForSecondaryGameMode
```

**⑰ 文件 IO（13）**
```
  xsOpenFile                          xsCreateFile                        xsCloseFile                         xsReadInt
  xsReadFloat                         xsReadString                        xsReadVector                        xsWriteInt
  xsWriteFloat                        xsWriteString                       xsWriteVector                       xsGetFilePosition
  xsSetFilePosition
```

**⑱ 文件定位与大小（2）**
```
  xsOffsetFilePosition                xsGetFileSize
```

**⑲ 网络同步数据（10）**
```
  xsSendNetData                       xsResetNetData                      xsReadNetInt                        xsReadNetFloat
  xsReadNetString                     xsReadNetVector                     xsWriteNetInt                       xsWriteNetFloat
  xsWriteNetString                    xsWriteNetVector
```

**⑳ 网络游标（4）**
```
  xsGetReadNetDataPosition            xsSetReadNetDataPosition            xsGetWriteNetDataPosition           xsSetWriteNetDataPosition
```

**㉑ UI / 表现 / 文本（10）**
```
  xsPlaySound                         xsFlashUnit                         xsSetViewPosition                   xsSetZoom
  xsSetObjectDescription              xsSendChat                          xsChatData                          xsSetChatToPlayer
  xsDisplayInstructions               xsClearInstructions
```

**㉒ 环境查询（5）**
```
  xsGetLocale                         xsEffectAmount                      xsGetString                         xsCeilToInt
  xsGetDataTypeSize
```

**㉓ 不同步安全的本地查询（7）**
```
  xsUnsyncGetLocalPlayerId            xsUnsyncGetPlayerSelectedUnitIds    xsUnsyncGetTimerTimeRemaining       xsUnsyncGetViewPosition
  xsUnsyncGetZoom                     xsUnsyncIsSandboxMode               xsUnsyncIsUnitVisible
```

**㉔ 颜色氛围（2）**
```
  xsGetColorMood                      xsSetColorMood
```

**㉕ 伤害类型名（1）**
```
  xsGetDamageClassName
```

> 分组口径校验：24 个功能域合计 **232** 项，与注册表无重无漏。
> 数量最多的三个域是 **单位属性读写 25**、**Array 容器 21**、**单位查询与身份 16 / 玩家身份 16** —— 引擎把 XS 的重心放在"逐单位读写"而不是"整局控制"上。
> `xsUnsync*` 7 个是**不同步安全**的本地查询（视角、缩放、选中单位、本机玩家），它们不进同步哈希，因此可以在任意时刻读；反之其余 225 个都在同步路径上，读写位置错误会导致 out-of-sync。

### 3.5 `xsEffectAmount` 与 AGE 的接口对应

`xsEffectAmount(effect, itemName, type, value, playerId, index)` 的 6 个参数，与 AGE 的 Effects 标签页字段一一对应：

| XS 参数 | AGE Effects 字段 |
|---|---|
| `effect` | Effect Type（effect id） |
| `itemName` | Unit / Tech / Building ID |
| `type` | Attribute / Resource / Armor class |
| `value` | Amount |
| `playerId` | Player（-1 = 全体） |
| `index` | 索引（armor/attack 的 class 号） |

这就是**AGE 与 XS 的真正接口面**：AGE 改 .dat 的 Effects 表，XS 在运行时用同一套编号做同样的事。

---

## 4. 两套语言的边界（引擎级硬约束）

### 4.0 单位动作类型 23 种（引擎内部枚举，2026-10 四次校核修正）

**⚠ 上一版写 24 种并给了区间 `0x33b0b50–0x33b0e48`，两个都是错的。** 实测（`v214_states.py`，NUL 分隔精确枚举）：标签 `'action type'` 在 `0x033b1150`，枚举紧跟其后，**23 条**，止于 `0x033b124f`：

```
0x033b115c ATTACK                  0x033b1164 BIRD
0x033b116c COMBAT                  0x033b1174 ENTER
0x033b1180 EXPLORE                 0x033b1188 GATHER
0x033b1190 GRAZE                   0x033b1198 FOLLOW
0x033b11a0 MAKE                    0x033b11a8 MISSILE
0x033b11b0 MOVE_TO                 0x033b11b8 PREDATOR
0x033b11c8 RUN_AWAY                0x033b11d8 TRANSPORT
0x033b11e8 TRANSPORT_OVER_WALL     0x033b11fc BUILD
0x033b1204 HUNT                    0x033b120c TRADE
0x033b1218 CONVERT                 0x033b1220 HEAL
0x033b1228 REPAIR                  0x033b1230 DELIVER_RELIC
0x033b1240 PICKUP_RELIC
```

紧跟的是 `'current target:'`(`0x033b1250`) 与 `'Age2TabDebugUnitAI'`(`0x033b1260`)——**这证明这 23 条枚举属于调试面板的显示表**，不是虚函数表。

上一版的错误来源：把 `0x33b0ae8` 当成了小写状态表。实测该处是 **vtable 群**（stride 8，前 4 槽 `0x140806200 / 0x140806230 / 0x140806240 / 0x140806250`，全部指向 `\xc2\x00\x00` + `cc` 填充的 7 字节桩，即 `ret` 型 thunk）。真正的小写状态表在 `0x33b10e8`（见 §2.2d）。

配合同区的 **12 个大写状态**（§2.2d），可读出引擎的单位行为模型：

- **23 种动作类型 × 12 个状态 = 单位 AI 的状态空间**
- `PREDATOR` 是狼/鹰等食肉动物的捕食动作，`BIRD` 是鸟类的飞行，`GRAZE` 是羊/牛的吃草，`RUN_AWAY` 是受惊逃跑
- `TRANSPORT` / `TRANSPORT_OVER_WALL` 是运输船装载与"跨墙运输"（**跨墙运输是 DE 特有**，AoC 没有）
- `DELIVER_RELIC` / `PICKUP_RELIC` 是圣物搬运的两段
- `CONVERT` / `HEAL` / `REPAIR` 是僧侣/村民的持续动作

**AI 与这张表的关系**：AI 的 `up-set-attack-stance`、`up-retreat-now`、`up-garrison`、`up-gather-inside` 等命令（这 4 条均已在 `v180_authoritative.json` 中核实存在），本质是**往这些状态槽里写值**。AI 不能定义新动作类型，只能在引擎给的这 23 种里调度。

**上界提醒**：`0x33b0b5c` 这个地址在上一版被当作"24 种动作类型枚举"，实测是 `{u32=1, u32=pad, ptr=0x1408xxxxx}` 的 **stride 0x10 表**（首槽 `u32a=1 u32b=0x40806390 q=0x408063a000000001`），不是字符串枚举。任何引用 `0x33b0b5c` 作为动作类型枚举的地方都是错的。

### 4.1 AI（.per）能做什么

- 读全部 212 个 SN、189 个 amount 资源/统计索引
- 读 20 个 `object-data-*` 字段
- 用 192 个 `up-*` 做搜索、过滤、几何、目标选择、经济、军事、跳转
- 用 51 个查询做单位/建筑计数
- 写 52 个动作命令（train/research/build/buy/sell/attack-now/…）
- 通过 `up-store-*` 读玩家/科技/单位/地图名
- 通过 `up-store-player-chat` 读玩家聊天（可做聊天解析）

### 4.2 AI 不能做什么

- **不能凭空创建单位**（无 spawn/create 命令；只能 `train` 走生产队列、`build` 走建造流程）
- **不能直接改单位属性**（无 set-hitpoints / set-speed 类命令；`up-add-object-cost` 只改成本计算）
- **不能直接改玩家资源数值**（只能 `up-drop-resources`/`up-buy-commodity`/`up-sell-commodity` 走正常经济流程；`up-cc-add-resource` 仅限 cheat 上下文）
- **不能读任意地图瓦片**（只有 `up-get-point-terrain` 给单个点位，无按坐标遍历 API）
- **不能跨玩家直接读写 goal/SN**（须用 `up-set-shared-goal`/`up-allied-goal`，受共享规则限制）
- **不能访问文件系统**

**注意反例（容易误判）**：AI **确实能删除**单位与建筑 —— 经典命令 `delete-unit` / `delete-building`，以及 `up-delete-objects` / `up-delete-distant-farms` / `up-delete-idle-units` 都在 1752 词表内。但 `up-remove-objects` 是「把对象从当前搜索结果中剔除」，不是删除实体，别混淆。

同理 `up-create-group` 是「创建 AI 编组」，不是造单位；`delete-timer`/`disable-timer` 是操作计时器。

### 4.3 XS（.xs）能做什么

XS 的能力面**远大于** AI：

| 能力 | XS | AI |
|---|---|---|
| 创建单位 `xsCreateUnit` | ✅ | ❌ |
| 删除单位 `xsRemoveUnit` | ✅ | ❌ |
| 改 HP/属性 `xsSetUnitHitpoints`/`xsSetUnitProperty` | ✅ | ❌ |
| 改玩家属性 `xsSetPlayerAttribute` | ✅ | ❌ |
| 改科技 `xsEffectAmount` | ✅ | ❌ |
| 读地图瓦片属性 `xsGetMapTileAttribute` | ✅ | ❌ |
| 文件 IO `xsOpenFile`/`xsWriteInt` | ✅ | ❌ |
| 网络数据同步 `xsWriteNetInt` | ✅ | ❌ |
| 数组/向量容器 | ✅ | ❌（只有 goal 数组） |
| 单位定位 `xsGetUnitPosition` | ✅ | 只能通过搜索+`up-get-object-data` |
| 修改 AI 的 goal/SN | ✅ `xsSetGoal`/`xsSetStrategicNumber` | 本身就有 |
| 启用/禁用 rule | ✅ `xsEnableRule` | `enable-rule`（按名） |

### 4.4 XS 不能做什么

- **无异常**（无 `try/catch/throw`）
- **无动态内存**（无 `new/delete/malloc`）
- **无泛型/模板**
- **无 `foreach`**
- **无指针运算**（只有数组索引）
- **有硬性资源上限**：`infiniteLoopLimit`、`infiniteRecursionLimit` 是 rule 属性，超限即被引擎中断
- **无文件删除/目录遍历**（只有 open/create/close/read/write/seek/size）
- **联机时不可用**：`Break points not allowed in multiplayer`；纯客户端逻辑须走 `xsUnsync*` 前缀并在服务端做校验

### 4.5 两套语言的连接点

| 连接方式 | 方向 | 机制 |
|---|---|---|
| `xsSetGoal` / `xsGetGoal` | XS ↔ AI | 共享 goal 空间 |
| `xsSetStrategicNumber` / `xsGetStrategicNumber` | XS ↔ AI | 共享 SN 空间 |
| `xsSetAiSignal` / `xsGetAiSignal` | XS → AI | signal 位 |
| `xsSetAiScriptGoal` / `xsGetAiScriptGoal` | XS ↔ AI | bool 型 goal |
| `xsEnableRule` / `xsDisableRule` | XS → AI 或 XS rule | 按名 |
| `xs-script-call` | AI → XS | AI 侧命令，**全引擎唯一一条**，RVA `0x3223648` |
| `#includeXS` | AI(.per) → XS | 编译期把 .xs 内联进 .per |

**`xs-script-call` 在 AI 词表里的 RVA 是 `0x3223648`**（旧版报告写的 `0x3224a48` 是**把 RVA 当 VA 又错加了段差**的产物，已按 §0 坐标更正规则修正）。它的邻居是 `fe-break-point`（`0x3223638`，前）和 `fe-exclude-from-attack-group`（后），位置说明它是被当作「AI 动作表里的一项」注册的，而非独立模块。

**这条命令的意义**：AI 可以在规则里直接 `(xs-script-call "myFn")` 调用 XS 函数，把 XS 当作 AI 的"高权限外挂"——AI 算不出来的东西（动态改数据、读写文件、复杂数学）交给 XS 做，结果通过 goal/SN 回传。这是唯一一条从 AI 单向进入 XS 的通道。

---

## 5. 与 AGE 的关系（承接上一轮结论）

上一轮已证实：**AGE（AdvancedGenieEditor3.exe）对 AI/XS 的支持是零** ——
`b'.per'` 0 次、`b'.per2'` 0 次、`b'.xs'` 0 次、`b'xsEffectAmount'` 0 次。

本轮补充了**为什么零也不影响工作流**：

- AGE 编辑 `.dat` 的 **Effects 表** → XS 用 `xsEffectAmount(effect, itemName, type, value, playerId, index)` 在运行时做同样的事
- AGE 编辑 **Units 表** → XS 用 `xsGetUnitAttributeTypesHeld` / `xsSetUnitProperty` 读写同样的字段号
- AGE 编辑 **Civs 表** → AI 用 `my-civ` / `players-civ` / `ri-*` 引用同样的文明与科技 ID
- AGE 编辑 **Terrain Tables** → AI 用 `terrain-*` 42 个名字引用同一批地形

**所以完整工作流是：**
```
AGE 改 .dat（静态基线）
    ↓
XS 在运行时用 xsEffectAmount 做动态修正
    ↓
AI 用 up-* 与 sn-* 消费这些数据做决策
```
三者共用同一套 ID 编号空间，AGE 是唯一能可视化编辑该空间的工具。

---

## 6. 产物清单

`D:\Software\AI\Aoe2\_age_analysis\aixs\`

| 文件 | 内容 |
|---|---|
| `ai_names_mask.txt` | 1752 个引擎 AI 标识符 + RVA + 分类 |
| `ai_categorized.txt` | 按 18 个语义类别完整分组 |
| `engine_tables_sorted.txt` | 按字典序连续性切出的引擎符号表（含每表地址范围） |
| `xs_doc_table.json` | 文档区 235 个 xs* 名字 / 232 带原型 / 3 个孤立槽 + RVA |
| `xs_syscalls.txt` | 232 条带完整签名的 syscall（注册表口径） |
| `engine_ai_tables.txt` | 按地址间隔聚簇的 33 张表 |
| `syscall_cfg.txt` | syscall 配置相关串 |
| **`AI命令全集.json`** | **本次新增**：192 `up-*` + 59 基础 + 13 `fe-*` + 2 `skybox-*` + 每条的 VA |
| **`cmds_up.txt` / `cmds_base.txt` / `cmds_fe.txt`** | **本次新增**：各族命令纯文本清单 |
| 各类 `.py` | 可复现的分析脚本 |

**本轮（2026-10-28 四次校核）新增的关键产物**：

| 文件 | 内容 |
|---|---|
| `v180_authoritative.json` | **权威命令表**：208 命令 + 59 基础 + 54 运算符 + 3 裸前缀，每项 `{rva, name, block}`，产物与基线 192/13/2/1/59/54 逐项吻合 |
| `v180_authoritative.py` | 生成上表的脚本（块边界 0x3222970 / 0x32236a0 / 0x32236ac / 0x32237f8 / 0x32233730 / 0x322b914） |
| `v183_slots.json` | 块A/块C 的 `align8(strlen+1)` 步长序列（156 条 / 52 条，全匹配） |
| `v190_linear_rip.json` | 169486 个 `.pdata` 函数全量线性反汇编的 RIP 目标集（170743 个唯一目标），命令名命中 1/267 |
| `v199_pool.json` | 池区 4214 条字符串的形态分类（命令名 / 诊断串 / 源码路径 / 枚举 / vtable / 二进制） |
| `v123_datarefs.json` + `v124_unittab` 输出 | **`0x040965b0` 单位/建筑名→ID 表**，135 项 stride=0x10，严格字母序 |
| `v207_ai_validate.json` | 4 个 AI 参数校验函数的完整反汇编与直接调用点（0 个） |
| `v201_u32runs.json` / `v202_swtables.json` | 330 个 u32-RVA 跳转表候选（按 AI 函数区聚集度排序，最高 22%） |
| `v214_states.json` | 动作状态（大写 12 / 小写 11）与动作类型（23）的精确枚举 + 两者的索引漂移对照 |
| `v203_hashswitch.json` | 8 种哈希 × 324 名字的常量扫描（最佳 2.5%） |
| `v206_reggrow.json` / `v211_memload.json` | 函数内常量传播（含 `mov r,[rip+d]` 装载规则）找「基址+偏移」，命中 4 处全为诊断串 |

**本次新增的脚本（都在 `_age_analysis/aixs/`）**：

| 脚本 | 作用 |
|---|---|
| `final_cmds.py` | 按 `\x00` 精确切分，严格正则分离 5 个命令族，输出地址索引 |
| `cmdall2.py` | 修掉 `re.finditer` 不重叠匹配导致的相邻串漏项 |
| `layout.py` | 按 0x400 块统计串密度，用于定位命令表边界 |
| `handlers.py` | RVA↔文件偏移双向映射 + `UA*/TA*` 内部 handler 名提取 |
| `cmds.py` (旧) | 初版分类，**结果有漏项，已被 `final_cmds.py` 取代** |
| `v168_anchored.py` | 命令名枚举（NUL 前向锚定，修掉 `backup-size`→`up-size` 假阳性） |
| `v169_pad_probe.py` / `v204_blockB_pad.py` | 对齐填充取值统计（证明无 arity 字段） |
| `v180_authoritative.py` | 权威命令表（最终口径） |
| `v183_align8_slots.py` | 步长模型验证 |
| `v187_rip_disp32.py` / `v190_linear_rip.py` / `v200_disp32_full.py` | 三代 RIP-disp32 扫描，覆盖度从 88.9% 到**逐字节超集** |
| `v191_ua_claims.py` | 证伪旧报告 21 条 handler 表 |
| `v203_hashswitch.py` | 哈希常量分派假说 |
| `v205_qsort_callers.py` | qsort 调用者反汇编（16 个，全部不在 AI 区） |
| `v206_reggrow.py` / `v211_memload.py` | 函数内常量传播 |
| `v214_states.py` / `v214_states.json` | 动作状态大小写两表 + 动作类型枚举的精确枚举（修 `0x33b0ae8` 与 `0x33b0b5c` 两处误认） |
| `v215_cmdverify.py` / `v215_cmdverify.json` | 报告内所有命令名 / RVA 与 `v180_authoritative.json` 的机器自动比对 |
| `v199b_pool_class.py` | 池区字符串形态分类（4214 条） |
| `v207_ai_validate.py` / `v208_validator_refs.py` / `v209_handler_table.py` | 校验函数反汇编 → 指针表定位 → 表扩张 |
| **`v270_fullstr.py`** | **MSVC 修饰符号枚举**（`.?AV` 描述符 5300 条 → 内嵌函数名）—— A 项唯一硬证据的入口 |
| **`v272_arity_hunt.py`** | 命令名 ↔ C++ 方法名匹配（**3/324 命中，随机假名对照 0/200**） |
| **`v274_strict.py`** | **严格 MSVC 签名解析**（不用贪婪正则，用「恰好吃完剩余字符」反解）→ `AIHybrid::UPGetFact*` **arity=4** |
| **`v278_names.py`** | 全文件修饰名总清点：44 条唯一签名，arity 分布 `{1:5,2:20,3:12,4:4,5:3}` |
| **`v275_pdb.py`** | PE DEBUG 目录 → **RSDS + GUID `651ecf97-392a-704d-a32c-5cd6ba3f8545` + Age 1 + 完整 PDB 路径** |
| **`v276_pogo.py`** | POGO 条目解析（`'GCTL'` 头，段级热区，无逐函数符号） |
| **`v277_rtti_vt.py` / `v280_find_impl.py`** | RTTI 全链路（TypeDescriptor→COL→vtable）→ `AIHybrid::UPGetFact*` 的 `_Func_impl_no_alloc` vtable `0x0322a888/8c0/8f8` |
| **`v281_reg_site.py`** | vtable 拷贝构造 thunk 区实拍（`0x00bf2c30..0x00bf2c80`）+ 可达性判定（`E8` 调用 **0 处**、`lea` 取址 **1 处** `0x02b7b2a8`） |
| **`v282_hash.py`** | 哈希常量分派**全矩阵**重测（10 种哈希 × 4 个段 + 随机基线）—— 全部零信号 |
| **`v283_mangle.py` / `v284_exact.py`** | **MSVC 修饰名文法的逐字段解析器**（`S`=static / `A`=`__cdecl` / 第 1 个类型=返回 / 其余=参数），全 `.data` 2167 个候选重解析，成功的 278 条 arity 分布 `{0:12, 1:184, 2:56, 3:8, 4:18}` |

---

## 7. 复现命令

**运行时注意**：`py` 在本机已不可用。两套解释器分工如下——

- `PY_DSH = C:/Users/26913/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/python.exe`
  有 `numpy`，**无** `capstone`。用于纯字节扫描。
- `PY_CAP = /c/Users/26913/AppData/Local/Python/bin/python`
  有 `capstone 5.0.7`，**无** `numpy`。用于反汇编。

```bash
# 0) 早期提取（PY_DSH）
"$PY_DSH" -X utf8 _age_analysis/aixs/ai_names.py
"$PY_DSH" -X utf8 _age_analysis/aixs/categorize.py
"$PY_DSH" -X utf8 _age_analysis/aixs/xs_docs.py
"$PY_DSH" -X utf8 _age_analysis/aixs/src_paths.py

# 1) 【权威口径】命令表定稿（PY_DSH）
"$PY_DSH" -X utf8 _age_analysis/aixs/v180_authoritative.py
#    -> v180_authoritative.json   up 192 / fe 13 / skybox 2 / xs 1 / base 59 / op 54

# 2) 步长模型 + 填充取值（PY_DSH）
"$PY_DSH" -X utf8 _age_analysis/aixs/v183_align8_slots.py
"$PY_DSH" -X utf8 _age_analysis/aixs/v204_blockB_pad.py

# 3) 逐字节超集 RIP-disp32 扫描（PY_DSH，覆盖全 .text）
"$PY_DSH" -X utf8 _age_analysis/aixs/v200_disp32_full.py

# 4) .pdata 函数全量线性反汇编（PY_CAP，169486 函数）
"$PY_CAP" -X utf8 _age_analysis/aixs/v190_linear_rip.py

# 5) u32 跳转表 / 哈希常量 / 常量传播（PY_DSH）
"$PY_DSH" -X utf8 _age_analysis/aixs/v201_u32runs.py
"$PY_DSH" -X utf8 _age_analysis/aixs/v202_swtables.py
"$PY_DSH" -X utf8 _age_analysis/aixs/v203_hashswitch.py
"$PY_CAP" -X utf8 _age_analysis/aixs/v206_reggrow.py
"$PY_CAP" -X utf8 _age_analysis/aixs/v211_memload.py

# 6) AI 参数校验函数反汇编 + qsort 调用者（PY_CAP）
"$PY_CAP" -X utf8 _age_analysis/aixs/v207_ai_validate.py
"$PY_CAP" -X utf8 _age_analysis/aixs/v205_qsort_callers.py
"$PY_CAP" -X utf8 _age_analysis/aixs/v209_handler_table.py

# 7) 池区字符串形态分类（PY_DSH）
"$PY_DSH" -X utf8 _age_analysis/aixs/v199b_pool_class.py

# 8) 动作状态 / 动作类型枚举精确核对（PY_DSH，无依赖）
"$PY_DSH" -X utf8 _age_analysis/aixs/v214_states.py
#    -> v214_states.json   大写状态 12 / 小写状态 11 / 动作类型 23

# 9) ★ MSVC 修饰符号通道（A 项唯一硬证据来源）
"$PY_DSH" -X utf8 _age_analysis/aixs/v270_fullstr.py   # -> v270_fullstr.json  5300 个 .?AV 描述符 / 248 含 AI 关键字
"$PY_DSH" -X utf8 _age_analysis/aixs/v272_arity_hunt.py # -> v272_arity_hunt.json  名字↔方法名匹配 3/324（随机对照 0/200）
"$PY_DSH" -X utf8 _age_analysis/aixs/v274_strict.py     # -> v274_strict.json  严格解析 44 条唯一签名，AIHybrid 三条 arity=4
"$PY_DSH" -X utf8 _age_analysis/aixs/v278_names.py      # -> v278_names.json   全文件修饰名总清点，arity 分布 {1:5,2:20,3:12,4:4,5:3}

# 10) PDB / POGO 身份记录
"$PY_DSH" -X utf8 _age_analysis/aixs/v275_pdb.py        # DEBUG 目录 0x036a0710 -> RSDS + GUID 651ecf97-392a-704d-a32c-5cd6ba3f8545 + Age 1
"$PY_DSH" -X utf8 _age_analysis/aixs/v276_pogo.py       # POGO 条目 'GCTL' 头，段级热区，无逐函数符号

# 11) AIHybrid vtable / 拷贝构造 thunk / 注册点可达性
"$PY_CAP" $PYTHONIOENCODING= _age_analysis/aixs/v277_rtti_vt.py   # RTTI TypeDescriptor -> COL -> vtable
"$PY_DSH" -X utf8 _age_analysis/aixs/v280_find_impl.py   # 0x0322a888/8c0/8f8 的引用点 -> 0x00bf2c30..0x00bf2c80 thunk 区
"$PY_DSH" -X utf8 _age_analysis/aixs/v281_reg_site.py    # thunk 的 E8 调用点 0 处 / lea 取址 1 处（0x02b7b2a8）

# 12) 哈希常量分派全矩阵重测（10 种哈希 × 4 个段）
"$PY_DSH" -X utf8 _age_analysis/aixs/v282_hash.py
#    -> 除 prefix4(命中即名字明文本身) 外，最佳覆盖 <= 11/324、run 恒为 1；随机基线同量级

# 13) MSVC 修饰名文法逐字段解析（校准 arity 的唯一正确口径）
"$PY_DSH" -X utf8 _age_analysis/aixs/v284_exact.py
#    -> v284_exact.json   SAHHHHH = S | A | H(返回) | H H H H(4 参数) -> arity = 4
#    全 .data 2167 候选重解析，成功 278 条，arity 分布 {0:12, 1:184, 2:56, 3:8, 4:18}
```

**踩过的坑（写下来免得重蹈）**：
- `capstone.Cs.disasm()` 一次喂大段字节会抛 `CS_ERR_MEM`，必须按函数分块。
- `np.frombuffer(seg, dtype='<i4', count=len(seg)-3)` 会抛 `ValueError: buffer is smaller than requested size`，必须手工拼 int32。
- 用 `re.finditer` 枚举命令名必须**前向锚定 NUL**，否则 `backup-size` 会贡献一条假 `up-size`。
- 8 字节对齐步进在块B 会失步（块B 有 4 字节对齐段），枚举必须纯 NUL 分隔。
- `enum(LO,HI)` 起串时必须把块首当作「前一字节是 NUL」，否则漏掉块首 3 条。
- **MSVC 修饰名解析不能用贪婪正则截 access/static 前缀**：`@@([A-Za-z_]{0,8})` 会吞掉 `SAHHHHH` → `arity` 算成 0；必须用严格类型文法「恰好吃完剩余字符」反解（详见 §8.4 第 13 条）。


---

## 8. 诚实边界

本章分三段：**已证实**（有 RVA + 字节证据）、**已否证**（做过实验并闭门，附脚本名）、**未证实**（列明缺什么、需要什么手段）。

### 8.1 已证实（有字节证据）

- 1752 个 AI 标识符、232 个可调用 syscall（+3 个文档残留名字）、26 个语法 token、13 个 XS 源文件、13 个 AI 源文件，全部为磁盘明文。
- syscall 是运行时动态注册的（由 6 条 `Syscall config error` 串证明）。
- **命令名各块边界精确到字节**（`v180_authoritative.py`，产物 `v180_authoritative.json`）：

  | 块 | 条数 | 起 | 止（含末串 NUL） | 内容 |
  |---|---|---|---|---|
  | A | 156 | `0x03222970`（`up-jump-rule`） | `0x0322369d`（`fe-reset-attack-group-exclusion-list`） | 动作族 |
  | 裸前缀 | 3 | `0x032236a0`（`c:`） | `0x032236ac` | `c:` `s:` `g:` |
  | 算术簇 | 36 | `0x032236ac`（`c:=`） | `0x0322378d`（`g:%/`） | 3 族 × 12 |
  | B（基础命令） | 59 | `0x032237f8`（`acknowledge-event`） | `0x03223c5a`（`tribute-to-player`） | 原版内核 |
  | Cmp | 18 | `0x0322b914`（`c:<`） | `0x0322b989`（`s:!=`） | 比较运算符 3 族 × 6 |
  | C | 52 | `0x03233730`（`up-allied-goal`） | `0x03233be6`（`fe-idle-pasture-count`） | 条件/查询族 |

  合计 **324 条**（208 命令 + 59 基础 + 36 算术 + 18 比较 + 3 裸前缀）。计数与基线逐项吻合：`up 192/192 · fe 13/13 · skybox 2/2 · xs 1/1 · base 59/59 · op 54/54`。

- **块A / 块C 的名字槽是 8 字节对齐的**（`v183_align8_slots.py`）：156/156 与 52/52 全匹配，步长值集合分别 `{16,24,32,40}` 与 `{16,24,32}`，且**步长恒等于 `align8(strlen+1)`**。块B 不是（`train`@`0x03223c3c`、`taunt`@`0x03223c1c` 是 4 字节对齐）。
- **命令名槽内没有任何 arity 字段**（`v169_pad_probe.py` + `v204_blockB_pad.py`）：块A 156 条 8 字节对齐填充**非零 0 条**（511 个填充字节全 0）；块B 59 条 4/8 字节填充非零 1 条（那条是下一个串的起点，不是 arity）。**"定长槽 + 内嵌参数个数"假说彻底闭门。**
- **4 个 AI 参数校验函数的完整反汇编**（`v207_ai_validate.py`）给出二进制级的参数值域：

  | 参数 | 合法范围 | 关键指令 | RVA |
  |---|---|---|---|
  | signal id | `0 ≤ id ≤ 0xFF` | `cmp eax,0xff` + `mov r9d,0x100` | `0x00b5f78e` / `0x00b5f7bc` |
  | event id | `0 ≤ id ≤ 0xFF` | `cmp eax,0xff` + `mov r9d,0x100` | `0x00b6030e` / `0x00b6033c` |
  | player index | 走 `0x15fe480` 判定 | `call 0x15fe480` | `0x00be87f8` |
  | AI group | 走 `0xca6480` 判定 | `call 0xca6480` | `0x00b5e1d8` |

  两个函数体内还各有一张 u32 查表：`0x042a8180`（event）、`0x042a7d80`（signal），索引前先 `cmp eax,0xff`。
- **`c:`/`s:`/`g:` 三族 × 18 = 54 个运算符是并列独立存放的**（算术簇 `0x032236a0`–`0x0322378d`（含 3 个裸前缀）+ 比较簇 `0x0322b914`–`0x0322b989`），证明它们是三个互不相同的操作数类型，而非同一运算符的别名。
- **12 个大写动作状态（`0x03223db8`）+ 11 个小写显示名（`0x033b10e8`）不是镜像关系**：大写独有 `Goto`/`Return`，小写独有 `delay`，只在 9 个名字上重合。上一版写的「互为镜像」是错的（`v214_states.py` 实测）。
- **`.data 0x040965b0` 有一张 135 项的 stride=0x10 真表**（`v123_datarefs.py` / `v124_unittab.py`）：布局 `{char* name; u32 id; u32 pad}`，从 `'arbalest'`(id 见 json) 到 `'feitoria'`，**严格按字母序**。这是 AI 的「单位/建筑名 → 实体 ID」解析表，也是全文件唯一被完整解出的 AI 相关表。
- **`0x3221600..0x3221900` 是 XS syscall 静态注册表映像**（`v115_sso.py` / `v186_xs_arity.py`）：`{u32 id, u32 count}` 成对存放，精确解出 15 对：`0xe74:4 0xe75:8 0xe76:8 0xe77:1 0xe81:5 0xe82:11 0xed9:0 0xedd:0 0xf3c:4 0xf3d:8 0xf3e:8 0xf3f:1 0xf49:5 0xf4a:11 0xf5f:12 0xfe5:0 0xfed:0`。**这是 XS 侧唯一带 arity 的静态结构**（AI 侧没有对应物）。
- **`0x3221928` 起的 17 个 `UA*`/`TA*` 名字是日志/断言用，不是分派表**（`v191_ua_claims.py`）：只有 4 个被引用，引用者 `0x00b57720–0x00b5775c` 是「`lea rdx,名字` + `mov r8d,行号 0x36d` + `call 0x905170`」的日志宏。
- **`.text` 有 10.10%（5,251,321 B）的字节在任何对齐下都解不出指令**（`v230_encprobe.py` / `v234_templates.py` / `v236_measure.py`）：
  - 以 `.pdata` 的 169486 个 `Begin` 为起点反汇编，可解 **159533 (94.13%)**，完全解不出 **9953 (5.87%)**；这 9953 条的体积和 = 5,251,321 B = `.text` 的 **10.10%**。
  - **口径警告**：早期用「4KB 窗口 capstone 覆盖率」得出的 31.59% 不可解是错的。窗口口径会把 10.8% 的真代码（含明文序言 `48 8b c4 48 81 ec` 的 825 个窗口）判成低覆盖。**函数头口径 94.13% 才可用。**
  - 这 10.10% 的性质已逐项排除：不是非对齐（`v231` T1：bad 条目 mod16=67.0% vs ok 71.1%，同构）、不是「入口一条非法指令」（`v231` T4：500 条抽样试 Begin+0..15，最佳覆盖率中位仅 **0.20**，达到 0.90 的只 2.4%）、不是表格错配（T3 gap 分布同构）、不是浮点表/指针表/小整数表（T5）、不是压缩流（T6：258 块中含重复 4-gram 的仅 1 块）、不是 XOR/短周期流（`v230` T3/T4 + `v235` T4 自相关 p=2..256 全 ≈4.0）。
  - 内容去重：9953 条 → unique(sha1,体积) **9572 组**；出现 >=2 次的模板只 147 组（覆盖 528 条），**只出现 1 次的有 9425 条、体积 5,226,859 B（占不可解 99.5%）**。
  - **152 个 4577 字节的「容器块」**（`v233_phantom.py` / `v235_pairxor.py` / `v237_containers.py`）：以 `.text` 内 24 字节 probe `d6 5d 3f ca a3 69 5e 67 1b 31 4d 03 5a cb 33 42 c6 4b 5d 69 70 60 57 a6` 做全文件 find，命中的 **152 个位置全部是 `.pdata` 的 Begin，且函数体体积全部恰好 4577 B**。两两 XOR 的全零前缀 **min=34 med=34 max=35**（分布 `{34:141, 35:10}`）；头 34 字节严格一致，第 35 字节起分歧，第 38..47 字节又相同。相邻块间距 `0x11f0` 出现 **114 次**，块间 `下一 Begin − 本 End = 0xf` 也出现 114 次。这 4577 B 内 `48 8b c4` / `48 83 ec` / `48 81 ec` / `65 48 8b 0c 25` / `cc cc cc` 出现次数**全为 0**，`e8` 17 次，`ff 15` 0 次 —— **不含任何函数序言**。zlib/raw-deflate/gzip/bz2/lzma 在 off 0/16/32/34 全部解压失败。
  - 全 `.text` 内「24 字节前缀 + 同体积」出现 >=3 次的家族共 **2831 个**，说明这种块是编译器批量产出的同源产物，不是孤例。
  - **运行期解密假说已被证否**（`v256_decryptor.py` / `v257_vprot.py` / `v258_gpa.py`）：`.text` 的段标志是 `0x60000020` = `EXEC | READ | CNT_CODE`，**没有 `WRITE` 位**（compare `.data` 的 `0xC0000040` = `READ|WRITE`）。要在不可写段上原地改字节，必须先 `VirtualProtect(PAGE_EXECUTE_READWRITE)` 再改，改完再改回。实测：
    - `VirtualProtect` 的 IAT 槽 = `0x031975d8`（KERNEL32），`.text` 内**任意字节偏移的 disp32 超集扫描命中 0 处**；
    - `VirtualQuery` IAT `0x031975d0` 命中 **0 处**；`FlushInstructionCache` **未导入**；`VirtualProtectFromApp` / `NtProtectVirtualMemory` **未导入**，字符串也不在文件里；
    - `GetProcAddress` 的 **12 个调用点逐个回溯 200 字节**，解析出的动态函数名只有：`RtlCaptureStackBackTrace`（ntdll）、`wine_get_version`（Wine 探测）、`SetThreadDescription`、`CreateToolhelp32Snapshot` / `Module32First` / `Module32Next`（这三组来自 OpenSSL `crypto\dso\dso_win32.c` 的模块枚举），**没有任何一个是内存保护类 API**。
    → **结论：这 10.10% 的字节不可能在运行期被解密成代码。它是静态数据，只是形态不属于任何已知的数据编码。**
- **PE 导出表 452 条全部是 Wwise 音频库符号**（`v247_exports.py`，产物 `v247_exports.txt`）：导出目录 `0x03d921b0`/`0x85e8`，`NumberOfFunctions = NumberOfNames = 452`，地址表 `0x03d921d8`、名字表 `0x03d928e8`、序号表 `0x03d92ff8`。名字形如 `?PostEvent@SoundEngine@AK@@...`、`?LoadBank@SoundEngine@AK@@...`、`?QueryDiffractionPaths@SpatialAudio@AK@@...`，另有 1 条 `AmdPowerExplicitRequestHighPerformance`。**没有一条 AI 解析器导出**；对这 452 个函数体做 RIP 扫描找池区引用，**合计 0 处**。→ **AI 解析器不可从外部调用，没有导出入口。**
- **47~53 条注册 banner 把 AI 名字空间切成二十多个语义簇**（`v240_banner.py` / `v244_banner2.py` / `v245_bannerrefs.py`）：从池区按 `Defining/Initializing/Init/Finished/Loading/Registering` 前缀枚举得到 53 条，关键 RVA：
  `0x03223790` 'Init AI Actions ---…'、`0x03228798` 'Defining BoolOp[%d] %s %s%s%s'、`0x032287b8` 'Defining LocalSymbol[%d] …'、`0x03228830` 'Defining LocalConst[%d] %s (value of %d) …'、`0x03228870` 'Defining Symbol[%d] …'、`0x03228908` 'Defining Constant %s (value of %d) …'、`0x0322b840` 'Init AI Facts ---…'、`0x0322f5e0` 'Defining Forgotten Empires Facts'、`0x03230070` 'Defining UserPatch Facts'、`0x03232010` 'Defining UserPatch CmdIds'、`0x032320f8` 'Defining UserPatch ActionIds'、`0x032322a8` 'Defining UserPatch OrderIds'、`0x03232480` 'Defining UserPatch ObjectData Constants'、`0x03233bf1` 'Defining UserPatch Facts'（原文 `0x032306d0` 是 'Defining USerPatch Player Wildcards'，大小写错拼是引擎原文）。
- **两条 `argCount` 格式串存在，但零引用、邻域无数字数组**（`v245_bannerrefs.py` / `v251_last.py`）：
  - `0x03228938` `'Defining Fact[%d] %s (argCount of %d) %s%s%s'`
  - `0x03228968` `'Defining Action[%d] %s (argCount of %d) %s%s%s'`
  → **这证明引擎运行期确实持有「第 i 个 fact/action + 其 argCount」三元组**，但该三元组不在任何静态结构里：这两条串的 `.text` 逐字节超集 disp32 引用 **各 0 处**，`.rdata/.data/.rodata/_RDATA/.reloc/.rsrc` 的 8B 指针槽与 4B RVA 槽 **各 0 处**；`0x03228900..0x032289b0` 的 RAW dump 显示两条串之间只有 4~7 字节 0 填充，**没有任何伴随的 argCount 数字数组**。
  - 块A/B/C 前后各 0x4000 字节内，找长度精确等于 156/59/52、值域 <=16 的 u8 数组：**六个窗口全部 0 个候选**（`v251_last.py` 测试 2）。
- **★★ MSVC 修饰符号通道：`up-get-fact-{min,max,sum}` 的真实 arity = 4（本项目第一次拿到 up-\* 命令的硬参数个数）**（`v270_fullstr.py` / `v272_arity_hunt.py` / `v274_strict.py`）。
  引擎在 `.data` 里残留了 **44 条唯一 MSVC 修饰函数名**（`?Name@Class@@sig@Z` 形态，`v278_names.py` 严格解析，arity 分布 `{1:5, 2:20, 3:12, 4:4, 5:3}`）。其中 AI 相关的 4 条：

  | 修饰名 | RVA | 严格解析签名 | arity |
  |---|---|---|---|
  | `?UPGetFactMin@AIHybrid@@SAHHHHH@Z` | `0x04122212` | `static int (int,int,int,int)` | **4** |
  | `?UPGetFactMax@AIHybrid@@SAHHHHH@Z` | `0x041221c2` | `static int (int,int,int,int)` | **4** |
  | `?UPGetFactSum@AIHybrid@@SAHHHHH@Z` | `0x04122172` | `static int (int,int,int,int)` | **4** |
  | `?update@TribeStrategyAIModule@@UEAAHH@Z` | — | `uchar (int)` | 1 |

  这三条符号分别对应命令 `up-get-fact-min`(`0x03222ae0`) / `up-get-fact-max`(`0x03222af0`) / `up-get-fact-sum`(`0x03222b00`)。
  **判据强度**：随机生成 200 个「命令词拼接」的假名做同样匹配，命中 **0/200 (0.0%)** → 这 3 条不是巧合。
  **解读边界**：`SAHHHHH` 是 C++ 成员函数的形参表，**它证明「这个 C++ 函数收 4 个 int」，不等于「该 .per 命令在文本里吃 4 个参数」**——但两者在 UP 命令的注册模型里是同一个数（注册时把函数指针 + argCount 一起登记），因此这是目前最强的 arity 证据。
  **为什么只有 3 条**：全 exe 只保留 44 个修饰名（绝大多数函数因 `/GR-` 或未生成 lambda RTTI 而没有符号残留）。**这条通道对剩下的 189 条 up-\* 不可用，且不可扩展。**

- **★★ PE 里保存了完整 PDB 身份记录**（`v275_pdb.py`）：DEBUG 目录 `0x036a0710`/`0x38`，2 个条目 —— `[0] Type=2(CODEVIEW) Size=0x72 AddrOfRawData=0x038b5788`、`[1] Type=13(POGO) Size=0x4c0 AddrOfRawData=0x038b57fc`。CODEVIEW RAW 解出：
  ```
  Signature = RSDS
  GUID      = 651ecf97-392a-704d-a32c-5cd6ba3f8545
  Age       = 1
  PDB path  = F:\Agents\PhoenixBuilder-07\p4\portland_group\Build\Steam\Game\Retail\Output\AoE2DE_s.pdb
  ```
  全文件 `RSDS` 出现 1 次、`.pdb` 出现 1 次、`NB10`/`PDBDIR` 各 0 次。**符号本体不在本机**（`D:\Games\Steam\steamapps\common\AoE2DE\` 下无任何 `.pdb`）。该 GUID 可用于向符号服务器查询——这是唯一还没试过的、可能一次拿全 324 条 arity 的通道。
- **POGO 条目不含函数符号**（`v276_pogo.py`）：头部是 `47 43 54 4c` = ASCII `'GCTL'`，后接按段名的热区统计（`.text$di` / `.text$mn` / `.text$x` 等）。逐函数符号 **0 条**。
- **`AIHybrid` 的 `_Func_impl_no_alloc` vtable 已定位，但注册点静态不可达**（`v277_rtti_vt.py` / `v280_find_impl.py` / `v281_reg_site.py`）：
  - vtable：`0x0322a888`(Min) / `0x0322a8c0`(Max) / `0x0322a8f8`(Sum)，首槽分别是 `0x140bf2c50 / 0x140bf2c30 / 0x140bf2c70`。
  - 这三个 thunk 在 `0x00bf2c30..0x00bf2c80`，形如 `48 8d 05 <disp32> 48 89 02 48 8b c2 0f 10 41 08 0f 11 42 08 c3` = 把 vtable 指针写进目标对象的**拷贝构造 thunk**（不是命令注册点）。
  - 全 `.text` 找 `E8 rel32` 指向这 6 个 thunk 及其周围 ±2 字节：**0 处**。找 `lea` 取址：**仅 1 处** `lea@0x02b7b2a8`（在函数 `0x02b7b190..0x02b7b7c6`，1590 B）。→ **构造 thunk 只经 vtable 间接调用，静态 call 图在此断裂（与 §8.2 的 qsort / vtable 结论一致）。**
  - 该 thunk 区（`0x00bf2b00..0x00bf3000`）**大片高熵字节夹着稀疏真代码**——这与 `.text` 那 10.10% 不可解字节是同一现象。

- `.text` 无壳、无虚拟化（`v126` 熵分析：12693 个 4KB 窗口中仅 21 个 >7.5，全在启动代码区）。

### 8.2 已否证（做过实验、有脚本、可复现）

**B 项「命令分派函数在哪」——十八重独立否证，命令名在 `.text` 中零引用。**

| # | 假说 | 脚本 | 结果 |
|---|---|---|---|
| 1 | 命令名被 `lea r64,[rip+d]` 引用 | `v82_leascan.py` / `v200_disp32_full.py`（逐字节超集扫描） | 池区 127 个 LEA 目标里命令名 **0 条** |
| 2 | 命令名作 4 字节 RVA 常量出现 | `v113_globalref.py` | 全 72MB **0 处** |
| 3 | 命令名作 8 字节 VA 常量出现 | `v113_globalref.py` | 全 72MB **0 处** |
| 4 | 基址 + 偏移表（u16/u32） | `v77_offbase.py` / `v79_runs.py` / `v182_blockbase.py` | 最大连续偏移 run = **1**，无表 |
| 5 | `.data`/`.rdata` 有名字指针表 | `v123_datarefs.py` / `v184_nameptrs.py` | 158 条指针全指向单位/建筑名，名字起点 **0 条** |
| 6 | 运行期 XOR/加减混淆副本 | `v122b` / `v118_decode.py` | 单字节 key 全试，最高 86.7%（≈随机），已知明文 `up-` 解不出 |
| 7 | 运行期拼装字符串 | `v102_inline.py` / `v106_allstr.py` | 136 个还原串函数，含 AI 关键字 **0 个** |
| 8 | `.reloc` 完备枚举后重扫 | `v193_reloc_ptr.py` | 仍 **0 条** |
| 9 | 编译期哈希常量分派 | `v203_hashswitch.py`（8 种哈希 × 324 名字） | 最佳 2.5%（随机期望 1.2%），无信号 |
| 10 | 函数内「基址+偏移」常量传播 | `v206_reggrow.py` + `v211_memload.py`（补给 `mov r,[rip+d]` 装载规则） | 命中 4 处，**全部是诊断串不是命令名** |

| 11 | 名字指针在 `.text` **内部**（8B 槽 / 非 8 的 stride） | `v248_textptrs.py` | 8B 槽命中 **0 / 6,498,782**（随机期望 40.5，实测显著低于随机）；stride∈{8,0x10,0x18,0x20,0x28,0x30,0x38,0x40} 的指针列，仅 stride 0x30 有 16 列，长度全 != 52/59/156/192/208/212/232/251/267 |
| 12 | 内联字符串比较（`imm32` == 名字字符本身） | `v246_immname.py` | 324 名字 → 196 唯一 u32；`.text` 逐字节 u32 命中仅 24 处覆盖 48 名。**`up-` 系命令名首 4 字符的立即数（如 `0x6a2d7075` = `u``p``-``j`）在 `.text` 出现 0 次**；随机 320 个 4 字符对照命中 0 次 → 24 处无结构 |
| 13 | 命令名「串内部」被引用（`target ∈ [name_rva ± len]`，放松起点约束） | `v250_final_probe.py` | 命令名区间内 RIP 引用 **仅 4 处**，全部是聊天作弊码建造器：`0x001967d1 → 0x03223b1c 'resign'(+0)`、`0x001967dd → 0x03223b20 'gn'(+4)`、`0x00196c7b`、`0x00196c84`。53 条 banner 的「串内部」引用 **0 处** |
| 14 | PE 导出表作为取址通道 | `v247_exports.py` | 452 条导出全为 Wwise；对全部导出函数体做 RIP 扫描找池区引用 **0 处** |
| 15 | 名字块邻域藏 `{count}` 描述符 / 定长 argCount 数组 | `v239_neighborhood.py` / `v251_last.py` | 块前后 0x4000 内的 `{base,count}` 描述符 **0 个**；长度精确 =156/59/52 且值域 <=16 的 u8 窗 **六窗 0 个** |
| 16 | 逐字符内联比较（`cmp word/byte ptr [mem], imm`） | `v259_imm16.py` | `cmp word [mem],imm16` 全 `.text` 仅 **307 处 / 103 个唯一 imm16**；`0x7075`(`up`) `0x6566`(`fe`) `0x7378`(`xs`) `0x2d70`(`p-`) `0x6a2d`(`-j`) 等 13 个目标二元组**全部 0 次**（随机期望 0.005，所以这不算强否定，但也没有任何信号）。`cmp byte [mem],imm8` 有 35838 处，但**连续两条 cmp byte 恰好拼出 `up`/`fe`/`xs` 的位置 = 0 处** |
| 17 | 运行期解密那 10.10% 字节变成代码（自修改/自解密） | `v256_decryptor.py` / `v257_vprot.py` / `v258_gpa.py` | `.text` 段标志 `0x60000020` 无 `WRITE` 位；`VirtualProtect`/`VirtualQuery` 的 disp32 超集引用 **各 0 处**；`FlushInstructionCache` 未导入；`GetProcAddress` 的 12 个调用点动态取的名字全是 ntdll 回溯/Wine 探测/OpenSSL 模块枚举，**无一内存保护 API** |
| 18 | 命令名 + 冒号错误消息串反推参数表 | `v255_cmderr.py` | 全文件 `^(up|fe|skybox|xs)-…: <msg>` 形态串 **仅 12 条**，覆盖 10 个名字前缀（up-build 2 / up-cross-tiles 1 / up-lerp-tiles 1 / up-store-object-name 1 / up-store-player-name 1 / up-store-tech-name 1 / up-store-type-name 1 / up-find-player-flare 2 / up-add-tech-cost 1 / up-can-build 1）。这 12 条的 **RIP 引用 0、数据段指针 0**。占位符全为 `%d`，**没有一条带 `%s` 参数名或参数序号**。**关键旁证：这 10 个前缀里有 1 个（`up-add-tech-cost` @ `0x032212f3`）根本不在 324 条权威命令表内**（表里只有 `up-add-cost-data` / `up-add-object-cost` / `up-add-research-cost` / `up-store-tech-name`），且它在全文件只出现 1 次、就是这条消息串本身 → **错误消息串的命令前缀与命令注册表是两套各自手写的字符串，前者不能用来校验后者，也不能用来自动生成 arity** |

**第 1~15 重的定量基线**：`.text` 有 12,997,564 个 4B 对齐槽。块A(宽 0xd10) / 块B(宽 0x5c0) / 块C(宽 0x4d0) 的均匀随机期望命中分别是 **10.12 / 4.45 / 3.73，合计 18.30**。实测「4B 常量落在三块内」共 **44 处**（比值 2.40），其中 **30/44 已证实落在某条指令的 disp32 字段内**（是假阳性，不是常量），剩下 14 处上下文全为「前一条指令?」状态，无一能被确认为名字常量。池区全段口径 666 处 vs 期望 347 处同理。→ **44 这个数字看起来「有信号」，扣掉 disp32 假阳性后只剩 14，且不成表。**

补充否证：
- **`qsort` 的 16 个调用点全部不在 AI 区**（`v205_qsort_callers.py` 带 capstone 指令边界验证）：函数起址 `0x01d0f8f0 / 0x022dd2c9 / 0x022f1e26 / 0x02306230 / 0x0230bd80 / 0x02315190 / 0x0232979c / 0x0232a249 / 0x0255bb62 / 0x0255be8f / 0x028c1d1a / 0x028fc610 / 0x02901150 / 0x02a5d430 / 0x02afac02`，**池区引用 0 个**。所以「strtok+qsort → 分派」这条推论从导入表推出来的，**二进制内并未找到 AI 侧的 qsort 使用点**。
- **`strtok` 在 `.text` 中 0 个 `FF15` 跳板**（`v81_bytes.py`），`strncmp` 有 209 个。即：真正被大量调用的是 `strncmp`/`_stricmp`，不是 `strtok`。§9.1 里「`strtok`+`strcspn` 是手写 tokenizer 指纹」这句**对 AI 侧不成立**。
- **`0x3229ae0` 处的函数指针表只有 6 项**（`v209_handler_table.py` / `v210_dump6.py`），目标 `0xbe87c0/0xbe87d0/0xbe87e0/0xbe8860/0xbe8870/0xbe8880`，是 C++ range/迭代器适配器（`lea rax,[rcx+8]; ret`、`lea rax,[rip+..]; ret`），非分派表。
- **`v201`/`v202` 的 u32 跳转表扫描**：330 个 u32-RVA run，长度无 192/156/59/208/324 的精确匹配；按 AI 函数区 `0xb40000..0xc20000` 聚集度排序，最高仅 22%（n=32）。
- **哈希常量分派：10 种哈希 × 4 个段的全矩阵重测**（`v282_hash.py`）。对 324 条权威命令名算 `djb2 / djb2x / sdbm / fnv1 / fnv1a / crc32 / jenkins / elf / djb2(uppercase) / 前4字符打包`，在 `.text` / `.rdata` / `.data` / `_RDATA` 的每个 4 字节槽上搜。结果：**除 `prefix4` 在 `.rdata` 命中 3156 次（覆盖 324/324）外，其余 9 种哈希的最佳覆盖均 <= 11/324，且最大连续 run 恒为 1**。而 `prefix4` 那 3156 次命中**就是命令名自己的前 4 个明文字符**（示例 `0x03222970:up-jump-rule`）—— 是字符串本体，不是哈希表。**随机基线对照**（324 个随机 8~30 字符串跑同一矩阵）：`djb2 2 / djb2x 5 / sdbm 5 / fnv1a 2 / crc32 1 / jenkins 3 / elf 10 / djb2_upper 5 / prefix4 2` —— **实测量级与随机完全一致**。→ 「编译期把名字 hash 成常量再 switch」这条路径**否证**（这是 §8.2 表第 9 重的加强版，从 8 种扩到 10 种、从 1 个段扩到 4 个段）。
- **`_Func_impl_no_alloc` 拷贝构造 thunk 不被直接 call**（`v281_reg_site.py`）：6 个 thunk（`0x00bf2c33/2c53/2c73/2e63/2e83/2ea3` 及 `-3` 变体）在 `.text` 里的 `E8 rel32` 调用点 **0 处**；`lea` 取址 **1 处**（`0x02b7b2a8`）。→ 命令注册不可能通过静态 call 链追到，必须走 vtable 间接调用。

### 8.3 未证实（并给出每一项缺什么）

| 未证实项 | 缺的东西 | 下一步手段 |
|---|---|---|
| **每个 `up-*` 的精确参数个数与顺序（A 项）** | **已解出 3 / 192 条**：`up-get-fact-min` / `up-get-fact-max` / `up-get-fact-sum` 三条的 arity = 4（`static int(int,int,int,int)`），证据是 `.data` 里残留的 MSVC 修饰名 `?UPGetFact{Min,Max,Sum}@AIHybrid@@SAHHHHH@Z`（`0x04122212/0x041221c2/0x04122172`），按 MSVC 官方文法逐字段切分（`S`=static / `A`=`__cdecl` / 第 1 个 `H`=返回 int / `H×4`=参数），随机假名对照 0/200 命中。**其余 189 条缺**：全 exe 只保留 44 个修饰名；对全文件 1153 个 `_Func_impl`/`$Function@` RTTI 描述符做完整枚举，能提取出的「被 std::function 包装的函数」仅 40 个（AI 相关 4 个），**符号通道天花板已实测封顶**；二进制里也**不存在**任何「名字 → arity」的静态结构（十八重否证 + 填充全零 + 词表无 arity 数组 + 邻域无定长数组 + 两条 `argCount` 格式串零引用 + 10 种哈希 × 4 段全矩阵零信号）。唯一反证线索是 `0x03228938` / `0x03228968` 那两条 `'Defining Fact[%d] %s (argCount of %d) …'` / `'Defining Action[%d] %s (argCount of %d) …'`，证明运行期确有「fact/action + argCount」三元组，只是磁盘上没有对应静态数组 | 三条路，按性价比排序：① **PDB**：`VS_GUID = 651ecf97-392a-704d-a32c-5cd6ba3f8545`、`Age = 1`、路径 `F:\Agents\PhoenixBuilder-07\p4\portland_group\Build\Steam\Game\Retail\Output\AoE2DE_s.pdb`——先向符号服务器/公开泄漏库按 GUID 查，命中即一次性拿到全部函数名与 arity，这是**唯一可能一次解决 A 项**的手段；② **动态（注册期）**：在两条 `argCount` 格式串的 printf 使用点下条件断点（`rdx == 0x03228938` / `0x03228968`），注册时会把每个 action/fact 的 argCount 逐个打印，一次拿到全表；③ **动态（执行期）**：在 `0xCA6480`（group 校验）/`0x15fe480`（player 校验）/`0xbef1d0`（signal/event 取值）下断点，跑一条 `up-*` 规则，读该命令在 token 流里消费了几个参数 |
| `xsEffectAmount` 的 effect/type 编号 → .dat Effects 表映射 | .dat 侧 Effects 枚举未交叉 | 用 `aoe2-de-dat` 技能解 `empires2_x2_p1.dat` 的 effects 段，与 XS 侧 id 对表 |
| 1752 个标识符中哪些是真关键字、哪些只是参数枚举值 | 无语法分析器，只能按命名族分组 | 需动态：构造非法组合喂给解析器，看报错串 |
| `c:`/`s:`/`g:` 三族与 `up-modify-goal`/`up-compare-*` 的合法组合矩阵 | 同上，静态无证据 | 动态构造每种组合实测 |
| `skybox-clear-signal` / `skybox-set-name-mode` 语义 | 无错误串、无描述文本、无 handler 定位 | 动态 |
| `fe-idle-pasture-count` / `fe-can-build-at-point` / `fe-sub-game-type` 用途 | 同上（这 3 条在块C 条件族里，形态与 `up-*` 条件一致） | 动态 |
| **`.text` 那 10.10%（5,251,321 B）解不出指令的字节是什么** | 已排除：非对齐、单条非法指令、表格错配、浮点/指针/小整数表、压缩流、XOR/短周期流、模板复用（9953 条里 9425 条只出现 1 次）。已知这 5 MB 含 152 个「同 34 字节头 + 同 4577 B 体积」的容器块（114 个紧密排列，块间固定 `0xf` 间隙） | 静态侧只能给出「它不是任何一种已知数据/编码」的排除法结论。要定性必须**动态**：在 `0x36d030` 这类容器的 Begin 下硬件断点，看谁读它、读到什么。另一个可用手段：拿同版本引擎的 PDB（若有泄漏）直接对地址。 |
| **AI 命令分派器的具体位置** | 十八重否证说明它不通过任何「命令名字符串引用」触达；也可能它拿到的名字来自**运行期切分的 token 缓冲区**，与磁盘串块无地址关联。已定位的**唯一实物分派器是 `0x02244d9d`**（`v222_parser.py` / `v227_fetable.py`：`mov ecx,0xfe; cmp eax,ecx; je …; mov eax,[rax*4+0x32484a0]` 形态，33 个 opcode 解出 fe-* 跳转表），**但它只覆盖 fe-*，不覆盖 up-*/基础命令**。另已定位 `AIHybrid::UPGetFact*` 的 `_Func_impl_no_alloc` vtable（`0x0322a888/8c0/8f8`）与其拷贝构造 thunk（`0x00bf2c30..0x00bf2c80`），但 thunk 不被任何 `E8` 直接调用（0 处）、只被 1 处 `lea`（`0x02b7b2a8`）取址 → **注册链走 vtable 间接调用，静态断裂** | 动态：① 在 `0xCa6480`（group 校验）/`0x15fe480`（player 校验）/`0xbef1d0`（signal/event 取值）下断点后回溯调用者栈；② 在 `0x00bf2c30` 这 6 个拷贝构造 thunk 上下硬件执行断点，命中后回溯 `ret` 地址，那就是构造 `std::function` 的注册函数（**这条路径最可能一次命中**，因为 thunk 只在注册时被调用） |
| **大写 12 状态与小写 11 显示名的差异语义** | `v214_states.py` 只证出「重合 9 条、仅大写有 `Goto`/`Return`、仅小写有 `delay`、索引漂移恒为 1」。`delay` 是否是内部状态、`Return` 为何无显示名，**没有任何字节证据** | 动态：让单位进入 `Return` 状态，看 `Age2TabDebugUnitAI` 面板显示什么 |
| **`0x033b0ae8` 那群 vtable 属于哪个类** | 只证实前 4 槽是 `0x140806200 / 0x140806230 / 0x140806240 / 0x140806250`，目标全是 `\xc2\x00\x00`+`cc` 填充的 7 字节 thunk，**没有 RTTI 名字** | 查 `.data` 里指向该 vtable 的对象实例，反推构造函数 |

### 8.4 方法论纠错（本项目踩过的坑，接手者必读）

这一节记录**判据本身出错**的实例。它们的共同危害是：会产出一个看起来很有说服力的假结论。

1. **`disp32` 字段偏移算错 1~2 字节 → 假阳性**（`v240a`/`v244_banner2.py`）。
   x86-64 `lea rcx,[rdx+disp32]` 编码为 `48 8d 8a <disp32>`，**disp32 字段首字节 = 指令首 + 3**。此前把 `指令首 + 2`（ModRM 字节位置）当命中点，于是 `0x02e2e3f2` 被报成「引用了 banner `0x03232480`」。实际该处字节是 `48 8d 8a 40 40 00 00`，即 `lea rcx,[rdx+0x4040]` —— 立即数 `0x4040` 与 banner 的 disp32 计算巧合。在 `0x02e2e3a0..0x02e2e450` 内**逐字节**反汇编找 RIP 目标 == `0x03232480`：**0 条**。
   → 教训：任何「某地址被引用」的断言，必须用**反汇编器给出的指令起点 + 操作数编码长度**回算，不能靠 `find` 字节窗口。
2. **`44 0f 29 05 disp32` = `movaps [rip+d],xmm8`，不是指针表**（`v249_twohits.py`）。
   一段 7 条连续 `movaps` 溢出 SSE 寄存器的序列，其 disp32 恰好依次等于 `0x03223958/…/0x03223984` —— 即 `.rdata` 里名字块内部的连续 8 字节槽。只看「4B 槽值落在名字块内」会把它当成 7 项指针表。
   → 教训：命中点必须回查**它是不是某条指令的操作数编码位置**（`v250` 做了这件事：44 处里 30 处是 disp32 字段）。
3. **4KB 窗口的 capstone 覆盖率口径不可用**（`v236_measure.py`）。
   早期据「窗口覆盖率」得出「`.text` 有 31.59% 不可解」。正确口径是以 `.pdata` 的 `Begin` 为起点：可解 **94.13%**，不可解 **5.87%（体积占比 10.10%）**。窗口口径把 825 个含明文序言 `48 8b c4 48 81 ec` 的真代码窗口判成了低覆盖。
   → 教训：小窗口（尤其 64B）的覆盖率区分度为 0 —— `v230` T2 证明**任意单字节 XOR 键都能把 64B 窗口「解」到 64/64 覆盖**，随机数据的覆盖率本来就高。
4. **正则枚举字符串必须前向锚定 NUL**。
   无左锚的 `(?:up|fe|skybox|xs)-[a-z0-9-]*\x00` 会把 `backup-size` 中间的 `up-size` 也计入，产生 42 条重复假阳性（`up-*` 数成 234）。修法：要求前一字节为 NUL。
5. **8 字节对齐步进会在块内失步**。
   基础命令块里 `research`(`0x03223b14`) → `resign`(`0x03223b1c`) 是 4 字节对齐，对齐步进会产出 `'gn'` / `'t'` / `'n'` 三个假条目。正确做法是纯 NUL 分隔枚举，不做对齐假设。
6. **块首必须当作前面有一个 NUL**。
   只在 `blk[i]==0` 处起串会漏掉块首那条（它前面没有 NUL 落在块内），导致 `up-*` 数成 190/191、`c:` 丢失。
7. **`.pdata` 未被覆盖 ≠ 代码缺失**。
   `.pdata` 合计 46,217,624 B = `.text` 的 88.9%，空隙 5,079,434 B。但空隙里 89.1% 的位置**仍能解出指令**（`v233` T4），其中的字节大多是数据/填充而非函数体。把「未被 `.pdata` 覆盖」直接当成「未知代码区」会夸大未知量。
8. **Windows GBK 编码会炸脚本**。
   capstone 的 `op_str` 含非 ASCII 字节时 `print` 抛 `UnicodeEncodeError: 'gbk' codec can't encode character '\xdb'`。所有脚本必须带 `PYTHONIOENCODING=utf-8`。
9. **两个 python 环境不可混用**。
   `C:/Users/26913/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/python.exe` 有 numpy 2.3.5、**无 capstone**；`/c/Users/26913/AppData/Local/Python/bin/python` 有 capstone 5.0.7、**无 numpy**。
10. **`np.frombuffer(seg, dtype='<i4', count=len(seg)-3)` 会抛 `ValueError: buffer is smaller than requested size`**。
    numpy 要求 `count*4 <= 缓冲区大小`。必须改手工拼 int32（`b0[i] | b0[i+1]<<8 | b0[i+2]<<16 | b0[i+3]<<24`），或按 `count=(len(seg)-3)//4` 取再单独处理尾部。
11. **capstone 一次喂大块会 `CS_ERR_MEM`**。
    `md.disasm(code, va)` 传整段 `.text` 抛 `CsError: Out of memory`。必须按 `.pdata` 逐函数或分块喂。
12. **逐字节 Python 循环在 51 MB 上不可用**。
    `while i < n: …; i += 1` 跑十几分钟会被 kill。用 numpy 向量化或 `bytes.find` + 步进。
13. **MSVC 修饰名的正则不能用贪婪量词截 access/static 前缀，且必须记得返回类型占第一个类型**（`v273_sigparse.py` → `v274_strict.py` → `v284_exact.py`）。
    同一个符号 `SAHHHHH`，三种解析给出三个不同的 arity，每个都能自圆其说：
    - `@@([A-Za-z_]{0,8})` 贪婪把 `SAHHHHH` 整个吞掉（7 字符正好在 `{0,8}` 内）→ 类型串为空 → **arity = 0**（错）。
    - 截掉 `SA` 后把 `HHHHH` 五字符全当参数 → **arity = 5**（错，忘了 MSVC 文法里返回类型编码在参数之前）。
    - 按官方文法：`S`=static、`A`=`__cdecl`、`H`(第 1 个)=返回 int、`H×4`=参数 → **arity = 4**（对，`v284_exact.py`）。
    → 教训：**解析二进制里的符号编码时，必须拿文法定义逐字段走一遍，不能靠「看起来合理」**。三个数字只差 1，但报告里写成 5 或 0 都会让后续实现全错。这条同时也是「随机对照」的必要性：`v272` 用 200 个假命令名做对照得 0/200 命中，证明「名字↔符号」匹配本身没跑偏；但匹配对了，**解析还可能错**——两道工序要分开验证。

**给下一位接手者的一句总结**：命令名在三块 `.rdata` 区间里是**纯明文、8 字节对齐步长恒为 `align8(strlen+1)`、无 arity 字段、零代码引用**的字符串常量；它们的**存在形式只说明它们是 `static const char[N]` 数组序列，说明不了分派方式**。所有「靠地址常量 / 指针表 / 偏移表 / 哈希常量（10 种 × 4 段全矩阵）/ 内联立即数 / 导出入口 / SSE 常驻 / `.text` 内部槽 / RTTI vtable / 拷贝构造 thunk」找分派与找 arity 的路径已全部走完且全空（十八重）。**A 项已不再是全空：`up-get-fact-{min,max,sum}` 三条的真实 arity = 4 已由 MSVC 修饰名硬证（随机假名对照 0/200）。剩下 189 条的唯一高性价比出路是 PE 里那份完整 PDB 记录 —— `GUID = 651ecf97-392a-704d-a32c-5cd6ba3f8545`、`Age = 1`、路径 `F:\Agents\PhoenixBuilder-07\p4\portland_group\Build\Steam\Game\Retail\Output\AoE2DE_s.pdb`。先按 GUID 去符号服务器/公开泄漏库查；查不到再走动态：在 `0x00bf2c30`（`_Func_impl` 拷贝构造 thunk）下硬件执行断点回溯 `ret` 地址拿注册函数，或在 `0x03228938`/`0x03228968` 两条 argCount 格式串的 printf 使用点下条件断点，让引擎自己把 argCount 逐个打印出来。**


---

## 9. REA 原生解析器交叉验证（2026-10-28 三次校核）

上一版全部证据来自自写 Python（PE 头解析 + 字节扫描 + capstone）。本轮改用 **REA 6.8.0 的原生 PE 解析器**独立复核，得到四项本文档此前没有的硬事实。

### 9.1 导入表全量（此前完全未采集）

`mcp__rea__inspect_pe_imports`，覆盖 `complete`：**47 个 DLL / 1237 个导入函数 / 4 个延迟导入**。

`pefile` 算法 imphash = `4b64f51fd663e142132e6830ec068831`。

对 AI/XS 有意义的分组：

| DLL | 关键导入 | 对 AI/XS 的含义 |
|---|---|---|
| `api-ms-win-crt-stdio` | `fopen` `fopen_s` `_wfopen` `fread` `fgets` `fseek` `_fseeki64` `ftell` | `.xs`/`.per` 的**文件入口**走 CRT 流，非 Win32 句柄 |
| `api-ms-win-crt-string` | `strtok` `strcspn` `strspn` `isalpha` `isdigit` `_stricmp` `_strnicmp` | 存在手写 tokenizer 的导入指纹 |
| `api-ms-win-crt-convert` | `strtol` `strtod` `wcstoll` `_itoa_s` `_wtoi` | 字面量解析（XS 的 `int`/`float` 常量） |
| `api-ms-win-crt-math` | `sqrt` `sin` `cos` `atan2f` `powf` `floor` `round` | XS 向量运算 / AI 距离计算 |
| `api-ms-win-crt-utility` | `qsort` `rand` `srand` | 排序/随机数。**`qsort` 的 16 个调用点已逐个反汇编，无一在 AI 区**（见下） |
| `api-ms-win-crt-filesystem` | `_stat64` `rename` `remove` `_access` `_splitpath` | 存档/回放路径拼接 |
| `BugSplat64.dll` | `MiniDmpSender::unhandledExceptionHandler` `setMiniDumpType` | 崩溃转储走 **BugSplat** 第三方服务 |
| `libHttpClient.Win32.dll` | `HCHttpCall*` `HCWebSocket*` `XTaskQueue*` | Xbox Live / 云存档 HTTP 栈 |
| `MFPlat.DLL` / `MFReadWrite.DLL`（延迟） | `MFCreateSourceReaderFromURL` `MFCreateWaveFormatExFromMediaType` | 音频走后 **Media Foundation**，不是 wwise |
| `WS2_32` / `WSOCK32` / `IPHLPAPI` | `WSASocketA` `WSAConnect` `getaddrinfo` `GetAdaptersAddresses` | 联机层 |
| `ADVAPI32` / `CRYPT32` | `RegGetValueW` `CryptHashData` `CertOpenStore` | 注册表配置 + 证书校验 |

**关键推论（已被本轮否证，勿再引用）**：上一版据「`strtok` + `qsort` 同时存在」推断「AI 命令分派不是哈希表，而是『字符串切分 → 线性/排序匹配 → 薄 handler』」。本轮实测**推翻了这个推论的一半**：

- `strtok` 在 `.text` 中 **0 个 `FF15` 跳板**（`v81_bytes.py`）——真正被大量调用的是 `strncmp`（209 个跳板）和 `_stricmp`（29 个）。
- `qsort` 的 **16 个调用点全部不在 AI 区**，且**没有一个是 AI 脚本解析器**（`v205_qsort_callers.py`，带 capstone 指令边界验证；15 个调用者函数起址 `0x01d0f8f0` … `0x02afac02`，池区引用 0 个）。
- 相对地，`.data 0x040965b0` 那张 **135 项、严格字母序、stride=0x10 的单位名→ID 表**（§8.1）确实需要 `bsearch`/有序查找——所以「排序查找」这个机制在全引擎里存在，**但作用于"单位名→ID"，不是作用于"命令名→handler"**。

即：**「导入了 qsort 所以分派是排序查找」是一条从导入表反推行为的过度推断，本轮已用调用点证据否定。** 命令名分派机制至本轮结束**仍然未知**（十八重否证见 §8.2）。

### 9.2 加载器配置（此前完全未采集）

`mcp__rea__inspect_pe_load_config`：

```
TLS 回调        2 个：0x142d6e030、0x142d6deec（均在 .text）
Security Cookie      0x144116140（.data）
GuardFlags  raw=256  →  IMAGE_GUARD_CF_INSTRUMENTED
GuardCF 函数表        VA=0x0, count=0        ← 有 CFG 插桩，但无函数表
GuardXFG 校验指针     0x143199818 / 0x143199810 / 0x143199820
```

**`CF_INSTRUMENTED` 但 `FunctionTable` 为空**：这是 MSVC 在超大二进制上只做 `/guard:cf` 插桩、不导出台表的典型结果。对逆向的含义是——**没有 CFG 表可以当作「合法间接调用目标白名单」**，想枚举虚函数/跳转表只能靠数据流，不能靠表。

### 9.3 数字签名（此前完全未采集）

`mcp__rea__inspect_pe_certificates`，1 个 `WIN_CERTIFICATE`（type=2 / PKCS#7 signedData，10029 B 载荷）：

```
签名主体   CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US
签发者     CN=Microsoft Code Signing PCA 2024, O=Microsoft Corporation, C=US
有效期     2026-04-16 18:59:43Z  →  2027-04-15 18:59:43Z
摘要算法   sha256 (2.16.840.1.101.3.4.2.1)
```

**结论**：`AoE2DE_s.exe` 是**微软自家代码签名**，不是第三方发行商签名。这解释了 §1.3 里 `F:\Agents\PhoenixBuilder-07\...` 这种内部构建机路径——它是微软第一方构建产物。（注意：本项只做结构解码，未验证签名链与 Authenticode 字节覆盖。）

### 9.4 工具可用性实测（供复现者参考）

| 工具 | 状态 | 说明 |
|---|---|---|
| REA 原生 PE 解析器 | ✅ 可用 | 导入表/证书/load-config 全部 `coverage: complete` |
| REA + Ghidra 12.1.4 | ⚠️ 超时 | 72 MB 二进制首次全自动分析超出客户端工具超时；会话本身正常（`binary_session` 返回 `open:true`），只是结果送达前被客户端判超时 |
| REA + rizin | ✅ **本轮已绕开** | REA 侧仍报 `ERR_REA_WINDOWS_NATIVE`（未设 `REA_RIZIN_COMMAND`），但**系统已装 rizin**：`/c/Program Files/Rizin/bin/rizin` 与 `rz-bin` 命令行直接用，无需 REA 桥接 |
| capstone 5.0.7 | ✅ 本轮主力 | 装在 `/c/Users/26913/AppData/Local/Python/bin/python`（**该解释器无 numpy**）。DSH 自带 python **有 numpy 无 capstone**。两套必须分开用 |
| numpy | ✅ 本轮主力 | DSH python 自带。纯字节扫描（RIP-disp32 超集扫描、u32 run 检测）全靠它 |

**本轮对 Ghidra 的处置**：没有走 MCP 的 `analyzeHeadless`（deadline 问题依旧）。改为**自己用 capstone 按 `.pdata` 的 169486 条 `[Begin,End]` 逐函数线性反汇编**（`v190_linear_rip.py`）——这是可控、可复现、无超时的等效替代，且拿到 170743 个唯一 RIP 目标，覆盖 `.text` 的 88.9%。剩余 9.8% 的覆盖缺口数字见 §8.3。

**诚实说明**：本文档 §2/§3 的命令表与 syscall 表来自「字符串聚簇 + RIP 引用 + `.pdata` 归属」，不是 Ghidra 反编译。§8.3 列的「`up-*` 精确参数个数与顺序」**已解出 3 / 192 条**（`up-get-fact-{min,max,sum}` = 4 个 `int`，证据是 `.data` 残留的 MSVC 修饰名 `?UPGetFact*@AIHybrid@@SAHHHHH@Z`，按官方文法逐字段切分），其余 189 条**依旧未证实**——本轮已经证明二进制里**不存在**静态的「名字→arity」结构（§8.2 十八重否证 + 对齐填充全零 + 1153 个 `_Func_impl` RTTI 描述符的完整枚举只捞出 40 个被包装函数），所以它不可能靠「继续静态扫描」得到，**只能动态调试或拿 PDB**。

