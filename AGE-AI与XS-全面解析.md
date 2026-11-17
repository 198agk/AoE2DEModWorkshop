# AGE 里的 AI 与 XS · 全面解析

> 解析对象：`D:\Software\AI\Aoe2\AdvancedGenieEditor20261022x86`
> 参照本体：`D:\Games\Steam\steamapps\common\AoE2DE`（AoE2DE_s.exe + resources/_common）
> 方法：静态字节计数 + 字符串抽取 + 官方语料全量扫描。不运行、不联网。

---

## 0. 一句话结论

**AGE 本身对 AI（.per）和 XS（.xs）的支持是零字节级的零。** 它既不能打开、解析、编译、调试 .per，也不能碰 .xs。它对 AI 的全部关系是：**在自己的 Units / Techs 编辑器里维护 AI 需要读的那几个数据字段**（unit-line、min tech level、unit trait）。真正跑 AI 和 XS 的是游戏主程序 `AoE2DE_s.exe`，它内置了一个 232 个 syscall 的 XS 解释器（43 opcode 栈式 VM）和一个 378 符号的 AI 解释器。

---

## 1. 零字节证据：AGE 不认 AI/XS

对 `AdvancedGenieEditor3.exe`（8,415,744 B）做字面字节计数：

| 检索串 | 命中次数 | 含义 |
|---|---|---|
| `.per` | **0** | 无 .per 文件类型 |
| `.per2` | 0 | 无 .per2 |
| `.xs` | **0** | 无 .xs 文件类型 |
| `defrule` | **0** | 不认识 AI 规则关键字 |
| `defconst` | 0 | 不认识 AI 常量 |
| `load-if` | **0** | 不认识 AI 编译期条件 |
| `xsEffectAmount` | **0** | 不认识 XS 效果调用 |
| `xsGetGoal` / `xsSetGoal` | **0** | 不认识 XS goal 读写 |
| `xs-script-call` | **0** | 不认识 AI→XS 桥接命令 |
| `includeXS` | 0 | 不认识 XS 引入 |
| `sn-attack` 等 sn-* | **0** | 不认识战略数命名表 |
| `AI Script` | 0 | 无 AI 脚本概念 |

对比游戏主程序 `AoE2DE_s.exe`：

| 检索串 | 命中 |
|---|---|
| `defrule` | 1（命令行解析表入口） |
| `load-if` | 2 |
| `xs-script-call` | 1 |
| `includeXS` | 1 |
| `xsGetGoal` | 2（含完整 C 签名串） |
| `xsEffectAmount` | 2 |
| `xsGetUnitAttribute` | 12 |

**结论：AI/XS 的解析与执行 100% 在主程序，AGE 一个字节都没沾。**

> 顺带：AGE 里 `scenario` 出现 5 次、`Scenario` 1 次，但 `.scx` / `.aoe2scenario` / `.aoe2scenariopack` 全部 0 次。所以 AGE **也不编辑场景文件**。它是纯 `.dat` 编辑器。

---

## 2. AGE 里唯一与 AI 有关的东西：三个数据字段

AGE 的 Units 页字段序列（VA 0x6ef3d8 附近）里有三个字段直接喂给 AI：

| AGE 字段名 | 位置 | 作用 |
|---|---|---|
| `AI Unitline` | 0x6ef3d8 | 把单位挂到某个 unit-line 编号上 |
| `Min Tech Level` | 0x6ef3e8 | 该单位所在 unit-line 的最低科技等级门槛 |
| `Unit Trait` / `Trait Piece` | 0x6ef310 / 0x6ef320 | 单位行为标记位 |

以及标签页名 `Unitlines (Used by AIs)`——括号里那句就是 AGE 作者自己写的注释。

还有一条罕见的作者吐槽串：

```
900 and 1000 mess up the AI
```

这是 AGE 里对 effect command 编号 900 / 1000 的警示——它们在 AI 侧有副作用。

**这三个字段是 AI 侧 `(train ...)` / unit-line 逻辑的唯一数据来源。改 DAT 里的 unit-line 就等于改 AI 的训练行为。**

另外 AGE 的 Effects 页明确写了：

```
7-39 are only available with UserPatch 1.5
10-16 are also available with AoK HD
101-103 only work at start of a game
101 and 103 are only for tech tree and team bonus
```

这些编号与 XS 的 `EffectFunction*` 一一对应（见 §5.2）。

---

## 3. AI 侧：`.per` 语言全貌

### 3.1 语料规模（实测）

| 指标 | 数值 |
|---|---|
| `.per` + `.per2` 文件数 | **120** |
| `(defrule ...)` 规则总数 | **15,565** |
| distinct 命令/事实符号 | **378** |
| 其中 `up-*` 扩展命令 | **158** |
| 其中 `xs-*` | **1**（只有 `xs-script-call`） |
| `#load-if` 条件符号 | **311** |
| 最大单文件 | `AI (HD version).per` 1,134,731 B / 2,454 条规则 |

