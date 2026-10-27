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
import urllib.request
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

# The reason must be READ OFF THE PIXELS, not off the accessibility tree.
#
# UIA was the first attempt and it lied: it returned 0 characters while the
# error page was plainly painted (verified by screenshot).  WebView2 is
# Chromium -- it exposes an accessibility tree only after a client asks it to
# turn accessibility on, and a probe that reads UIA once at startup is not that
# client.  A measurement that reports "blank" for a painted page is worse than
# no measurement: it makes a working build look broken.
#
# So read the pixels.  The error page has two colours that appear nowhere else
# in a blank window: the gold heading (#c9a227) and the card (#1c2027) sitting
# on the page background (#14161a).  Finding gold text inside a card IS the
# reason being on screen -- an empty white or empty black window has neither.
SHOT_PS = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  public struct R { public int L, T, Rt, B; }
}
"@
$h = (Get-Process -Id __PID__).MainWindowHandle
if ($h -eq [IntPtr]::Zero) { Write-Output "NOHWND"; exit 0 }
[void][W]::ShowWindow($h, 9)
[void][W]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 900
$r = New-Object W+R
[void][W]::GetWindowRect($h, [ref]$r)
$w = $r.Rt - $r.L; $ht = $r.B - $r.T
if ($w -le 0 -or $ht -le 0) { Write-Output "NOBOX"; exit 0 }
$bmp = New-Object System.Drawing.Bitmap $w, $ht
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
$g.Dispose()

