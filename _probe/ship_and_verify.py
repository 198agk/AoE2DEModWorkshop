# -*- coding: utf-8 -*-
"""Ship the measured tables, and prove every route answers from the shipped copy.

The defect this fixes
--------------------
The bundle carried `app/aoe2mod/ui/static` and `app/aoe2mod/schema`, and nothing
else. So in the SHIPPED program:

  * `/api/parse` answered "名字表没有随程序发布，认不出这句话说的是哪个单位";
  * `/api/build` answered "读不到 _golden/stat_offsets.json";
  * `/api/ai-meta` produced an empty grammar.

All three are correct refusals of a missing file, and all three mean the product
does not work. They were invisible because every route had been verified against
the DEVELOPMENT binary, whose cwd happened to walk up into the repo.

What ships, and why each is data rather than code
-------------------------------------------------
  stat_offsets.json   19 MB, regenerable in ~40 s by make_stat_offsets.py, and
                      measured by `locate` rather than written by hand
  entity_names.json   135 KB, exported from the semantic index
  ai_grammar.json     3 KB, exported from the reader

They go to `app/` because that is the folder the exe treats as its root, and the
loader walks up from there. `stat_offsets.json` is 19 MB; shipping it keeps the
program correct without a Python step at first run, which is the point of this
whole exercise.
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
OUT = r"D:\Software\AI\AoE2ModWorkshop"
GOLDEN = ["stat_offsets.json", "entity_names.json", "ai_grammar.json",
          "tech_offsets.json", "effect_offsets.json", "command_cards.json", "class_names.json", "sprite_pairs.json"]


def install_tables(app_dir):
    dst_dir = os.path.join(app_dir, "_golden")
    os.makedirs(dst_dir, exist_ok=True)
    total = 0
    for name in GOLDEN:
        src = os.path.join(ROOT, "_golden", name)
        if not os.path.isfile(src):
            print("REFUSING: missing %s (run the make_* probe)" % src)
            return None
        dst = os.path.join(dst_dir, name)
        shutil.copy2(src, dst)
        total += os.path.getsize(dst)
        print("  %-20s %8.1f KB" % (name, os.path.getsize(dst) / 1024.0))
    return total


def check_routes(port):
    base = "http://127.0.0.1:%d" % port
    def get(path):
        return urllib.request.urlopen(base + path, timeout=120).read()

    def post(path, obj):
        d = json.dumps(obj, ensure_ascii=False).encode()
        r = urllib.request.Request(base + path, data=d,
                                   headers={"Content-Type": "application/json"},
                                   method="POST")
        return json.loads(urllib.request.urlopen(r, timeout=300).read().decode())

    ok = True

    def note(name, good, detail=""):
        nonlocal ok
        print("  %-22s %s%s" % (name, "ok" if good else "FAIL", detail))
        if not good:
            ok = False

    m = json.loads(get("/api/meta"))
    note("/api/meta", m.get("ok") and len(m.get("civs") or []) == 63,
         " civs=%d" % len(m.get("civs") or []))
    p = json.loads(get("/api/progress"))
    note("/api/progress", (p.get("progress") or {}).get("ready") is True)

    pr = post("/api/parse", {"text": "村民血量改成1000"})
    got = (pr.get("intents") or [])
    note("/api/parse", bool(got) and got[0].get("stat") == "hit_points",
         " intents=%d" % len(got))
    if not got:
        print("      refusal:", pr.get("refusals"))

    f = json.loads(get("/api/forms"))
    note("/api/forms", len(f.get("forms") or []) == 23,
         " forms=%d" % len(f.get("forms") or []))
    l = json.loads(get("/api/locale?locale=zh"))
    note("/api/locale", len(l.get("strings") or {}) == 55,
         " keys=%d" % len(l.get("strings") or {}))

    try:
        mods = json.loads(get("/api/mods"))
    except Exception as exc:
        print("      /api/mods raised:", exc)
        mods = {}
        ok = False
    note("/api/mods", mods.get("ok") is True,
         " rows=%d" % len(mods.get("mods") or []))

    ic = get("/api/icon?kind=unit&id=15&section=Units&max=64")
    note("/api/icon", ic[:4] == b"\x89PNG", " %d bytes" % len(ic))

    br = json.loads(get("/api/browse?kind=unit&limit=5"))
    note("/api/browse", (br.get("browse") or {}).get("total") == 1651,
         " total=%s" % (br.get("browse") or {}).get("total"))

    cd = json.loads(get("/api/card?building=12"))
    note("/api/card", cd.get("box_count") == 4 and cd.get("unit_count") == 49,
         " 兵营 %s 格 %s 单位" % (cd.get("box_count"), cd.get("unit_count")))

    mv = post("/api/card-move", {"unit": 74, "building": 12, "box": 5,
                                  "title": "gate-card-move"})
    note("/api/card-move", mv.get("ok") is True and mv.get("bytes_changed") == 1,
         " %s->%s" % (mv.get("before"), mv.get("after")))

    d = json.loads(get("/api/describe?kind=unit&id=1810"))
    note("/api/describe", (d.get("entity") or {}).get("name") == "村民")

    ai = json.loads(get("/api/ai-meta"))
    note("/api/ai-meta", len(ai.get("grammar") or "") > 500,
         " grammar=%d chars" % len(ai.get("grammar") or ""))

    tp = post("/api/parse", {"text": "织布机研究时间改成5"})
    ti = (tp.get("intents") or [])
    note("/api/parse (tech)", bool(ti) and ti[0].get("intent") == "tech.research_time",
         " %r" % (ti[0] if ti else tp.get("refusals")))

    u = json.loads(get("/api/update-check"))
    note("/api/update-check", u.get("ok") is True,
         " rows=%d" % len(u.get("rows") or []))

    return ok


def main():
    app = os.path.join(OUT, "app")
    if not os.path.isdir(app):
        print("REFUSING: no bundle at", OUT)
        return 1
    print("installing tables into", os.path.join(app, "_golden"))
    total = install_tables(app)
    if total is None:
        return 1
    print("  total %.1f MB" % (total / (1024.0 * 1024.0)))
    # Every table the engine reads must be present: a missing one does not crash,
    # it silently changes behaviour -- "步弓手对骑兵攻击加2" fell through to
    # unit.stat when class_names.json was absent from the bundle.
    golden_dir = os.path.join(app, "_golden")
    have = set(os.listdir(golden_dir)) if os.path.isdir(golden_dir) else set()
    missing = [g for g in GOLDEN if g not in have]
    if missing:
        print("  FAIL missing tables: %s" % missing)
        return 1
    print("  all %d tables present" % len(GOLDEN))

    exe = os.path.join(OUT, "aoe2-mod-workshop.exe")
    subprocess.run(["taskkill", "/IM", "aoe2-mod-workshop.exe", "/F"],
                   capture_output=True)
    time.sleep(1)
    p = subprocess.Popen([exe, "--port", "7799"], cwd=OUT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(10)
        print()
        print("checking the SHIPPED program on port 7799")
        ok = check_routes(7799)
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
    print()
    print("SHIPPED BUNDLE: %s" % ("ALL ROUTES OK" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
