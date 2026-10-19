# -*- coding: utf-8 -*-
"""Start the local mod workshop UI.

    python tools/run_ui.py            # opens a browser on a random free port
    python tools/run_ui.py --port 8700
    python tools/run_ui.py --no-browser

This is the single entry point the project's constraints ask for: one command,
no build step, no packaging.  The screen itself is `aoe2mod/ui/static/index.html`
and the API behind it is `aoe2mod/ui/server.py` -- both plain files a user can
open and edit.
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

from aoe2mod.ui import server as S                          # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="本地模组工坊")
    ap.add_argument("--port", type=int, default=0,
                    help="0 picks a free port (default)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--game-root", default=None,
                    help="AoE2DE install directory; auto-detected when omitted")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    httpd, app, url = S.serve(port=args.port, host=args.host,
                              game_root=args.game_root)
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
