# -*- coding: utf-8 -*-
"""What exactly does the `python` on PATH do when it is the Store stub?

`spawn_server` treats "spawn() returned Ok" as success, and then `wait_ready`
polls for 150 s.  The stub is the reason that can go wrong, so measure it:
how long it lives, what it exits with, and whether the Microsoft Store window
opens (which would be another silent symptom on a player's machine).
"""
import os
import shutil
import subprocess
import sys
import time

print("python on PATH:", shutil.which("python"))
print("python3 on PATH:", shutil.which("python3"))

for name in ("python", "python3"):
    exe = shutil.which(name)
    if not exe:
        continue
    try:
        size = os.path.getsize(exe)
    except OSError as exc:
        size = "? (%s)" % exc
    print("\n=== %s -> %s (%s bytes) ===" % (name, exe, size))
    t0 = time.time()
    p = subprocess.Popen([exe, "-X", "utf8", "-u", "-c", "print('alive')"],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # how fast does it die?
    marks = []
    for _ in range(200):                       # up to 20 s
        rc = p.poll()
        if rc is not None:
            marks.append(("exit", rc, round(time.time() - t0, 3)))
            break
        time.sleep(0.1)
    else:
        marks.append(("still running after 20 s", None, 20.0))
        p.kill()
    try:
        out, err = p.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = b"", b""
    for what, rc, when in marks:
        if what == "exit":
            print("  %s after %.3f s, code=%r (0x%08X)"
                  % (what, when, rc, rc & 0xFFFFFFFF if rc is not None else 0))
        else:
            print("  %s" % what)
    print("  stdout:", (out or b"")[:200])
    print("  stderr:", (err or b"")[:300])

# And the thing spawn_server actually does: run tools/run_ui.py --serve-only
print("\n=== the real invocation, via the PATH stub ===")
stub = shutil.which("python")
if stub:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    t0 = time.time()
    p = subprocess.Popen([stub, "-X", "utf8", "-u", "tools/run_ui.py",
                          "--serve-only", "--port", "3481"],
                         cwd=root, stdout=subprocess.DEVNULL,
                         stderr=subprocess.PIPE)
    rc = None
    for _ in range(150):
        rc = p.poll()
        if rc is not None:
            break
        time.sleep(0.1)
    print("  exited=%r after %.3f s" % (rc, time.time() - t0))
    if p.poll() is None:
        p.kill()
