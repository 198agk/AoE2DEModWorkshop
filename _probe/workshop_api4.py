"""Probe the real mod-workshop API endpoints extracted from the site bundle.

Base: https://api.ageofempires.com/api/v4/mods   (variable F)
  modsFind      F/Find
  modsFeatured  F/Featured
  modsTags      F/Tags
  modsTypes     F/Types
  modsDetail    F/Detail/<id>
  modsInstalled F/Installed
  modsMine      F/My
  modsReviews   F/Reviews
  modsRelated   F/Related
  modsNotifications F/Notifications

Read-only.
"""
import json
import os
import urllib.error
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")
os.makedirs(OUT, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
F = "https://api.ageofempires.com/api/v4/mods"


def get(url, extra=None):
    h = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.ageofempires.com",
        "Referer": "https://www.ageofempires.com/mods/",
    }
    if extra:
        h.update(extra)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()
    except Exception as e:
        return None, {}, ("%s: %s" % (type(e).__name__, e)).encode()


CANDS = [
    (F + "/Find", None),
    (F + "/Find?size=2", None),
    (F + "/Find?page=1&size=2", None),
    (F + "/Find", {"Content-Type": "application/json"}),
    (F + "/Featured", None),
    (F + "/Featured?size=3", None),
    (F + "/Tags", None),
    (F + "/Types", None),
    (F + "/Detail/1", None),
    (F + "/Installed", None),
    (F + "/My", None),
    (F + "/Notifications", None),
]
for url, extra in CANDS:
    st, h, b = get(url, extra)
    ct = h.get("Content-Type", "")
    print("=" * 100)
    print("%s   [extra=%s]" % (url, extra))
    print("  status=%s  bytes=%s  ct=%s" % (st, len(b), ct))
    print("  head: %s" % b[:300].decode("utf-8", "replace").replace("\n", " ")[:280])
    if st == 200 and "json" in (ct or "").lower() and b[:1] in (b"{", b"["):
        try:
            j = json.loads(b)
        except Exception as e:
            print("  JSON parse failed: %s" % e)
            continue
        tag = url.split("/api/v4/mods/")[-1].split("?")[0].replace("/", "_")
        name = os.path.join(OUT, "v4_%s.json" % tag)
        json.dump(j, open(name, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("  PARSED -> %s" % name)
        if isinstance(j, dict):
            print("  top keys: %s" % list(j.keys())[:25])
            for k, v in list(j.items())[:8]:
                if isinstance(v, list):
                    print("    %s: list[%d]" % (k, len(v)))
                    if v and isinstance(v[0], dict):
                        print("       item[0] keys: %s" % list(v[0].keys())[:30])
                elif isinstance(v, dict):
                    print("    %s: dict keys %s" % (k, list(v.keys())[:15]))
                else:
                    print("    %s: %r" % (k, str(v)[:90]))
        elif isinstance(j, list):
            print("  list[%d]" % len(j))
            if j and isinstance(j[0], dict):
                print("  item[0] keys: %s" % list(j[0].keys())[:30])
                print("  item[0]: %s" % json.dumps(j[0], ensure_ascii=False)[:600])
