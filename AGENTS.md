# Aoe2 · 工作区约定

## 交付以发布包为准（硬约束，2026-11-09 用户指令）

> **「所有改动均要以发布包交付为准，我只验收发布包的。」**
> 这条对**本工作区的全部会话生效，包括今后新建的会话** —— AGENTS.md 被 DSH 自动注入每个会话，
> 写在这里就等于写进了每个会话的第一条约束。读到这行的会话，不问「要不要同步到包里」，直接同步；
> 不许只改仓库源码就宣布「修好了」。

**验收对象只有一个**：`_out\AoE2ModWorkshop\aoe2-mod-workshop.exe` 双击起来的那一份。
它读同目录的 `app\`（`engine_root()` 在 `desktop/src-tauri/src/main.rs:124-149`，候选顺序
`AOE2MOD_ROOT` → `<exe目录>\app` → `<exe目录>` → cwd 上溯 → ui_root 上溯三层）。

以下**都不是**交付物，只是中间物：仓库里的 `aoe2mod/**` `tools/**` 源码；
`python -X utf8 -u tools/run_ui.py --port 7811` 起的 dev 服务；包里没跟着源码一起更新的旧副本。

改完的唯一判定：仓库源码 == 包内 `app\`，且包里那个 exe 能把路由答对。

### 收尾必跑的四步（顺序不能换）

```bat
python -X utf8 _probe\sync_app_package.py         :: 1. 源码 -> 包 app\（Python + tools）
python -X utf8 _probe\sync_ui_to_bundle.py         :: 2. 前端 -> 包 app\（ui/static + schema）
python -X utf8 _probe\test_bundle_package_sync.py  :: 3. 双向比对，必须 0 DIFFERENCE
python -X utf8 _probe\ship_and_verify.py           :: 4. 起包里那个 exe，逐条打路由
```

第 4 步的收尾行只有两种：`SHIPPED BUNDLE: ALL ROUTES OK` 或 `FAILURES ABOVE`。
**汇报里必须贴这一行原文**；贴不出来就不算修完，也不算验完。
`sync_app_package.py` 拷完会自己再比一遍，不一致就 return 1；`sync_ui_to_bundle.py` 用
`MARKER = 'id="nav-card"'` 断言新页面真的进去了。

只有动了 `desktop/src-tauri/**`（`.rs`、`tauri.conf.json`、图标）才需要重编 exe：
在 `_cache\AGE2\desktop\` 里 cargo build，产出 `P.EXE` 再拷进 `_out\AoE2ModWorkshop\`；
`ship_and_verify.py` 的 `check_exe_is_the_built_one()` 会逐字节比 `P.EXE` 与包里的 exe ——
**大小相同但字节不同也算红**。只改 Python / HTML / JS / JSON 的轮次不重编 exe。
路径只从 `_probe/_paths.py` 取（`P.BUNDLE` / `P.BUILD` / `P.EXE` / `P.BUNDLED_EXE`），不手写绝对路径。

### 证据也必须来自包里

- 截图与实测的对象是 `ship_and_verify.py` 起的 7799 实例、或 `test_pages_shipped.py` 的 7807，
  **不是 7811 的 dev 服务**。7811 全绿而包里还是旧的，就是「说了半天修了，用户打开还是旧的」。
- 用户报「没变化 / 没有啊」时，第一动作是比对包内文件与源码（`test_bundle_package_sync.py`，或逐文件 md5），
  先证明包里是不是旧的，再谈逻辑；不要拿源码结论去反驳用户看到的界面。
- 端到端另有两条：`_probe/test_e2e_shipped.py`（玩家 profile 副本，端口 7807）、
  `_probe/test_pages_shipped.py`（逐视图断言有内容、无未捕获异常）。

### 禁止

1. 只改源码、只跑 7811、只跑 design/render 两道门禁，就宣布完成。
2. 把构建产物（`__pycache__`、`*.pyc`、测试输出）留在包的 `app\` 里 ——
   `make_bundle.stray_output(app)` 会拒；2026-11-02 包里曾涨到 1.7GB / 77 次测试跑在里面。
3. 用 `make_bundle_native.py --force` 重建整包来「顺手刷新」—— 它会 `rmtree` 输出目录，
   历史上这样删掉过 19.8MB 的表。要刷新就走上面前两步同步。

## 图标与 logo

> **硬约束。本工作区后续制作的所有软件，应用图标与 logo 都用 `brand/app-icon.png`。**

唯一母版 `brand/app-icon.png`（1024×1024 RGBA），导出的 `brand/app-icon.ico` 是同款 7 帧。
不另画 logo、不派生变体、不抠图、不锐化、不裁切、不分档特写 —— 母版自带的 alpha 已经干净，
再做"美颜"只会在边缘造出白毛（踩过）。细节与坑见 `BRAND.md`。

导出跑 `_probe/tmp_icon_direct.py --tauri`，改 exe 跑 `_probe/tmp_pe_icon3.py`，
验收跑 `_probe/tmp_icon_dump.py`，必须打印 `PASS`。

## 界面改动（aoe2mod 模组工坊）

> **两个会话共用一个工作区。动 `index.html` 之前先读 `UI-协作分工.md`：**
> 主会话独占 `<style>`、`aria-*`、门禁脚本；子会话独占 class、文案、表单结构。
> 越界改对方那一层会静默丢改动（`e57cc16` 就这样覆盖掉了 4 个 `aria-label`）。

改动 `aoe2mod/ui/static/index.html` 的任何样式前，必须先读这三份：

- `UI-协作分工.md` —— 谁改哪一层。动手前先看登记表。
- `aoe2mod/DESIGN.md` —— 设计契约。token 表、字号 4 档、间距 4px 基准、圆角 3 值、组件规格、禁用清单、验收 12 条。
- `aoe2mod/UI-AUDIT.md` —— 逐条问题类型清单（**行号已随重构失效，只当问题类型看，别当行号地图**）。

规则：

1. 先出计划（改哪几个 token / 哪几个组件 / 涉及哪些行），再动代码。
2. 样式改动只落在 `<style id="aoe2mod-legible">`（**当前 index.html:167-52359 字节，约第 7-1093 行**）与必要的 class 上。不动 1093 行之后的 JS 逻辑，不动 API。
3. 改完跑两道门禁，全绿才算改完：
   - `python -X utf8 _probe/design_acceptance.py` —— 文本 15 条
   - `python -X utf8 _probe/render_acceptance.py` —— 渲染 10 条（文本绿但渲染红是常态，必须真在浏览器里量）
   注意：本机 **没有 `py` / `python3`**，只有 `python`（3.14.4）；`py script.py` 会 `CommandNotFoundException`。
4. 禁止出现十六进制字面量、`x.5px` 字号、内联 `style=""`、`@media` 管组件内部布局。

## 环境事实

- git 根：`D:\Software\AI\Aoe2`（不是 aoe2mod）
- **构建产物一律留在工作区内**（硬规则，2026-11-01 用户要求两次「以后都这样」）：
  `_out\AoE2ModWorkshop\`（打包版）、`_cache\AGE2\desktop\`（ASCII cargo 构建树）、
  `_cache\_shellbuild\`（旧的 C:\dsh-build 构建树，已搬进来）。全部在 `.gitignore` 里。
  **任何脚本都不许再往 `D:\Software\AI\`、`D:\` 或 `C:\` 根下写东西** ——
  路径只在 `_probe/_paths.py` 一处定义（`P.BUNDLE` / `P.BUILD` / `P.EXE`），
  探针一律 `import _paths as P`，不再手写绝对路径。
  这样做的另一个原因：本机 DSH 沙箱给工作区打的完整性标签与外面不同，
  打包版的 `runtime\python.exe` 在工作区内继承 Medium 才能启动
  （放在外面时曾整片报 0xC0000135，排查了六小时）。
  临时文件只许落 `_probe\_tmp\` 或 `tempfile.mkdtemp()`。
- 被渲染的真实界面：`aoe2mod/ui/static/index.html`（单文件，约 4549 行，`<style id="aoe2mod-legible">` 在 167-52359 字节）
- 页面图标：`aoe2mod/ui/static/app-icon.png`（256×256，从 `desktop/src-tauri/icons/icon.png` 拷来，同母版）；
  `server.py:46` 的 `STATIC_DIR` 已提供 `/static/` 路由，**不需要为它加路由**
- 起服务：`python -X utf8 -u tools/run_ui.py --port 7811 --no-browser`
- 截图：`SHOT_W=1264 SHOT_H=821 python -X utf8 _probe/shot_now.py home`（可选 `mods` / `editor`）
- 本机 Python 必须用 `C:\Users\26913\AppData\Local\Python\bin\python.exe`（3.14.4）；
  裸 `python` 在部分 shell 里是 Store stub（静默 rc=49）；**Pillow 13.0.0 已装**
- 真实窗口 1264×821；`?diag=1` 会在页面右下打印 vw / dpr / cols 诊断

## 网络

`raw.githubusercontent.com` 与 `cdn.jsdelivr.net` 直连在本机失败（curl exit 35 / TLS 重置）。
可用通道：`https://gh-proxy.com/https://raw.githubusercontent.com/<owner>/<repo>/main/<path>`
