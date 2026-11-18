# -*- coding: utf-8 -*-
"""The shipped program must run the engine the repository runs.

WHY THIS EXISTS
---------------
The window shell is a Rust program (`desktop/src-tauri`) and there used to be a
second, native engine inside it.  That engine was a subset: five of fourteen
sentence families, eight routes missing, an eighty-kilobyte-older page.  So a
player who double-clicked the release got a dumber tool than a developer who ran
`tools/run_ui.py` -- and every suite in this folder passed, because they all
started the Python engine.

The decision this pins: **the shell runs the Python engine when one is present**
(`engine_root()` in `desktop/src-tauri/src/main.rs`), and the native engine is
only the fallback for a machine that has no `app/` at all.

The second thing pinned here is the watchdog.  `TerminateProcess` -- which is
what a force-kill, Task Manager's "end task", and `proc.terminate()` all are --
never delivers `WM_CLOSE`, so the shell's own exit handler never runs.  Measured
2026-10-30: a dozen force-killed shells left a dozen 1 GB interpreters holding
ports.  So the child watches its parent and dies with it.

Run:  python -X utf8 _probe/test_shell_engine.py
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import _paths as P

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

MAIN_RS = os.path.join(ROOT, "desktop", "src-tauri", "src", "main.rs")
RUN_UI = os.path.join(ROOT, "tools", "run_ui.py")
BUNDLE = P.BUNDLE
FAILS = []


def check(label, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                         (" :: " + detail) if (detail and not ok) else ""))
    if not ok:
        FAILS.append(label)
    return ok


def eq(label, got, want):
    return check("%s :: %r" % (label, want) if got != want else label,
                 got == want, "" if got == want else "got %r" % (got,))


def free_port(start=7960):
    for p in range(start, start + 40):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    raise RuntimeError("no free port")


def port_open(port):
    s = socket.socket()
    s.settimeout(0.4)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def meta(port):
    with urllib.request.urlopen("http://127.0.0.1:%d/api/meta" % port,
                                timeout=3) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    src = open(MAIN_RS, encoding="utf-8").read()

    print("\n=== 1. the shell prefers the Python engine ===")
    check("main.rs has an engine_root()", "fn engine_root(" in src)
    check("it looks for tools/run_ui.py, not for a second engine's data",
          'join("tools").join("run_ui.py")' in src, "searched for run_ui.py")
    # The whole point of the function: if a Python engine is present, use it.
    check("and the found root is used to spawn python",
          "spawn_python" in src, "spawn_python")
    check("the native engine is only the else-branch",
          re.search(r"if\s+let\s+Some\([^)]*\)\s*=\s*engine", src) is not None
          or "engine_root(&root)" in src, "engine_root(&root)")

    print("\n=== 2. the child is told to serve only, and who its parent is ===")
    check("--serve-only is passed", '"--serve-only"' in src)
    check("--parent-pid is passed", '"--parent-pid"' in src)
    check("with the shell's own pid",
          "std::process::id()" in src, "std::process::id()")
    # A console window flashing up behind a GUI app is the classic Windows bug.
    check("no console window is created", "CREATE_NO_WINDOW" in src)

    print("\n=== 3. run_ui.py understands both flags ===")
    ui = open(RUN_UI, encoding="utf-8").read()
    check("--serve-only is a real argument", '"--serve-only"' in ui)
    check("--parent-pid is a real argument", '"--parent-pid"' in ui)
    check("it records the pid before any thread can read it",
          "AOE2MOD_PARENT_PID" in ui)
    check("and it watches that pid", "def _watch_parent(" in ui)
    check("falling back to getppid() when the flag is absent",
          "getppid()" in ui)
    # Returning True on any doubt matters: a false "dead" would kill a server the
    # player is using, which is worse than a stale process.
    check("the liveness check errs toward alive",
          "ERROR_INVALID_PARAMETER" in ui and "!= 87" in ui)

    print("\n=== 4. the shipped folder really contains a Python engine ===")
    exe = os.path.join(BUNDLE, "AoE2 DE Mod Workshop.exe")
    app = os.path.join(BUNDLE, "app")
    if not os.path.isfile(exe):
        print("  --  no shipped bundle at %s, skipping the launch checks" % BUNDLE)
        print("      (`_probe/make_bundle.py --force` produces one)")
    else:
        check("the bundle carries app/tools/run_ui.py",
              os.path.isfile(os.path.join(app, "tools", "run_ui.py")))
        check("and app/aoe2mod/", os.path.isdir(os.path.join(app, "aoe2mod")))
        check("and runtime/python.exe",
              os.path.isfile(os.path.join(BUNDLE, "runtime", "python.exe")))
        # engine_root() starts from the exe's own directory, so `app` beside the
        # exe IS what makes the shipped program run Python.  A bundle without it
        # silently falls back to the native engine.
        check("app/ sits beside the exe, which is where engine_root looks",
              os.path.isdir(app))

        print("\n=== 5. the watchdog: the child dies with its parent ===")
        port = free_port()
        if port_open(port):
            print("  REFUSING: port %d is already in use" % port)
            return 1
        # A parent that does nothing but live, so the child has something to
        # watch.  Started with a real process id; `TerminateProcess` on it is
        # exactly the case the shell's own exit handler cannot cover.
        parent = subprocess.Popen([sys.executable, "-c",
                                   "import time; time.sleep(600)"])
        env = dict(os.environ)
        env.pop("AOE2MOD_PARENT_PID", None)
        child = subprocess.Popen(
            [sys.executable, "-X", "utf8", "-u", RUN_UI,
             "--serve-only", "--port", str(port), "--parent-pid", str(parent.pid)],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True)
        try:
            ready = False
            deadline = time.time() + 150
            while time.time() < deadline:
                if child.poll() is not None:
                    break
                try:
                    m = meta(port)
                    ready = bool(m.get("ok"))
                    if ready:
                        break
                except Exception:                       # noqa: BLE001
                    pass
                time.sleep(0.5)
            check("the engine came up and answered /api/meta", ready,
                  "child exited early" if child.poll() is not None else "timed out")
            check("it is serving the page's own engine",
                  ready and bool((meta(port) or {}).get("intents")),
                  "no intents in /api/meta")
            # Kill the parent the way a force-quit does: no WM_CLOSE, no
            # graceful notice, no chance for the shell to clean up.
            parent.terminate()
            parent.wait(timeout=30)
            gone = False
            deadline = time.time() + 45
            while time.time() < deadline:
                if child.poll() is not None:
                    gone = True
                    break
                time.sleep(0.5)
            check("the child notices and exits", gone,
                  "still running as pid %s" % child.pid)
            # The port is the reason this matters: a survivor holds it, and the
            # next start talks to the stale engine.
            freed = False
            deadline = time.time() + 20
            while time.time() < deadline:
                if not port_open(port):
                    freed = True
                    break
                time.sleep(0.3)
            check("and releases the port", freed, "port %d still bound" % port)
        finally:
            for p in (child, parent):
                try:
                    if p.poll() is None:
                        p.kill()
                        p.wait(timeout=20)
                except Exception:                       # noqa: BLE001
                    pass

    print()
    if FAILS:
        print("SHELL ENGINE: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("SHELL ENGINE: THE SHELL RUNS THE REPOSITORY'S ENGINE, AND ITS CHILD "
          "DIES WITH IT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
