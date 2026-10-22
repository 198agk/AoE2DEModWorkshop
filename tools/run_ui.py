# -*- coding: utf-8 -*-
"""Start the local mod workshop UI.

    python tools/run_ui.py            # opens a browser on a random free port
    python tools/run_ui.py --port 8700
    python tools/run_ui.py --no-browser

This is the single entry point the project's constraints ask for: one command,
no build step, no packaging.  The screen itself is `aoe2mod/ui/static/index.html`
and the API behind it is `aoe2mod/ui/server.py` -- both plain files a user can
open and edit.

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
                    help="不自动打开浏览器")
    args = ap.parse_args(argv)

    root, notes = _preflight(args.game_root)
    for n in notes:
        print(n)

    httpd, app, url = S.serve(port=args.port, host=args.host, game_root=root)
    print("模组工坊: %s" % url)
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