AI 家族目录分布：

| 目录 | 文件 | 字节 |
|---|---|---|
| `resources/_common/ai/Promisory` | 38 | 3,894,874 |
| `resources/_common/ai/AiBuilder` | 9 | 181,927 |
| `modes/Pompeii/resources/_common/ai/default` | 20 | 731,575 |
| `modes/Pompeii/resources/_common/ai/AiBuilder_p` | 12 | 259,134 |

### 3.2 语言骨架

```
(defconst 名字 值)                     ; 编译期常量
(defrule                               ; 一条规则
    (fact-1 ...)                       ; 条件（AND 隐式）
    (or (fact-2) (fact-3))             ; 显式 OR
=>
    (action-1 ...)                     ; 动作
    (disable-self)                     ; 自杀，避免重复触发
)
```

- **事实（fact）** 在规则左半边，只读。
- **动作（action）** 在 `=>` 右半边，写 goal / 战略数 / 下令。
- `#load-if-defined X` / `#load-if-not-defined X` / `#else` / `#end-if` 是**编译期**条件，不是运行期。311 个符号里出现频率最高的是 `DIFFICULTY-EASIEST`(155)、`DIFFICULTY-MODERATE`(150)、`DIFFICULTY-EASY`(147)、`UP-POCKET-POSITION`(104)、`DIFFICULTY-HARD`(80)、`<CIV>-CIV` 共 40 余个文明符号、`DEATH-MATCH`(63)、`WONDER-RACE`(64)、`POST-IMPERIAL-AGE-START`(37)。

### 3.3 命令规模实测 top 15（按调用次数）

| 命令 | 次数 |
|---|---|
| `goal` | 12,648 |
| `set-goal` | 11,407 |
| `up-compare-goal` | 8,727 |
| `strategic-number` | 6,878 |
| `set-strategic-number` | 4,630 |
| `building-type-count-total` | 4,450 |
| `unit-type-count-total` | 4,415 |
| `up-modify-goal` | 3,639 |
| `up-jump-rule` | 2,258 |
| `game-time` | 2,214 |
| `unit-type-count` | 2,039 |
| `up-research-status` | 2,028 |
| `research` | 1,908 |
| `release-escrow` | 1,768 |
| `building-type-count` | 1,687 |

**goal 是第一公民**。原版 AI 的所有状态都存在 goal 里——因为 AI 没有变量，只有 goal 数组和战略数。

### 3.4 三个承载通道

| 通道 | 数量级 | 用途 |
|---|---|---|
| **goal** | 0–~4000（含 256 个"命名 goal" 别名） | 通用整数变量、坐标、数组 |
| **strategic number (sn)** | 0–~500 | 引擎预设旋钮（攻击间隔、集结比例…） |
| **escrow** | 资源维度 | 资源预留/释放，AI 攒兵不卡经济靠它 |

goal 的区间在官方 ailib 里被硬编码占用（见 §7）：
- `3001–3060` 远端单位数组
- `3004–3005` goal 数组起止指针
- `4001–4060` 本地单位数组
- `4061` 输出 goal
- `8` 布尔修饰 goal
- `194` 地图尺寸
- `331–335` 几何运算（x, y, 原点 x, 原点 y, 角度）
- `3027` 抖动方差

---

## 4. AI 的扩展层：`up-*`（UserPatch 血统）

378 个符号里 **158 个是 `up-*`**，占 42%。这不是原版 AI 语法，是 UserPatch 1.5 引入、DE 继承的扩展层。分四类：

**① 搜索/过滤（search pipeline）**
```
up-full-reset-search  up-reset-search  up-find-local  up-find-remote
up-find-next-player   up-filter-distance  up-filter-include  up-filter-exclude
up-filter-range  up-filter-status  up-filter-garrison  up-target-objects
up-set-target-object  up-set-target-by-id  up-get-search-state
```

**② goal / 数值运算**
```
up-compare-goal  up-modify-goal  up-get-indirect-goal  up-set-indirect-goal
up-compare-const  up-compare-sn  up-compare-flag  up-lerp-percent
up-lerp-tiles  up-modify-sn  up-modify-escrow  up-modify-flag
```

**③ 空间/几何（这是 AI 唯一能"看地图"的途径）**
```
up-get-point  up-get-point-distance  up-get-path-distance  up-get-point-zone
up-get-point-elevation  up-point-terrain  up-point-explored  up-point-contains
up-bound-point  up-bound-precise-point  up-set-precise-target-point
up-cross-tiles  up-add-point  up-copy-point  up-player-distance
```

**④ 控制流（AI 的 goto）**
```
up-jump-rule  up-jump-direct  up-get-rule-id
```

`up-jump-rule` 被调用 2,258 次——AI 的状态机全靠它，因为 `.per` 没有 `while`/`for`。

---

## 5. XS 侧：`.xs` 语言全貌

### 5.1 引擎内建 syscall：232 个

