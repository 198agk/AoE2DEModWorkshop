"""The decisive test: Steam's own public Workshop API for AoE2 DE (appid 813780).

ISteamRemoteStorage/GetPublishedFileDetails/v1/ needs NO api key and NO login.
It returns title, description, tags, file size, subscriptions, time_updated,
consumer_app_id, and the filename for any published file id.

Also: the public Steam Workshop browse pages (server-rendered HTML).

Read-only.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
os.makedirs(OUT, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
APPID = 813780

KNOWN = [182654, 550412, 550009, 423822, 550749, 297820, 423821]


def post_form(url, fields):
    body = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/plain, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode()


print("=" * 100)
print("ISteamRemoteStorage/GetPublishedFileDetails/v1/  (no key, no login)")
fields = {"itemcount": str(len(KNOWN))}
for i, pid in enumerate(KNOWN):
    fields["publishedfileids[%d]" % i] = str(pid)
st, b = post_form(
    "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/", fields)
print("  status=%s bytes=%s" % (st, len(b)))
print("  head: %s" % b[:250].decode("utf-8", "replace"))
try:
    j = json.loads(b)
except Exception as e:
    print("  parse fail: %s" % e)
    j = None
if j:
    json.dump(j, open(os.path.join(OUT, "steam_filedetails.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    files = (j.get("response") or {}).get("publishedfiledetails") or []
    print("  returned %d details" % len(files))
    for f in files:
        print("  " + "-" * 90)
        for k in ("publishedfileid", "result", "title", "filename", "file_size",
                  "consumer_app_id", "creator", "time_created", "time_updated",
                  "visibility", "subscriptions", "favorited", "views", "lifetime_subscriptions",
                  "num_children", "banned", "ban_reason"):
            if k in f:
                v = f[k]
                if k in ("title", "filename"):
                    v = str(v)[:80]
                print("     %-24s %s" % (k, v))
        tags = f.get("tags")
        if tags:
            print("     tags: %s" % [t.get("tag") for t in tags])
        if f.get("short_description"):
            print("     short_description: %s" % str(f["short_description"])[:220].replace("\n", " "))

print()
print("=" * 100)
print("Steam Workshop browse page (public HTML, appid %d)" % APPID)
for sort in ("trend", "mostrecent", "totaluniquesubscribers"):
    u = ("https://steamcommunity.com/workshop/browse/?appid=%d&browsesort=%s&section=readytouseitems"
         % (APPID, sort))
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            st, html = r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        print("  %s -> %s: %s" % (sort, type(e).__name__, e))
        continue
    # total count and item ids
    tot = re.search(r"([\d,]+)\s*(?:results|entries|items)", html, re.I)
    ids = re.findall(r'workshopItemTitle[^>]*>([^<]{1,90})<', html)
    pids = re.findall(r'sharedfile_(\d+)', html)
    print("  sort=%-24s status=%s bytes=%-8s titles=%d" % (sort, st, len(html), len(ids)))
    if tot:
        print("       total-ish: %s" % tot.group(1))
    for t in ids[:8]:
        print("       - %s" % t.strip()[:80])
    print("       distinct file ids on page: %d  e.g. %s"
          % (len(set(pids)), sorted(set(pids))[:5]))
