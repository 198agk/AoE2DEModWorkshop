# 「dat 目录下的声明式 JSON」到底读哪一份（2026-10-22 实测，**已修正**）

## 一句话结论

`resources\_common\dat\` 下**松散 JSON 的 mod 副本会被引擎采纳**。
`civilizations.json` 已用双 canary 在同一局里同时证明（见 §一）。

⚠️ 本文件的第一版结论（「mod 副本不生效」）是**错的**，§三 记录它错在哪、为什么当时的判据不成立。

---

## 一、铁证：同一个 mod 里，`.dat` 编辑与松散 JSON 同时生效（v45）

`_probe\tmp_build_v45.py` 构建 `dsh test v45 ships civilizations.json`：

| 部分 | 内容 |
|---|---|
| `resources\_common\dat\empires2_x2_p1.dat` | 村民（83）`hit_points = 40`（产品路径 `tk.plan` → `serialize_dat`，`edits 1701` 覆盖 63 文明） |
| `resources\_common\dat\civilizations.json` | **全部 63 个** `civilization_list[].name_string_id` 改成 `10281`（维京） |

`civilizations.json` 41,586 B；安装 `installed True prio 2 dat_sha b89c408e…`。

冷启动 → 选 v45 → 开局，实测（`_probe\tmp_play.py 'dsh test v45'` 的 OCR）：

```
[town centre panel]
   ( 253, 881) 城镇中心
   ( 616, 882) RemonBo（维京）     ← JSON 生效：随机到的不是维京，却显示"维京"
   ( 254, 953) 2904/2904
