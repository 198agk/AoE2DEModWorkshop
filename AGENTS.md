# 帝国项目 · 工作区约定

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
2. 样式改动只落在 `<style id="aoe2mod-legible">`（**当前 index.html:7-679**）与必要的 class 上。不动 679 行之后的 JS 逻辑，不动 API。
3. 改完跑两道门禁，全绿才算改完：
   - `py -X utf8 _probe/design_acceptance.py` —— 文本 12 条
   - `py -X utf8 _probe/render_acceptance.py` —— 渲染 10 条（文本绿但渲染红是常态，必须真在浏览器里量）
4. 禁止出现十六进制字面量、`x.5px` 字号、内联 `style=""`、`@media` 管组件内部布局。

## 环境事实

- git 根：`D:\Software\AI\帝国项目`（不是 aoe2mod）
- 被渲染的真实界面：`aoe2mod/ui/static/index.html`（单文件，2241 行）
- Tauri 外壳：`desktop/src-tauri`，启动时找 python 起本地服务再开 `http://127.0.0.1:PORT`
- 实际窗口宽度约 1237px；`?diag=1` 会在页面右下打印 vw / dpr / cols 诊断

## 网络

`raw.githubusercontent.com` 与 `cdn.jsdelivr.net` 直连在本机失败（curl exit 35 / TLS 重置）。
可用通道：`https://gh-proxy.com/https://raw.githubusercontent.com/<owner>/<repo>/main/<path>`
