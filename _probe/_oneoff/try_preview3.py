import json, subprocess, time, urllib.request
EXE = r"D:\Software\AI\AoE2ModWorkshop\aoe2-mod-workshop.exe"
PORT = 7843
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
            if get("/api/progress").get("progress", {}).get("ready"): break
        except Exception: pass
        time.sleep(0.5)
    for s in ["织布机第0条效果 +5", "织布机第2条效果改成100"]:
        pl = ((post("/api/parse", {"text": s}).get("clauses") or [{}])[0].get("preview") or {}).get("plan") or {}
        print("==", s, "->", json.dumps(pl, ensure_ascii=False)[:500])
finally:
    p.terminate()
