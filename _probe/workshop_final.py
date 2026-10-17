"""Final consolidation: anonymous surface + the WP `mcp` namespace routes.

Read-only.
"""
import json
import os
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                              "Accept": "application/json, */*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode()


print("=== /api/v4/mods/Games  (anonymous) ===")
st, b = get("https://api.ageofempires.com/api/v4/mods/Games")
j = json.loads(b)
for g in j:
    print("   gameTitleId %-6s %-28s version=%s"
          % (g.get("gameTitleId"), g.get("gameTitleName"), g.get("gameVersion")))
print("   -> %d game titles" % len(j))

print()
print("=== WP /wp-json/mcp routes ===")
st, b = get("https://www.ageofempires.com/wp-json/mcp")
j = json.loads(b)
print("   namespace: %s" % j.get("namespace"))
for r, meta in (j.get("routes") or {}).items():
    eps = meta.get("endpoints", [])
    meth = sorted({m for e in eps for m in e.get("methods", [])})
    print("   %-40s %s" % (r, meth))

print()
print("=== Does api v4 have a version-index / swagger? ===")
for u in ("https://api.ageofempires.com/api/v4",
          "https://api.ageofempires.com/api/v4/",
          "https://api.ageofempires.com/swagger/index.html",
          "https://api.ageofempires.com/api/v4/mods/",
          "https://api.ageofempires.com/api/v4/Games"):
    st, b = get(u)
    print("   %-52s status=%-6s bytes=%-8s %s"
          % (u, st, len(b), b[:80].decode("utf-8", "replace").replace("\n", " ")))
