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
import re
import urllib.request
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import _paths as P

NEW_EXE = P.EXE
BUNDLE = P.BUNDLE
DLL = os.path.join(BUNDLE, "WebView2Loader.dll")
# OUTSIDE the checkout on purpose -- see the module docstring of
# `_probe/_tmp/fix_pkgtest.py`: the exe resolves its UI root by walking up
# from its cwd, so a fixture inside the repo finds the repo's page and this
# probe stops exercising the error page at all.
SANDBOX = tempfile.mkdtemp(prefix="aoe2_pkgtest_")
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
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool RedrawWindow(IntPtr h, IntPtr r, IntPtr hr, uint f);
  public struct R { public int L, T, Rt, B; }
  public struct M { public int L, T, Rt, B; }
}
"@
$h = (Get-Process -Id __PID__).MainWindowHandle
if ($h -eq [IntPtr]::Zero) { Write-Output "NOHWND"; exit 0 }
# Reported twice (m22632「都说了别在主显示器弹出窗口来」, m22792「别在弹出来了，
# 每次都被你打断」) that this probe yanked a 1255x897 window over the desktop and
# took focus.  A gate that steals the screen gets skipped, and a skipped gate
# protects nothing.
#
# So the window is MOVED to the secondary display FIRST, without activating it,
# and only then revealed with `SW_SHOWNOACTIVATE` (4): shown, never focused,
# never on the primary monitor.  Revealing is not optional -- WebView2 paints
# nothing while its host window stays hidden, and an earlier version of this fix
# read a pure white bitmap and reported `reason ON SCREEN = False` for a build
# whose error page was fine.
$m = New-Object W+M
# MOVED to the secondary display with SWP_NOACTIVATE, then revealed with
# SW_SHOWNOACTIVATE: shown (WebView2 paints nothing while its host is hidden)
# without ever taking focus or landing on the primary monitor.  The capture no
# longer depends on the position, but the user's desktop still does.
[void][W]::SetWindowPos($h, [IntPtr]::Zero, -1050, -140, 0, 0, 0x15)
[void][W]::ShowWindow($h, 4)
Start-Sleep -Milliseconds 2600
$r = New-Object W+R
[void][W]::GetWindowRect($h, [ref]$r)
$w = $r.Rt - $r.L; $ht = $r.B - $r.T
if ($w -le 0 -or $ht -le 0) { Write-Output "NOBOX"; exit 0 }
# Read the window's own pixels, without taking focus or covering the screen.
#
# `PrintWindow` with flag 0, and the flags matter -- all three measured on this
# exact fixture (error page on screen, 2026-11-02):
#   PW_RENDERFULLCONTENT (2) -> a WHITE bitmap.  gold=0 where the screen has 384.
#                               Chromium hands its surface to DirectComposition
#                               and the DC render comes back empty.
#   CopyFromScreen(rect)     -> shifted ~135 px at x=-1060, so the gold heading
#                               fell outside the crop and the gate read gold=50
#                               for a page that was drawing it fine.
#   PrintWindow(flag 0)      -> the whole page, heading included.  Verified by
#                               saving the PNG and looking at it.
# Ask for a fresh paint.  Without this a retry photographs the SAME stale
# surface again: measured in a loaded full-suite run, `gold=1 card=898` forever
# while the error page was up and nothing was drawing it.
#   RDW_INVALIDATE 0x1 | RDW_UPDATENOW 0x100 | RDW_ALLCHILDREN 0x80
[void][W]::RedrawWindow($h, [IntPtr]::Zero, [IntPtr]::Zero, 0x181)
Start-Sleep -Milliseconds 350
[void][W]::GetWindowRect($h, [ref]$r)
$w = $r.Rt - $r.L; $ht = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap $w, $ht
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$printed = [W]::PrintWindow($h, $hdc, 0)
$g.ReleaseHdc($hdc)
$g.Dispose()
if (-not $printed) { Write-Output "NOBOX"; exit 0 }
$how = "printwindow0"

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
# Colour histogram as well as the palette classes.  The palette below can only
# say "this window is the error page" -- it cannot say "this window has been
# painted at all", because it names three specific colours and the loading page
# is none of them.  The histogram answers the second question without knowing
# what the page looks like: quantise each channel to 16 levels, then count the
# buckets holding at least 0.5% of the samples.  An unpainted window is ONE
# colour edge to edge, so its count is 1 whatever that colour happens to be.
$bins = New-Object 'int[]' 4096
# Stride 3 in both axes: the error page's card is ~600x200 px painted solid, so
# sampling 1 in 9 pixels cannot lose it.
for ($y = 0; $y -lt $ht; $y += 3) {
  $row = $y * $stride
  for ($x = 0; $x -lt $w; $x += 3) {
    $i = $row + $x * 3
    $b = $buf[$i]; $gg = $buf[$i + 1]; $rr = $buf[$i + 2]
    $n++
    $bins[(([int]$rr -shr 4) * 256) + (([int]$gg -shr 4) * 16) + ([int]$b -shr 4)]++
    if ([Math]::Abs($rr - 0xc9) -le 26 -and [Math]::Abs($gg - 0xa2) -le 26 -and [Math]::Abs($b - 0x27) -le 26) { $gold++ }
    elseif ([Math]::Abs($rr - 0x1c) -le 26 -and [Math]::Abs($gg - 0x20) -le 26 -and [Math]::Abs($b - 0x27) -le 26) { $card++ }
    elseif ([Math]::Abs($rr - 0x14) -le 26 -and [Math]::Abs($gg - 0x16) -le 26 -and [Math]::Abs($b - 0x1a) -le 26) { $page++ }
    else { $other++ }
  }
}
$big = 0
$max = 0
for ($i = 0; $i -lt 4096; $i++) {
  if (($bins[$i] * 200) -ge $n) { $big++ }
  if ($bins[$i] -gt $max) { $max = $bins[$i] }
}
Write-Output ("PIX {0} {1} {2} {3} {4} {5} {6} {7} {8}" -f $w, $ht, $n, $gold, $card, $page, $how, $big, [Math]::Round(100.0 * $max / $n, 2))
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
    # Column 7 says WHICH capture path produced these pixels: `printwindow`
    # (the window's own DC, no focus taken) or `offscreen` (moved to the second
    # monitor, photographed, never activated).  Printed so a reader can tell a
    # direct measurement from a fallback.
    how = f[7] if len(f) > 7 else "unknown"
    # Columns 8 and 9 are how many colours cover at least 0.5% of the window,
    # and the biggest one's share.  The first is what `drawn()` reads; the
    # second is printed for a human wondering what the window looked like.
    big = int(f[8]) if len(f) > 8 else 0
    flat = float(f[9]) if len(f) > 9 else 0.0
    return {"w": w, "h": h, "n": n, "gold": gold, "card": card, "page": page,
            "how": how, "big": big, "flat": flat,
            "other": n - gold - card - page,
            "gold_pct": round(100.0 * gold / n, 4),
            "other_pct": round(100.0 * (n - gold - card - page) / n, 2)}


