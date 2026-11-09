# Aoe2 · 工作区约定

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
