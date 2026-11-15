# 界面分工 · 两个会话不许互相覆盖

> 写于 2026-10-27 00:58，由**改 UI 的那个会话**（写本文者，下称 **UI 会话**）起草。
> 起因：UI 会话与功能会话同时改 `aoe2mod/ui/static/index.html`，
> 功能会话提交 `e57cc16` 时把 UI 会话加的 4 个 `aria-label` 全部覆盖掉了
> （`textarea#say`、`input#rname` 现在又只靠 placeholder 命名，渲染门禁 R7 报 2 红）。
> 这不是谁写错了，是两个会话没约定谁在哪一层动手。
>
> **命名说明**：下面按「谁拥有哪一层」叫，不按主/从叫。
> **UI 会话** = 负责视觉、CSS、可访问性、门禁脚本的那个（写本文的）。
> **功能会话** = 负责 Python 服务、JS、加载流程、Tauri 外壳的那个（提交 `e57cc16` 的）。

---

## 一句话分工

**UI 会话拥有 `<style>` 与可访问性；功能会话拥有 JS 与 API。**
**一个文件同一时刻只允许一方动 `<style>`。**

---

## 各自能改什么

| 区域 | UI 会话 | 功能会话 | 说明 |
|---|---|---|---|
| `<style id="aoe2mod-legible">`（index.html:7-1093） | **独占** | 只读 | 任何 CSS 规则增删改都由 UI 会话做 |
| `aria-*` / `role=` / `label[for]` | **独占** | 只读 | 上一轮就是被覆盖的，划归 UI 会话 |
| `.class` 的增删（HTML 里） | **独占** | 需先登记 | class 是样式的挂点，跟着样式走 |
| `<script>`（1093 行之后的所有 JS） | 只读 | **独占** | 含 `boot()`、事件绑定、`fetch` |
| `aoe2mod/api.py`、`ui/server.py`、`progress.py`、`loading.py` | 只读 | **独占** | |
| 文案 / `data-i18n` 键 | 可改 class 相关 | **独占** | 文案归功能会话，避免两边写不同措辞 |
| `_probe/*.py` 门禁脚本 | **独占** | 只读 | `design_acceptance.py`、`render_acceptance.py` |
| `aoe2mod/DESIGN.md`、`AGENTS.md`、本文件 | **独占** | 只读 | 契约由 UI 会话维护 |

「需先登记」＝动手前在本文末尾的登记表里加一行，写明要改哪个 class、哪几行、为什么。

---

## 交付顺序（避免互相踩）

1. **UI 会话先动**：改完骨架 → 跑两道门禁
   - `py -X utf8 _probe/design_acceptance.py`（文本 12 条）
   - `py -X utf8 _probe/render_acceptance.py`（渲染 10 条）
   → 两条全绿才算这轮完。
2. **UI 会话提交并在「轮次记录」加一行**：写明这轮占了哪些行段、下次谁可以动。
3. **功能会话再动**：只改 JS/API 那一层，改完**必须**跑一次 `render_acceptance.py`，`R7`（input 无可访问名）不许变红。
4. **功能会话提交前**：`git diff --stat` 看有没有动到 7-679 行，动了就是越界，退回。

**反向也成立**：功能会话先动（比如加重载流程），UI 会话这轮就不动 `<style>`，等对方提交完再同步重跑门禁。

---

## 三条硬约束

1. **动手前先 `git log -1 --format='%cd %s'` 和 `stat -c %y` 看文件时间。** 如果 10 分钟内有人提交过同一文件，先确认对方已完成，再动手。
2. **提交信息里写明动了哪一层。** 例：
   - `Rail: three-band layout (style only)` —— UI 会话
   - `Mods row: hover-only actions (markup + class)` —— 需登记
   - `Loading: progress events (api + js)` —— 功能会话
   看提交信息就知道该不该等。
3. **谁覆盖谁负责补回。** 如果发现自己的提交把对方的改动弄丢了，在本文「事故」一节记一行，并把丢失的内容补回去，不要装作没发生。

---

## 现在的真实状态（2026-10-28 18:58）

