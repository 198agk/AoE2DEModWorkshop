# -*- coding: utf-8 -*-
"""Measure acceptance item 11 at the two widths the contract names.

The item reads "窗口 1237px 与 1100px 两个宽度下无横向滚动、无控件被裁".  It was
reported as MANUAL because a grep cannot answer it, and a MANUAL item is an item
nobody checks -- the page shipped with a clipped right column for a whole round
while three text greps said the styling was fine.

How it works: the page posts its own viewport numbers to `/api/diag` when asked
with `?diag=1` (that route exists because `WebviewWindow::title()` silently
returns the shell's own title, so the first five attempts to read the viewport
measured nothing).  For each width this drives a real headless browser, then
reads the numbers back.  `scroll == doc` is the no-horizontal-scroll half; the
second half is that the grid still has two columns at 1237 (so nothing was
squeezed out) and one column at 1100 (the documented collapse).

Never touches the game, never builds, never installs.
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPORT = os.path.join(HERE, "width_report.json")

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def diag(base):
    raw = urllib.request.urlopen(base + "/api/diag", timeout=10).read()
    return json.loads(raw.decode("utf-8")).get("diag") or {}


def measure(base, width, shot):
    subprocess.run(
        [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--window-size=%d,900" % width, "--screenshot=" + shot,
         "--virtual-time-budget=45000", base + "/?diag=1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    # The page posts on every diag tick; give the last one time to land.
    time.sleep(1.5)
    return diag(base)


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:7811"
    shots = os.path.join(HERE, "shots")
    if not os.path.isdir(shots):
        os.makedirs(shots)

    out = {}
    for width in (1237, 1100):
        shot = os.path.join(shots, "w%d.png" % width)
        got = measure(base, width, shot)
        out[str(width)] = got
        print("%dpx -> vw=%s doc=%s scroll=%s display=%s flow=%s cols=%s"
              % (width, got.get("vw"), got.get("doc"), got.get("scroll"),
                 got.get("display"), got.get("flow"), got.get("cols")))

    with io.open(REPORT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote", REPORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
