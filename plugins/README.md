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
- **不能只加一条却没有句子层**。`aoe2mod/ui/nl.py` 的 12 个分支是手写的，
  屏幕上的「说一句话」不会自动认识新意图；只能走 `/api/plan`、`/api/build`。
- **不能是代码**。这个模块从不 import 插件目录，插件也没有执行入口。

## 为什么用环境变量也能指定

`AOE2MOD_PLUGINS` 会**替换**默认的 `plugins/`（不是追加），这样测试才能说
「插件根是空的」并拿到恰好出厂的那份 schema。多个目录用 `os.pathsep` 分隔。

## 已验证

`_probe/test_schema_plugins.py`（23 条）：插件意图进 `load_schema()` 与
`/api/meta`、走 `plan()`/`build()` 且**与它复用的出厂意图写出逐字节相同的
`.dat`**、撞名被拒（意图与字段各一条）、插件不能引入未知策略、缓存键跟着
目录集合走（运行中丢进一个插件会立刻生效）。