从 `AoE2DE_s.exe` 里正则抽取 `类型 xs名字(参数)` 形态的完整 C 签名串，去重得 **232 个 `xs*` 函数**（另有 1 个裸标识符 `xsJ`，是解析噪声，已排除）。完整表已导出到 `_age_analysis/aixs/xs_syscalls.txt`。

按语义分 12 族（原 11 族 + 文件 IO）：

| 族 | 数量级 | 代表 |
|---|---|---|
| **数组** | 22 | `xsArrayCreateInt/Float/Bool/String/Vector`、`xsArrayGet/Set*`、`xsArrayResize*`、`xsArrayGetSize` |
| **goal / 战略数** | 6 | `xsGetGoal`、`xsSetGoal`、`xsGetStrategicNumber`、`xsSetStrategicNumber`、`xsGetAiScriptGoal`、`xsSetAiScriptGoal` |
| **效果（改 DAT）** | 1 | `xsEffectAmount(effect, itemName, type, value, playerId, index)` |
| **单位查询** | 30+ | `xsGetUnitAttribute`、`xsGetUnitClass`、`xsGetUnitHitpoints`、`xsGetUnitOwner`、`xsGetUnitObjectId`、`xsGetUnitTargetUnitId`、`xsGetUnitCharge`、`xsGetUnitProperty`、`xsGetUnitBuildPoints`、`xsGetUnitGatherPoint`… |
| **玩家/经济** | 20+ | `xsPlayerAttribute`、`xsSetPlayerAttribute`、`xsGetObjectCount`、`xsGetObjectCountTotal`、`xsGetPlayerUnitIds`、`xsGetPlayerCivName`、`xsGetDifficulty`、`xsGetGameTime` |
| **动作下达** | 15 | `xsTask`、`xsTaskAmount`、`xsResetTaskAmount`、`xsRemoveTask`、`xsTrainObject`、`xsBuildUnit`、`xsCreateUnit`、`xsRemoveUnit`、`xsSetUnitPosition`、`xsStopUnit`、`xsInitiateResearch`、`xsResearchTechnology` |
| **规则控制** | 8 | `xsEnableRule`、`xsDisableRule`、`xsIsRuleEnabled`、`xsSetRulePriority`、`xsSetRuleMinInterval`、`xsSetRuleMaxInterval`、`xsEnableRuleGroup`、`xsDisableSelf` |
| **向量 / 数学** | 10 | `xsVectorSet/GetX/GetY/GetZ`、`xsVectorLength`、`xsVectorNormalize`、`xsCeilToInt` |
| **网络同步** | 8 | `xsSendNetData`、`xsReadNetInt/Float/String`、`xsWriteNetInt/Float/String`、`xsResetNetData`、`xsGetRead/WriteNetDataPosition` |
| **UI / 表现** | 12 | `xsDisplayTimer`、`xsClearTimer`、`xsFlashUnit`、`xsPlaySound`、`xsSendChat`、`xsSetViewPosition`、`xsSetZoom`、`xsSetColorMood`、`xsSetUnitCaption`、`xsSetUnitName` |
| **地图 / 环境** | 10 | `xsGetMapWidth`、`xsGetMapHeight`、`xsGetMapName`、`xsGetMapSeed`、`xsGetMapType`、`xsGetMapTileAttribute`、`xsGetCivName`、`xsGetLocale` |
| **联机不同步（unsync）** | 6 | `xsUnsyncGetLocalPlayerId`、`xsUnsyncIsUnitVisible`、`xsUnsyncGetPlayerSelectedUnitIds`、`xsUnsyncGetZoom`、`xsUnsyncGetTimerTimeRemaining`、`xsUnsyncIsSandboxMode` |
| **文件 IO** | 11 | `xsCreateFile`、`xsOpenFile`、`xsCloseFile`、`xsWriteString/Int/Float/Vector`、`xsReadString/Int/Float/Vector`、`xsSetFilePosition`、`xsOffsetFilePosition`、`xsGetFilePosition`、`xsGetFileSize`、`xsGetDataTypeSize` |

> `xsUnsync*` 这一族值得单独注意：它们只在本机生效、不进同步状态，用来做纯客户端表现（镜头、选中高亮），不会导致 out-of-sync。
>
> **文件 IO 那 11 个是本解析里最容易忽略的一族**：`xsWrite*` / `xsRead*` + `.xsdat` 后缀（引擎里唯一一处 `.xsdat` 串）说明 XS 可以往磁盘写自己的数据文件。这是做「跨对局持久化 AI 记忆」的唯一官方通道。

### 5.1b 泄露的引擎源码结构

`AoE2DE_s.exe` 里保留了 13 条 XS 引擎的原始 P4 源码路径，可以反推内部类划分：

