"""The mods RSS feed and sitemaps -- do they enumerate mod detail pages?

If the sitemap lists /mods/details/<id>/ URLs, we get the full mod ID space
without any login. Then each detail page is SPA-rendered, but the *IDs and
slugs* alone are valuable, and the RSS may carry titles.

Read-only.
"""
import os
import re
import urllib.error
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                              "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


print("=" * 104)
print("A) /mods/feed/  (full)")
print("=" * 104)
st, txt = get("https://www.ageofempires.com/mods/feed/")
print("  status=%s bytes=%s" % (st, len(txt)))
print(txt[:2500])

print()
print("=" * 104)
print("B) sitemap index -> child sitemaps")
print("=" * 104)
st, txt = get("https://www.ageofempires.com/sitemap_index.xml")
print("  status=%s bytes=%s" % (st, len(txt)))
maps = re.findall(r"<loc>(.*?)</loc>", txt)
for m in maps:
    print("   %s" % m)
open(os.path.join(OUT, "sitemap_index.xml"), "w", encoding="utf-8").write(txt)

print()
found_ids = set()
for m in maps:
    st, sub = get(m)
    locs = re.findall(r"<loc>(.*?)</loc>", sub)
    modish = [l for l in locs if "/mods/" in l or "mod" in l.lower()]
    print("  %-62s status=%-5s locs=%-6d mod-ish=%d"
          % (m[:60], st, len(locs), len(modish)))
    for l in modish[:12]:
        print("       %s" % l)
    ids = re.findall(r"/mods/details/(\d+)", sub)
    found_ids |= set(ids)
    if modish:
        tag = re.sub(r"[^A-Za-z0-9]+", "_", m)[-50:]
        open(os.path.join(OUT, "sitemap_%s.xml" % tag), "w", encoding="utf-8").write(sub)

print()
print("  distinct mod detail ids found across sitemaps: %d" % len(found_ids))
if found_ids:
    print("  sample: %s" % sorted(found_ids)[:20])