- `index.html`：**3207 行**，`<style>` **7-1093**，HEAD 是 `c881a53`（本轮改动未提交）。
- 文本门禁 `design_acceptance.py`：**15/15 绿**（§12.4 新增第 13-15 条）。
- 渲染门禁 `render_acceptance.py`：**0 红**（1237px 与 1100px 两档）。
- 本轮已修：
  - 左栏 543px 死区 → 三段式 grid，第三段是「记住的句子」列表（可滚动，`flex:1`）
  - 18 个「改成」按钮墙 → `:has()` 灰化，空输入框时退成幽灵
  - 编辑区表头 4.55 对比度 → 7.30，权重 400 → 600
  - 模组行 3 控件常显 → 只留开关，次操作 hover/focus 显影
  - `aria-label` 全部补回，R7 从 2 红到 0
  - 左上角绿底「II」方块 → `brand/app-icon.png` 真图标（256px，`object-fit:contain`，无容器底色）
  - 左栏状态卡从「浮在中间」→ 贴窗口底边（`.rail` 的 `max-height` 改回 `height`，实测 footer 底 788 / rail 底 805，差 17px = padding+border）
- 仍可做（下轮，非阻塞）：首页信息编排（只有 2 张卡，第一张 920 字说明）

---

## 登记表

| 时间 | 谁 | 层 | 范围 | 状态 |
|---|---|---|---|---|
| 2026-10-28 18:58 | UI 会话 | `<style>` + markup | `.rail` 定高与 `.rlist:has()` 居中、`.mark` 换真图标、断点 `height:auto`、`<span class="mark">` 内加 `<img>` | 已提交 `029bc35` |
| 2026-11-09 14:2x | 功能会话（用户直接指派） | `<script>` + 一处 HTML 文案 | 「一键适配新版本」接进已有的 `#repair` 面板：**不新增 HTML 元素、不新增 class、不动 `aria-*`**，只在 `<script>` 里给 `repairRow()` 补一个按钮、给 `checkRepairs()` 补一句统计，并改掉 `#repair` 上方那段 `data-i18n="mods.note"` 的正文（文案归功能会话）。样式全部沿用现有 `.chip` / `.hint` / `.stat` | 已改，未提交 |
| 2026-11-09 22:0x | 功能会话（用户直接指派） | `<style>`（**占地，需 UI 会话复核**） | 图标窗口 `#cardpick` 一整套（`.ckpanel`/`.ckhead`/`.cktitle`/`.ckbar`/`.ckbody`/`.ckfoot`/`.ckgap`/`.nid`/`.cell.busy`/`.cell.waiting`，约 55 行，全部用 `var(--*)` token，无十六进制、无 `x.5px`）；删掉旧列表 `.cpicklist`/`.cpickrow` 三条（那条路已整条删除，留着就是死样式）；「关于」页 `.abact`（一行两颗按钮 `flex:none` 成一个整体，修 1360px 下两颗按钮一右一左）。**这是越界**，与 2026-11-09 那两行同一性质 | 已改，未提交 |
| 2026-11-09 22:0x | 功能会话（用户直接指派） | `<script>` + markup | 命令面板：`#cardpick` 窗口（`cardPickOpen`/`cardPickOpenKind`/`cardPickSetKind`/`cardPickLoad`/`cardPickTile`/`cardPickFillIcons`/`cardPickSelect`/`cardPickTake`）、带子里两枚按钮 `#card-slot-addunit`/`#card-slot-addtech`、`CARD_FRESH`、删掉旧路 `drawPickList`/`cardPut`/`#card-pick-list`。markup 只加 `#cardpick` 那块面板与两枚 `.chip`（沿用现有 class，不动 `aria-*`） | 已改，未提交 |
| 2026-11-10 00:3x | 功能会话（用户直接指派） | `<script>` 一行常量 | 图标窗口的批量从 800 降到 60（`const CARD_PICKBATCH = 60;`，`aoe2mod/ui/static/index.html:10414` 一带）。**不动 `<style>`、不动 `aria-*`、不动任何 class**，只改这一行的数值与它上面那行注释（注释记的是实测：一批 800 让 120 格停在「?」7.7 秒，一批 60 时 0.6 秒出首图）。理由是 800 是 `/api/icons` 单次上限（服务端能算多少），不是界面的等待预算（人能等多久） | 已改，未提交 |
| 2026-11-10 14:5x | 功能会话（用户直接指派） | `<script>` + markup 两行 | 拆掉三处写死的守卫：挑选窗加第三个页签 `#cardpick-bld`（`CARD_PICKKIND` 三态、`[tabId, kind]` 分表绑定、`cardPickLoad` 丢陈旧答案、`cardPickOpenKind` 改成先定列表再开窗）、带子里加 `#card-slot-addbld` / `#card-slot-addbld-empty` 两枚 `.chip`、建筑下拉分两组 optgroup、toast 加「把「X」放进第 N 格了」一支。**不动 `<style>`、不动 `aria-*`、不新增 class**（全部沿用 `.chip` / `optgroup`） | 已改，未提交 |
| 2026-11-10 00:4x | 功能会话（用户直接指派，接手一键更新收尾） | <style>（占地，需 UI 会话复核） | #repair .mod 五项：height:auto + align-items:flex-start（.mod 的 30px 定高把「判定 / 摘要 / 备注」三行挤在一起，实机截图里文字叠成一片）、cursor:default（这些行不可拖）、.nm 取消 nowrap 允许折行、.hint 收窄到 4px、按钮 flex:none 贴右上。不动 aria-*、不动任何 .mod 原有行（模组列表用的那份），选择器全部带 #repair 前缀 | 已改，未提交 |
| 2026-11-09 10:44 | 功能会话（用户直接指派） | `<style>` + markup class | 四处署名「By - RemonBo」：新增 `.brandby`（品牌块第三行）、`header .byline`（标题条 h1 之后），`.railby`（`.railprodname` 内联，不能另起一行，`.railfoot` 有 180px 硬上限）；`index.html` 的 `<title>`、`loading.py` 的 `<title>`/`<h1>` 与 `.by`、`main.rs:536`、`tauri.conf.json:13` 同步加后缀。用户点名要的，未经 UI 会话排期 | 已改，未提交 |
| 2026-11-10 23:3x | 功能会话（用户直接指派，接手一键更新收尾） | `<script>` + markup（**不动 `<style>`、不动 `aria-*`、不新增 class**） | 「官方数据档案库」面板：`#view-mods` 里第二块 `.box.datpick#archive`（`#archive-note` 说明 + `#archive-list` 一栏 + `#archive-open` 打开文件夹），全部沿用 `.box` / `.datpick` / `.dphead` / `.clab` / `.dprow` / `.dplabel` / `.dpscope` / `.dpver` / `.dpnow` / `.dpfmt` / `.empty` / `.hint` / `.row` / `.chip`；JS 新增 `fmtMB` / `loadArchive` / `ARCHIVE_INFO`，`boot()` 里 `loadDatPicker()` 之后调一次，`#archive-open` 走 `api("/api/archive-open", {})`。面板不给任何节点挂 `data-i18n`（`applyLocale()` 会 `textContent` 覆盖子树），文案直接写在 markup 里 | 2026-11-11 13:2x | 功能会话（用户直接指派，接手一键更新收尾） | `<script>` + markup（**不动 `<style>`、不动 `aria-*`、不新增 class**） | 两个列表默认折叠：`#dp-toggle`（改哪一个数据文件）与 `#archive-toggle`（官方数据档案库）各一枚 `.chip`，`#dp-list` / `#archive-list` / `#archive-actions` 初值带 `hidden`（靠 index.html 第 108 行的全局 `[hidden]{display:none!important}`，不新增 class）；新增 `foldPanel(btnId, boxId, open, closedText, extraId)` 一函数管三处、`#dp-toggle` / `#archive-toggle` 的 onclick 绑 `DP_OPEN` / `ARCHIVE_PANEL_OPEN`（**不跨刷新记住**）；`clab` 文案「改哪一个数据文件」→「选择要修改的数据文件」；档案库行改成「真实 build 日期区间 + N 个版本可展开」：`archiveNote()` 头部写「共 53 份官方数据，跨 11 代记录格式，2019-10-18 至 2026-10-27」，每代一行 `dplabel`(VER x.y) + 展开 chip(N 个版本) + `dpscope`(N 份) + `dpver`(first_date ~ last_date) + `dpnow`/`dpfmt`，展开后每 build 一行「日期 时间 / 大小 / gid / 在架|缺这一份」，缩进用 `dplabel` 文本里的两个全角空格（不新增 padding class，样式表里也没有可复用缩进类）。**日期换了真源**：原来那列是 `first_seen`（工具复制时间，全显示 2026-11-10，用户当场指出「日期不对吧」），现在是 `dat_archive/index.json` 的 `date`（Steam manifest 上架日），`first_seen` 退到 `title` 与无 ledger 时的兜底「存下于」 | 已改，未提交 |
| 2026-11-11 21:4x | 功能会话（用户直接指派） | `<script>` + markup（**不动 `<style>`、不动 `aria-*`、不新增 class**） | 模组页「检查」按钮改成先选再查：新增 `drawRepairRoster(box, list)`（一排 `.chip.on` 勾选 + `.cands` 容器 + `.row` 里的「检查选中的 N 个」/「全部检查」两枚 `.chip`），`checkRepairs(only, skipRoster)` 在 `skipRoster` 假时先 `api("/api/upgrade-candidates")`（失败当没有，兼容旧服务端）、候选 >1 才画清单，查的时候 `jobBar()` + `watchJob("upgrade", bar)` 并 `stopBar()` 后撤掉进度条那行；行按钮与 `adaptAll()` 内部调用改 `checkRepairs(null, true)`。样式全部沿用 `.row` / `.cands` / `.chip` / `.chip.on` / `.loadbar*`，`<style>` 一行没动 | 已改，未提交 |
| 2026-11-14 20:2x | 功能会话（用户直接指派） | `<script>` + 一处 api 路由（**不动 `<style>`、不动 `aria-*`、不动 markup 结构、不新增 class**） | 模组页可编辑标题/作者/简介：`aoe2mod/api.py` 新增 `POST /api/mod-info`（读 `mods[].info` 四键 Author/Title/Description/CacheStatus，未知模组回中文句 + `where` traceback），`aoe2mod/mod/mods.py` 新增 `read_info` / `write_info`（只写这四个必键、紧凑无空格无尾换行、保留社区模组额外键如 `Unpublished`、超长标题拒绝而不是截断、写前留 `info.json.dsh-bak`）；页面 `#mods` 行里「详情」旁边多一枚 `.chip`「改简介」沿用现有 class，编辑窗口复用 `.ckpanel` 那一套；`upgrade.py` 的 info 继承改成原 info.json 的 Title/Author/Description 优先于文件夹名，`Unpublished` / `No Description` 当空值处理。**踩过的坑**：验收时用 curl 对真实模组 `subscribed/167396_Red Alert 2 MOD` 发了一次 `author:""` `description:""` 的 POST，把作者原文简介清空（78 B）；原文已从 `_probe/_tmp/meta.json` 快照 + 旧会话日志逐字节还原并写回（278 B，193 字，2 个 CRLF，与快照三项全等） | 已改，未提交 |