# How many colours, each covering at least 0.5% of the window, are on it.
#
# Measured 2026-11-07, 125,281 samples per window, at the FINISHED state (the
# one the verdict is printed from -- `_probe/_tmp/measure_big.py` also caught
# frames mid-paint, flat=57.3% / 7.26%, where this count is 18 and 53, which is
# why the finished numbers below are taken from the probe's own run):
#     loading page (the control)      big =  4   flat = 94.1%
#     error page   (the case)         big =  5   flat = 68.6%
#     never painted                   big =  1   (one colour edge to edge; before
#                                                 that the window has no handle:
#                                                 NOBOX)
# One is the only number an undrawn window can produce, and it does not depend
# on WHICH colours the page uses -- that is the property the two previous
# criteria lacked (`gold` named the error page's heading, `page+card` named its
# dark background, and the loading page is light #f6f8fa so it scored 6..778
# against a 2,000 floor and the control reported "never drew" for a window that
# WAS drawing).
DREW_BIG = 2


def drawn(p):
    """Has anything been painted on this window at all?

    The question the retry loop and the control both need.  Kept separate from
    `looks_like_error()`, which is about WHICH page this is and legitimately
    names colours -- the bug was answering the first question with the second
    one's measurement.
    """
    if not p:
        return False
    return p.get("big", 0) >= DREW_BIG