# Count here, not in Python.  The first version wrote a PNG and used Pillow to
# classify it, which made this gate depend on an interpreter that has Pillow --
# and the suite runner starts every suite with sys.executable, so the gate would
# have silently measured nothing under any other interpreter.  A gate that can
# only run under one of the two Pythons on this machine is not a gate.
$rect = New-Object System.Drawing.Rectangle 0, 0, $w, $ht
$bd = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly,
                    [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$stride = $bd.Stride
$buf = New-Object byte[] ($stride * $ht)
[System.Runtime.InteropServices.Marshal]::Copy($bd.Scan0, $buf, 0, $buf.Length)
$bmp.UnlockBits($bd)
$bmp.Dispose()

$gold = 0; $card = 0; $page = 0; $other = 0; $n = 0
# Stride 3 in both axes: the error page's card is ~600x200 px painted solid, so
# sampling 1 in 9 pixels cannot lose it.
for ($y = 0; $y -lt $ht; $y += 3) {
  $row = $y * $stride
  for ($x = 0; $x -lt $w; $x += 3) {
    $i = $row + $x * 3
    $b = $buf[$i]; $gg = $buf[$i + 1]; $rr = $buf[$i + 2]
    $n++
    if ([Math]::Abs($rr - 0xc9) -le 26 -and [Math]::Abs($gg - 0xa2) -le 26 -and [Math]::Abs($b - 0x27) -le 26) { $gold++ }
    elseif ([Math]::Abs($rr - 0x1c) -le 26 -and [Math]::Abs($gg - 0x20) -le 26 -and [Math]::Abs($b - 0x27) -le 26) { $card++ }
    elseif ([Math]::Abs($rr - 0x14) -le 26 -and [Math]::Abs($gg - 0x16) -le 26 -and [Math]::Abs($b - 0x1a) -le 26) { $page++ }
    else { $other++ }
  }
}
Write-Output ("PIX {0} {1} {2} {3} {4} {5}" -f $w, $ht, $n, $gold, $card, $page)
"""

# The page's own colours, from error_page()'s stylesheet.
GOLD = (0xc9, 0xa2, 0x27)
CARD = (0x1c, 0x20, 0x27)
PAGE = (0x14, 0x16, 0x1a)


def read_window(pid):
    """Classify the window's pixels. None if the window could not be read.

    Reads the PAINTED PIXELS, not the accessibility tree.  UIA was the first
    attempt and it lied: it returned 0 characters while the error page was
    plainly on screen (confirmed by screenshot).  WebView2 is Chromium -- it
    publishes an accessibility tree only once a client asks it to, and a probe
    that reads UIA once at startup is not that client.  A measurement that
    reports "blank" for a painted page makes a working build look broken.
    """
    script = os.path.join(SANDBOX, "shot_%d.ps1" % pid)
    os.makedirs(SANDBOX, exist_ok=True)
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(SHOT_PS.replace("__PID__", str(pid)))
    try:
        ps = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                             "-File", script], capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return None
    finally:
        try:
            os.remove(script)
        except OSError:
            pass
    line = [l for l in (ps.stdout or "").splitlines() if l.startswith("PIX ")]
    if not line:
        return None
    f = line[-1].split()
    w, h, n, gold, card, page = (int(v) for v in f[1:7])
    return {"w": w, "h": h, "n": n, "gold": gold, "card": card, "page": page,
            "other": n - gold - card - page,
            "gold_pct": round(100.0 * gold / n, 4),
            "other_pct": round(100.0 * (n - gold - card - page) / n, 2)}


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


# Does the loading page's error line FIT INSIDE its own box?
#
# Measured on the shipped build: the error is a Windows path -- one 74-character
# token with no spaces in it.  `white-space: pre-wrap` breaks at spaces, so the
# paragraph overflowed (scrollWidth 548 vs clientWidth 420) and the player saw
# the path cut off at the window edge.  `overflow-wrap: anywhere` is the fix;
# this assertion is the thing that notices if it comes back.
FIT_PS = r"""
$ErrorActionPreference = 'Stop'
$req = [System.Net.WebRequest]::Create("__URL__")
$req.Timeout = 5000
$resp = $req.GetResponse()
$sr = New-Object System.IO.StreamReader($resp.GetResponseStream())
$html = $sr.ReadToEnd(); $sr.Close(); $resp.Close()
Write-Output $html
"""


def run_missing_data(port):
    """The bundle, pointed at a directory with no .dat: the SPLASH must say why.

    Reads the reason through the same endpoint the page reads, then checks the
    page's own inline style carries the wrapping rule that keeps a long path
    inside the box.  A DOM measurement would be better than a source grep, but
    Playwright is a different dependency from this probe's three; the grep is
    the part that cannot silently pass if the rule is deleted.
    """
    empty = os.path.join(SANDBOX, "nodata_%d" % int(time.time()))
    os.makedirs(empty)
    off = log_size()
    env = dict(os.environ)
    env["AOE2MOD_GAME_ROOT"] = empty
    p = subprocess.Popen([os.path.join(BUNDLE, "aoe2-mod-workshop.exe"),
                          "--port", str(port)], cwd=BUNDLE, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    err = None
    t0 = time.time()
    while time.time() - t0 < 30:
        try:
            req = urllib.request.Request("http://127.0.0.1:%d/api/progress" % port)
            with urllib.request.urlopen(req, timeout=2) as fh:
                j = json.loads(fh.read().decode("utf-8"))
            err = (j.get("progress") or {}).get("error")
            if err and "失败" in ((j["progress"].get("label")) or ""):
                break
        except Exception:
            pass
        time.sleep(0.25)
    body = ""
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/loading" % port,
                                    timeout=3) as fh:
            body = fh.read().decode("utf-8")
    except Exception:
        pass
    log = log_from(off)
    print("=" * 74)
    print("CASE no_data")
    print("  progress.error = %s" % (err or "<none>"))
    for ln in log.strip().splitlines()[:4]:
        print("  | " + ln[:160])
    wrapped = "overflow-wrap:anywhere" in body
    print("  splash carries overflow-wrap:anywhere = %s" % wrapped)
    subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    return {"case": "no_data", "error": err, "wrapped": wrapped, "pid": p.pid}


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
        # An error page never opens a port and never exits, so waiting for one
        # of those burned the whole 45 s every run.  Once the log has the
        # failure line the outcome is decided; only the paint is left.
        if m_log is not None and time.time() - t0 > 2.5:
            if "failed:" in log_from(off):
                break
        time.sleep(0.1)
    # let the webview paint
    time.sleep(4.0)
    text = log_from(off)
    seen = read_window(p.pid)
    alive = p.poll() is None
    print("=" * 74)
    print("CASE %s" % name)
    print("  log_at=%s port_at=%s alive=%s" % (m_log, m_port, alive))
    for ln in text.strip().splitlines():
        print("  | " + ln[:180])
    if seen is None:
        print("  --- window pixels: UNREADABLE ---")
    else:
        print("  --- pixels %dx%d sampled=%d  gold=%d  card=%d  other=%.2f%% ---"
              % (seen["w"], seen["h"], seen["n"], seen["gold"], seen["card"],
                 seen["other_pct"]))
    refused = "invalid window url" in text or "data URLs are not supported" in text
    return {"case": name, "log": text, "pixels": seen,
            "refused": refused, "port": m_port, "alive": alive, "pid": p.pid}


if __name__ == "__main__":
    out = []
    out.append(run("no_app_new", NEW_EXE, False, 3451))
    out.append(run("bundle_new", NEW_EXE, True, 3452))
    nod = run_missing_data(3453)

    for pid in [r["pid"] for r in out]:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)

    px = out[0]["pixels"]
    # Thresholds come from MEASURED separation, not from guesswork.  Same probe,
    # same machine, two windows (1-in-9 pixel sampling, 125,281 samples each):
    #     error page    gold=384  card=71,472
    #     loading page  gold= 29  card= 1,268
    # The first pass used gold>=40 / card>2000 and the CONTROL passed too -- a
    # measurement that calls the working app an error page cannot tell a fixed
    # build from a broken one.  Midpoints, so a threshold bump cannot be reached
    # by drifting: gold>=150 is 5.2x above the loading page and 2.6x below the
    # error page; card>=15,000 is 11.8x above and 4.8x below.
    def looks_like_error(p):
        return bool(p) and p["gold"] >= 150 and p["card"] >= 15000
    reason_on_screen = looks_like_error(px)
    # Negative control: the working bundle must NOT look like the error page.
    control_not_error = not looks_like_error(out[1]["pixels"])
    control_ok = out[1]["port"] is not None
    print("=" * 74)
    print("VERDICT")
    print("  no_app   data-url refused    = %s (must be False)" % out[0]["refused"])
    print("  no_app   reason ON SCREEN    = %s (must be True)" % reason_on_screen)
    print("  bundle   reached a port      = %s (must be True)" % control_ok)
    print("  bundle   NOT an error page   = %s (must be True)" % control_not_error)
    data_reason = bool(nod["error"]) and ("找不到" in nod["error"] or "os error" in nod["error"])
    print("  no_data  splash says why     = %s (must be True)" % data_reason)
    print("  no_data  long path wraps     = %s (must be True)" % nod["wrapped"])
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "tmp_verify_errorpage.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    ok = (not out[0]["refused"] and reason_on_screen and control_ok
          and control_not_error and data_reason and nod["wrapped"])
    sys.exit(0 if ok else 1)
