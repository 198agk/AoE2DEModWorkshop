# -*- coding: utf-8 -*-
"""Start the local mod workshop UI.

    python tools/run_ui.py              # a real window, or a browser if it cannot
    python tools/run_ui.py --browser    # always a browser tab
    python tools/run_ui.py --window     # refuse to fall back; a window or nothing
    python tools/run_ui.py --port 8700 --no-browser

This is the single entry point the project's constraints ask for: one command,
no build step, no packaging.  The screen itself is `aoe2mod/ui/static/index.html`
and the API behind it is `aoe2mod/ui/server.py` -- both plain files a user can
open and edit.

Why a window at all
-------------------
The screen is a normal web page, so a browser tab is enough to use it, and that
is what shipped first.  But a browser tab is not a program: it has an address
bar, it can be navigated away, and a player who double-clicks a launcher expects
something that looks like an application.  pywebview is a thin shell over the
Edge WebView2 runtime the machine already has, so the same static files render
inside a window with no build step and no bundler -- the constraint that killed
Electron/Tauri here was the toolchain, not the idea.

Measured 2026-10-25: `import webview` failed in this runtime until it was
installed into `_vendor/` with `pip --target`; once installed, a real window
opened and ran its own script (probe: `_probe/tmp_webview_probe.py`, which drives
the window from python through `evaluate_js` instead of trusting the JS bridge).
The machine's WebView2 runtime is separately confirmed present (156.0.4314.42).
So "window mode" is a real option now, and it is the default when it imports.

Why there is a pre-flight check
-------------------------------
The server binds a socket without touching the game, so the first version
started happily on a machine with no install and said nothing; the player got a
browser window whose first request failed with an English `FileNotFoundError`
about an `empires2_x2_p1.dat` path.  That is the worst place to learn the game
is missing, so the two cheap facts (is there an install, is there a profile) are
checked here, before the window opens, in a sentence that says what to do.  The
expensive fact -- whether the `.dat` parses -- is left to the request that needs
it; parsing 93 MB to print a banner would make every start take ten seconds.
"""
import argparse
import os
import sys
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# pywebview lives here when it was installed with `pip --target`.  Inserting the
# path is what makes the import decide correctly: without it the answer is
# "not installed" on a machine that has it, which is the same sentence the notes
# spent two days saying about the icon layer -- true once, then false.
VENDOR = os.path.join(ROOT, "_vendor")
if os.path.isdir(VENDOR) and VENDOR not in sys.path:
    sys.path.insert(0, VENDOR)

from aoe2mod.game import locations as L                      # noqa: E402
from aoe2mod.ui import server as S                           # noqa: E402


def _preflight(game_root):
    """Return (game_root, notes) or raise with a sentence a player can act on.

    `notes` are facts worth saying out loud that are NOT failures: an install
    found by search rather than by flag, a profile that does not exist yet.
    """
    notes = []
    if game_root:
        root = os.path.abspath(game_root)
        if not L.looks_like_game_root(root):
            raise SystemExit(
                "这个目录不像《帝国时代 2 决定版》的安装目录：%s\n"
                "它下面应该有 resources\\_common\\dat\\empires2_x2_p1.dat。" % root)
    else:
        try:
            root = L.find_game_root()
        except FileNotFoundError as exc:
            # The message already lists every place that was tried.
            raise SystemExit(str(exc))
        notes.append("自动找到游戏目录：%s" % root)
    if not os.path.isfile(os.path.join(root, L.DAT_REL)):
        raise SystemExit(
            "游戏目录里没有 resources\\_common\\dat\\empires2_x2_p1.dat：%s\n"
            "先用 Steam 校验一次游戏文件。" % root)
    try:
        L.find_profile_root()
    except FileNotFoundError as exc:
        # Not fatal: the screen can still preview edits.  Only installing needs
        # a profile, so this is a note rather than a refusal.
        notes.append(str(exc))
    return root, notes


def _serve_in_background(httpd):
    """Run the HTTP server on a daemon thread so the main thread can own a window.

    `serve_forever()` in the main thread is what makes window mode impossible:
    pywebview's own loop has to own the main thread.  Daemon=True matters for the
    failing case -- a window that never opens must not leave a port bound.
    """
    t = threading.Thread(target=httpd.serve_forever, name="mod-workshop-http",
                         daemon=True)
    t.start()
    return t


def _run_window(url):
    """Open `url` in a native window.  Return the exit code.

    Two things here are deliberate:
      * the window is created with `url=`, not with a copy of the HTML, so the
        thing on screen is served by the same routes the tests exercise;
      * a failure to import or to start is reported as "fall back", not as a
        crash -- the browser path still works, and a launcher that dies because
        an optional shell is missing is worse than one that opens a tab.
    """
    try:
        import webview
    except Exception as exc:                                  # noqa: BLE001
        print("图形窗口不可用（%s），改用浏览器。" % exc)
        print("装它只要一句（不需要管理员权限，装进这个仓库的 _vendor\\）：")
        print("  <python> -m pip install --target _vendor pywebview")
        return None
    try:
        webview.create_window("模组工坊", url=url, width=1280, height=860,
                              min_size=(900, 600))
        webview.start()
        return 0
    except Exception as exc:                                  # noqa: BLE001
        print("图形窗口启动失败（%s），改用浏览器。" % exc)
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="本地模组工坊（帝国时代 2 决定版）",
        epilog="例：python tools/run_ui.py --port 7792")
    ap.add_argument("--port", type=int, default=0,
                    help="端口；0 表示挑一个空闲端口（默认）")
    ap.add_argument("--host", default="127.0.0.1",
                    help="监听地址；默认只监听本机")
    ap.add_argument("--game-root", default=None,
                    help="游戏安装目录；不给就自动找")
    ap.add_argument("--no-browser", action="store_true",
                    help="不自动打开浏览器（图形窗口仍然会开）")
    ap.add_argument("--window", action="store_true",
                    help="只开图形窗口；开不了就退出，不退回浏览器")
    ap.add_argument("--browser", action="store_true",
                    help="只在浏览器里打开（老行为）")
    args = ap.parse_args(argv)
    if args.window and args.browser:
        raise SystemExit("--window 和 --browser 是两种模式，只能选一个。")

    root, notes = _preflight(args.game_root)
    for n in notes:
        print(n)

    httpd, app, url = S.serve(port=args.port, host=args.host, game_root=root)
    print("模组工坊: %s" % url)

    want_window = not args.browser
    if want_window:
        _serve_in_background(httpd)
        code = _run_window(url)
        if code is None and args.window:
            httpd.shutdown()
            httpd.server_close()
            raise SystemExit(
                "要图形窗口，但这台机器上没有能用的 pywebview。\n"
                "去掉 --window 就会用浏览器打开同一个地址：%s" % url)
        if code is not None:
            httpd.shutdown()
            httpd.server_close()
            print("bye")
            return code
        print("（退回浏览器模式）")

    print("（Ctrl+C 结束）")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