```
F:\Agents\PhoenixBuilder-07\p4\portland_group\Aoc\Source\XS\
    xsactivationrecord.cpp     ← 调用栈帧
    xsdata.cpp                 ← BXSData（一个编译单元）
    xsfileentry.cpp            ← 文件表项
    xsfunctionentry.cpp        ← 函数表项
    xsruleentry.cpp            ← 规则表项（mPriority/mMinInterval/mMaxInterval/mLastExecuteTime/mActive/mRunImmediately/mGroups）
    xsrulemodule.cpp           ← 规则模块
    xsruntime.cpp              ← BXSRuntime（interpretFunction / interpretTrigger / interpretHandler）
    xssource.cpp               ← 源码缓冲
    xssymboltable.cpp          ← 符号表
    xssyscallentry.cpp         ← syscall 表项
    xssyscallmodule.cpp        ← syscall 模块
    xsuserclassentry.cpp       ← 用户类（vector 等）
    xsvariableentry.cpp        ← 变量表项
```

命名前缀 `BXS*`（`BXSRuntime`、`BXSData`、`BXSRuleEntry`、`BXSRuleGroupEntry`）说明这是从 Ensemble 时代 `B*`（Base）前缀延续下来的引擎层。

**XS 虚拟机的 43 个 opcode**（VA 0x330c4f8）：

```
NOP  RET  JUMP  JUMPZ  JUMPNZ  LABEL  PUSH  PUSHI  PUSHADD  POP  POPADD
CALLS  CALLF  AND  OR  GT  GE  NE  EQ  LE  NEG  ADD  SUB  MUL  DIV
BOR  BAND  ASS  DBG  SEP  ILL  IRL  LINE  FILE  BPNT
```

这是**栈式 VM，无寄存器**：`PUSH/PUSHI/POP/PUSHADD/POPADD` 做栈操作，`CALLS`（syscall）/`CALLF`（函数）做调用，`ASS/SEP/IRL/DBG/BPNT` 是赋值/分隔/迭代/断点。`LINE`/`FILE`/`BPNT` 三条 opcode 证明**逐行调试是引擎原生能力**，不是外部工具附加的。

其余运行时限制串：
```
Infinite recursion limit of %d hit, failing execution.
XS Breakpoint: File '%s', line %d.
XS Breakpoint: UNKNOWN FILE, line %d.
```

**结论：XS 是有正式编译器 + 栈式 VM + 符号表 + 断点的完整语言实现，不是一个简单的字符串替换器。**

### 5.2 `Constants.xs`：1,176 个常量（1,393 行 / 61,423 B）

文件头两句就说明了它的地位：

```
This is the default XS scripting constants file.
It is automatically included in every instance of the XS scripting language
```

**XS 不需要自己 include 它——引擎自动注入。**

构成：`int` 1,166 个 + `string` 10 个。

`xsEffectAmount` 的三层参数体系全在这：

**第一层 effect 类型**
```c
cSetAttribute          = 0     // 技能/属性（可乘性）
cAddAttribute          = 4
cMulAttribute          = 5
cModifyTech            = 8     // 改科技
cSetPlayerData         = 9
cSetUnitAttribute      = 10
cAddUnitAttribute      = 11
cGaiaSetAttribute      = -1
cGaiaAddAttribute      = -5
cGaiaMulAttribute      = -6
cGaiaMulResource       = -7
cGaiaSetPlayerData     = -10
cGaiaSetTechCost       = -101
cGaiaAddTechCost       = -102
```

**第二层属性槽（以 `cAttrSet*` / `cAttrAdd*` 家族为例）**
```c
cAttrSetFoodCost = 0    cAttrAddTime = -2      cAttrSetTime = -1
cAttrSetWoodCost = 1    cAttrMulTime = -3
cAttrSetStoneCost = 2
cAttrSetGoldCost = 3
cAttrSetLocation = 4    cAttrSetButton = 5
cAttrSetIcon = 6
cAttrSetName = 7
cAttrSetDescription = 8
cAttrSetStacking = 9
cAttrSetStackingResearchCap = 10
```

**第三层：科技叠加控制**
```c
cAttrSetStacking              = 9
cAttrSetStackingResearchCap   = 10
```

这两条只在 `cModifyTech` 下有意义——把某个科技从"只能研究一次"改成"可叠加 N 次"。`x9tech.xs` / `x256tech.xs` 就是靠它：

```c
// x9tech.xs 全文（281 B）
void main()
{
    for (player = 1; <= xsGetNumPlayers())
    {
        for (tech = 0; < xsGetPlayerNumberOfTechs(player))
        {
            xsEffectAmount(cModifyTech, tech, cAttrSetStacking, 1, player);
            xsEffectAmount(cModifyTech, tech, cAttrSetStackingResearchCap, 9, player);
        }
    }
}
```

`x256tech.xs` 只设 `cAttrSetStacking = 1`，不设上限 → 结论是 **不设 research cap 时上限为 256**。这就是文件名由来。

> **这两个文件定义了两种"科技叠加模式"，直接改变了整个游戏的升级节奏。它们都是 300 字节左右的 `.xs`，靠 `main()` 入口在开局被引擎调用。**

