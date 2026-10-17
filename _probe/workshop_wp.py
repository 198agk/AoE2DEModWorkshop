"""Two more anonymous avenues:

1. WordPress REST route index  https://www.ageofempires.com/wp-json/
   -> lists every registered namespace/route; may expose a public mods route.
2. Individual mod detail pages https://www.ageofempires.com/mods/details/<id>/
   -> Rank Math SEO is installed, so meta may be server-rendered.

Known Steam WorkshopIDs from the user's own install:
  182654, 550412, 550009, 423822, 550749, 297820, 423821

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
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()
    except Exception as e:
        return None, {}, ("%s: %s" % (type(e).__name__, e)).encode()


print("=" * 100)
print("1. WordPress REST route index")
st, h, b = get("https://www.ageofempires.com/wp-json/")
print("  status=%s bytes=%s ct=%s" % (st, len(b), h.get("Content-Type", "")))
if b[:1] == b"{":
    try:
        j = json.loads(b)
        json.dump(j, open(os.path.join(OUT, "wp_index.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        ns = j.get("namespaces", [])
        print("  namespaces (%d): %s" % (len(ns), ns))
        routes = j.get("routes", {})
        print("  routes: %d" % len(routes))
        print("  --- routes mentioning mod/ugc/aoe2 ---")
        for r in sorted(routes):
            if any(k in r.lower() for k in ("mod", "ugc", "aoe", "publish", "workshop")):
                ep = routes[r].get("endpoints", [])
                meth = ",".join(sorted({m for e in ep for m in e.get("methods", [])}))
                print("     %-52s [%s]" % (r, meth))
    except Exception as e:
        print("  parse fail: %s" % e)

print()
print("=" * 100)
print("2. Mod detail pages (are they server-rendered?)")
IDS = [1, 2, 100, 1000, 182654, 297820, 423821, 423822, 550009, 550412, 550749]
for i in IDS:
    st, h, b = get("https://www.ageofempires.com/mods/details/%d/" % i)
    html = b.decode("utf-8", "replace")
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    desc = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', html, re.I)
    og = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]*)"', html, re.I)
    print("  id=%-7s status=%s bytes=%-7s" % (i, st, len(b)))
    if title:
        print("        title: %s" % title.group(1).strip()[:110])
    if og:
        print("        og:title: %s" % og.group(1).strip()[:110])
    if desc:
        print("        desc: %s" % desc.group(1).strip()[:130])
    if h1:
        print("        h1: %s" % re.sub(r"<[^>]+>", "", h1.group(1)).strip()[:110])
