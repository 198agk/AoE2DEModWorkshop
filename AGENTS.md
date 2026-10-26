# 帝国项目 · 工作区约定

## 界面改动（aoe2mod 模组工坊）

改动 `aoe2mod/ui/static/index.html` 的任何样式前，必须先读这两份：

- `aoe2mod/DESIGN.md` —— 设计契约。token 表、字号 4 档、间距 4px 基准、圆角 3 值、组件规格、禁用清单、验收 12 条。
- `aoe2mod/UI-AUDIT.md` —— 逐条问题清单。P0/P1/P2 分级，带精确行号与改法。

规则：

1. 先出计划（改哪几个 token / 哪几个组件 / 涉及哪些行），再动代码。
2. 样式改动只落在 `<style id="aoe2mod-legible">`（index.html:7-435）与必要的 class 上。不动 437 行之后的 JS 逻辑，不动 API。
3. 改完跑 `DESIGN.md` §10 的 12 条验收，一条不绿不算改完。
4. 禁止出现十六进制字面量、`x.5px` 字号、内联 `style=""`、`@media` 管组件内部布局。

## 环境事实

- git 根：`D:\Software\AI\帝国项目`（不是 aoe2mod）
- 被渲染的真实界面：`aoe2mod/ui/static/index.html`（单文件，2241 行）
- Tauri 外壳：`desktop/src-tauri`，启动时找 python 起本地服务再开 `http://127.0.0.1:PORT`
- 实际窗口宽度约 1237px；`?diag=1` 会在页面右下打印 vw / dpr / cols 诊断

## 网络

`raw.githubusercontent.com` 与 `cdn.jsdelivr.net` 直连在本机失败（curl exit 35 / TLS 重置）。
可用通道：`https://gh-proxy.com/https://raw.githubusercontent.com/<owner>/<repo>/main/<path>`