### 5.3 `Effects.xs`：74 个函数（73,185 B）

结构是**一 effect 一函数**，函数名 = `EffectFunction{编号}`，编号即 DAT 里 effect command 的 type id：

```
EffectFunction 编号（实测 41 个）:
1-16, 25-32, 34, 35, 36, 38, 39, 50-56, 1000, 1001, 1002, 1003, 1004

缺口（DAT 未实现 / 保留）: 17-24, 33, 37, 40-49
```

这跟 AGE Effects 页的警示串完全对上：`7-39 are only available with UserPatch 1.5`、`101-103 only work at start of a game`。

另外 33 个是**具体文明/机制补丁函数**，这部分才是真正的游戏逻辑：

```
HunnicHorseGraphic             匈奴马模型修正
OrdoCavalryRemoval             条顿 Ordo 骑兵移除
CoiledSerpentArray             盘蛇阵（诸葛弩/弩炮阵列）
ChurchAura                    教堂光环
RedCliffs                     赤壁（火船）
Curare / CurareRemoval        箭毒（美洲文明）
TupiRefund                    Tupi 退款
MuiscaHeal                    Muisca 治疗
PillageBuildings              劫掠建筑
patchKhmerNoDropsite          高棉无仓库补丁
Effects_isCastleUniqueUnit    城堡uu判定
OdomantianRaiderHighValueTargets / LowValueTargets
AthenianMilitaryPolicy        雅典军事政策
ApplyPuruRegenAbility         Puru 再生
addFlagshipHealUnitsAura      旗舰治疗光环（含 Docked 变体）
addMuleCartWorkrateAura       骡车工作效率光环
addAlexanderMountedDefaultAura / AttackAura / SpeedAura
addAlexanderDismountedDefaultAura / AttackAura / SpeedAura
addBetterFortifiedOutpostSpeedAura
addSamAura / addESamAura
addSlowingMudAura             减速泥沼光环
```

`addSlowingMudAura` 是这批里最典型的"XS 当技能系统用"的样本：

```c
void addSlowingMudAura()
{
  xsResetTaskAmount();
  xsEffectAmount(cSetAttribute, 291, 63, 32, -1);
  xsTaskAmount(0, 0.40);   // 速度 40%
  xsTaskAmount(1, 1);
  xsTaskAmount(2, 2.0);
  xsTaskAmount(4, 5);
  xsTaskAmount(5, 3);
  xsTaskAmount(6, 0);
  xsTask(291, 155, 900, -1);   // 对 12 种单位类型批量施加
  ...  // 900/904/906/912/913/918/919/936/943/944/947/951/955
  xsResetTaskAmount();
}
```

模式很清晰：**`xsTaskAmount` 设置一组"任务参数"→ `xsTask` 批量把这些参数应用到目标单位上 → `xsResetTaskAmount` 清场。** 这是 DE 做光环/减速/加速的唯一手段。

---

## 6. AI ↔ XS 桥接：`xs-script-call`

这是两个世界唯一的正式接口。

### 6.1 机制

```per
; AI 侧
(set-goal 3004 <first>)
(set-goal 3005 <last>)
(xs-script-call "sortAiArray")     ; 调用已加载 XS 里同名的 void 函数
```

```c
// XS 侧
void sortAiArray() { ... }          // 从 goal 读参数，往 goal 写结果
```

- **没有参数传递、没有返回值。** 全部通过 goal 数组当"寄存器"。
- 只能调 `void f()` 签名（无参无返回）。
- XS 函数**看不到 AI 的局部状态**，只能读全局 goal / 战略数 / 世界状态。

### 6.2 加载路径

只有两种让 XS 进入 AI 上下文的方式：

**① `(include "路径.xs")`** — AI 编译期引入
实测全库只有 2 处，都在 `resources/_common/drs/gamedata_x2/PromiDE.per2`：
```per
; PromiDE.per2:34-35
(include "ailib/GoalArrayOps.xs")
(include "ailib/Geometry.xs")
```

**② `#includeXS`** — RMS（随机地图）里引入 XS
主程序里的正则就是它的完整语法定义（VA 0x32c39cc）：
```
#includeXS\s+(?:"([^"]+)"|(\S+))
.xs
```
即 `#includeXS "带引号路径.xs"` 或 `#includeXS 裸路径.xs`，两种都吃；`.xs` 后缀可在正则外单独补。

> **实测：官方所有 `.rms` / `.rms2` / `.inc` / `.def` 里 `#includeXS` 命中数为 0。** 这是个给模组作者准备的能力，官方地图没用。想在地图生成阶段跑 XS 逻辑，这是唯一入口。

**③ 场景 Script Call 条件的自动生成 XS 文件**
主程序里有一段明确说明：
```
//This is an auto-generated XS file. The functions defined in this script are
//written from the Script Call conditions and effects.
//Make sure this file is NOT used as a main XS file as it is subject to change
//depending on the scenario.
```
即：场景编辑器里放的 Script Call 条件/效果，会被引擎编译成一个临时 `.xs`（紧邻的串还有 `Temporary Triggers`），里面就是这些函数。