def painted(p):
    """How much of the window is THE ERROR PAGE -- not "is anything drawn".

    Two questions live in this probe and they must not share a number:

    * "has this window been painted at all" -- `drawn()` above, colour buckets,
      no palette, used for the control and for the relaunch decision.  A
      palette-based answer to THIS question was the false red of 2026-11-06:
      the control is a light loading page and scored 6..778 against a 2,000
      floor, so a drawn window was reported as "never drew".
    * "is the error page up, and has it stopped changing" -- this function.
      Here the error page's own colours are the thing being looked for, so
      naming them is the point, not a leak.  Measured 2026-11-07: answering
      this one with `drawn()` ended the wait 25 s in, while the window held the
      splash (colours=7, gold=0) and the failure had not been navigated to yet.

    `page` (#14161a) + `card` (#1c2027) cover most of the error page and almost
    none of the loading page, which is what makes them usable as "is the error
    page on screen".
    """
    if not p:
        return 0
    return p["page"] + p["card"]


# 2,000: measured separation between "the error page is up" and "it is not",
# 125,281 samples per window, 2026-11-06/07:
#     loading page / not navigated yet   page+card =      6 ..   1,268
#     transitional frame, error pending  page+card =  4,795   <- 2026-11-07
#     error page, card drawn no heading  page+card = 74,049
#     error page, complete               page+card = 115,866
# It is NOT a "did it draw" threshold -- see `drawn()` and DREW_BIG for that.
ERR_PAINTED = 2000

