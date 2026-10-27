# -*- coding: utf-8 -*-
"""Settle the two `log=False` cases: interrupted, or failed for real?

The handoff page says "真失败 + 弹窗没退", and that reading is plausible -- but
plausible is what the earlier probes also were. The distinction has an
observable consequence, so measure it:

  * 被打断 (interrupted): the process was alive and had not yet reached the
    line that writes the log. Reading again later would find bytes.
  * 真失败 at loader time: `main()` never ran, so `log()` was never called and
    NO amount of waiting produces bytes. The process can still be `alive=True`
    because Windows put up a modal dialog whose own message loop keeps the
    thread alive.

The two are told apart by a second reading much later, plus the exit code:
`0xC0000135` is STATUS_DLL_NOT_FOUND, which is decided before `main`.

Cases, all with the CURRENT exe (the native one -- there is no `runtime\\` any
more, so a case that stages `runtime\\` would be testing a folder this build
cannot produce):
  bare       exe only
  bare_dll   exe + WebView2Loader.dll, no app\\      -> must SHOW the reason
  full       exe + DLL + app\\                       -> control, must reach port
"""
import json
import os
import shutil
import socket
import subprocess
import time

EXE = r"D:\Software\AI\AGE2\desktop\src-tauri\target\release\aoe2-mod-workshop.exe"
BUNDLE = r"D:\Software\AI\AoE2ModWorkshop"
DLL = os.path.join(BUNDLE, "WebView2Loader.dll")
SANDBOX = r"D:\Software\AI\_pkgtest"
LOG = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "aoe2-mod-workshop.log")

EARLY = 0.35      # the old probe read here and called it log=False
LATE = 12.0       # a second reading, far past any plausible startup


def log_bytes_after(off):
    try:
        with open(LOG, "rb") as fh:
            fh.seek(off)
            return fh.read()
    except FileNotFoundError:
        return b""


def port_open(p):
    with socket.socket() as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", p)) == 0


def dialog_windows():
    """Modal error boxes owned by our exe. Absent dialog + dead process is a
    different story from absent dialog + live process."""
    ps = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process -Name aoe2-mod-workshop -ErrorAction SilentlyContinue | "
         "Select-Object Id,MainWindowTitle | ConvertTo-Json -Compress"],
        capture_output=True, text=True, timeout=30)
    return (ps.stdout or "").strip()


def stage(name):
    d = os.path.join(SANDBOX, "%s_%d" % (name, int(time.time() * 1000) % 10 ** 7))
    os.makedirs(d)
    shutil.copy2(EXE, os.path.join(d, "aoe2-mod-workshop.exe"))
    return d


def run(name, with_dll, with_app, port):
    d = stage(name)
    if with_dll:
        shutil.copy2(DLL, os.path.join(d, "WebView2Loader.dll"))
    if with_app:
        shutil.copytree(os.path.join(BUNDLE, "app"), os.path.join(d, "app"))

    off = os.path.getsize(LOG) if os.path.exists(LOG) else 0
    t0 = time.time()
    p = subprocess.Popen([os.path.join(d, "aoe2-mod-workshop.exe"), "--port", str(port)],
                         cwd=d)

    time.sleep(EARLY)
    early = len(log_bytes_after(off))
    early_alive = p.poll() is None

    m_port = None
    while time.time() - t0 < LATE:
        if m_port is None and port_open(port):
            m_port = round(time.time() - t0, 2)
            break
        if p.poll() is not None:
            break
        time.sleep(0.1)

    time.sleep(max(0.0, LATE - (time.time() - t0)))
    late = len(log_bytes_after(off))
    late_alive = p.poll() is None
    rc = p.poll()
    wins = dialog_windows() if late_alive else ""

    print("=" * 78)
    print("CASE %-9s dll=%-5s app=%-5s" % (name, with_dll, with_app))
    print("  @%.2fs  log=%-6s alive=%s" % (EARLY, early, early_alive))
    print("  @%.1fs log=%-6s alive=%s  port=%s" % (LATE, late, late_alive, m_port))
    print("  exit code           : %s%s" % (
        rc, "  (0x%08X)" % (rc & 0xFFFFFFFF) if isinstance(rc, int) and rc else ""))
    print("  windows while alive : %s" % (wins[:200] or "(none -- process gone)"))
    for ln in log_bytes_after(off).decode("utf-8", "replace").splitlines()[:6]:
        print("  | " + ln[:170])

    verdict = "?"
    if late == 0 and rc == 0xC0000135:
        verdict = "真失败 at loader (DLL 缺失), main() 从未运行"
    elif late == 0 and late_alive:
        verdict = "卡在弹窗, main() 从未运行"
    elif late > 0 and m_port:
        verdict = "正常"
    elif late > 0:
        verdict = "起来了但没到端口"
    print("  VERDICT: %s" % verdict)

    if late_alive:
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    return {"case": name, "early": early, "late": late, "rc": rc,
            "port": m_port, "verdict": verdict, "dir": d}


if __name__ == "__main__":
    out = [run("bare", False, False, 3471),
           run("bare_dll", True, False, 3472),
           run("full", True, True, 3473)]
    print("=" * 78)
    print("A 项结论")
    print("  bare      日志@0.35s=%s  最终=%s  exit=%s  -> %s"
          % (out[0]["early"], out[0]["late"], out[0]["rc"], out[0]["verdict"]))
    print("  bare_dll  日志@0.35s=%s  最终=%s  exit=%s  -> %s"
          % (out[1]["early"], out[1]["late"], out[1]["rc"], out[1]["verdict"]))
    print("  full      日志@0.35s=%s  最终=%s  port=%s -> %s"
          % (out[2]["early"], out[2]["late"], out[2]["port"], out[2]["verdict"]))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "tmp_settle_logfalse.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
