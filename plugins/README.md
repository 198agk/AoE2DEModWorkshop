# 插件目录（plugins/）

一个插件就是这里的**一个文件夹**，里面只有 JSON、没有 Python：

```
plugins/
  我的插件/
    schema/
      intents.json          # 必须；要有 "intents" 这个键
      dat_bindings.json     # 可选；只能往里加字段，不能改出厂字段
```

`aoe2mod/intent/compiler.py` 的 `plugin_schema_dirs()` 会按名字排序扫描这些
文件夹，`load_schema()` 把它们合并到出厂的 `aoe2mod/schema/` 之上。

## 一个插件能做什么

- **加一个意图**，只要它复用一个产品已经实现的 `compile.strategy`
  （`in_place_patch` / `civtechtrees_json` / `loose_files` / `repaint_sld` /
  `new_unit` / `linked_techs_json` / `new_tech`）。
- **加一个字段绑定**（`dat_bindings.json` 的 `unit_fields` / `tech_fields` 等），
  前提是这个字段的字节位置 `aoe2mod/dat/locate.py` 本来就知道。
- 一句话：**换个说法用已有的能力**。加完之后 `/api/meta` 会把它列出来，
  `_probe/ui_page_harness.js` 那类通用渲染会自己显示它。

## 一个插件不能做什么

- **不能加新的 `compile.strategy`**。四条分派链
  （`aoe2mod/api.py` 的 `plan` / `_build_one` / `_split_by_strategy`，
  `aoe2mod/intent/compiler.py` 的 `compile_edits`）只认写死的七个名字，
  不认识的名字会被拒绝并点名 —— 2026-10-23 之前 `plan()` 没有这道闸，
  会「预览成功、构建失败」。
- **不能顶掉出厂的名字**。意图 id 或字段名撞车会被拒绝，报错里带目录名。
- **能借到句子，但只能借「改一个数字」那种**，而且**三个条件都成立才算**：
  ① 字段在 `dat_bindings.json` 里绑好；② 它带 `label`（读者靠 label 学词）；
  ③ 某个意图在 `stat.options` 里点名这个字段，且**没有更早的意图抢走它**
  （`intent_for_stat()` 只把词交给按 id 排序第一个认领者 —— 出厂 `unit.stat`
  认领那十四个，所以插件意图再声明 `hit_points` 也没用）。
  三条都满足时句子就能说到它（2026-10-25 起；此前完全不行）。**只有 ②没有 ③
  时读者不教这个词**，因为教了之后句子会被解析成 `unit.stat` 然后被拒
  （实测：绑定 `blast_width` + label「爆炸宽度」但不声明意图 ⇒ 改前是
  「读得懂、建不了」，改后直接说「没听出要改哪个属性」）。
  但**加不了句子形状**：`aoe2mod/ui/nl.py` 的 13 条分支是手写的，凡不是「改一个
  数值字段」的事（可用性 / 造单位 / 造科技 / 科技分组 / 换美术）都仍然没有句子，
  只能走 `/api/plan`、`/api/build`。页面的「能做的事」会按 `by_sentence` 给不能说的
  那些标「只能用接口（句子还认不出来）」。
- **不能是代码**。这个模块从不 import 插件目录，插件也没有执行入口。

## 为什么用环境变量也能指定

`AOE2MOD_PLUGINS` 会**替换**默认的 `plugins/`（不是追加），这样测试才能说
「插件根是空的」并拿到恰好出厂的那份 schema。多个目录用 `os.pathsep` 分隔。

## 已验证

`_probe/test_schema_plugins.py`（23 条）：插件意图进 `load_schema()` 与
`/api/meta`、走 `plan()`/`build()` 且**与它复用的出厂意图写出逐字节相同的
`.dat`**、撞名被拒（意图与字段各一条）、插件不能引入未知策略、缓存键跟着
目录集合走（运行中丢进一个插件会立刻生效）。
