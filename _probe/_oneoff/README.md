# 一次性脚本（不是门禁）

这里的每个文件都是**某一次调查**用过的脚本，跑完就完成了它的任务。
它们不在 `run_suites.py` 里，也不应该在。留着是为了让某条历史结论
（`变更日志.md` / `_接手_主体项目2.md` 里写着"用 X 探针量过"的那些）
还能被找回来重跑。

**判断标准**：能回答"这条断言在什么样的改动中会回退"的，才是门禁，留在
`_probe/` 顶层；说不出来的，进这里。

| 文件 | 当年量的是什么 |
|---|---|
| `_add_attack_class.py` | 给 `unit.attack_class` 补类名表的临时补丁 |
| `_i18ncheck.js` | 数页面里 `data-i18n` 键的覆盖数 |
| `_intents.js` `_intents2.js` | 抽 `/api/meta` 的意图清单看形状 |
| `_txtcount.js` `_txtcount2.js` `_txtcount3.js` `_txtcount.py` | 数渲染后可见字符数（同一件事试了四遍） |
| `_patch_handoff_done.py` | 往交接文档里写"已完成"标记 |
| `_stage1_compare.txt` | Rust 与 Python 的 stage 1 游标对拍输出 |
| `_page_check.js` | 2026-10 的页面脚本**整份快照**（1875 行），当年在 node 里直接跑它量点击链。
  它里面那份 `checkRepairs()` 已经过时：打的是 `/api/repair-check`、判定是
  `auto`/`manual`/`impossible`/`identical`/`no_dat`，而现行页面打 `/api/upgrade-check`、
  判定是 `mergeable`/`conflicts`/`impossible`/`up_to_date`。**不要再拿它当页面现状的对照物**，
  现行的页面门禁是 `_probe/ui_page_harness.js`（它从 `index.html` 里现取脚本，不是快照）。 |
| `compare_rust_stage1.py` | 上面那份输出的生成脚本 |
| `fix_mcp_patch.py` | 修 MCP 配置的一次性补丁 |
| `probe_dll_bisect.py` `probe_dll_chain.py` | 二分定位缺哪个 DLL（结论：`0xC0000135`） |
| `probe_imports.py` | 列 exe 的导入表 |
| `probe_pe_integrity.py` `probe_rsrc.py` | PE 头与资源段体检 |
| `probe_python_stub.py` | 确认 PATH 上的 `python` 是商店存根 |
| `tmp_read_dead2.js` `tmp_read_dead_session.js` | 读 `.dat` dead-fish 块的浏览器端小工具 |
