# -*- coding: utf-8 -*-
"""Mark §1 D and the DLL gap as done, and record the commits that closed them."""
import io
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "_接手_主体项目2.md")
text = io.open(P, encoding="utf-8").read()

D_OLD_HEAD = u"**D. 新发现（真缺陷，发布前必须处理）：`--features` 没开，错误页永远出不来**"
D_NEW = u"""**D. ✅ 已修并验证（2026-10-27 14:1x，提交 `b2dee82`）—— `webview-data-url` 已开，错误页真的显示出来了**

原来 `Cargo.toml` 是 `tauri = { version = "2", features = [] }`，而 `main.rs` 两条失败分支都走 `data_url(&error_page(...))`。
实测（目录里只有 exe + DLL、没有 `app\\`）：

```
failed: 找不到工具目录：… tools/run_ui.py
opening data:text/html;charset=utf-8,…
window build failed: invalid window url: data URLs are not supported without the `webview-data-url` feature.
```

修法：`features = ["webview-data-url"]`（引入 `data-url 0.3.2`，已 `cargo fetch` 进本地 registry，`Cargo.lock` 同步回仓库）。

**验证方式不是看日志——日志上一次也对。** 是启动那个目录、然后用可访问性树读窗口里的字：

```
Text "模组工坊没能启动"
Text "找不到工具目录：从 exe 和当前目录向上都找不到 tools/run_ui.py。可以用环境变量 AOE2MOD_ROOT 指定仓库根目录。"
Text "数据层（读 " / ".dat" / "）需要本机有一个 Python 3。这个窗口只是外壳。"
Text "日志：" / "%TEMP%\\aoe2-mod-workshop.log"
```

对照：修之前同一个目录是停在「正在读取游戏数据」的加载页，一行原因都不显示。钉子 `_probe/probe_startup_failure.py`。

**★ 构建这条命令有个环境前提**：`%TEMP%\\mingw\\mingw64\\bin` 必须在 PATH 上，否则 `dlltool.exe: program not found`，`parking_lot_core` / `windows` 在编到我们的代码之前就失败。完整命令：

```bash
export PATH="/c/Users/26913/AppData/Local/Temp/mingw/mingw64/bin:/c/Users/26913/.cargo/bin:$PATH"
cd D:/Software/AI/AGE2/desktop/src-tauri && cargo build --release --offline
```

注意 cargo 的输出在 `AGE2/desktop/src-tauri/target/release/`，不是 `AGE2/target/release/`（后者是 12:41 的旧二进制，`make_bundle.py` 原来指的就是它 —— 一直在打包旧的 exe）。

"""
text = text.replace(D_OLD_HEAD, D_NEW, 1)

# DLL gap: the E paragraph mentions it; add the closure right after E.
E_ANCHOR = u"装好的包必须在一台既没有 dsh、也没有 Python 的机器上验，或至少先把 D 修好，让失败能在加载页里说出来。"
E_ADD = E_ANCHOR + u"""

**F. ✅ DLL 拷贝已补（2026-10-27，提交 `570ddd3`）—— 上一会话最后想做而没做成的那一步**

`_probe/make_bundle.py`（原来叫 `tmp_make_bundle.py`，`_probe/tmp_*.py` 被 .gitignore 挡着，所以改成正式名字）现在：

- 从 release exe 旁边取 `WebView2Loader.dll` 拷到 bundle 根目录；
- **DLL 不在就整个拒绝出包**，而不是产出一个「双击弹系统错误、日志 0 字节」的文件夹；
- 出包后再核一次 exe 与 DLL 都在；
- `EXE` 指向 cargo 真正写出的 `AGE2/desktop/src-tauri/target/release/`（原来指 `AGE2/target/release/`，是个旧二进制）。

`--force` 重建实测：43.0 MB / 668 files，`loader WebView2Loader.dll beside the exe: 160880 B`，self-check `bundled ok: python 3.12.14 intents 15`，新 bundle 起服务到 `ready`、`root: … (bundled)`。

**剩下的 E 仍未修**（不是 DLL，是找不到 Python 时 `wait_ready` 空等 150 s）。现在 D 修好了，E 至少有地方可以把原因说出来 —— 但 `wait_ready` 超时那条分支本身还没改。"""
text = text.replace(E_ANCHOR, E_ADD, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(text)
print("patched: D closed, F added")
print("D marker present:", "✅ 已修并验证" in text)
print("F marker present:", "DLL 拷贝已补" in text)
