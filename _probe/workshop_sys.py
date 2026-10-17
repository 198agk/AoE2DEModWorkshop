"""Systematic probe of EVERY apiV4 mods endpoint with both GET and POST.

Discovered from the site bundle:
  F = https://api.ageofempires.com/api/v4/mods
  endpoints: Games, Delete, Detail/<id>, Download/<id>, Featured, Find, Report,
             GetFlagged, GetFlaggedDetail, Subscribe, Installed, Like, My,
             Moderate, Publish, CheckAndPublishFile, Rate, Related, Reviews,
             Report, Tags, Types, UnSubscribe, Notifications

Goal: find which ones are anonymous (200 JSON) vs login-gated (401).

Read-only.
"""
import json
import os
import urllib.error
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
F = "https://api.ageofempires.com/api/v4/mods"

SUB = ["Games", "Delete", "Detail/1", "Download/1", "Featured", "Find", "Report",
       "GetFlagged", "GetFlaggedDetail", "Subscribe", "Installed", "Like", "My",
       "Moderate", "Publish", "CheckAndPublishFile", "Rate", "Related", "Reviews",
       "Tags", "Types", "UnSubscribe", "Notifications"]


def call(url, method, body=None):
    h = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.ageofempires.com",
        "Referer": "https://www.ageofempires.com/mods/",
    }
    data = None
    if body is not None:
        h["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode()


BODY = {"start": 0, "count": 2, "game": 1}
rows = []
for s in SUB:
    url = "%s/%s" % (F, s)
    for meth in ("GET", "POST"):
        st, b = call(url, meth, BODY if meth == "POST" else None)
        snippet = b[:150].decode("utf-8", "replace").replace("\n", " ")
        rows.append((s, meth, st, len(b) if b else 0, snippet))

print("%-22s %-5s %-5s %-8s %s" % ("path", "meth", "stat", "bytes", "head"))
print("-" * 130)
for s, meth, st, n, sn in rows:
    print("%-22s %-5s %-5s %-8s %s" % (s, meth, st, n, sn[:88]))

print()
print("=== ANONYMOUS (200 + JSON) ===")
for s, meth, st, n, sn in rows:
    if st == 200 and sn.lstrip().startswith(("{", "[")):
        print("   %-5s %-22s %d bytes" % (meth, s, n))
        tag = s.replace("/", "_")
        try:
            j = json.loads(call("%s/%s" % (F, s), meth, BODY if meth == "POST" else None)[1])
            json.dump(j, open(os.path.join(OUT, "sys_%s_%s.json" % (tag, meth)), "w",
                              encoding="utf-8"), indent=1, ensure_ascii=False)
        except Exception as e:
            print("       save fail: %s" % e)
