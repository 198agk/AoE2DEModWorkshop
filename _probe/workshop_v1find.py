"""THE endpoint: api/v1/Mods/Find/  -- the game's own anonymous mod search.

exe strings (0x0329D667):
  "MODS: Searching mods as authenticated user. Search options: %s." -> api/v1/Mods/FindAsUser/
  "MODS: Searching mods without authentication. Search options: %s." -> api/v1/Mods/Find/
  "MODS: List my published mods."                                    -> api/v1/Mods/My/
  "MODS: List my installed mods."                                    -> api/v1/Mods/Installed/
  "MODS: Retrieving batched mod details as authenticated user."
Search-option fields seen nearby: game, sort, order (DESC), filter, createDate, totalCount

App id mapping learned from /api/v4/mods/Games:
  1 = Age of Empires DE, 2 = Age of Empires II DE, 3 = AoE3 DE, 4 = AoE4, 1001 = AoM Retold

Read-only.
"""
import json
import os
import urllib.error
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
os.makedirs(OUT, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
BASE = "https://api.ageofempires.com"


def call(path, method="GET", body=None):
    url = BASE + path
    h = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.ageofempires.com",
        "Referer": "https://www.ageofempires.com/mods/",
    }
    data = None
    if body is not None:
        h["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode()


TESTS = [
    ("/api/v1/Mods/Find/", "GET", None),
    ("/api/v1/Mods/Find/", "POST", {"game": 2, "start": 0, "count": 5}),
    ("/api/v1/Mods/Find/", "POST", {"game": "2", "start": 0, "count": 5}),
    ("/api/v1/Mods/Find/", "POST", {}),
    ("/api/v1/Mods/Find/", "POST", {"game": 2}),
    ("/api/v1/Mods/Find/", "POST", {"GameTitleId": 2, "start": 0, "count": 5}),
    ("/api/v1/Mods/Find/", "POST", {"game": 2, "start": 0, "count": 5, "sort": "createDate", "order": "DESC"}),
]
for path, meth, body in TESTS:
    st, b = call(path, meth, body)
    print("=" * 104)
    print("%s %s  body=%s" % (meth, path, json.dumps(body) if body else None))
    print("  status=%s bytes=%s" % (st, len(b)))
    print("  head: %s" % b[:300].decode("utf-8", "replace").replace("\n", " ")[:280])
    if st == 200 and b[:1] in (b"{", b"["):
        try:
            j = json.loads(b)
        except Exception as e:
            print("  parse fail: %s" % e)
            continue
        name = os.path.join(OUT, "v1find_%s.json" % (abs(hash(json.dumps(body, sort_keys=True))) % 10000))
        json.dump(j, open(name, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("  PARSED -> %s" % name)
        if isinstance(j, dict):
            print("  keys: %s" % list(j.keys()))
            for k, v in j.items():
                if isinstance(v, list):
                    print("    %s: list[%d]" % (k, len(v)))
                    if v and isinstance(v[0], dict):
                        print("      item[0] keys: %s" % list(v[0].keys()))
                        print("      item[0]: %s" % json.dumps(v[0], ensure_ascii=False)[:500])
                else:
                    print("    %s: %r" % (k, str(v)[:120]))
