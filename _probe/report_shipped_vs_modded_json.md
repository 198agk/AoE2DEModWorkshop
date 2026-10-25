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