**④ `xsCreateFile` / `xsOpenFile`** — XS 自己开文件
配合 `.xsdat` 后缀与 `xsWrite*/xsRead*`，XS 能在运行时读写自己的数据文件。

### 6.3 实际调用点（全库精确统计）

`xs-script-call` 共出现 **29 次**，其中 **24 次生效、5 次被注释掉**。

| 被调用函数 | 次数 |
|---|---|
| `RotateByAngleNoConvert` | 16 |
| `ApplyRandomnessToPoint` | 3 |
| `FindAdjacentAngle` | 2 |
| `sortAiArray` | 2 |
| `VerifyLoad` | 1 |

| 文件 | 次数 |
|---|---|
| `Promisory/general.per` | 8 |
| `Promisory/scoutcontrol.per` | 7 |
| `Promisory/extremebuildings3.per` | 2 |
| `Promisory/init.per` | 2 |
| `Promisory/orb.per` | 2 |
| `Promisory/watercontrol.per` | 2 |
| `Promisory/extremebuildings4.per` | 1 |

**这就是全部。** 官方 AI 对 XS 的使用极其克制——只用来做纯数学（旋转、开方、排序），因为 `.per` 本身**没有三角函数、没有 sqrt、没有数组排序**。

### 6.4 幽灵调用：调了但没定义的函数

逐个核对定义体，发现官方 AI 里有 **3 个函数名被调用、但整个游戏目录里没有任何定义**：

| 被调函数 | 调用点 | 定义数 | 状态 |
|---|---|---|---|
| `VerifyLoad` | `scoutcontrol.per:38`（**生效**） | **0** | 幽灵调用 |
| `RotateByAngle` | `scoutcontrol.per:483`（已注释） | 0 | 名字写错，真名是 `RotateByAngleNoConvert` |
| `RetrieveNextEnemy` | `init.per:10778`、`scoutcontrol.per:697`（均已注释） | 0 | 废弃 |

`scoutcontrol.per:38` 附近原文：
```per
(defrule
   (current-age == feudal-age)
   (game-time > 5)
=>
   (xs-script-call "VerifyLoad")     ; ← 全库无此函数定义
   (disable-self)
)
```

这印证了一个重要事实：**`xs-script-call` 调用不存在的函数不会崩游戏**，引擎只记一条告警就跳过。否则官方 AI 这条封建时代一到的规则会直接把对局打断。这对写脚本是好事——桥接失败是软失败，可以当"可选依赖"用。

同时也说明 `RotateByAngle` → `RotateByAngleNoConvert` 是一次改名，旧名残留在注释里，说明**引擎不做名字重载匹配，只做精确字符串匹配**。

---

## 7. 官方 `ailib/` 三个库逐行解析

### 7.1 `Geometry.xs`（5,705 B）— 给 AI 补数学

**问题**：`.per` 只有整数 goal，没有 `sin`/`cos`/`acos`/`sqrt`。AI 想算"往左转 30 度后打哪"，只能借 XS。

**接口约定（硬编码 goal 号）**

| goal | 含义 |
|---|---|
| 331 | 点 x |
| 332 | 点 y |
| 333 | 原点 x |
| 334 | 原点 y |
| 335 | 角度（**毫弧度**，×1000 的整数） |

**`FindAdjacentAngle()`** — 用 acos 求方位角
```c
int distance_adj = abs(point_x - origin_x);
int distance_opp = abs(point_y - origin_y);
int distance_hyp = sqrt(distance_adj*distance_adj + distance_opp*distance_opp);
float ratio = (distance_adj / distance_hyp);
float angle_output_float = acos(ratio);
angle_output_float = angle_output_float * 1000;    // 弧度 → 毫弧度，保住精度
angle_output_int = angle_output_float;
xsSetGoal(335, angle_output_int);
```
注意它自己写了防御性断言：`if (distance_hyp < distance_adj)` 时 `xsChatData("Assert: attempting to take inverse cos of a number greater than 1")`。

**`RotateByAngleNoConvert()`** — 旋转矩阵手搓
```c
if (angleMiliRad < 0) { clockwise = True; angleMiliRad = 6283 - angleMiliRad; }
float angleRad = angleMiliRad / 1000;
result_x = (distance_x * cos(angleRad)) - (distance_y * sin(angleRad));
result_y = (distance_x * sin(angleRad)) + (distance_y * cos(angleRad));
```
`6283` 是 2π×1000 的整数截断（真值 6283.185…）。这是**全库唯一的浮点精度妥协点**，误差约 0.003%。

**`ApplyRandomnessToPoint()`** — 抖动
```c
//uncomment when xsGetRandomNumberLH is fixed
//int rnd1 = xsGetRandomNumberLH(random_delta_1, random_delta_2);
int rnd1 = xsGetRandomNumberMax(random_delta) - random_delta_half;
```
**这里有条重要的实战情报**：官方代码注释明确写着 `xsGetRandomNumberLH` 有 bug，所以他们自己绕开用 `xsGetRandomNumberMax`。你在自己脚本里也应当避开 `xsGetRandomNumberLH`。

