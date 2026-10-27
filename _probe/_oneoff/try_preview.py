import json, subprocess, time, urllib.request
EXE = r"D:\Software\AI\AoE2ModWorkshop\aoe2-mod-workshop.exe"
PORT = 7841
p = subprocess.Popen([EXE, "--port", str(PORT)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
def get(path):
    return json.loads(urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, path), timeout=60).read())
def post(path, body):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=120).read())
try:
    for _ in range(120):
        try:
            pr = get("/api/progress")
            if pr.get("progress", {}).get("ready"):
                break
        except Exception:
            pass
        time.sleep(0.5)
    for s in ["村民血量改成100", "不列颠村民血量改成100", "民兵黄金成本 -5",
              "织布机研究时间 -5", "织布机黄金成本 -10", "织布机第0条效果 +5",
              "把织布机和铸币术做成只能选一个", "民兵对平民攻击加2",
              "民兵人口成本设为0", "让弓兵长得像长弓兵"]:
        j = post("/api/parse", {"text": s})
        c = (j.get("clauses") or [{}])[0]
        pv = c.get("preview") or {}
        pl = pv.get("plan") or {}
        print("%-28s buildable=%-5s kind=%-5s %s" % (
            s, c.get("buildable"), c.get("kind"),
            {k: pl.get(k) for k in ("description","edit_count","civ_count","editable","shape") if pl.get(k) is not None}))
finally:
    p.terminate()
