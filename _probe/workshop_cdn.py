"""Last anonymous avenues for mod CONTENT (not just taxonomy):

1. cdn.ageofempires.com  -- the exe references it; mod images/files may be public
2. aoe2.net              -- well-known community API mirror
3. Is there any community mod browser that mirrors the official workshop?

Read-only.
"""
import json
import os
import re
import urllib.error
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def get(url, hdr=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/html, */*"}
    if hdr:
        h.update(hdr)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()
    except Exception as e:
        return None, {}, ("%s: %s" % (type(e).__name__, e)).encode()


print("=" * 104)
print("1. cdn.ageofempires.com")
print("=" * 104)
for u in ("https://cdn.ageofempires.com/aoe/rl-server-status.json",
          "https://cdn.ageofempires.com/",
          "https://cdn.ageofempires.com/aoe/",
          "https://cdn.ageofempires.com/mods/",
          "https://cdn.ageofempires.com/aoe/mods/",
          "https://static.ageofempires.com/aoe/aoe-server-status.html"):
    st, h, b = get(u)
    print("  %-58s status=%-6s bytes=%-8s ct=%s" % (u, st, len(b), h.get("Content-Type", "")))
    if st == 200 and len(b) < 3000:
        print("      %s" % b[:200].decode("utf-8", "replace").replace("\n", " "))

print()
print("=" * 104)
print("2. aoe2.net community API")
print("=" * 104)
for u in ("https://aoe2.net/api/strings?game=aoe2de&language=en",
          "https://aoe2.net/api/leaderboard?game=aoe2de&leaderboard_id=3&count=1",
          "https://aoe2.net/api/mods",
          "https://aoe2.net/"):
    st, h, b = get(u)
    print("  %-58s status=%-6s bytes=%-8s ct=%s" % (u, st, len(b), h.get("Content-Type", "")))
    if st == 200 and b[:1] in (b"{", b"["):
        try:
            j = json.loads(b)
            tag = re.sub(r"[^a-z0-9]+", "_", u.split("aoe2.net/")[-1])[:40]
            json.dump(j, open(os.path.join(OUT, "aoe2net_%s.json" % tag), "w",
                              encoding="utf-8"), indent=1, ensure_ascii=False)
            print("      PARSED -> saved; type=%s len=%s"
                  % (type(j).__name__, len(j) if hasattr(j, "__len__") else "-"))
        except Exception as e:
            print("      parse fail: %s" % e)

print()
print("=" * 104)
print("3. Does the official site have a public 'mods' sitemap / RSS / feed?")
print("=" * 104)
for u in ("https://www.ageofempires.com/sitemap_index.xml",
          "https://www.ageofempires.com/wp-sitemap.xml",
          "https://www.ageofempires.com/mods/feed/",
          "https://www.ageofempires.com/wp-json/wp/v2/posts?per_page=3&_fields=id,link"):
    st, h, b = get(u)
    txt = b[:300].decode("utf-8", "replace").replace("\n", " ")
    print("  %-58s status=%-6s bytes=%-8s" % (u, st, len(b)))
    print("      %s" % txt[:220])
