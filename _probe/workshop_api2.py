"""Probe the discovered mods API: https://api.ageofempires.com/api/v4/mods

The site bundle defines:
    const V="https://api.ageofempires.com", N=V+"/webapi", F=V+"/api/v4/mods"

Read-only.
"""
import json
import os
import re
import urllib.error
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
os.makedirs(OUT, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.ageofempires.com",
        "Referer": "https://www.ageofempires.com/mods/",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()
    except Exception as e:
        return None, {}, ("%s: %s" % (type(e).__name__, e)).encode()


CANDS = [
    "https://api.ageofempires.com/api/v4/mods",
    "https://api.ageofempires.com/api/v4/mods?size=2",
    "https://api.ageofempires.com/api/v4/mods?page=1&size=2",
    "https://api.ageofempires.com/api/v4/mods/search?size=2",
    "https://api.ageofempires.com/api/v4/mods?count=2",
    "https://api.ageofempires.com/webapi/mods?size=2",
]
for c in CANDS:
    st, h, b = get(c)
    ct = h.get("Content-Type", "")
    print("=" * 100)
    print("%s\n  status=%s  bytes=%s  ct=%s" % (c, st, len(b), ct))
    head = b[:400].decode("utf-8", "replace").replace("\n", " ")
    print("  head: %s" % head[:380])
    if "json" in ct.lower() and st == 200:
        try:
            j = json.loads(b)
            name = os.path.join(OUT, "v4mods_probe.json")
            json.dump(j, open(name, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            print("  PARSED JSON -> saved %s" % name)
            if isinstance(j, dict):
                print("  top keys: %s" % list(j.keys())[:20])
                for k, v in j.items():
                    if isinstance(v, list):
                        print("    %s: list of %d" % (k, len(v)))
                        if v and isinstance(v[0], dict):
                            print("      item keys: %s" % list(v[0].keys()))
                    else:
                        print("    %s: %r" % (k, str(v)[:80]))
        except Exception as e:
            print("  JSON parse failed: %s" % e)