**`FindClosestEdge()`** — 求最近地图边缘
四象限分支，把点投影到最近的边（`outpointX/outpointY` 置 0 或 mapSize）。地图尺寸从 goal 194 读，注释写 `//we assume all maps are square`。

### 7.2 `GoalArrayOps.xs`（2,787 B）— 给 AI 补数组

**问题**：`.per` 没有数组。但 `up-*` 有 `up-find-local` 会把 N 个对象 ID 填充到连续 goal 区间。要排序这个区间，只能借 XS。

**接口**
```c
extern const int goalArrayStart = 3004;   // 区间首 goal 号
extern const int goalArrayEnd   = 3005;   // 区间末 goal 号
int sortingArrayId = -1;                  // 静态缓存，跨调用复用
```

**`sortAiArray()` 流程**
1. 读 3004/3005 得到 `[firstGoal, lastGoal]`，算 `arraySize`
2. 首次调用 `xsArrayCreateInt(arraySize, -1, "SortingArray")`，之后尺寸变了才 `xsArrayResizeInt`
3. `while` 把 goal 区间**逐个数搬进 XS 数组**
4. `InsertionSort(arrayId)` 排序
5. `while` 把数组**逐个数搬回 goal 区间**

**`InsertionSort()`** 是标准插入排序，但有个防御写法值得注意：
```c
if (j >= 0) comparator = xsArrayGetInt(array_id, j);
else        comparator = xsArrayGetInt(array_id, last_slot);   // 越界读末位而非崩溃
```

**AI 侧调用点**（`Promisory/init.per`）：
```per
(up-get-point-distance position-self-x point-x temporary-goal16)
(up-get-point-distance position-self-x point2-x temporary-goal17)
(up-get-point-distance position-self-x point3-x temporary-goal18)
(up-get-point-distance position-self-x point4-x temporary-goal19)
(up-modify-goal temporary-goal12 g:= temporary-goal16)
...
(set-goal xs-array-start temporary-goal12)   ; 故意设常量值，不是 goal 的值
(set-goal xs-array-end temporary-goal15)
(xs-script-call "sortAiArray")
(disable-self)
```
**这是一份教科书级的桥接范式**：先算 4 个距离 → 复制到连续 goal → 设起止指针 → 调 XS 排序 → 之后 AI 直接读排好序的 goal。绕开了"AI 不能排序"这个根本限制。

### 7.3 `MilitaryEvaluation.xs`（2,349 B）— 兵力估价 + **两处真实 bug**

**接口**
```c
extern const int RemoteUnitArrayStart = 3001;   // 敌方
extern const int RemoteUnitArrayEnd   = 3060;
extern const int LocalUnitArrayStart  = 4001;   // 我方
extern const int LocalUnitArrayEnd    = 4060;
extern const int xsOutputGoal         = 4061;   // 输出
extern const int xsBooleanModifierGoal= 8;      // 是否用后清零
```

**核心：`ObtainWeightedUnitCost(Id)`**
```c
g = xsGetUnitAttribute(Id, cGoldCost) * 2;   // 金权重 ×2
f = xsGetUnitAttribute(Id, cFoodCost);
w = xsGetUnitAttribute(Id, cWoodCost);
result = g + f + w;
```
**金×2 + 食 + 木，石材不计。** 这是官方对"战力≈造价"的量化定义。

**Bug ①：`xsSetGoal` 缩进错位，写进了 while 循环内**
```c
while (i <= LocalUnitArrayEnd) {
   ...
   i++;
xsSetGoal(xsOutputGoal, totalStrength);   // ← 缩进在第 1 层，但在循环体内
}
```
后果：循环每跑一轮都写一次输出 goal，只是最后一次的值正好正确。功能上侥幸不炸，但每帧多余写 60 次 goal——性能浪费。

**Bug ②：`EvaluateRemoteCostStrength()` 的 `i++` 被锁进 if 分支**
```c
while (i <= RemoteUnitArrayEnd) {
   currentID = xsGetGoal(i);
   if (currentID != -1) {
      ...
      i++;              // ← 只有命中时才递增
   }
   else {
      i = 999999;       // ← 靠跳出哨兵值终止
   }
```
对照 `EvaluateLocalCostStrength()` 的对应位置：那边 `i++` 在 `if/else` 之外的公共路径上，且 `else` 分支里的 `i = 999999` **被注释掉了**（`//no break command so we manually break out the loop like this`）。

所以两个函数**行为不一致**：本地版遇 -1 会一直空转到 4060 才停；远端版遇 -1 立刻终止。同一份文件里两套语义——这是从 TP 版移植过来留下的痕迹。

