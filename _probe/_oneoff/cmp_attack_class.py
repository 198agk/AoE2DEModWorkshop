import json, subprocess, time, urllib.request
import _paths as P
EXE = P.BUNDLED_EXE
PORT = 7844
p = subprocess.Popen([EXE, "--port", str(PORT)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
def get(path):
    return json.loads(urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, path), timeout=60).read())
def post(path, body):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=180).read())
try:
    for _ in range(120):
        try:
            if get("/api/progress").get("progress", {}).get("ready"): break
        except Exception: pass
        time.sleep(0.5)
    for s in ["民兵对平民攻击加2", "民兵对骑兵攻击加2", "民兵对建筑攻击加2"]:
        j = post("/api/parse", {"text": s})
        c = (j.get("clauses") or [{}])[0]
        pl = (c.get("preview") or {}).get("plan") or {}
        print("%-18s intents=%s" % (s, json.dumps(j.get("intents"), ensure_ascii=False)))
        print("   plan:", json.dumps({k: pl.get(k) for k in
              ("description", "editable", "reason", "edit_count", "mirror_count") if pl.get(k) is not None},
              ensure_ascii=False))
finally:
    p.terminate()