# 15,000: the card's own footprint.  Used ONLY to decide "waiting longer cannot
# change the answer", so it must not be reachable by a frame that is still
# arriving.  The transitional 4,795 above clears ERR_PAINTED but not this, which
# is exactly the difference between "the card is up and the heading never came"
# (a finding, stop waiting) and "neither is up yet" (keep waiting).
CARD_MIN = 15000

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
    # 90 s, not 30: this case launches the shipped exe and waits for its
    # localhost listener, which is the slowest thing in the whole probe.  Under a
    # full 221-suite run the 30 s budget expired while the process was still
    # starting, and the empty splash that followed was reported as a missing CSS
    # rule.  2026-11-09.
    while time.time() - t0 < 90:
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
    # Fetching the splash is a SECOND wait, not a side effect of the first one.
    # When this ran inside a full suite the error text appeared before the
    # listener had bound (the machine was busy), the single fetch below got a
    # refused connection, and the case reported that the page had lost its
    # wrapping rule -- a claim about the page, made out of a claim about time.
    # Give it its own deadline and remember why it was empty.
    body = ""
    why = "<never fetched>"
    t1 = time.time()
    while time.time() - t1 < 60:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/loading" % port,
                                        timeout=3) as fh:
                body = fh.read().decode("utf-8")
            why = ""
            break
        except Exception as exc:
            why = "%s: %s" % (type(exc).__name__, exc)
        time.sleep(0.25)
    log = log_from(off)
    print("=" * 74)
    print("CASE no_data")
    print("  progress.error = %s" % (err or "<none>"))
    for ln in log.strip().splitlines()[:4]:
        print("  | " + ln[:160])
    # The rule, not its typography.  This started as a literal
    # `"overflow-wrap:anywhere" in body`, and it went red on 2026-11-05 for a
    # page that HAS the rule: the declaration was rewritten with a space after
    # the colon (`overflow-wrap: anywhere`), which is the same CSS.  A gate that
    # pins one spelling of a correct rule reports a defect that does not exist.
    # Match the property and value with optional whitespace.
    wrapped = re.search(r"overflow-wrap\s*:\s*anywhere", body) is not None
    print("  splash carries overflow-wrap:anywhere = %s" % wrapped)
    print("  splash body bytes = %d%s" % (len(body), (" (fetch failed: %s)" % why) if why else ""))
    subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    return {"case": "no_data", "error": err, "wrapped": wrapped,
            "body_bytes": len(body), "fetch_note": why, "pid": p.pid}


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
    # Poll for the paint instead of trusting one fixed sleep.  Measured
    # 2026-11-02: the same fixture captured 66 s after launch gives
    # `gold=370` on the FIRST try, while the same capture 10 s after launch gives
    # `gold=0` -- WebView2 paints this window late, and a single sleep long enough
    # for the slow case would add half a minute to every run.  Retrying keeps the
    # common case fast and stops the gate from calling a drawn page blank.
    # 100 s, not 40: measured 2026-11-02, with every other suite on the box the
    # error page took longer than 40 s to paint and the gate reported the page
    # missing.  The common case still exits on the first capture.
    #
    # A FAILED READ IS NOT A FAILED PAGE.  The first version wrote
    # `while seen is not None and ...`, so one unreadable capture -- PowerShell
    # taking longer than its own startup under a loaded machine, which is the
    # normal state during a full suite run -- skipped the loop entirely and the
    # gate reported "the reason is not on screen" for a page that draws it.
    # Measured 2026-11-03 in `_probe/_tmp/suites39.log`: `reason ON SCREEN =
    # False` inside the suite, `gold=370` for the same fixture run alone.
    # So: retry while we have not yet seen the paint, whether or not the last
    # read produced anything, and stop early on the usual case.
    # 300 s, not 150: the loop exits on the FIRST capture that shows the paint,
    # so a generous deadline costs nothing in the common case -- it only spends
    # time in the case that was about to report red.  Measured 2026-11-05 in
    # `_probe/_tmp/suites54.log`: `no_app reason ON SCREEN = False` for a page
    # that draws it, with `gold=0` after 150 s of retries while 198 other suites
    # had the box; the same probe run alone passes in seconds.  A gate that says
    # "the reason is not on screen" when it merely ran out of patience is the
    # same false red as pinning a spelling -- see `_测试钉子清单.md` 第 9 条.
    #
    # AND PATIENCE IS NOT THE POINT: progress is.  A flat deadline still guesses
    # how slow the box can get.  What the gate actually needs to know is whether
    # the page is STILL ARRIVING, so every capture that shows more gold than the
    # last one buys another 60 s, up to a hard 10 minutes.  A page that is truly
    # blank never buys anything and still fails in 300 s.
    HARD_STOP = time.time() + 600
    deadline = time.time() + 300
    # When the numbers stop moving the outcome is decided, and waiting out the
    # rest of the deadline only costs the suite ten minutes to say so.  Measured
    # 2026-11-06: a launch that drew the card but not the heading sat at the same
    # `gold=0 card=14598 page=59451` for the whole run.  25 s of no change after
    # the page has drawn is a verdict.
    CALM = 25.0
    moved_at = time.time()
    while time.time() < min(deadline, HARD_STOP) and (seen is None or seen["gold"] < 150):
        # The error page's CARD is up and has stopped changing: the verdict is
        # in.  This is the palette question on purpose -- `drawn()` turns true
        # when the SPLASH paints, which happens before the failure is navigated
        # to -- and it asks for the card's full footprint (CARD_MIN), because a
        # frame still arriving can show a few thousand card-coloured pixels and
        # would otherwise be judged as a finished page with no heading.
        if (seen is not None and painted(seen) >= CARD_MIN
                and time.time() - moved_at > CALM):
            break
        time.sleep(1.5)
        again = read_window(p.pid)
        if again is None:
            # The process is gone: no further read can succeed.
            if p.poll() is not None:
                break
            continue
        # "Still arriving" is two different signals and both deserve time: more
        # gold than last time (the page is drawing its text), or MORE OF THE
        # WINDOW IS NOW THE PAGE (it had not started at all).  The second one is
        # what a white window looks like, and under a loaded box that is the
        # normal state for the first tens of seconds.
        arrived = (again["gold"] > (seen or {}).get("gold", -1)
                   or painted(again) > painted(seen))
        if arrived:
            moved_at = time.time()
        if seen is None or arrived:
            if seen is not None and arrived:
                deadline = min(HARD_STOP, time.time() + 60)   # it is still painting
            seen = again
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


