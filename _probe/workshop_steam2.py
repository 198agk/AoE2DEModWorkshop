"""Inspect the Steam Workshop browse response for appid 813780.

190 KB returned but 0 titles parsed -> figure out what the page actually is
(login wall? JS app? wrong appid?).

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
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


TESTS = [
    ("aoe2de browse", "https://steamcommunity.com/workshop/browse/?appid=813780&browsesort=trend&section=readytouseitems"),
    ("aoe2de root", "https://steamcommunity.com/app/813780/workshop/"),
    ("aoe2de sharedfiles", "https://steamcommunity.com/app/813780/workshop/"),
    ("csgo sanity", "https://steamcommunity.com/workshop/browse/?appid=730&browsesort=trend&section=readytouseitems"),
]
for label, url in TESTS:
    st, html = get(url)
    print("=" * 100)
    print("%s\n  %s\n  status=%s bytes=%s" % (label, url, st, len(html or "")))
    if not html:
        continue
    open(os.path.join(OUT, "steam_%s.html" % label.replace(" ", "_")), "w",
         encoding="utf-8").write(html)
    # what is this page?
    for pat, nm in ((r"<title[^>]*>(.*?)</title>", "title"),
                    (r'id="error_box"', "error_box"),
                    (r"Sign In", "sign-in text"),
                    (r"workshopItem", "workshopItem class"),
                    (r"sharedfile_(\d+)", "sharedfile ids"),
                    (r'"publishedfileid"\s*:\s*"?(\d+)', "publishedfileid json"),
                    (r"g_rgWorkshopItems", "g_rgWorkshopItems"),
                    (r"application_config", "application_config"),
                    (r"Age of Empires", "Age of Empires text")):
        hits = re.findall(pat, html, re.I | re.S)
        if nm == "title" and hits:
            print("  title: %s" % re.sub(r"\s+", " ", str(hits[0]))[:120])
        elif nm == "sharedfile ids":
            print("  %-24s %d distinct" % (nm, len(set(hits))))
        elif nm == "publishedfileid json":
            print("  %-24s %d distinct" % (nm, len(set(hits))))
        else:
            print("  %-24s %s" % (nm, ("yes (%d)" % len(hits)) if hits else "no"))
    # total results line
    m = re.search(r'([\d,]+)\s*(?:results|items|entries)', html, re.I)
    if m:
        print("  results-ish text: %s" % m.group(0)[:80])
    # server-rendered item blocks
    blocks = re.findall(r'class="workshopItemTitle[^"]*"[^>]*>(.*?)<', html, re.S)
    print("  workshopItemTitle blocks: %d" % len(blocks))
    for b in blocks[:6]:
        print("      - %s" % re.sub(r"\s+", " ", b).strip()[:80])