```

再按 `.`（PERIOD）选中空闲村民（`--box 230 850 900 1000`）：

```
( 242, 881)  0.99  村民
( 616, 882)  0.91  RemonBo（维京）   ← JSON 生效
( 243, 953)  0.93  10/40             ← .dat 生效：出厂 25，改后 40
```

**两个 canary 在同一局、同一 mod 里同时成立。** 「把 63 个文明名都指向同一个字符串 id」这个设计
让 JSON 的读数不再依赖随机到哪个文明 —— 这是本次能拿到铁证的关键。

## 二、为什么先前会得出相反结论

第一版报告依据的是 v41/v42/v43/v44，它们都用 `objreplacement.json` 当被测文件，
判据是「村民看起来是男是女 / 骑马还是站着」。这些判据**一个都不成立**：

1. **面板不显示性别**：出厂 `5121 = "村民 (男性)"`，但屏幕上一直只读「村民」。
   v45 这次也一样（`10/40` 那一局同样只读「村民」）。所以「读不到女性」不是证据。
   已装的第三方文本模组（`423822_军团长天赋文本` prio 10、`550009_文明联盟文本UI(v21)` prio 9）
   都可能覆盖了这条文本。
2. **美术被整体换皮**：`182654_Age of Anime (Chibi Edition)`（prio 7，enabled）把单位外观全换了，
   「看起来像女性」不是 `objreplacement` 能产生的判据。
3. **场景模组伪造了开局**：`[Map]7V1_The_ThreeKingdoms`（prio 19，当时 enabled）让开局变成
   **20000 资源 / 帝王时代 / 自带骑兵**。v44 那次我看到「四个骑马单位、零个站着村民」就以为
   `objreplacement` 生效了 —— 那其实是场景自带的部队。**这一条差点让我把假信号写成结论。**

⇒ 结论：`objreplacement.json` 的 `replacement_rate`/`chance` **至今没有任何有效读数**，
不是「已证不生效」。

## 三、仍然成立的那一半：原地改出厂文件有效（A→B→C→D）

把 `<game>\resources\_common\dat\objreplacement.json` 原地改写（该文件**不在** EXE 内编译的
50 条 CRC 表里），每次关游戏重开。四轮唯一变量是文件内容：

| 轮 | 内容 | 帧 | 观察 |
|---|---|---|---|
| A | 出厂原样（2533 B，sha16 `ee2f1f5a5b3a1591`） | `shots\nomod_1.png` | 站着的村民 + 一个骑马斥候 |
| B | `83→293 chance 100` + `448→546 chance 100` | `shots\nomod_1.png` | 判据不可用（见 §二） |
| C | `83→448 chance 100` | `shots\nm2_1.png` | 四个单位全部骑马，零个站着村民 |
| D | 逐字节还原 | `shots\nmA_1.png` | 村民回到地上 |

C 与 D 的差异只能由这个文件解释。**但 C 的判据依赖 chibi 之外的外观，仍需在关掉美术模组后复验，
才能和 v45 的 JSON 通路合成同一句话。**

## 四、产品层面的处理

- 三份 JSON 层报告（`report_json_layers.md` / `report_unitlines.md` / `report_linkedtechs.md`）
  列出的空槽，**可以**通过「发一个带 `.dat` carrier 的数据 mod + 松散 JSON」交给玩家 ——
  前提是那个 JSON 本身被采纳。`civilizations.json` 已证；其余逐个需要自己的 canary。
- `aoe2mod/mod/emitter.py` 现有的「往 DAT storage point 写 JSON 就必须带 `.dat`」规则是真的
  （不带确实起不了），它与「JSON 会被采纳」是两件事，都要写进产品文档。
- 文本必须单独成 mod（用户点破）—— 那是另一条独立规则，已实测。

## 五、方法论（这次真正的收获）

1. **一个变量一个 canary，两个 canary 放在同一局里**：`.dat` 的 canary 用血值（面板可读），
   JSON 的 canary 用一个**与随机无关**的字段（把 63 个文明全指同一个名字），这样「随机到谁」不再影响判定。
2. **先证明仪器能动**：任何外观类判据在换皮模组下都无效；任何开局类判据在场景模组下都无效。
3. **不确定就换文件**：`objreplacement` 纠缠了三个混淆变量（文本被覆盖、美术被换皮、场景模组），
   换成 `civilizations.json` 一次就干净了。

## 六、本次留下的工具与备份

- `_probe\tmp_build_v45.py`：本次铁证的构建脚本（可复用骨架）。
- `_probe\tmp_patch_shipped.py` / `tmp_patch2.py` / `tmp_restore.py`：原地改 / 还原出厂文件，打印 sha 对比。
- `_probe\tmp_record_abba.py` → `_probe\objreplacement_abba.json`：四轮链的可复查记录。
- `_probe\tmp_play.py` / `tmp_play_resume.py` / `tmp_play_nomod.py`：开局与读数工具。
- `_probe\shipped_objreplacement_backup.json`：出厂文件原样备份（2533 B，sha16 `ee2f1f5a5b3a1591`）。
  现场已还原，游戏目录里只剩 `objreplacement.json`（2533 B）。

---

## 七、2026-10-25 追加：三处只读取证，把开放项收窄了

这一节不改上面任何读数，它补的是「这个文件自己的词汇」和「它坐在哪个存储点」。

### 7.1 引擎里有一张字段表，紧跟文件名之后

`AoE2DE_s.exe` 偏移 **53213376** 起是连续的一组字符串：

| 偏移 | 字符串 |
|---|---|
| +0 | `objreplacement.json` |
| +24 | `objects` |
| +32 | `object_id` |
| +48 | `object_override` |
| +64 | `replacement_object` |
| +84 | `chance` |
| +96 | `replacement_attribute` |
| +120 | `required_attribute` |
| +144 | `excluded_computer_players` |
| +176 | `technology` |
| +192 | `technology_state` |
| +216 | `replacement_rate` |

它们是**有序连续**的，不是散落在别处的同名片段；紧跟着的一段是
`F:\Agents\PhoenixBuilders-08\...\RandomMap\Modules\ObjectGenerator.cpp`
和若干 `(RandomMapSync) ...` 日志格式串 —— 也就是这个文件的解析器在这个模块里。

- 出厂数据用到 11 个字段里的 **10 个**；`replacement_rate` 在整个 2,533 字节里**一次都没有**。
- 所以「这个文件有哪几种键」不再是猜的。仍然不能由此推出「引擎读 mod 的副本」。

### 7.2 `chance` 是百分比，不是布尔开关

出厂文件里 `chance` 只出现 **两次**，值都是 **50**，且都在同一对上：

```
[0] Villager         -> Villager (Female)   chance=50
[1] Villager (Female)-> Villager            chance=50
```

村民与女村民互换，正是游戏里唯一「随机换一个单位」的地方。所以 50 = 一半概率，
这是文件自己的用法，不是从画面上反推的。

**这条对实验设计的直接后果**：以后测 `objreplacement` 必须把 `chance` 写成 100，
否则「一半概率不换」会被读成「没生效」——2026-10-24 的 B 轮就有这个歧义。

### 7.3 存储点表：`resources\_common\dat` 是唯一带 `use_modes_path_for_mods` 的

`modes\Pompeii\Pompeii.json` 的 `storage_point_list` 共 **28** 个存储点，
其中 `use_modes_path_for_mods` 为真的只有 **1** 个：

```
resources\_common\dat    type=DAT    use_modes_path_for_mods=True
```

`objreplacement.json` 与 `linkedTechs.json` 都在这个目录下。

### 7.4 于是那条「mod 副本不生效」的说法站不住

同目录的 `civilizations.json` **已经用 v45 证明过 mod 副本会被采纳**（63 个文明
`name_string_id` 全改成 10281，面板把非维京读成「维京」）。它与 `objreplacement.json`
是兄弟文件、同一个存储点。

⇒ 收窄后的诚实状态是两句，而不是一句：

1. **这个目录里的松散 JSON 会被读**（v45，双 canary 同局成立）；
2. **`objreplacement.json` 本身仍没有一次干净的读数** —— 2026-10-24 那几轮同时开着
   换皮、主题、场景三个模组，任何外观判据都被它们污染。

所以开放项从「这个文件读不读」变成「**用一局干净的游戏确认它**」，而这一局的
设计约束已经被 §7.1–7.3 定下来了：`chance=100`（不引随机）、掉换对要**看得见差别**
（村民→斥候，而不是村民→女村民）、同文件夹带一个 `.dat` canary（面板可读的血值）
证明挂载、且**第三方模组全部关掉**。

### 7.5 这一节新增的工具（只读）

- `_probe\tmp_objrepl_chance.py`：文件形状、键名普查、`chance` 取值的分布、EXE 里
  这几个名字的命中数。
- `_probe\tmp_objrepl_fields.py`：把 EXE 偏移 53213376 前后的可打印串全部打出来，
  以及 8 条出厂条目逐条原样打印。
- `_probe\tmp_objrepl_nested.py`：**第一版读错层级的记录** —— 它问
  `entry.get("chance")`，而数据嵌在 `object_override` 里，于是印出「没有任何条目带
  chance」而文件里明明有两处。同一天第 N 次「在方便读的层级读字段」。改正后 10/11
  字段被出厂数据使用、`chance` 2/8 条目。
- `_probe\tmp_objrepl_storage.py`：28 个存储点全表 + 两个 JSON 文件落在哪一格。
- `_probe\tmp_objrepl_logs.py`：EXE 里与 `replace` 相关的 33 条可打印串、以及 26 个
  日志目录 258 个文件里**没有任何一条**替换相关的日志行 ⇒ 没有日志旁证，只能靠屏幕。
- `_probe\tmp_mod_listing.py`：当前安装 19 个 mod、启用 5 个，其中**第三方启用 4 个**
  （换皮、主题、文明联盟文本、军团长文本）—— 干净的一局必须先把这 4 个关掉。
- `_probe\tmp_build_objrepl.py`：已构建 `_probe\out_objrepl_mod`（`info.json` 92 B +
  `.dat` 11,982,495 B + `objreplacement.json` 1,656 B，7 条条目，`chance=100` 的
  村民→斥候）。**尚未安装、尚未开局**，因为全量套件正在跑，装模组会让那一轮描述
  两个状态。

## 八、读它的不是对局代码，是随机地图模块（2026-10-25 11:4x）

这一节回答了「这层什么时候生效」—— 而时机决定了实验怎么做，所以它比再多跑一局更值钱。

### 证据：字段表后面紧跟的是地图生成器的日志

`objreplacement.json` 的偏移是 53213376，字段表占 240 字节，**紧跟着的字符串是**

```
F:\Agents\PhoenixBuilders-08\p4\portland_group\Aoc\Source\Game\RandomMap\Modules\ObjectGenerator.cpp
```

再往后全部是地图生成期的日志格式串，逐条都在说「往地图上放一个对象」：

```
+352  (RandomMapSync) create objects: obj-id: %d, group-flag: %d, num-of-groups: %d, land-id: %d
+592  (RandomMapSync) place_land_objects(info_line, info.lands[index].x=%d, ...
+840  (RandomMapSync) ANYWHERE - place_objects(info_line)
+1136 (RandSync) Placing single object: obj-id:%d, pos:<%f,%f>, player:%d
+1664 place_land_objects
+1832 place_group
+2016 place_cluster
+2384 GetActualObject
+2400 ResolveMasterID
+2496 RGE_RMM_Shallows_Generator
+2584 RGE_RMM_Terrain_Generator
+2664 RGE_RMM_Script_Controller
+3112 (RandomMapSync) Initiating random map script (rms) generation.
```

`RGE_RMM_*` 是 Ensemble 引擎里 Random Map Module 的前缀，`GetActualObject` / `ResolveMasterID` 就是「这个对象真正要放成什么」的那个解析函数。整份文件里 `objreplacement.json` 只出现一次。

### 它意味着什么

`objreplacement.json` 在**地图生成时**决定「脚本要放的这个对象，实际放成哪个对象」。它不是对局中的规则，也不是面板上的东西。

三条直接后果：

1. **出厂数据里唯一用 `chance` 的那一对是村民 ↔ 女村民**（各 50），而开局那几个村民**正是地图脚本放的** —— 这是出厂数据为什么只在这一对上用随机的解释，也和「别处没有随机换单位」一致。
2. **判据必须看「地图放了什么」**，也就是开局就站在地上的单位。用「造出来的兵」「打到一半的状态」去判，永远读不到这层。
3. **必须是新开的一局**：文件在地图生成前读，事后改它对这一局没有任何作用。

### 这同时解释了 2026-10-24 四轮实验里唯一那次正结果

`A/B/C/D` 四轮里 run C（把出厂文件改成村民 → 斥候、`chance=100`）看到「四个全部骑马、没有站着的村民」，run D（逐字节还原）看到「村民回到地上」。当时我只敢说「这个文件的改动能被看见」，现在知道**为什么**：开局村民是地图放的，替换在生成期发生，所以换的正是开局的单位。

### 于是「mod 副本读不读」这一问现在是可测的，而且只差一局

实验设计（四条同时成立，缺一条读数就不可归因）：

1. mod 里发 `resources\_common\dat\objreplacement.json`，`chance=100`，村民 → 斥候（不要村民 → 女村民，那对在美术模组下看不出差别）；
2. 同一个 mod 里带一个 `.dat` canary（改城镇中心血量，面板可读）证明 mod 挂上了；
3. **关掉所有第三方模组**（2026-10-24 那几轮开着换皮、主题、场景三个，读数不可归因）；
4. 装完**新开一局**，看开局那几个单位是村民还是骑兵 —— 不是看造出来的兵。

构建脚本 `_probe/tmp_build_objrepl.py` 已按这四条产出 `_probe/out_objrepl_mod`（`info.json` 92 B + `.dat` 11,982,495 B + `objreplacement.json` 1,656 B，7 条、`chance=100` 的村民 → 斥候 448）。**尚未安装**：当前正在跑全量套件，而 `test_zero_mod_experiment.py` 会数已启用的模组 —— 装一个实验 mod 会让那一轮套件失去意义。

## 九、这条发现对产品本身意味着什么

「读它的是随机地图模块」不只是实验设计的输入，它改变了产品该怎么说话。

### 1. `declared_edges()` 是**地图生成期**的替换，不是编辑期的别名
产品里 `aoe2mod/game/families.py` 的 `declared_edges()` 读的就是这个文件，把村民 ↔ 女村民当成一族（`(83, 293)`）。以前这个关系读起来像「这两个 id 是同一个东西的两种记录」。现在有了证据支持的是更窄的说法：**地图脚本放村民时，百分之五十会放成女村民**。两者仍然是两条独立记录，各有各的血值、成本、图标槽 —— 这正是 `unit.stat` 对 83 单独改不会自动改 293 的原因（`edit_count 63` 而不是 `126`）。

### 2. 任何「换皮」类改动都分两半
`unit.sprite` 走的是 `.sld` 松散文件覆盖，玩家在**对局里**看到的是文件；而 `objreplacement` 走的是**地图生成期**的单位选择。两半在不同阶段生效，所以：

- 对局中把村民换成别的样子 —— 可能被地图生成期的替换再改一次（如果那一对还在表里）；
- 反过来，改 `objreplacement` 不会让已经站在地上的单位变样子，它只影响**这一局开始时**被放下的那些。

产品里目前只有前半（`unit.sprite`），后半（`objreplacement`）**一个意图都没有**，而这条发现说明它是个**独立的、有价值的意图**：`unit.replace_on_map`（「地图上放的村民有一半换成斥候」）——出厂数据自己在用，`chance` 是现成字段，判据是开局那几个单位。

### 3. 诚实边界的措辞要改
报告 §七 收尾那句「mod 副本读不读仍没有干净读数」现在可以更准确：**判据已经明确，缺的只是一局**（四条约束见 §八）。这比「不知道」强，也比「已证不生效」诚实 —— 后者是我 2026-10-24 写下的错误结论，靠兄弟文件 `civilizations.json` 被 v45 证伪。

### 4. 下一步的顺序（写在这里，免得再靠记忆）
1. 现在这一轮全量套件跑完（`_probe/out_suites_objrepl.txt`，125 条 py + 1 条 node）；
2. 装 `_probe/out_objrepl_mod`（已按四条约束构建好，**尚未安装**），**关掉全部第三方模组**，新开一局，看开局那几个单位；
3. 读数无论正反都写进 §七/§八；
4. 只有读数为「读」时，才值得把 `unit.replace_on_map` 做成第 14 个意图；读数为「不读」就把 `declared_edges()` 的用途重新审一遍 —— 因为那意味着出厂那一对也是死的。

## 十、2026-10-25 16:2x：干净一局之前，模组这一侧的四条前提全部在磁盘上量过了

上一节把「为什么要一次干净的一局」写清了，但没写「怎么知道那一局读了什么」。
今天用两个只读探针把模组这一侧能量到的都量了（`_probe/out_objrepl_check.txt`、
`_probe/out_objrepl_canary.txt`），这样开局之后**唯一的未知量就只剩引擎的行为**。

### 10.1 四条前提（三条在磁盘上，一条在 profile 上）

| 前提 | 为什么要 | 实测 |
|---|---|---|
| `chance = 100` | 出厂是 50；「一半概率不换」会被读成「没生效」 | 村民 83 → 斥候 448，`chance=100` ✓ |
| 掉换对肉眼可见 | 村民 → 女村民这一对，两个美术模组已经让它们看起来一样 | 村民 → 斥候（有没有马） ✓ |
| 同文件夹带 `.dat` canary | 「什么都没变」与「模组没挂载」必须能区分 | 五条城镇中心记录 2400/1950 → **4000** ✓ |
| 第三方模组全关 | 2026-10-24 那几轮同开换皮/主题/场景三个 mod，不可归因 | 4 个第三方 ON，**开局前必须关** ✗ |

### 10.2 canary 的具体读数（`tmp_objrepl_canary.py`）

不复用「上次那轮的 4840」——那是帝王时代加成后的**显示值**，而 `.dat` 里存的是
**原始值**。逐条比对模组流与出厂流：

```
British records: mod 2164, shipped 2164
unit 71    RTWC2   2400 -> 4000    CHANGED
unit 109   RTWC    2400 -> 4000    CHANGED
unit 141   RTWC3   2400 -> 4000    CHANGED
unit 142   RTWC4   2400 -> 4000    CHANGED
unit 444   PTWC    1950 -> 4000    CHANGED
differing records: 5        differing records outside British: 0
```

⇒ **开局后城镇中心面板必须是 4000（黑暗时代倍率 1.00），或者 4840（帝王 1.21）；
读到 2904 就说明这一局没挂载**（出厂 2400 × 1.21）。

### 10.3 这条探针第一版是错的，错法与本月另外三次同族

第一版按「显示名含『城镇中心』」筛记录，打印 `records whose hit_points differ: 0`
—— 读起来正是「这份 `.dat` 不带 canary」。**真因**：`locate()` 的 unit 记录里
`name` 是内部名（`VMBAS` / `RTWC`），没有显示名；显示名要另查字符串表。
于是「0 条不同」是「问错了字段」，不是「没改」。

同族的三次：`u.get("attacks")`（应该在 `type50` 里）、`entry.get("chance")`
（应该在 `object_override` 里）、`tk._civs` 未初始化时按 `None` 迭代。
**判据**：一个探针报「零」，先问它问的是不是那个字段，再问被测系统。

### 10.4 下一次干净一局的最小步骤（不需要再改代码）

1. 关掉 4 个第三方模组（`Age of Anime` / `透明主题` / `文明联盟文本UI(v22)` / `军团长天赋文本`）；
2. `Start-Process` 关游戏（如果开着），`tk.install(_probe/out_objrepl_mod, position=1)`；
3. 开一局**标准**（不选场景模组，否则 20000 资源 / 帝王时代会把画面伪造成证据）；
4. 读城镇中心面板：4000/4840 = 挂载；2904 = 未挂载；
5. **看地上站着的是村民还是斥候** —— `objreplacement` 在**地图生成期**生效
   （§八），所以判据必须是开局就站在地上的单位，不是造出来的兵。

第 5 条是这次和以前最大的区别：以前几轮都在看「造出来的单位长什么样」，
而这一层在造兵之前就已经决定了。

## 十一、★★ ANSWERED 2026-10-25 16:3x：`objreplacement.json` 的**模组副本会被采纳**

这是本文件唯一一个悬了两个月的问句。今天一局干净的游戏把它回答了。

### 11.1 这一局是怎么干净的

与 2026-10-24 那几轮的区别只有一条，但正是那一条让读数有意义：**除了我们自己的
探针模组，没有任何模组是开着的**。

```
turned off: 182654_Age of Anime (Chibi Edition)
            550412_透明主题整合自用
            550009_2026 Civilization Alliance 文明联盟  文本UI(v22)
            423822_四月-juntuanzhangtianfuwenben军团长天赋文本
left on   : dsh 模组工坊 文本        (这个工具自己的字符串表)
installed : dsh test objrepl 村民换斥候   (prio 2)
```

> 踩到的一处：`550009` 的记录名里 `文本UI` 前面是**两个空格**，`want in name`
> 用单个空格匹配不到，第一次"关掉了四个"其实只关掉三个。第二次按工坊编号
> `550009` 匹配才关掉。**这说明「我关掉了第三方模组」这句话本身也需要读数。**

### 11.2 同一局里的两个读数

模组是一个文件夹、两样东西：一份 `.dat`（唯一改动是五条英国城镇中心记录
2400/1950 → **4000**，用作挂载 canary）和一份 `objreplacement.json`（村民 83 →
斥候 448，`chance=100`）。放在同一个文件夹是刻意的：「什么都没变」必须能和
「模组没挂载」区分开。

```
[town centre panel]   (254, 953) 4000/4000          <- .dat 挂载了（出厂 2400）
[click a mounted unit] (254, 881) 斥候骑兵            <- 地上那个单位是 448
                       (241, 953) 45/45
```

`_probe/tmp_objrepl_attrib.py` 从出厂流里读出的对照：
```
unit 83   VMBAS   hit_points=25  class=4     <- 规则点名的那个
unit 448  SCOUT   hit_points=45  class=47    <- 面板读到的那个
```

⇒ **45 只能来自 448**。这不是"看起来像骑兵"，是记录编号对得上。而且那一局
**开局站在地上的单位就已经是斥候**，一个村民都没有 —— 这一层在**地图生成期**
（§八：`RandomMap/Modules/ObjectGenerator.cpp`）生效，与造兵无关。

### 11.3 因此收窄成三句话（取代之前那两句）

1. `resources\_common\dat` 这个存储点里的松散 JSON **会被读** —— v45 用
   `civilizations.json` 证过，今天用 `objreplacement.json` 又证一次，两次都是
   同一局里另一个 canary 同时成立。
2. `objreplacement.json` 的 `chance` 是**百分比**，`100` 才是确定的替换
   （出厂只有村民↔女村民那两处用 50）。
3. 它的作用时刻是**地图生成期**，所以判据必须是开局站在地上的单位；此前几轮
   看「造出来的兵长什么样」，看的是另一个时刻。

### 11.4 我此前写错的那句，现在正式作废

`2026-10-24` 我在本文件里写过「mod 发货的松散副本不被采纳」。那句话来源于
几轮**同时开着换皮、主题、场景三个美术/文本模组**的实验 —— 不可归因。
今天的干净一局证明它是错的，而 `civilizations.json`（v45）早就该让我怀疑它。

**这是本文件第二次自我推翻**（第一次是 §七 用兄弟文件收窄它）。留在这里，
因为「一个不可归因的读数被写成结论，然后被引用」正是这个项目最贵的失败模式。

### 11.5 现场已还原

`_probe/tmp_objrepl_restore.py`：留了两张证据帧（`_evidence/objrepl-map-start-scouts.png`
与 `_evidence/objrepl-scout-45hp.png`）、关游戏、卸载探针模组
（`entries_removed=1 folder_removed=True`）、把快照里四个第三方模组逐个打开。
收尾时 profile 是 5 个 enabled（1 个本工具的 + 4 个第三方），与开局前一致。

### 11.6 对产品意味着什么

`objreplacement` 现在是一个**已验证可行、但产品还没有意图**的能力：它能让
「某个单位在地图上换成另一个」（村民→斥候这种），生效时刻是开局。产品现在只有
`unit.sprite`（换外观，不换身份）和 `unit.create`（造新单位），没有「让这个文明
开局就用另一个单位」。把它做成意图（例如 `unit.replace_on_map`）是下一步的
候选，需要：`chance` 固定写 100、目标与来源必须是同一文明可造的、并且明说
**只影响开局生成、不影响已存在的单位**。