def run_drawn(name, exe, with_app, port, tries=3):
    """Launch until the window actually paints, then report that launch.

    A window WebView2 never drew has no pixels to classify: measured 2026-11-06
    as `gold=0 card=3 page=3` of 125,281 samples under a full suite run, against
    `gold=370 card=115863` for the identical fixture launched alone.  Waiting
    cannot help -- there is nothing arriving -- so the fixture is relaunched.
    Every attempt is killed before the next one starts, and the returned dict
    carries `launches` so the verdict names the cost.
    """
    last = None
    for i in range(tries):
        got = run(name, exe, with_app, port)
        got["launches"] = i + 1
        last = got
        # Only a window that never drew at all is worth relaunching.  A page that
        # painted its card and not its heading is a finding, and restarting it
        # would hide the finding behind a lucky second launch.
        if drawn(got["pixels"]):
            return got
        try:
            subprocess.run(["taskkill", "/PID", str(got["pid"]), "/T", "/F"],
                           capture_output=True)
        except Exception:
            pass
        if i + 1 < tries:
            print("  (window %s never drew: colours=%s, launching again)"
                  % (name, (got["pixels"] or {}).get("big")))
            time.sleep(1.0)
    return last


if __name__ == "__main__":
    out = []
    out.append(run_drawn("no_app_new", NEW_EXE, False, 3451))
    out.append(run_drawn("bundle_new", NEW_EXE, True, 3452))
    # A retry, not a second opinion: the first attempt can lose its 90 s to a
    # machine that is busy building something else, and the only claim at stake
    # is whether the splash carries its wrapping rule.  A fresh port, because a
    # half-started process from attempt one may still be holding the old one.
    nod = run_missing_data(3453)
    if not nod["wrapped"]:
        print("  (the splash was never fetched on the first try; retrying on a "
              "fresh port)")
        nod = run_missing_data(3454)

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
    # A control that never painted says nothing: `not looks_like_error(white)`
    # is True, so an undrawn window would certify any build.  Measured
    # 2026-11-06: three launches, page+card=121, "NOT an error page = True".
    control_drew = drawn(out[1]["pixels"])
    control_not_error = control_drew and not looks_like_error(out[1]["pixels"])
    control_ok = out[1]["port"] is not None
    print("=" * 74)
    print("VERDICT")
    print("  no_app   launches            = %d" % out[0].get("launches", 1))
    print("  no_app   data-url refused    = %s (must be False)" % out[0]["refused"])
    print("  no_app   reason ON SCREEN    = %s (must be True)" % reason_on_screen)
    # When this line goes red, the numbers are the difference between "the page
    # is blank" and "the camera was still warming up".  Print them with the
    # verdict instead of only above it: the suite log truncates each case.
    print("           no_app pixels       = %s" % (
        "UNREADABLE" if px is None else
        "gold=%d card=%d page=%d of %d sampled (colours=%d, flat=%.1f%%, %s)" % (
            px["gold"], px["card"], px["page"], px["n"], px.get("big", 0),
            px.get("flat", 0.0),
            "the page never drew" if not drawn(px) else "the page drew")))
    print("  bundle   launches            = %d" % out[1].get("launches", 1))
    print("  bundle   reached a port      = %s (must be True)" % control_ok)
    print("  bundle   NOT an error page   = %s (must be True)" % control_not_error)
    print("           bundle pixels       = %s" % (
        "UNREADABLE" if out[1]["pixels"] is None else
        "gold=%d card=%d page=%d of %d sampled (colours=%d, flat=%.1f%%, %s)" % (
            out[1]["pixels"]["gold"], out[1]["pixels"]["card"],
            out[1]["pixels"]["page"], out[1]["pixels"]["n"],
            out[1]["pixels"].get("big", 0), out[1]["pixels"].get("flat", 0.0),
            "the page never drew" if not drawn(out[1]["pixels"])
            else "the page drew")))
    data_reason = bool(nod["error"]) and ("找不到" in nod["error"] or "os error" in nod["error"])
    print("  no_data  splash says why     = %s (must be True)" % data_reason)
    print("  no_data  long path wraps     = %s (must be True)" % nod["wrapped"])
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "tmp_verify_errorpage.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    ok = (not out[0]["refused"] and reason_on_screen and control_ok
          and control_not_error and data_reason and nod["wrapped"])
    # The fixtures are throwaway copies of a 5.5 MB exe plus a 54 MB app folder;
    # the previous fixed sandbox grew to 3.6 GB because nothing removed it.
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(0 if ok else 1)