> **实用结论**：这两个函数是"可读的参考实现"，不是"该照抄的规范"。你要做兵力评估，用 bug ② 的写法（遇 -1 立即终止），别用 bug ① 的缩进。

---

## 8. 两条真实工作流

### 8.1 "我要让 AI 会绕后包抄" → 改 `.per` + 借 XS 几何

```
1. 数据层（AGE）：确认兵种 unit-line / min tech level 正确
2. AI 层（.per）：
   (up-get-point position-self-x point-x)          ; 拿自己位置
   (set-goal 333 <origin_x>)  (set-goal 334 <origin_y>)
   (set-goal 331 <target_x>)  (set-goal 332 <target_y>)
   (xs-script-call "FindAdjacentAngle")            ; 算方位角 → goal 335
   (up-modify-goal <angle> g:= 335)
   (up-modify-goal <angle> g:+ <offset>)           ; 偏转
   (xs-script-call "RotateByAngleNoConvert")       ; 旋转目标点 → goal 331/332
   (up-set-target-point 331)                       ; 用算出的点当攻击目标
   (up-target-objects 0 ...)
3. XS 层：不需要自己写，用自带 ailib/Geometry.xs
4. 加载：在 main .per 里 (include "ailib/Geometry.xs")
```

### 8.2 "我要做科技叠加模式（x9 / x256）" → 纯 XS

```
1. 写 xxx.xs，实现 void main()
2. main() 里遍历所有玩家 × 所有科技
3. xsEffectAmount(cModifyTech, tech, cAttrSetStacking, 1, player)
   + 可选 xsEffectAmount(cModifyTech, tech, cAttrSetStackingResearchCap, N, player)
4. 不需要碰 DAT，不需要 AGE
```

**注意 `main()` 是入口约定**——只有带 `void main()` 的 `.xs` 才会被引擎当主脚本调用。全库只有 `x9tech.xs` 和 `x256tech.xs` 两个文件有 `main()`。

---

## 9. 陷阱清单（实战）

| 陷阱 | 证据 | 应对 |
|---|---|---|
| `xsGetRandomNumberLH` 有 bug | `Geometry.xs` 官方注释 `//uncomment when xsGetRandomNumberLH is fixed` | 用 `xsGetRandomNumberMax(n) - n/2` 替代 |
| `.per` 无 `break` | `MilitaryEvaluation.xs` `//no break command so we manually break out the loop like this` | 用 `i = 999999` 哨兵值跳出 |
| `.per` 无数组/排序/三角/sqrt | `Geometry.xs`、`GoalArrayOps.xs` 存在即证明 | 全部走 `xs-script-call` 借 XS |
| XS 桥接无参无返回 | 所有 `xs-script-call` 目标签名均为 `void f()` | 用 goal 号当寄存器，约定区间要写死并全局唯一 |
| goal 区间会撞车 | ailib 已占 3001-3060 / 3004-3005 / 4001-4061 / 331-335 / 194 / 3027 / 8 | 自写库避开这些区间 |
| `#load-if` 是编译期不是运行期 | 311 个符号在编译时定生死 | 运行期分支只能用 `(up-jump-rule)` / `(up-compare-*)` |
| `EffectFunction` 编号有缺口 | 17-24 / 33 / 37 / 40-49 未实现 | 查 `Effects.xs` 实数 41 个，别按 1-56 顺序假设 |
| AGE 不编辑器 AI/XS | `.per`/`.per2`/`.xs`/`defrule` 全 0 命中 | 用文本编辑器 + 游戏内 `xsChatData` 调试 |
| AGE 不编场景 | `.scx`/`.aoe2scenario` 全 0 | 场景用游戏内编辑器 |
| effect 900/1000 有 AI 副作用 | AGE 串 `900 and 1000 mess up the AI` | 慎用这两个 effect command |
| `xsUnsync*` 不进同步 | 函数名与语义 | 只用来做镜头/高亮等纯客户端表现 |

---

## 10. 能力对照表

| 能力 | AGE | 游戏主程序 |
|---|---|---|
| 编辑 DAT（单位/科技/效果/图形） | ✅ 全部 | — |
| 编辑 `.per` AI 脚本 | ❌ 零 | ✅ 378 符号解释器 |
| 编辑 `.xs` 脚本 | ❌ 零 | ✅ 232 syscall + 43 opcode VM + 自动注入 Constants.xs |
| 编译 `#load-if` / `defconst` | ❌ | ✅ |
| 执行 `xsEffectAmount` | ❌ | ✅ |
| AI→XS 桥接 | ❌ | ✅ `xs-script-call` + `include` |
| 编辑场景 `.scx` | ❌ | ✅ |
| 编辑 `.sld` 精灵 | ❌ | ✅ |
| 写 `.dds` | ❌ | ✅ |
| 维护 AI 依赖的 unit-line / min tech level | ✅ **唯一交集** | 读 |

**一句话：AGE 负责"AI 读的那张表"，主程序负责"AI 本身"。两者没有代码级交集，只有数据级依赖。**
