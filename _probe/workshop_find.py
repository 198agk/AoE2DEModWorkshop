"""POST the real /Find endpoint with the body shape the site uses.

Bundle: _fetchModsData() -> e = Object.assign({start, count}, queryParams);
        gt({url: F+'/Find', data: JSON.stringify(e)})

Read-only.
"""
import json
import os
import urllib.error
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
F = "https://api.ageofempires.com/api/v4/mods"


def post(path, body, extra=None):
    url = F + path
    h = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.ageofempires.com",
        "Referer": "https://www.ageofempires.com/mods/",
    }
    if extra:
        h.update(extra)
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()
    except Exception as e:
        return None, {}, ("%s: %s" % (type(e).__name__, e)).encode()


BODIES = [
    ("/Find", {"start": 0, "count": 3}),
    ("/Find", {"start": 0, "count": 3, "game": 1}),
    ("/Find", {"start": 0, "count": 3, "gameTitleId": 1}),
    ("/Featured", {"start": 0, "count": 3}),
]
for path, body in BODIES:
    st, h, b = post(path, body)
    ct = h.get("Content-Type", "")
    print("=" * 100)
    print("POST %s  body=%s" % (path, json.dumps(body)))
    print("  status=%s  bytes=%s  ct=%s" % (st, len(b), ct))
    print("  head: %s" % b[:400].decode("utf-8", "replace").replace("\n", " ")[:380])
    if st == 200 and b[:1] in (b"{", b"["):
        try:
            j = json.loads(b)
        except Exception as e:
            print("  parse fail: %s" % e)
            continue
        tag = path.strip("/").replace("/", "_")
        name = os.path.join(OUT, "find_%s_%d.json" % (tag, abs(hash(json.dumps(body))) % 1000))
        json.dump(j, open(name, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("  PARSED -> %s" % name)
        if isinstance(j, dict):
            print("  top keys: %s" % list(j.keys()))
            for k, v in j.items():
                if isinstance(v, list):
                    print("    %s: list[%d]" % (k, len(v)))
                    if v and isinstance(v[0], dict):
                        print("      item[0] keys: %s" % list(v[0].keys()))
                        print("      item[0]: %s" % json.dumps(v[0], ensure_ascii=False)[:700])
                else:
                    print("    %s: %r" % (k, str(v)[:100]))
        elif isinstance(j, list):
            print("  list[%d]" % len(j))
            if j and isinstance(j[0], dict):
                print("  item[0] keys: %s" % list(j[0].keys()))
                print("  item[0]: %s" % json.dumps(j[0], ensure_ascii=False)[:800])
