"""Does `tools/run_ui.py --window` really put the page in a native window?

The claim under test is not "webview imports" -- that was already measured
separately.  The claim is: this one command opens a window, the window is served
by the same routes the tests exercise, and closing it leaves no port bound.

So this starts the real entry point as a separate process, waits for the HTTP
side to answer, enumerates the top-level windows to find one titled 模组工坊, and
then stops the process and checks the port is gone.  Driving it through the real
process is the point: an in-process test of `_run_window` would pass even if the
`__main__` wiring were wrong.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
PORT = 7823


def window_titles():
    """Top-level window titles, via ctypes -- no extra dependency."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _lp):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n <= 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        found.append(buf.value)
        return True

    user32.EnumWindows(cb, 0)
    return found


def get(url, tries=40, delay=0.5):
    last = None
    for _ in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                return r.status, r.read()
        except Exception as exc:                             # noqa: BLE001
            last = exc
            time.sleep(delay)
    raise SystemExit("the HTTP side never answered: %s" % last)


def port_open(port):
    import socket
    s = socket.socket()
    s.settimeout(0.4)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def main():
    fails = []

    def check(name, ok, detail=""):
        print("  %s %s%s" % ("ok  " if ok else "FAIL", name,
                             (" :: " + str(detail)) if (detail and not ok) else ""))
        if not ok:
            fails.append(name)

    print("=== A. start the entry point in window mode")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen(
        [PY, "-X", "utf8", "-u", os.path.join("tools", "run_ui.py"),
         "--window", "--port", str(PORT), "--no-browser"],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace")
    title = "模组工坊"
    try:
        st, body = get("http://127.0.0.1:%d/api/meta" % PORT)
        check("the server answers while the window owns the main thread", st == 200,
              "status=%r" % (st,))
        meta = json.loads(body.decode("utf-8"))
        check("and it is the real toolkit", meta.get("intents") and meta.get("civs"),
              "intents=%r civs=%r" % (len(meta.get("intents") or []),
                                      meta.get("civs")))

        want = "模组工坊"
        deadline = time.time() + 25
        titles = []
        while time.time() < deadline:
            titles = window_titles()
            if any(want in t for t in titles):
                break
            time.sleep(0.6)
        hit = [t for t in titles if want in t]
        check("a native window titled 「%s」 is on screen" % want, bool(hit),
              "titles=%r" % (titles[:8],))
        if hit:
            check("and it is exactly one window", len(hit) == 1, repr(hit))

        st2, page = get("http://127.0.0.1:%d/" % PORT)
        check("the window's URL serves the workshop page", st2 == 200
              and b"<textarea id=\"say\"" in page,
              "status=%r bytes=%d" % (st2, len(page or b"")))
        check("the process is still alive after the window opened",
              proc.poll() is None, "exit=%r" % (proc.poll(),))
    finally:
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
        time.sleep(0.8)
        print("  --- the entry point's own output ---")
        for line in (out or "").strip().splitlines():
            print("      %s" % line)

    print("=== B. closing the window releases the port")
    gone = False
    for _ in range(20):
        if not port_open(PORT):
            gone = True
            break
        time.sleep(0.4)
    check("the port is no longer bound", gone, "port %d still open" % PORT)
    check("and no pywebview window is left behind",
          not any("模组工坊" in t for t in window_titles()))

    print()
    if fails:
        print("WINDOW MODE: %d CHECK(S) FAILED -> %r" % (len(fails), fails))
        return 1
    print("WINDOW MODE: ONE COMMAND OPENS A REAL WINDOW, SERVED BY THE SAME ROUTES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
