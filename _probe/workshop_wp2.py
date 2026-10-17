"""The WP REST index exposed /wp/v2/game_modes (a custom post type) and an `mcp`
namespace. Probe both anonymously.

Also try the wp/v2 search across all public post types for a known mod title.

Read-only.
"""
import json
import os
import urllib.error
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()
    except Exception as e:
        return None, {}, ("%s: %s" % (type(e).__name__, e)).encode()


URLS = [
    "https://www.ageofempires.com/wp-json/wp/v2/game_modes?per_page=100",
    "https://www.ageofempires.com/wp-json/wp/v2/game_modes",
    "https://www.ageofempires.com/wp-json/wp/v2/types",
    "https://www.ageofempires.com/wp-json/wp/v2/search?search=chibi&per_page=10",
    "https://www.ageofempires.com/wp-json/wp/v2/search?search=mods&per_page=10",
    "https://www.ageofempires.com/wp-json/mcp",
    "https://www.ageofempires.com/wp-json/wp/v2/pages?per_page=100&_fields=id,slug,title,link",
]
for u in URLS:
    st, h, b = get(u)
    ct = h.get("Content-Type", "")
    print("=" * 100)
    print("%s\n  status=%s bytes=%s ct=%s" % (u, st, len(b), ct))
    if b[:1] in (b"{", b"["):
        try:
            j = json.loads(b)
        except Exception as e:
            print("  parse fail: %s" % e)
            print("  head: %s" % b[:200].decode("utf-8", "replace"))
            continue
        tag = u.split("wp-json/")[-1].split("?")[0].replace("/", "_")
        json.dump(j, open(os.path.join(OUT, "wpj_%s.json" % tag), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        if isinstance(j, dict):
            print("  dict keys: %s" % list(j.keys())[:25])
            if "code" in j:
                print("  code=%s msg=%s" % (j.get("code"), j.get("message")))
        elif isinstance(j, list):
            print("  list[%d]" % len(j))
            if j and isinstance(j[0], dict):
                print("  item[0] keys: %s" % list(j[0].keys())[:25])
                print("  item[0]: %s" % json.dumps(j[0], ensure_ascii=False)[:500])
    else:
        print("  head: %s" % b[:250].decode("utf-8", "replace").replace("\n", " "))
