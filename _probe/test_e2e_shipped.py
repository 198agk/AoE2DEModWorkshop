# -*- coding: utf-8 -*-
"""End to end through the SHIPPED program: sentence -> build -> install.

This is the test that matters, and the one that has been missing. Every earlier
check proved one endpoint; the four "all green, wrong artefact" failures in this
session were all joins -- stale exe, missing tables, loaders that could not see
`app/_golden`. So this drives the shipped binary only, with the player's profile
swapped for a copy.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import _paths as P

OUT = P.BUNDLE
EXE = os.path.join(OUT, "aoe2-mod-workshop.exe")
SRC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
TMP = os.path.join(os.environ["TEMP"], "aoe2mod-e2e-shipped")
PORT = 7807


def post(path, obj):
    d = json.dumps(obj, ensure_ascii=False).encode()
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=d,
                               headers={"Content-Type": "application/json"},
                               method="POST")
    return json.loads(urllib.request.urlopen(r, timeout=300).read().decode())


def get(path):
    return json.loads(
        urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, path),
                               timeout=120).read().decode())


def main():
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP)
    prof = os.path.join(TMP, "profile")
    os.makedirs(prof)
    shutil.copytree(os.path.join(SRC, "mods"), os.path.join(prof, "mods"),
                    ignore=shutil.ignore_patterns("*.bak", "*.before-*"))

    env = dict(os.environ)
    env["AOE2MOD_PROFILE"] = prof
    # A throwaway build record, so the run cannot touch the player's builds.json.
    state = os.path.join(TMP, "state")
    os.makedirs(state)
    env["AOE2MOD_STATE"] = state
    with open(os.path.join(state, "builds.json"), "w", encoding="utf-8") as fh:
        fh.write('{"builds":{}}')

    subprocess.run(["taskkill", "/IM", "aoe2-mod-workshop.exe", "/F"],
                   capture_output=True)
    time.sleep(1)
    p = subprocess.Popen([EXE, "--port", str(PORT)], cwd=OUT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = True

    def note(name, good, detail=""):
        nonlocal ok
        print("  %-30s %s%s" % (name, "ok" if good else "FAIL", detail))
        if not good:
            ok = False

    try:
        # Wait for READY, not merely for the port: `/api/progress` answers in
        # milliseconds from the moment the socket binds, while `parsed` is only
        # filled after the 93 MB walk. Waiting on the port made the first build
        # in this test fail with "游戏数据还没读完" -- a correct refusal, and a
        # test that measured its own impatience.
        for _ in range(240):
            time.sleep(0.25)
            try:
                pr = get("/api/progress")
                if (pr.get("progress") or {}).get("ready"):
                    break
            except Exception:
                pass

        # 1. a unit sentence, one call, no explicit intent
        pr = post("/api/parse", {"text": "村民血量改成1000"})
        it = (pr.get("intents") or [{}])[0]
        note("parse unit", it.get("intent") == "unit.stat", " %s" % it)

        # 2. build + install from that sentence's intent
        b = post("/api/build", {
            "stat": it.get("stat"), "unit": it.get("unit"),
            "value": it.get("value"), "title": "E2E村民血量", "install": True})
        note("build unit", b.get("ok") is True,
             " civs=%s value=%s err=%s" % (b.get("civs"), b.get("value"), b.get("error")))

        rows = [m for m in get("/api/mods")["mods"] if m["title"] == "E2E村民血量"]
        note("installed once", len(rows) == 1,
             " prio=%s" % (rows[0]["priority"] if rows else None))

        # 3. a TECH sentence and build
        tp = post("/api/parse", {"text": "织布机研究时间改成5"})
        ti = (tp.get("intents") or [{}])[0]
        note("parse tech", ti.get("intent") == "tech.research_time", " %s" % ti)
        tb = post("/api/build", {
            "intent": ti.get("intent"), "tech": ti.get("tech"),
            "value": ti.get("value"), "title": "E2E织布机速度", "install": True})
        note("build tech", tb.get("ok") is True,
             " locations=%s %s->%s" % (tb.get("locations"), tb.get("before"),
                                       tb.get("value")))

        # 4. the dat actually landed, at the size a data mod has
        dat = os.path.join(prof, "mods", "local", "E2E织布机速度",
                           "resources", "_common", "dat", "empires2_x2_p1.dat")
        size = os.path.getsize(dat) if os.path.isfile(dat) else 0
        note("tech dat on disk", 11_000_000 < size < 13_000_000,
             " %d bytes" % size)

        # 5. update-check sees both as current (they were just built)
        u = get("/api/update-check")
        mine = [r for r in (u.get("rows") or [])
                if r["title"] in ("E2E村民血量", "E2E织布机速度")]
        states = {r["title"]: r["status"] for r in mine}
        note("update-check knows them", len(mine) == 2, " %s" % states)
        note("both current", all(s == "current" for s in states.values()),
             " %s" % states)

        # 6. toggle one off, then rebuild it
        t = post("/api/mod", {"name": "E2E村民血量", "enabled": False})
        off = [m for m in t["mods"] if m["name"] == "E2E村民血量"]
        note("toggle off", bool(off) and off[0]["enabled"] is False)
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()

    print()
    print("SHIPPED E2E: %s" % ("ALL PASSED" if ok else "FAILURES ABOVE"))
    shutil.rmtree(TMP, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
