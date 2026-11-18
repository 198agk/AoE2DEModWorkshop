# -*- coding: utf-8 -*-
"""End to end through the SHIPPED program: sentence -> build -> install.

This is the test that matters, and the one that has been missing. Every earlier
check proved one endpoint; the four "all green, wrong artefact" failures in this
session were all joins -- stale exe, missing tables, loaders that could not see
`app/_golden`. So this drives the shipped binary only, with the player's profile
swapped for a copy.
"""
import json
import _gamepaths as GP
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import _paths as P

OUT = P.BUNDLE
EXE = os.path.join(OUT, "AoE2 DE Mod Workshop.exe")
SRC = GP.ACCOUNT
TMP = os.path.join(os.environ["TEMP"], "aoe2mod-e2e-shipped")
PORT = 7807
# An 8x8 red square as base64 PNG: a preview and a build need a decodable
# picture and nothing else, and a file on disk would make this test depend on
# a path that only exists on this machine.
TINY_PNG_B64 = ("iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAEklEQVR42mP4"
                "z8DwHx9mGBkKAMLXf4HVAzL9AAAAAElFTkSuQmCC")


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


def kill_engine_child():
    """Kill the shipped runtime python this exe started, if it outlived it.

    `taskkill /IM AoE2 DE Mod Workshop.exe` kills the shell only.  The child python
    keeps the listening socket for a few more seconds, and because Windows lets a
    second socket bind a port the dying one still accepts on, a request can land
    on the corpse.  The child is identified by executable path, never by image
    name -- `python.exe` is also the name of the interpreter running this test.
    """
    exe_dir = os.path.dirname(os.path.abspath(os.path.join(OUT, "x")))
    script = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
              "Where-Object { $_.ExecutablePath -like '" + exe_dir + "*' } | "
              "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    subprocess.run(["powershell", "-NoProfile", "-Command", script],
                   capture_output=True)


def port_free(port, secs=60):
    """Block until nothing holds a LISTEN socket on `port`."""
    cmd = ("(Get-NetTCPConnection -LocalPort %d -State Listen " % port
           + "-ErrorAction SilentlyContinue | Measure-Object).Count")
    t0 = time.time()
    while time.time() - t0 < secs:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                             capture_output=True, text=True)
        try:
            busy = int(out.stdout.strip().split()[0]) > 0
        except Exception:
            busy = False
        if not busy:
            return True
        time.sleep(1)
    return False


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

    subprocess.run(["taskkill", "/IM", "AoE2 DE Mod Workshop.exe", "/F"],
                   capture_output=True)
    kill_engine_child()
    port_free(PORT)
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
        ready = False
        for _ in range(240):
            time.sleep(0.25)
            try:
                pr = get("/api/progress")
                if (pr.get("progress") or {}).get("ready"):
                    ready = True
                    break
            except Exception:
                pass
        # Say it out loud.  A silent wait loop turns "the engine never came up"
        # into an exception at the first request, and the report then blames the
        # product instead of the launch.
        note("engine reached READY", ready)
        if not ready:
            raise SystemExit(1)

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

        # 7. A PICTURE, END TO END, THROUGH THE SHIPPED PROGRAM.
        # The player's complaint on 2026-11-11 was that one icon cost two mod
        # folders to enable.  A record that keeps the slot it already names
        # writes no .dat byte, so this save must produce ONE folder with no
        # .dat and no `_ui` sibling.  Asserted on the disk the program wrote,
        # not on the answer's own claim.
        icp = post("/api/icon-set", {"kind": "unit", "record": 74,
                                     "civ": "British", "dry": False,
                                     "filename": "gate.png",
                                     "data_b64": TINY_PNG_B64})
        note("icon-set writes in place", icp.get("ok") is True
             and icp.get("mode") == "inplace"
             and icp.get("record_unchanged") is True,
             " 槽 %s，待保存 %s" % (icp.get("slot"), icp.get("pending")))
        sv = post("/api/session-save", {"title": "E2E图标一个文件夹",
                                        "install": False})
        one = sv.get("built") or ""
        sib = one + "_ui"
        dats = os.path.join(one, "resources", "_common", "dat",
                            "empires2_x2_p1.dat")
        tex = os.path.join(one, "widgetui", "textures", "ingame", "units")
        note("icon save is ONE folder", sv.get("ok") is True
             and one and os.path.isdir(one)
             and not os.path.isdir(sib)
             and not os.path.isfile(dats)
             and os.path.isdir(tex),
             " %s（无 .dat、无 _ui 兄弟目录）dat=%s tex=%s sib=%s ok=%s"
             % (os.path.basename(one or "?"), os.path.isfile(dats),
                os.path.isdir(tex), os.path.isdir(sib), sv.get("ok")))
        note("icon save reports no ui half", sv.get("ui_mod_dir") is None
             and (sv.get("info") or {}).get("Title") == "E2E图标一个文件夹",
             " 标题 %s" % ((sv.get("info") or {}).get("Title"),))
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
