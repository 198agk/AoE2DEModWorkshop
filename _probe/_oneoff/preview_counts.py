"""What does the preview promise for every intent -- and does the build agree?

`edit_count` used to exist only on the unit.shape path, so `tech.research_time`
previewed "0 edits" for an edit that writes one.  A zero that means "this shape
does not report" is indistinguishable from a zero that means "nothing will
happen", so this prints both numbers side by side.
"""
import json, os, subprocess, sys, time, urllib.request

sys.path.insert(0, "D:/Software/AI/帝国项目")
BUNDLE = r"D:\Software\AI\AoE2ModWorkshop"
EXE = os.path.join(BUNDLE, "aoe2-mod-workshop.exe")
PORT = 7853

CASES = [
    "村民血量改成100", "不列颠村民血量改成100", "城堡攻击加5",
    "民兵人口成本设为0", "民兵对平民攻击加2",
    "织布机研究时间改成5", "织布机黄金成本改成5", "织布机第1条效果改成100",
    "把织布机和铸币术做成只能选一个",
    "把民兵放在兵营的第5格",
    "让弓兵的样子换成长弓兵",
]

def post(path, body, timeout=1800):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path),
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=timeout) as f:
        return json.loads(f.read().decode())

def main():
    p = subprocess.Popen([EXE, "--port", str(PORT)], cwd=BUNDLE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    bad = 0
    try:
        end = time.time() + 240
        while time.time() < end:
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/api/progress" % PORT, timeout=2) as f:
                    pr = json.loads(f.read().decode()).get("progress") or {}
                if pr.get("ready"): break
            except Exception: pass
            time.sleep(0.4)
        print("%-28s %-22s %8s %8s %s" % ("sentence", "intent", "preview", "build", "ok"))
        for s in CASES:
            got = post("/api/parse", {"text": s, "pins": {}})
            it = (got.get("intents") or [None])[0]
            if not it:
                print("%-28s %s" % (s, "refused: " + str((got.get("refusals") or [{}])[0].get("why"))[:50]))
                continue
            pl = ((got.get("clauses") or [{}])[0].get("preview") or {}).get("plan") or {}
            b = post("/api/build", {"intents": [it], "title": "cnt %d" % int(time.time()), "install": False})
            be = b.get("edit_count") if b.get("ok") else None
            pv = pl.get("edit_count")
            same = (pv == be)
            if not same: bad += 1
            print("%-28s %-22s %8s %8s %s%s" % (s, it.get("intent"), pv, be,
                  "same" if same else "DIFFER",
                  "" if b.get("ok") else "  build: " + str(b.get("error"))[:60]))
    finally:
        p.terminate()
        try: p.wait(timeout=10)
        except Exception: p.kill()
    print("\nVERDICT disagreements=%d (must be 0)" % bad)
    return 0 if bad == 0 else 1

raise SystemExit(main())
