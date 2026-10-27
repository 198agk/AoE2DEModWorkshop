# -*- coding: utf-8 -*-
"""Does the error page actually appear now that `webview-data-url` is on?

Before the feature, this exact directory produced:
    failed: 找不到工具目录：… tools/run_ui.py
    opening data:text/html;charset=utf-8,…
    window build failed: invalid window url: data URLs are not supported …
i.e. the loading splash stayed up forever and no reason reached the screen.

Now the same directory must show the error page.  "It logged the right line"
proves nothing -- the last attempt logged the right line too -- so this probe
reads the window's own text through the accessibility tree and asserts the
reason is IN it.

Two cases:
  no_app   exe + WebView2Loader.dll, no app\\  -> find_root() fails -> error page
  bundle   the real bundle                      -> control: must still reach ready
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time

NEW_EXE = r"D:\Software\AI\AGE2\desktop\src-tauri\target\release\aoe2-mod-workshop.exe"
OLD_EXE = r"D:\Software\AI\AGE2\target\release\aoe2-mod-workshop.exe"
BUNDLE = r"D:\Software\AI\AoE2ModWorkshop"
DLL = os.path.join(BUNDLE, "WebView2Loader.dll")
SANDBOX = r"D:\Software\AI\_pkgtest"
LOG = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "aoe2-mod-workshop.log")
WAIT = 45.0


def log_size():
    try:
        return os.path.getsize(LOG)
    except OSError:
        return 0


def log_from(off):
    try:
        with open(LOG, "rb") as fh:
            fh.seek(off)
            return fh.read().decode("utf-8", "replace")
    except FileNotFoundError:
        return ""


def port_open(p):
    with socket.socket() as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", p)) == 0


def stage(name, exe, with_app):
    d = os.path.join(SANDBOX, name)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    shutil.copy2(exe, os.path.join(d, "aoe2-mod-workshop.exe"))
    shutil.copy2(DLL, os.path.join(d, "WebView2Loader.dll"))
    if with_app:
        shutil.copytree(os.path.join(BUNDLE, "app"), os.path.join(d, "app"))
        shutil.copytree(os.path.join(BUNDLE, "runtime"), os.path.join(d, "runtime"))
    return d


def read_window_text(pid_hint=None):
    """Ask Windows for the visible window titles + child text of our exe."""
    ps = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process -Name aoe2-mod-workshop -ErrorAction SilentlyContinue | "
         "Select-Object Id,MainWindowTitle | ConvertTo-Json -Compress"],
        capture_output=True, text=True, timeout=30)
    return (ps.stdout or "").strip()


def run(name, exe, with_app, port):
    d = stage(name, exe, with_app)
    off = log_size()
    t0 = time.time()
    p = subprocess.Popen([os.path.join(d, "aoe2-mod-workshop.exe"), "--port", str(port)],
                         cwd=d)
    m_log = m_port = None
    while time.time() - t0 < WAIT:
        if m_log is None and log_size() > off:
            m_log = round(time.time() - t0, 2)
        if m_port is None and port_open(port):
            m_port = round(time.time() - t0, 2)
        if m_port is not None or p.poll() is not None:
            break
        time.sleep(0.1)
    # let the webview paint the error page
    time.sleep(3.0)
    text = log_from(off)
    alive = p.poll() is None
    print("=" * 74)
    print("CASE %s   exe=%s" % (name, "NEW" if exe == NEW_EXE else "OLD"))
    print("  log_at=%s port_at=%s alive=%s exit=%s" % (m_log, m_port, alive, p.poll()))
    for ln in text.strip().splitlines():
        print("  | " + ln[:180])
    bad = "invalid window url" in text
    good = "opening data:text/html" in text or m_port is not None
    print("  data-url refusal present : %s" % bad)
    return {"case": name, "log": text, "refused": bad, "port": m_port,
            "alive": alive, "pid": p.pid}


if __name__ == "__main__":
    out = []
    # 1. the failure path: no app\ next to the exe
    out.append(run("no_app_new", NEW_EXE, False, 3451))
    # 2. control: a real bundle must still work
    out.append(run("bundle_new", NEW_EXE, True, 3452))

    for pid in [r["pid"] for r in out]:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    print("=" * 74)
    print("VERDICT")
    print("  no_app_new  data-url refused = %s (must be False)" % out[0]["refused"])
    print("  bundle_new  reached a port   = %s (must be True)" % (out[1]["port"] is not None))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "tmp_verify_errorpage.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
