"""Browsing the official workshop without leaving the tool.

What this is
------------
A read-only window onto `api.ageofempires.com/api/v4/mods/`.  It can list, search,
filter, page and read one mod's detail.  It cannot subscribe, download, rate,
like, report, publish or delete anything, and that is enforced by construction
rather than by discipline: the endpoint table below has no entry for any of
those, and `_call` refuses a name that is not in it.

Why the session has to be borrowed
----------------------------------
`Find` answers 401 to everyone who is not signed in (measured 2026-11-15:
`errorCode 900`, "Access Denied - User not authenticated."), with a flat body and
a nested one alike.  There is no anonymous listing anywhere -- the marketing
site's own `/mods/` page issues zero requests to that API until the browser holds
a session, and paints an empty list otherwise.  The theme bundle authenticates
with cookies alone: no `Authorization` header, no CSRF token, just
`xhrFields.withCredentials = true`.

Those cookies are `HttpOnly`, so the page cannot read them, and `document.cookie`
cannot set them.  The shell reads them out of the WebView2 cookie jar and writes
`online-session.json` next to `builds.json`; this module reads that file.  Cookie
values never travel back to the page.

Why a disk cache
----------------
Every listing is a signed-in request against somebody else's server, and the
player will click between six filters in ten seconds.  Ten minutes of cache turns
that into one request.  The cache carries `fetchedAt` so the screen can say how
old the answer is -- a mirror presented as live is a lie even when the data
happens to be right.

What it will not do
-------------------
It will not retry a 401 into a login prompt it cannot satisfy, and it will not
report an empty list where the truth is "you are not signed in".  Those are two
different sentences on the screen.
"""
import io
import json
import os
import time
import urllib.error
import urllib.request

from ..mod import provenance as _PV

# The whole surface this module may touch.  A name absent from here is a name
# this tool does not call, which is what makes "only preview" true rather than
# merely intended: `apiV4` in the official bundle also carries Subscribe,
# UnSubscribe, Download, Publish, Delete, Rate, Like, Report, Moderate,
# CheckAndPublishFile, Installed, My and Notifications, and none of them appear
# below.
BASE = "https://api.ageofempires.com/api/v4/mods"

AO2_GAME_ID = 2          # "Age of Empires II DE" in /Games (measured 2026-11-15)
PAGE_SIZE = 24           # 6 columns x 4 rows at 1255 px; the official page uses 12
CACHE_SECONDS = 600      # ten minutes

# Every ageofempires endpoint answers 403 to a bare urllib request.  Measured
# 2026-11-15: `GET /home/checklogin` returned 403 Forbidden until a browser UA
# was supplied, then 200.  The UA is not a disguise; the API simply refuses
# requests that announce themselves as scripts.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0")

SESSION_FILE = "online-session.json"
CACHE_DIR = "online"

# Sentinel the API uses for "this mod has no thumbnail": the URL ends here with
# nothing after it, so an <img> would fetch the directory and paint a broken icon.
THUMB_SENTINEL = "https://cdn.ageofempires.com/aoe/mods/thumb_"


class OnlineError(Exception):
    """Something the player can act on: not signed in, offline, or a bad answer."""


def _state_dir():
    return _PV.state_dir()


def session_path():
    return os.path.join(_state_dir(), SESSION_FILE)


def cache_dir():
    return os.path.join(_state_dir(), CACHE_DIR)


def session_status():
    """What the screen needs to know about the borrowed session.

    Never returns cookie values.  The page only ever learns whether a session
    exists, when it was taken, and how many cookies it holds -- enough to write
    "登录状态：已保存（8 个小时前）" and not enough to leave the machine.
    """
    target = session_path()
    try:
        raw = io.open(target, encoding="utf-8").read()
        doc = json.loads(raw)
    except (OSError, ValueError, UnicodeDecodeError):
        return {"signed": False, "at": 0, "count": 0, "path": target}
    cookies = doc.get("cookies") if isinstance(doc, dict) else None
    if not isinstance(cookies, dict):
        return {"signed": False, "at": 0, "count": 0, "path": target}
    api = cookies.get("api") or ""
    names = [piece.split("=", 1)[0] for piece in api.split(";") if "=" in piece]
    return {
        "signed": bool(names),
        "at": int(doc.get("savedAt") or 0),
        "count": len(names),
        "path": target,
    }


