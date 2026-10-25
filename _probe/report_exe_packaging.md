# 能不能打包成一个 exe：实测（2026-10-25）

结论先说：**能构建、能跑、页面能发出去，但它和「schema 外置」这条设计约束正面冲突** —— 这不是打包工具的问题，是设计取舍。以下每条都有读数。

## 环境前提（先前的说法被推翻）

`_交接说明.md` 从 2026-10-21 起写着「PyInstaller 在本运行时装不起来」。那句话是**猜的**，今天量了：

```
pip install --target _vendor_pyinstaller pyinstaller   -> exit=0, 14 MB
```

装进去了。所以「装不起来」这条要撤回。

## A. 构建：成（但入口的第一个版本是错的）

```
pyinstaller --onefile --paths <root> --paths <root>/_vendor \
  --add-data "<root>/aoe2mod/ui/static;aoe2mod/ui/static" \
  --hidden-import webview.platforms.edgechromium  _probe/_exe_entry.py
-> build exit=0, 28.9 MB
```

三个只有真跑才暴露的坑：

1. **入口把 argv 丢了**。第一版 `_exe_entry.py` 写的是 `run_ui.main(['--no-browser'])`，于是 `--port 7795`、`--help` 全被静默丢弃，服务绑到**随机端口**，探针在 7795 上等了十分钟报「没应答」，而那个 exe 其实在隔壁端口上正常工作。教训：**冻结入口必须 `main(sys.argv[1:])`**，否则它就不是 `python tools/run_ui.py` 的等价物，那这次测试就没有意义。
2. **`tools` 不是包**（`tools/` 下没有 `__init__.py`，也不该有）。只加 `--paths root` 仍报 `ModuleNotFoundError: No module named 'tools'`；PyInstaller 需要看见具体模块，所以入口必须自己把仓库根放进 `sys.path` 再 `from tools import run_ui`。
3. **`--add-data` 的相对路径是相对 spec 目录**，不是 cwd。`--add-data 'aoe2mod/ui/static;...'` + `--specpath _probe/_exe_probe` 报
   `Unable to find 'D:\...\_probe\_exe_probe\aoe2mod\ui\static'`。必须给**绝对路径**。

## B. 尺寸：28.9 MB（单文件）

对照：`aoe2mod/` 源码约 50 MB、`_vendor`（pywebview）5.9 MB、`_vendor_pyinstaller` 14 MB。一个 28.9 MB 的 exe 对这个工具不算荒谬——它比它要改的那份 `.dat`（12 MB 压缩 / 93 MB 裸流）还小。

## C. 从工作区之外启动：**页面通，API 有洞**

在 `%TEMP%\dsh_exe_probe3`（不在仓库里）启动，`--game-root` 显式给出：

```
page  : HTTP 200, 52,603 B      <- 静态页发出去了
meta  : {"ok": false, "error": "[Errno 2] No such file or directory:
        'C:\\Users\\26913\\AppData\\Local\\Temp\\_MEI00005e702\\aoe2mod\\schema\\intents.json'"}
icon  : 200, 647 B, application/json  <- 是 JSON 拒绝，不是 PNG
```

**根因不是打包，是设计**：`aoe2mod/intent/compiler.py` 的 `_SCHEMA` 指向**磁盘上的 `aoe2mod/schema/*.json`**，这是「格式描述外置 schema + 插件化」这条硬约束的落地方式（用户能加 `plugins/<名字>/schema/intents.json`，能直接看、直接改）。打成 onefile 之后，`.py` 进了 exe 里的归档，**`schema/` 目录没有对应关系**，于是运行期找不到。

可以修的路有两条，代价不同，**这次没有擅自选**：

| 做法 | 代价 |
|---|---|
| 把 `aoe2mod/schema/*.json` 也 `--add-data` 进去，并让 `_SCHEMA` 在 `sys._MEIPASS` 下找 | 简单，但**外置 schema 就变成 exe 内部的东西** —— 用户改 JSON 必须重新打包，插件目录也必须改成「exe 旁边的 `plugins/`」才能生效。这条约束的**精神**（用户能看见、能改）会被削弱。 |
| 保持 schema 外置，exe 只在**同目录有 `aoe2mod/schema/` 时**才工作 | 那时它就不是「单文件」了，与「单入口、不挤进一个 exe」的取舍要先问清楚。 |

设计上还有个更根本的问题：`plugins/` 的发现路径目前是「仓库根旁边」，冻结之后「仓库根」是什么？这需要在动手前定，不能在打包脚本里顺手猜。

## D. 窗口：**未验证**

探针只跑了 `--browser --no-browser`（纯服务模式），**没有**打开冻结版的 WebView2 窗口。所以「冻结之后窗口还能开」这句话现在是**没有证据的**，不许当成已证。

## 我的操作错误（必须记下来）

测试期间我起了 10 个 `dsh-mod-workshop.exe` 进程留在后台（用户看到了「一堆 cmd」）。原因是**超时兜底失败**：脚本在 `Start-Process` 之后等待、超时后 `Stop-Process` 杀的是外层 pwsh，而 onefile 的 exe 是**独立进程树**。
规则：**跑子进程必须 `-PassThru` 记住 PID，并在 `finally` 里按 PID 结束整棵树**；靠「等一会再杀」兜不住。事后已全部 `Stop-Process` 清掉（`dsh-mod-workshop` 剩 0 个）。

## 结论

- 「PyInstaller 装不起来」**撤回**：能装、能构建、能启动、页面能发。
- 「打成单文件 exe」**和「schema 外置」冲突**，且冲突点在于**产品承诺**（用户可看可改），不在于技术难度。
- 窗口模式在冻结态下**未验证**。
- 下一步要么由用户决定这条取舍，要么把「exe 旁边放 schema 目录」做成正式形态再测；无论哪条，都不该在这一轮顺手改。

产物已清：`_probe/_exe_probe/`（174 MB 构建中间物）已删；`_vendor_pyinstaller/`（14 MB，可 `pip --target` 重建）暂留作复现材料。
