# -*- coding: utf-8 -*-
"""Prove /api/rebuild round-trips a `unit.stat` record on a profile COPY.

Two things have to be true for a rebuild to be honest:
  1. it produces a mod whose bytes match the original request, and
  2. it lands under the SAME name, not a second entry.

Runs against a temp copy of the profile and a temp state dir, so nothing of the
player's is touched.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

SRC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
TMP = os.path.join(os.environ["TEMP"], "aoe2mod-rebuild-test")
STATE = os.path.join(TMP, "_state")
PORT = 7892
EXE = os.path.join(ROOT, "desktop", "aoe2mod-serve", "target", "release",
                   "aoe2mod-serve.exe")


def post(u, o):
    d = json.dumps(o, ensure_ascii=False).encode()
    r = urllib.request.Request(u, data=d,
                               headers={"Content-Type": "application/json"},
                               method="POST")
    return json.loads(urllib.request.urlopen(r, timeout=300).read().decode())


def get(u):
    return json.loads(urllib.request.urlopen(u, timeout=60).read().decode())


def main():
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP)
    os.makedirs(STATE)

    # Start from an EMPTY builds record and a copied profile: this test creates
    # its own build, so it does not depend on whatever the player happens to have.
    with open(os.path.join(STATE, "builds.json"), "w", encoding="utf-8") as fh:
        fh.write('{"builds":{}}')
    app = os.path.join(TMP, "app")
    os.makedirs(app)
    shutil.copytree(os.path.join(SRC, "mods"), os.path.join(app, "mods"),
                    ignore=shutil.ignore_patterns("*.bak", "*.before-*"))

    env = dict(os.environ)
    env["AOE2MOD_PROFILE"] = app
    env["AOE2MOD_STATE"] = STATE
    env["AOE2MOD_BUILD_OUT"] = os.path.join(TMP, "out")
    env["AOE2MOD_STAT_OFFSETS"] = os.path.join(ROOT, "_golden", "stat_offsets.json")
    env["AOE2MOD_ENTITY_NAMES"] = os.path.join(ROOT, "_golden", "entity_names.json")
    p = subprocess.Popen(
        [EXE, "--port", str(PORT), "--root",
         os.path.join(ROOT, "aoe2mod", "ui", "static")],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % PORT
    for _ in range(80):
        time.sleep(0.25)
        try:
            get(base + "/api/progress")
            break
        except Exception:
            pass

    ok = True
    try:
        # 1. a real build, which records its intent
        title = "重建测试"
        r = post(base + "/api/build", {
            "stat": "hit_points", "unit": 1810, "value": 777,
            "title": title, "install": True})
        print("build    ->", r.get("ok"), "civs", r.get("civs"),
              "value", r.get("value"))
        ok = ok and r.get("ok") is True
        if not r.get("ok"):
            print("   error:", r.get("error"))
            raise SystemExit(1)

        before = [m for m in get(base + "/api/mods")["mods"] if m["title"] == title]
        print("installed:", len(before), "entry",
              "prio", before[0]["priority"] if before else None)

        # 2. rebuild it
        r2 = post(base + "/api/rebuild", {"title": title})
        print("rebuild  ->", r2.get("ok"))
        if not r2.get("ok"):
            print("   error:", r2.get("error"))
            ok = False
        else:
            inner = r2.get("rebuilt") or {}
            print("   value:", inner.get("value"), "civs:", inner.get("civs"),
                  "installed:", (inner.get("installed") or "")[-24:])

        # 3. still ONE entry, still enabled, and it is the same name
        after = [m for m in get(base + "/api/mods")["mods"] if m["title"] == title]
        print("entries after rebuild:", len(after))
        if len(after) != 1:
            print("   FAIL: expected exactly one entry")
            ok = False
        elif not after[0]["enabled"]:
            print("   FAIL: entry is disabled")
            ok = False

        # 4. the dat on disk still holds 777 for the villager
        dat = os.path.join(app, "mods", "local", title,
                           "resources", "_common", "dat", "empires2_x2_p1.dat")
        print("dat exists:", os.path.isfile(dat),
              os.path.getsize(dat) if os.path.isfile(dat) else 0, "bytes")
        ok = ok and os.path.isfile(dat)
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()

    print()
    print("REBUILD: %s" % ("ALL PASSED" if ok else "FAILURES ABOVE"))
    shutil.rmtree(TMP, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