def _cookie_header():
    target = session_path()
    try:
        doc = json.loads(io.open(target, encoding="utf-8").read())
        header = (doc.get("cookies") or {}).get("api") or ""
    except (OSError, ValueError, UnicodeDecodeError):
        raise OnlineError("还没有登录。点「登录账号」，登录完再回来。")
    if not header:
        raise OnlineError("还没有登录。点「登录账号」，登录完再回来。")
    return header


def _call(name, payload=None, timeout=20):
    """One HTTP call to one whitelisted endpoint.

    `name` is matched against a literal tuple, not interpolated into a URL from
    anything a page sent, so a crafted request cannot reach `Subscribe` through
    this function even if somebody later adds a route that forwards user text.
    """
    if name not in ("Find", "Detail"):
        raise OnlineError("这个功能只做预览，不支持 %s。" % name)
    if name == "Find":
        url = BASE + "/Find"
        body = json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
    else:
        mod_id = int(payload or 0)
        if mod_id <= 0:
            raise OnlineError("模组编号不对。")
        url = BASE + "/Detail/%d" % mod_id
        req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "application/json")
    req.add_header("Origin", "https://www.ageofempires.com")
    req.add_header("Referer", "https://www.ageofempires.com/mods/")
    req.add_header("Cookie", _cookie_header())

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            code = resp.status
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise OnlineError("登录已经过期。点「重新登录」，再过一次账号就行。")
        if exc.code == 403:
            raise OnlineError("官方接口拒绝了这次请求（403）。多半是登录过期了。")
        raise OnlineError("官方接口返回 %d。等一下再试。" % exc.code)
    except urllib.error.URLError as exc:
        raise OnlineError("连不上官方服务器：%s" % (exc.reason,))
    except OSError as exc:
        raise OnlineError("连不上官方服务器：%s" % exc)

    try:
        doc = json.loads(raw)
    except ValueError:
        raise OnlineError("官方接口回的不是 JSON（%d 字节）。" % len(raw))
    doc["_status"] = code
    return doc


def _cache_path(kind, key):
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in key)[:80]
    return os.path.join(cache_dir(), "%s-%s.json" % (kind, safe))


def _cache_read(path):
    try:
        doc = json.loads(io.open(path, encoding="utf-8").read())
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(doc, dict):
        return None
    at = doc.get("fetchedAt") or 0
    if time.time() - at > CACHE_SECONDS:
        return None
    return doc


def _cache_write(path, doc):
    folder = os.path.dirname(path)
    try:
        os.makedirs(folder)
    except OSError:
        pass
    doc = dict(doc)
    doc["fetchedAt"] = int(time.time())
    tmp = path + ".tmp"
    try:
        with io.open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(doc, ensure_ascii=False))
        os.replace(tmp, path)
    except OSError:
        # A cache that cannot be written is not a failure of the feature: the
        # answer was already in hand.  Say nothing and let the next call re-fetch.
        pass


def _thumb(url):
    """Drop the API's empty-thumbnail sentinel; leave real URLs alone."""
    text = (url or "").strip()
    if not text or text.rstrip("/") == THUMB_SENTINEL.rstrip("/"):
        return ""
    return text


def _card(item):
    """One row of the grid, flattened to what the card actually draws.

    The field names come from the official card template, not from guessing:
    the bundle's markup reads `modId`, `modName`, `thumbnail`, `creatorName`,
    `downloads`, `totalRatings` and `ratings.rating.average`.
    """
    rating = item.get("ratings") or {}
    inner = rating.get("rating") or {}
    return {
        "id": item.get("modId") or 0,
        "name": (item.get("modName") or "").strip() or "（没有名字）",
        "thumb": _thumb(item.get("thumbnail")),
        "author": (item.get("creatorName") or "").strip(),
        "avatar": _thumb(item.get("creatorAvatarUrl")),
        "downloads": item.get("downloads") or 0,
        "votes": item.get("totalRatings") or 0,
        "rating": round(float(inner.get("average") or 0), 1),
        "tags": [t for t in (item.get("modTagNames") or []) if t],
        "updated": item.get("lastUpdatedOn") or item.get("creationDate") or "",
        # Not used for any action -- only to write the word 已订阅 / 已下载 on a
        # card when the API volunteers it.  The tool never asks for these states
        # separately, because that would mean calling `Installed` / `My`.
        "installed": bool(item.get("userInstalled")),
    }


