# -*- coding: utf-8 -*-
"""Does the failure reason reach the SCREEN, or only the log?

Before `webview-data-url` was on, this exact directory produced:
    failed: 找不到界面目录…
    opening data:text/html;charset=utf-8,…
    window build failed: invalid window url: data URLs are not supported …
i.e. the splash stayed up forever and no reason reached the player.

Now the same directory must SHOW the reason. "It logged the right line" proves
nothing -- the broken build logged the right line too. So this probe reads the
window's own text out of the accessibility tree and asserts the reason is IN it.

Two cases:
  no_app   exe + WebView2Loader.dll, no app\\  -> find_root() fails -> error page
  bundle   the real bundle                      -> control: must still reach ready

An empty directory and a real one differ by `app\\` only; there is no `runtime\\`
any more, which is why the earlier version of this probe died on
`FileNotFoundError: …\\runtime` -- it was written against the Python child.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time

NEW_EXE = r"D:\Software\AI\AGE2\desktop\src-tauri\target\release\aoe2-mod-workshop.exe"
BUNDLE = r"D:\Software\AI\AoE2ModWorkshop"
DLL = os.path.join(BUNDLE, "WebView2Loader.dll")
SANDBOX = r"D:\Software\AI\_pkgtest"
LOG = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "aoe2-mod-workshop.log")
WAIT = 45.0

# UIA out of PowerShell: dump every visible string inside the process's window.
# Used instead of MainWindowTitle because a WebView2 page has no title worth
# reading -- the whole point is the BODY text.
UIA_PS = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$cond = New-Object System.Windows.Automation.PropertyCondition(
  [System.Windows.Automation.AutomationElement]::ProcessIdProperty, __PID__)
# The process owns SEVERAL top-level windows: the real one AND a 4x4 invisible
# helper. FindFirst returned the helper, which has no descendants, so the probe
# reported "0 chars" while the reason was plainly on screen. Collect them all
# and keep the one that actually carries text.
$wins = [System.Windows.Automation.AutomationElement]::RootElement.FindAll(
  [System.Windows.Automation.TreeScope]::Children, $cond)
$best = ''
foreach ($w in $wins) {
  $out = @()
  if ($w.Current.Name) { $out += $w.Current.Name }
  $all = $w.FindAll([System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition)
  foreach ($e in $all) {
    if ($e.Current.Name) { $out += $e.Current.Name }
  }
  $joined = $out -join "`n"
  if ($joined.Length -gt $best.Length) { $best = $joined }
}
Write-Output $best
"""

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
    # A UNIQUE directory per run: a previous run leaves its own exe running with
    # the sandbox as its cwd, and  then fails on the open handle -- with
    # ignore_errors swallowing the reason, the next line reported it as
    # FileExistsError instead of "still in use".
    d = os.path.join(SANDBOX, "%s_%d" % (name, int(time.time())))
    os.makedirs(d)
    shutil.copy2(exe, os.path.join(d, "aoe2-mod-workshop.exe"))
    shutil.copy2(DLL, os.path.join(d, "WebView2Loader.dll"))
    if with_app:
        shutil.copytree(os.path.join(BUNDLE, "app"), os.path.join(d, "app"))
    return d


def window_text(pid):
    """Every visible string inside the window, joined by newlines."""
    script = os.path.join(SANDBOX, "uia_%d.ps1" % pid)
    os.makedirs(SANDBOX, exist_ok=True)
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(UIA_PS.replace("__PID__", str(pid)))
    try:
        ps = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script],
            capture_output=True, text=True, timeout=60)
        return (ps.stdout or "").strip()
    except subprocess.TimeoutExpired:
        return ""
    finally:
        try:
            os.remove(script)
        except OSError:
            pass


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
    # let the webview paint
    time.sleep(4.0)
    text = log_from(off)
    seen = window_text(p.pid)
    alive = p.poll() is None
    print("=" * 74)
    print("CASE %s" % name)
    print("  log_at=%s port_at=%s alive=%s" % (m_log, m_port, alive))
    for ln in text.strip().splitlines():
        print("  | " + ln[:180])
    print("  --- window text (%d chars) ---" % len(seen))
    for ln in seen.splitlines()[:14]:
        print("  > " + ln[:180])
    refused = "invalid window url" in text or "data URLs are not supported" in text
    return {"case": name, "log": text, "screen": seen, "refused": refused,
            "port": m_port, "alive": alive, "pid": p.pid}


if __name__ == "__main__":
    out = []
    out.append(run("no_app_new", NEW_EXE, False, 3451))
    out.append(run("bundle_new", NEW_EXE, True, 3452))

    for pid in [r["pid"] for r in out]:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)

    reason_on_screen = "找不到界面目录" in out[0]["screen"]
    control_ok = out[1]["port"] is not None
    print("=" * 74)
    print("VERDICT")
    print("  no_app   data-url refused    = %s (must be False)" % out[0]["refused"])
    print("  no_app   reason ON SCREEN    = %s (must be True)" % reason_on_screen)
    print("  bundle   reached a port      = %s (must be True)" % control_ok)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "tmp_verify_errorpage.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    sys.exit(0 if (not out[0]["refused"] and reason_on_screen and control_ok) else 1)
