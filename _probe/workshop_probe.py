"""Locate the AoE2 mod/workshop (UGC) HTTP API.

The mods page is a WordPress-hosted SPA.  Probe for the JSON endpoint behind it
by (1) reading the page's script tags, (2) grepping the bundles for API-looking
paths, and (3) probing a list of candidate endpoints directly.

Read-only network access; nothing is written outside _probe/workshop/.
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


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode()


PAGE = "https://www.ageofempires.com/mods/"
print("=== fetching %s ===" % PAGE)
st, body = get(PAGE)
print("status=%s bytes=%s" % (st, len(body)))
html = body.decode("utf-8", "replace")
open(os.path.join(OUT, "mods_page.html"), "w", encoding="utf-8").write(html)

srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
print("script tags: %d" % len(srcs))
for s in srcs[:25]:
    print("   ", s)

# grep every fetched bundle for API-looking paths
print()
print("=== API-looking strings in bundles ===")
api_re = re.compile(r"""["'](/[A-Za-z0-9_\-./]*(?:api|mods|ugc|search)[A-Za-z0-9_\-./]*)["']""")
found = set()
for s in srcs:
    u = s if s.startswith("http") else ("https://www.ageofempires.com" + s if s.startswith("/") else None)
    if not u:
        continue
    st, b = get(u)
    if st != 200:
        print("   [%s] %s" % (st, u))
        continue
    t = b.decode("utf-8", "replace")
    hits = set(api_re.findall(t))
    if hits:
        print("   [200] %s -> %d hits" % (u.rsplit("/", 1)[-1], len(hits)))
        for h in sorted(hits)[:25]:
            found.add(h)
            print("        ", h)
    if "api" in t.lower() and not hits:
        idx = t.lower().find("api")
        print("   [200] %s -> raw ctx: %s" % (u.rsplit("/", 1)[-1], t[max(0, idx-90):idx+130].replace("\n", " ")[:220]))

print()
print("=== candidate endpoint probes ===")
CANDS = [
    "https://api.ageofempires.com/api/mods/search?size=2",
    "https://api.ageofempires.com/api/mods?size=2",
    "https://api.ageofempires.com/api/v2/mods/search?size=2",
    "https://api.ageofempires.com/api/ugc/mods?size=2",
    "https://www.ageofempires.com/api/mods/search?size=2",
    "https://www.ageofempires.com/wp-json/aoe2/v1/mods?size=2",
    "https://www.ageofempires.com/wp-json/wp/v2/mods?per_page=2",
    "https://aoe2.net/api/mods?size=2",
]
for c in CANDS:
    st, b = get(c)
    head = b[:110].decode("utf-8", "replace").replace("\n", " ")
    ct = ""
    print("  %-58s status=%-5s bytes=%-8s ct=%-6s %s" % (c.replace("https://", ""), st, len(b), ct, head))