def _query_key(payload):
    keys = ("q", "tags", "sort", "order", "start")
    parts = []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            value = ",".join(str(v) for v in value)
        parts.append("%s=%s" % (key, value if value is not None else ""))
    return "&".join(parts)


def find(text="", tags=None, sort="recentpopular", order="DESC", page=1, fresh=False):
    """One page of the catalogue.

    The body mirrors the official client's own `queryParams` object, because the
    server validates it: `{q, game, modid, filter, status, tags, sort, order}`
    wrapped with `{start, count}`.  `game: 2` is AoE2 DE.
    """
    tags = [t for t in (tags or []) if isinstance(t, int)]
    page = max(1, int(page or 1))
    payload = {
        "q": (text or "").strip(),
        "game": AO2_GAME_ID,
        "modid": 0,
        "filter": 0,
        "status": "",
        "tags": tags,
        "sort": sort or "recentpopular",
        "order": order or "DESC",
        "start": (page - 1) * PAGE_SIZE + 1,
        "count": PAGE_SIZE,
    }
    path = _cache_path("find", _query_key(payload))
    if not fresh:
        hit = _cache_read(path)
        if hit is not None:
            return hit

    doc = _call("Find", payload)
    total = doc.get("totalCount") or 0
    mods = [_card(item) for item in (doc.get("modList") or [])]
    out = {
        "ok": True,
        "page": page,
        "pageSize": PAGE_SIZE,
        "total": total,
        "pages": max(1, (int(total) + PAGE_SIZE - 1) // PAGE_SIZE),
        "mods": mods,
        "fetchedAt": int(time.time()),
        "cached": False,
    }
    _cache_write(path, out)
    return out


def detail(mod_id, fresh=False):
    """One mod, plus its screenshots.

    `Detail` is a different shape from the list rows: it carries `imageUrls[]`
    where each entry has `imageName` and `imageThumbnail`.  Both are passed
    through, because the gallery needs the large one and the strip the small one.
    """
    mod_id = int(mod_id or 0)
    path = _cache_path("detail", str(mod_id))
    if not fresh:
        hit = _cache_read(path)
        if hit is not None:
            return hit

    doc = _call("Detail", mod_id)
    body = doc.get("mod") if isinstance(doc.get("mod"), dict) else doc
    if not isinstance(body, dict):
        raise OnlineError("这个模组的详情读不出来。")
    shots = []
    for shot in (body.get("imageUrls") or []):
        if not isinstance(shot, dict):
            continue
        big = _thumb(shot.get("imageName"))
        if big:
            shots.append({"full": big, "thumb": _thumb(shot.get("imageThumbnail")) or big})
    card = _card(body)
    card["shots"] = shots
    card["description"] = (body.get("modDescription") or body.get("description") or "").strip()
    card["url"] = "https://www.ageofempires.com/mods/details/%d/" % mod_id
    out = {
        "ok": True,
        "mod": card,
        "fetchedAt": int(time.time()),
        "cached": False,
    }
    _cache_write(path, out)
    return out


def tags():
    """The tag list, so the filter can be built from the server's own words.

    Anonymous `GET /Tags` is 200 (measured: 3346 bytes), so this works before the
    player signs in and lets the empty state show real filters instead of nothing.
    """
    path = _cache_path("tags", "ao2")
    hit = _cache_read(path)
    if hit is not None:
        return hit
    url = BASE + "/Tags"
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            rows = json.loads(resp.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise OnlineError("标签读不出来：%s" % (exc,))
    out = {
        "ok": True,
        "tags": [{"id": r.get("modTypeId"), "name": r.get("modTypeName")}
                 for r in rows if r.get("gameTitleId") == AO2_GAME_ID],
        "fetchedAt": int(time.time()),
        "cached": False,
    }
    _cache_write(path, out)
    return out


def peek():
    """Everything the page needs on first paint, in one round trip.

    Deliberately does NOT fetch a listing: an unauthenticated player should see
    the sign-in card immediately rather than a spinner that resolves into an
    error.  The first real listing happens when they press 搜索 or the page loads
    with a session already on disk.
    """
    status = session_status()
    try:
        tag_list = tags()
        available = tag_list["tags"]
    except OnlineError:
        available = []
    return {
        "ok": True,
        "signed": status["signed"],
        "at": status["at"],
        "count": status["count"],
        "tags": available,
        "pageSize": PAGE_SIZE,
    }