---

## 轮次记录

| 时间 | 提交 | 占了哪些行段 | 下次谁可动 |
|---|---|---|---|
| 2026-10-27 00:16 | `e57cc16` | 整个 `<style>` 重写 + 4 个视图 + 加载页 | UI 会话（已接手） |
| 2026-10-27 13:00 | `911f5f9` | `.rail` 三段式 / `.mod` 行 / `td.e:has()` / 渲染门禁 | UI 会话 |
| 2026-10-27 13:09 | `75046c9` | `.rail` 高度、示例文案行宽 | UI 会话 |
| 2026-10-27 14:26 | `8d2e517` | 字号阶 / `--measure` / 二级表面 | UI 会话 |
| 2026-10-27 18:45 | `d4f6d70` | 命令面板视图 | 功能会话 |
| 2026-10-27 22:03 | `5bc0272` | 卡片网格读游戏布局文件 | 功能会话 |
| 2026-10-28 18:59 | `029bc35` | `index.html` 158-190、303-312、469、1096 + `static/app-icon.png` 新增 | UI 会话 |

---

## 事故

| 时间 | 症状 | 原因 | 处理 |
|---|---|---|---|
| 2026-10-27 00:16 | 4 个 `aria-label` 消失，R7 由 0 变 2 | `e57cc16` 整段替换 markup，覆盖了 UI 会话前一轮的补充 | UI 会话本轮补回 |
