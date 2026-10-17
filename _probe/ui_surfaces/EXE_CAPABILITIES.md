# AoE2DE_s.exe 内务侦察：命令行开关、测试框架、UI 自动化

只读静态分析，**未启动过游戏**。
目标：`D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe`（72,166,200 B，版本 `101.103.54800.0`）
脚本（全部在 `_probe\ui_surfaces\`）：`scan_exe_test.py`、`dump_exe_th.py`、`dump_exe_cli.py`、`dump_exe_flags.py`、`dump_exe_flags2.py`、`dump_flagtable*.py`、`dump_flagsyntax.py`、`dump_flagraw.py`、`dump_tkn.py`、`dump_autotest.py`、`scan_exe.py`
原始输出：`exe_*.txt`

---

## §1 命令行开关表（`+` 前缀）

**语法已确证**：开关用 **`+`** 前缀。证据是 `0x31f9460` 处字样与紧邻的开关名成对出现：
```
0x31f9460  "Use dummy game (voice) chat implementation"   ← 说明
0x31f9490  "+DummyVoiceChat"                              ← 开关（带 + 号，字面存在）
```
整段表位于 `0x3258C00–0x3259200`，格式为 `"说明句\0" ... "FLAG\0"`（说明在前、开关名在后，NUL 分隔）。另有 `+Blacklist`（`0x31f9bc0`）、`+Whitelist`（`0x31f9bd0`）证实同理。

### 完整开关清单（62 条，逐字来自 exe）

| 开关 | 官方说明原文 |
|---|---|
| `IGNORECRCFAILURE` | Ignore failures due to non-matching expected file crc's |
| `FAKE_BENCHMARK_SCORE` | Override your benchmark score |
| `UNCAPPED_SIMULATION_SPEED` | Test simulation speed uncapped |
| `SUBSCRIBE_TO_MODS` | Force subscription to comma-separated mod IDs on login. |
| `WW_ENABLE_BETA_SAVES` | Enable all saves on loading screen |
| `FORCE_LANGUAGE` | Force default language used when resetting defaults |
| `AIDEBUGGING` | Enable AI system debugging |
| `AISCRIPTDEBUGGING` | Enable AI script system debugging |
| `AISCRIPTPROFILING` | Enable AI system profiling |
| `DEBUG_SIMPLE_UI_OPTIONS` | Allow toggling debug simple ui elements. |
| `SKIP_EG_MEM_CHECK` | Skip the EG memory check |
| `SKIP_EG_INSTALL_CHECK` | Skip the EG install check |
| **`NOMODS`** | **Disables all mods** |
| `FORCE_SIMPLE_MENU` | Force light main menu |
| `FORCE_ORIGINAL_MENU` | Force original main menu |
| **`SCRIPT`** | **Script to run** |
| **`TEST_HARNESS_COMM`** | **Enable Test Harness socket communication - Test name as ID** |
| `SCRIPTREPORT` | Script report outputfile |
| `SESSIONID` | Session ID with which client script should join! |
| `RECORDGAME` | Force record game on |
| `FORCE_2X_ASSETS` | Force enable high resolution sprites |
| `UNLOCK_ALL_CIVS` | Ignore civ rotation feature entirely. |
| `SKIPINTRO` | Enable profiling |
| **`WINDOW`** | **Always launch app in windowed mode** |
| `NOVSYNC` | Disable Vertical Synchronization |
| `LOGFPS` | Log Frames per Second |
| `NETWORK_DEBUG` | Debug network activity |
| `OLDLOS` | used for savegame compatibility with old LOS shape |
| `NOFOOTPRINTS` | Disable snow footprints |
| `ALLCP` | All computer players? |
| `ONEBUTTON` | Force One Button Mouse |
| `TWOBUTTON` | Force two button mouse |
| `NOLOGSTATUS` | Output debug lgs for player index to logs |
| `ALLGRASS` | Use InfluencePlacement |
| `LOGGROUP` | Specific unit to log debug, |
| `LOGNET` | Custom path for logging to network. |
| `LOGPLAYER` | Player ID to log |
| `LOGSTART` | Time to begin logging |
| **`RANDOMGAME`** | **Starting random game seed** |
| **`RANDOMMAP`** | **Starting random map seed.** |
| `DRAWLOG` | Draw logging file |
| `DEBUGSPEEDS` | Enable 4.0/8.0 speeds. |
| `NORECORDING` | Disable recording games. |
| **`RELOADGAMEDATA`** | **Reload game data files between games.** |
| `KEEP_MODS_AFTER_CRASH` | Don't disable mods if the previous session has crashed |
| `KEEP_UNLISTED_MODS` | Don't remove mods if current server does not list them |
| `FORCE_RUNAWAY_ESCAPE_MOVE` | Make runaway/escape CTRL+click move behavior default (no CTRL needed) |
| `DISABLE_RUNAWAY_ESCAPE_MOVE` | Disable runaway/escape CTRL+click move behavior |
| `FORCE_SINGLE_UPDATE_PER_RENDER` | Forces only one update per render in multiplayer games |
| **`LIMIT`** | **Limit population (25 - 200)** |
| `NOWOLF` | （狼开关） |
| `FORCEWOLF` | （狼开关） |
| **`EXIT`** | **Automatically exit after specified game time** |
| `DEVELOPER` | （开发者模式） |
| `TESTUISCREEN` | Run game with testscreen |
| **`WRITE_MAP_INFO`** | **Write out a text file containing map info** |
| `LAUNCH_GAME_VARIANT` | AOE1 or AOE2. User privilege is still required |
| **`RUN_REGRESSION_TESTS`** | **Run regression tests on game data from previous versions of the game.** |
| **`EDITOR`** | **Boot directly into the scenario editor.** |
| `MORE_MAP_SIZES` | Display additional map sizes when setting up a game or scenario. |
| `SPEED1` / `SPEED2` | （速度档） |

### 工具管理器专用开关（`0x334E7A0` 起，独立表）
| 开关 | 官方说明原文 |
|---|---|
| `RUN_REGRESSION_TEST` | Run specific regression tests on game data from previous versions of the game. Takes the regression directory of a specific test. |
| `EXIT_AFTER_POST_INIT_TOOLS` | Request application to exit after post init tools are run. |
| `TOOL_MANAGER_LOG_LOCATION` | Specify the log file path for the tool manager |

### 自动化/测试专用开关（分散）
| 开关 | 官方说明原文 |
|---|---|
| **`RUNNING_AUTOTEST`** | **Ignore any code that may halt the game since we are running an automation test that may not handle what a human can.** |
| `DISABLE_CONTROLLER_DISCONNECTED_DIALOG` | Turn off the controller disconnected dialog |
| `DISABLE_GAMEPAD_RUMBLE` | Turn off gamepad rumble regardless of other settings |
| `DEBUG_TH_TIMEOUT` | Turns on the debug break when a WAITEVENTTASKTIMEOUT times out. |
| `EXTRA_SPACE_MODE` / `FORCE_BVT_AI` / `USE_BVT_AI_ON_ALL_SLOTS` / `SET_FIXED_WORLD_UPDATE` / `USE_FPS_CHECK` / `USE_MEMORY_LEAK_CHECK` / `USE_STARTAPP_TIMER` / `DEBUG_BREAK` | （测试用） |

### ★ 这些开关合起来意味着什么
`RANDOMMAP`（固定地图种子）+ `GAM`（起始存档）+ `EXIT`（到指定游戏时间自动退出）+ `WINDOW`/`NO_WINDOW` + `RELOADGAMEDATA`（局间重载数据）+ `KEEP_UNLISTED_MODS` + `NOMODS`（一键关全部 mod）+ `RUNNING_AUTOTEST` 这一组，**正是"可复现地自动跑一局、跑完自动退出、且能控制加载哪些 mod"所需的全部零件**。

本项目此前唯一挂着的真实未知是**"没有官方无头引擎，不可能真的跑一局验证"**。这张表把该判断修正为：**存在一条未公开但真实存在的自动化运行路径**。若可用，则"改完数据/地图/AI 能不能被引擎接受"可从文件级验证升级为**运行时验证**——这是整个项目最大的能力跃迁点。
`NOMODS` 与 `KEEP_UNLISTED_MODS` 还直接解决了"怎样做受控 A/B 实验"（只启用某一个 mod）的问题。

### 诚实边界（必须写明）
- 全部来自**静态字符串**，**未启动过游戏**。字符串存在 ≠ 在发行版里生效、≠ 按字面语义工作、≠ 不需要登录/联机。
- 未知：取值格式（`EXIT` 是秒还是帧？`LIMIT` 之外的参数形态）、是否需要 `DEVELOPER` 前置、是否被发行版剥离、`NO_WINDOW` 是否真是无渲染路径（它出现在窗口模式枚举 `FULL_DESKTOP/FULL_SCREEN/MAXIMIZED/MINIMIZED/NORMAL/NO_WINDOW` 里，也可能是内部状态名）。
- 参数拼接方式（`+EXIT 300` 还是 `+EXIT=300`）**未确证**。

---

## §2 内置测试框架 `testharness`（139 处引用）

不是死字符串，是一套完整子系统：

- **存储点**（`0x31F8A10` 起，且已注册进 `Pompeii.json`）：`testharness\`、`testharness\scripts\`、`testharness\reports\`、`testharness\regressionsaves\`、`testharness\xs\`
- **存储点枚举**：`TESTHARNESS`、`TESTHARNESS_SCRIPTS`、`TESTHARNESS_REPORTS`、`TESTHARNESS_REG_SAVES`、`TESTHARNESS_XS`、`TESTHARNESS_XS_SCRIPTS`
- **网络层**：`TEST_HARNESS_COMM`、`TEST_HARNESS_ADDRESS`、`testharness::comm::Init UDP socket initialized on address %s`、`testharness::comm::SockFree` → **通过 UDP socket 与外部测试驱动通信**
- **C++ RTTI 类型**（`0x412CCD0` 起，命名空间 `testharness::`）：`GameTestEventController`、`EdgeLinkObject`、`MapObject`、`GameOptionsObject`、`RandomObject`、`PlayerObject`（各带 `<lambda_1..5>`）
- **AI/XS 侧接口**：`up-testharness-report`、`up-testharness-test`、`fe-testharness-message`、`fe-testharness-log-seed`
- 源码路径：`Aoc\Source\Tools\Regression\RegressionTest.cpp`、`RegressionStringList.cpp`、`RegressionLocale.cpp`、`Aoc\Source\Tools\ToolFileSystem.cpp`
- 本机 `C:\Users\26913\Games\Age of Empires 2 DE\testharness\` 有 `regressionsaves` 与 `reports` 两个**空目录**

### 回归测试实际测什么（从字符串重建）
| 阶段 | 证据字符串 |
|---|---|
| 发现用例 | `..\RegressionTests\SaveFiles\*`、`Running regression tests '%s'`、`No regression tests found`、`Failed: %s` |
| 玩家档案 | `\*.nfp` → `Checking player profile file: %s` → `Player profile ok: %s` |
| 热键 | `\*.hkp` → `Checking hotkey file: %s` → `Hotkeys ok: %s` |
| 字符串表 | `Checking string list file: %s`、`stringlist.dat`、`string list ok: %s`、`verbose logging of the regression locale test.` |
| 场景 | `\resources\_common\scenario\` → `Testing scenario: %s` → `Scenario Ok: %s` |
| 战役 | `\resources\_common\campaign\` → `Testing campaign: %s` → `Campaign has %d scenarios` → `Campaign Scenario :%s` |
| **真起一局** | **`Creating scenario server...` → `Started game ok...` → `Campaign Ok: %s`** |
| 存档 | `\savegame\` → `Save game found: %s` → `Success!`；`\savegame\multi\` |
| 云接口 CRUD 自测 | `Creating new file` `testfile1.test` → `writeToCloudInterface did not increase file count` → `Reading the saved file` → `read from cloud data does not match what was saved` → `Deleting the test file` → … → `Cloud interface tests success!` / `failure!` |

**`Creating scenario server...` + `Started game ok...` 证明官方自己在无交互地起一局游戏做验证。**

---

## §3 ★ UI 自动化框架（本轮最重要的第二个发现）

exe 里存在一整套**按控件名驱动 UI 的任务处理器**，每个都带参数校验说明：

| 处理器 | 参数说明（原文） |
|---|---|
| `SELECTUIDROPDOWN` | `Incorrect number of params - should be 3 : Collection name, widgetName and dropdown Index.` |
| `SELECTUILISTBOX` | `Incorrect number of params - should be 4 : Collection name, widgetName, itemName and dropdown Index.` |
| `SETUISLIDER` | `Incorrect number of params - should be 3 : Collection name, widgetName and slider value.` |
| `UPDATELISTBOX` | `Incorrect number of params - should be 2 : Collection name and widgetName.` |
| `SETTEXTBOXSTRING` | `Incorrect number of params - should be 3 : Collection name, widgetName and String.` |
| `UIWIDGET` / `ACTIVECOLLECTIONS` | （集合/控件寻址） |

外加**键盘鼠标模拟**：`KEYBOARD`、`LBUTTONDOWN`/`LBUTTONUP`、`RBUTTONDOWN`/`RBUTTONUP`、`MBUTTONDOWN`/`MBUTTONUP`、`SYSKEYDOWN`/`SYSKEYUP`；错误串 `Active screen is not Age 2; KBM Simulation events will not work. Failing`。
任务系统：`Error: Execute Failed to find task '%s'`、`Error: Cannot execute multiple '%s' tasks`、`Created Task %s:%s`、`Error: Failed to spawn '%s' task`、`TASK ID<%lu> <%i:%04.1f>: %s %s`、`TASK STATS: Tasks Completed %i Tasks Failed %zu`。

### 意义（对本项目直接相关）
- 游戏**自带的自动化 UI 驱动**，按 `Collection name + widgetName` 寻址——与我们在 `widgetui/*.json` 里看到的 widget `Name` 字段**同一套命名空间**。
- 这意味着"模拟玩家在假界面上操作"这条产品路线，**游戏自己已经实现了底层原语**；我们的工具若走"真实游戏内预览"，可以复用这套寻址模型。
- 也解释了 `TESTUISCREEN`（Run game with testscreen）的用途。

---

## §4 内置脚本语言（`TKN_*` / `.fts`）

一套独立的、面向"驱动游戏 + 断言"的脚本语言：

- **9 个 token**：`TKN_EXECUTE`、`TKN_FPS_CHECK`、`TKN_GET`、`TKN_GOTOIF`、`TKN_MEMORY_LEAK_CHECK`、`TKN_REPORT`、`TKN_SET`、`TKN_STARTAPP_TIME`、`TKN_WAIT`
- **语法元素**：label（`label already define '%s'`、`illegally named label`）、赋值（`expected '='`、`a valid assignment operator`）、变量（`invalid named variable`、`variable already defined`）、`RANDOM(min,max)`、基本算术（`only basic arithmetic is supported`）、`{CURRENTTIME}` 占位符、注释、`GOTOIF`
- **事件任务**：`EVENTTASK`、`EVENTPROPERTY`、`EVENTPROPERTYCONTAINS`、`TIMEOUTCONTINUE`、`TIMEOUTFAIL`、`EVENTTASKTIMEOUTGOTO`、`EventController` 属性读写（`failed to Set Event Controller property '%s':'%s'`）
- **错误报告完整**：`Error: Parsing script '%s' @ line %d col %zu : ...`、`fts script line: %d`
- 相关开关：`SCRIPT`（Script to run）、`SCRIPTREPORT`（Script report outputfile）、`SESSIONID`

→ 这是**官方自用的端到端测试脚本引擎**（起应用 → 等待 → 检查 FPS/内存泄漏 → 读属性 → 断言 → 报告）。`+SCRIPT` 开关就是入口。

---

## §5 与已知结论的关系

**不推翻**任何已有结论。需要修正的只有一条措辞：
- 旧记录：「没有官方无头引擎，**不可能**真的跑一局验证平衡」→ 修正为：**「没有公开文档化的无头模式，但 exe 里存在一组用于自动化运行、自动退出与受控 mod 加载的开关，以及一套内置测试框架」**。是否真能用仍需一次实测。

**互相印证**：
- `modes\Pompeii\Pompeii.json` 的 28 条存储点注册表，正是 `Aoc\Source\Engine\FileSystem\storagepoint.cpp` 的产物；exe 里完整存储点枚举 **46 个**，并带**根枚举** `COUNT NONE NOTFOUND TEMP BASE APPATA USER MODSROOT LOCALMODS SUBSCRIBEDMODS DLC CLOUD`（`StoragePointBase_t` / `StoragePoint_t` / `PathSpec` 类型名可见）。→ **mod 覆盖是"逐存储点解析"**，这解释了为何 `replace:false` 的条目仍能被覆盖。
- `NOMODS`/`KEEP_UNLISTED_MODS`/`KEEP_MODS_AFTER_CRASH` 印证了"游戏更新或崩溃后会禁用 mod"这一官方已知行为，并给出**规避开关**。

**引擎认识但此前未记录的裸名 JSON**（补入清单）：`Achievements.json`、`CustomMapIcons.json`、`LifecycleTelemetryEvents.json`、`NamedIdGroups.json`、`TelemetryEventsHighPriority.json`、`TelemetryEventsNormalPriority.json`、`adapter_blacklist.json`、`history.json`、`intro.json`、`outro.json`、`paphos_campaign.json`、`peru_campaign.json`、`providence_campaign.json`、`standard_terrain_effects.json`、`fallback_layout.json`、`_layout.json`、`civTechTrees.json`。

---

## §6 下一步：需要用户决定是否做一次受控实测

要把 §1–§4 从"静态字符串"变成"已证实能力"，需要**实际启动一次 `AoE2DE_s.exe`**。真实风险：
1. 占用用户机器与 Steam 会话；用户正在游戏时会打断
2. 传参语法未确证，需试探，可能弹窗/崩溃
3. 首次启动可能要联网/登录
4. **绝不能在用户的正式存档/联机环境里乱试**

建议的安全做法：复制一份 profile 到临时目录 → 用 `+GAM` 指向自造存档或场景 → `+EXIT` 限时 → `+WINDOW`（不用 NO_WINDOW，先确保看得见）→ `+NOMODS` 隔离 → `+RELOADGAMEDATA`。即使如此，**仍必须先征得用户同意**。
