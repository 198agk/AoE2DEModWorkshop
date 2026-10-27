# -*- coding: utf-8 -*-
"""Exercise the mod-mutation routes against a COPY of the profile.

A test that edits the player's real `mod-status.json` cannot be safely repeated,
and this project has already paid once for writing a phantom entry into it. So
the whole profile is copied to a temp dir and `AOE2MOD_PROFILE` points there.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

SRC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
TMP = os.path.join(os.environ["TEMP"], "aoe2mod-profile-test")
PORT = 7861
EXE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "desktop",
    "aoe2mod-serve", "target", "release", "aoe2mod-serve.exe"))


def post(u, o):
    d = json.dumps(o, ensure_ascii=False).encode()
    r = urllib.request.Request(u, data=d,
                               headers={"Content-Type": "application/json"},
                               method="POST")
    return json.loads(urllib.request.urlopen(r, timeout=180).read().decode())


def get(u):
    return json.loads(urllib.request.urlopen(u, timeout=30).read().decode())


def main():
    if not os.path.isdir(SRC):
        print("REFUSING: no profile at", SRC)
        return 1
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    # Copy only what the routes touch: mod-status.json and the mods/ tree.
    os.makedirs(TMP)
    shutil.copytree(os.path.join(SRC, "mods"), os.path.join(TMP, "mods"),
                    ignore=shutil.ignore_patterns("*.bak", "*.before-*"))
    print("copied profile ->", TMP)

    env = dict(os.environ)
    env["AOE2MOD_PROFILE"] = TMP
    env["AOE2MOD_STAT_OFFSETS"] = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "_golden",
        "stat_offsets.json"))
    p = subprocess.Popen(
        [EXE, "--port", str(PORT), "--root",
         os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", "aoe2mod", "ui", "static"))],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % PORT
    for _ in range(60):
        time.sleep(0.25)
        try:
            get(base + "/api/progress")
            break
        except Exception:
            pass

    ok = True
    try:
        mods = get(base + "/api/mods")["mods"]
        print("initial mods:", len(mods))
        target = next(m for m in mods if m["kind"] == "local")
        print("target:", target["name"], "enabled=", target["enabled"])

        # 1. toggle off
        r = post(base + "/api/mod", {"name": target["name"], "enabled": False})
        after = [m for m in r["mods"] if m["name"] == target["name"]][0]
        print("toggle off ->", after["enabled"], "ok" if not after["enabled"] else "FAIL")
        ok = ok and (after["enabled"] is False)

        # 2. toggle back on
        r = post(base + "/api/mod", {"name": target["name"], "enabled": True})
        after = [m for m in r["mods"] if m["name"] == target["name"]][0]
        print("toggle on  ->", after["enabled"], "ok" if after["enabled"] else "FAIL")
        ok = ok and (after["enabled"] is True)

        # 3. a name that does not exist must be REFUSED, not created
        r = post(base + "/api/mod", {"name": "__no_such_mod__", "enabled": True})
        print("ghost toggle ->", "ok" if not r.get("ok") else "FAIL (created it)")
        ok = ok and (not r.get("ok"))
        names = [m["name"] for m in get(base + "/api/mods")["mods"]]
        if "__no_such_mod__" in names:
            print("  PHANTOM ENTRY APPEARED")
            ok = False

        # 4. move down then up
        before = [m["name"] for m in get(base + "/api/mods")["mods"]]
        r = post(base + "/api/mod-move", {"name": before[0], "delta": 1})
        mid = [m["name"] for m in r["mods"]]
        moved = mid[0] == before[1] and mid[1] == before[0]
        print("move down  ->", "ok" if moved else "FAIL")
        ok = ok and moved
        r = post(base + "/api/mod-move", {"name": before[0], "delta": -1})
        back = [m["name"] for m in r["mods"]]
        print("move up    ->", "ok" if back == before else "FAIL")
        ok = ok and (back == before)

        # 5. priorities must be 1..n, which is what the engine reads
        rows = get(base + "/api/mods")["mods"]
        pris = [m["priority"] for m in rows]
        seq = pris == list(range(1, len(rows) + 1))
        print("priorities ->", "ok" if seq else "FAIL %r" % pris)
        ok = ok and seq

        # 6. uninstall a mod we make ourselves, so nothing of the player's goes
        made = os.path.join(TMP, "mods", "local", "临时测试")
        os.makedirs(os.path.join(made, "resources", "_common", "dat"))
        with open(os.path.join(made, "info.json"), "w", encoding="utf-8") as fh:
            fh.write('{"Author":"t","CacheStatus":0,"Description":"","Title":"临时测试"}')
        rows = get(base + "/api/mods")["mods"]
        print("mods after adding on disk:", len(rows))
        r = post(base + "/api/uninstall", {"name": "临时测试"})
        gone = not os.path.isdir(made)
        print("uninstall  ->", "removed" if gone else "FAIL (folder still there)")
        ok = ok and gone and r.get("ok")
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()

    print()
    print("MOD ROUTES: %s" % ("ALL PASSED" if ok else "FAILURES ABOVE"))
    shutil.rmtree(TMP, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
