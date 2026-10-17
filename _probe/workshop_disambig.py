"""Disambiguate the 401: is it route-level, or gateway-level?

Compare api/v1 paths (real and nonsense) against known-good api/v4 paths.

Read-only.
"""
import json
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
BASE = "https://api.ageofempires.com"


def call(path, method="GET", body=None, hdr=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
    if hdr:
        h.update(hdr)
    data = None
    if body is not None:
        h["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, len(r.read()), ""
    except urllib.error.HTTPError as e:
        b = e.read()
        return e.code, len(b), b[:110].decode("utf-8", "replace").replace("\n", " ")
    except Exception as e:
        return None, 0, "%s: %s" % (type(e).__name__, e)


print("=== control: nonsense paths, to see how unknown routes are answered ===")
for p in ("/api/v1/ZZZNotFound/", "/api/v9/Mods/Find/", "/api/v1/Mods/ZZZ/",
          "/totally/bogus", "/api/v4/mods/ZZZ/"):
    print("  GET  %-30s -> %s" % (p, call(p)))
    print("  POST %-30s -> %s" % (p, call(p, "POST", {})))

print()
print("=== api/v1/Mods/* as the exe names them ===")
for p in ("/api/v1/Mods/Find/", "/api/v1/Mods/FindAsUser/", "/api/v1/Mods/Installed/",
          "/api/v1/Mods/My/", "/api/v1/Mods/Detail/", "/api/v1/Logs/"):
    print("  POST %-30s -> %s" % (p, call(p, "POST", {})))
    print("  GET  %-30s -> %s" % (p, call(p)))

print()
print("=== same path WITH the browser-ish headers the website sends ===")
HDR = {"Origin": "https://www.ageofempires.com",
       "Referer": "https://www.ageofempires.com/mods/",
       "Accept-Language": "en-US,en;q=0.9"}
for p in ("/api/v1/Mods/Find/", "/api/v1/Mods/Installed/"):
    print("  POST %-30s -> %s" % (p, call(p, "POST", {"game": 2, "start": 0, "count": 5}, HDR)))

print()
print("=== filter/sort field names the exe mentions, as body keys ===")
for body in ({"filter": ""}, {"filter": "", "game": 2}, {"sort": "createDate", "order": "DESC"},
             {"sort": "createDate", "order": "DESC", "game": 2, "start": 0, "count": 5},
             {"GameTitleId": 2}, {"gameTitleId": 2}):
    print("  POST /api/v1/Mods/Find/ %-58s -> %s"
          % (json.dumps(body), call("/api/v1/Mods/Find/", "POST", body, HDR)))
