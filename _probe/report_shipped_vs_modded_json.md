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
