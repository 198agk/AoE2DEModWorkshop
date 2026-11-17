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
import html as _html
import io
import json
import os
import re
import time
import urllib.error
import urllib.request

from ..mod import provenance as _PV
from .translate import tag_zh, tag_zh_table

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

# The official "am I signed in" question.  Nothing else answers it truthfully.
#
# Measured 2026-11-16, in the shipped exe: opening the Microsoft door writes an
# `AgeAuthSession` cookie IMMEDIATELY -- `CfDJ8...`, 184 chars -- and that cookie
# belongs to an anonymous visitor.  Counting cookies or looking for that name
# both said "signed in" over a form nobody had filled in, and the very next
# `/Find` came back 401.  This endpoint answers
# `{"username":null,...,"isAuthenticated":false}` for that same cookie and
# `{"username":"<name>",...,"isAuthenticated":true}` once the password is in.
#
# It costs one request and only runs when a jar exists, which is exactly when a
# wrong answer would be visible.
CHECKLOGIN = "https://auth.ageofempires.com/home/checklogin"

# Sentinel the API uses for "this mod has no thumbnail": the URL ends here with
# nothing after it, so an <img> would fetch the directory and paint a broken icon.
THUMB_SENTINEL = "https://cdn.ageofempires.com/aoe/mods/thumb_"

# There is deliberately NO cookie name that means "signed in".  This was the
# first design and it was wrong in production: `AgeAuthSession` is written the
# instant the Microsoft door paints its form, with an anonymous value
# (`CfDJ8...`, 184 chars, measured 2026-11-16 in the shipped exe), so it was
# present before anyone typed a password and the page announced 登录好了 over a
# form.  The only authority on whether a session is real is `CHECKLOGIN`.


class OnlineError(Exception):
    """Something the player can act on: not signed in, offline, or a bad answer."""


def _state_dir():
    return _PV.state_dir()


def session_path():
    return os.path.join(_state_dir(), SESSION_FILE)


def cache_dir():
    return os.path.join(_state_dir(), CACHE_DIR)


def _jar():
    """The cached cookie header and its names, or ("", [], 0).

    Reads the file the shell wrote; never raises.  Returning the names as well
    lets the screen say "8 个 cookie" without any value crossing the boundary.
    """
    target = session_path()
    try:
        doc = json.loads(io.open(target, encoding="utf-8").read())
        jars = doc.get("cookies") or {}
    except (OSError, ValueError, UnicodeDecodeError):
        return "", [], 0
    if not isinstance(jars, dict):
        return "", [], 0
    api = jars.get("api") or ""
    auth = jars.get("auth") or ""
    names = [piece.split("=", 1)[0] for piece in api.split(";") if "=" in piece]
    names += [piece.split("=", 1)[0] for piece in auth.split(";") if "=" in piece]
    header = "; ".join(x for x in (api, auth) if x)
    at = int(doc.get("savedAt") or 0) if isinstance(doc, dict) else 0
    return header, sorted(set(names)), at


# One in-memory cache for the signed-in question, keyed by the exact header it
# was asked with.  The page polls while the login window is open (every 1.5 s in
# the shell, and the card is rebuilt on each miss), so without this a wrong
# answer would arrive 40 times a minute; with it, the server is asked at most
# once per few seconds and only when the jar actually changed.
VERIFY_SECONDS = 4
_VERIFY = {"header": None, "at": 0.0, "signed": False, "why": "anon", "user": ""}


def _verify(header, force=False):
    """Ask the official endpoint whether this jar is a signed-in player.

    Returns (signed, why, username).  `why` is one of "ok", "anon" (cookies
    exist but the account never finished signing in), "offline".
    """
    now = time.time()
    if (not force and _VERIFY["header"] == header
            and now - _VERIFY["at"] < VERIFY_SECONDS):
        return _VERIFY["signed"], _VERIFY["why"], _VERIFY["user"]
    req = urllib.request.Request(CHECKLOGIN)
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "application/json")
    req.add_header("Cookie", header)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            doc = json.loads(resp.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError):
        # Do not cache a network failure as an answer: the next poll a second
        # later may well be fine, and "offline" is a state the page can explain.
        return False, "offline", ""
    signed = bool(doc.get("isAuthenticated"))
    user = doc.get("username") or ""
    _VERIFY.update({"header": header, "at": now,
                    "signed": signed, "why": "ok" if signed else "anon",
                    "user": user})
    return signed, "ok" if signed else "anon", user


def session_status(force=False):
    """What the screen needs to know about the borrowed session.

    Never returns cookie values -- only whether the account is really signed in,
    since when the jar was taken, and how many cookies it holds.  The signed
    question is answered by `checklogin`, not by looking at cookie names: the
    Microsoft door writes an anonymous `AgeAuthSession` the instant it opens.
    """
    header, names, at = _jar()
    target = session_path()
    if not header:
        return {"signed": False, "why": "anon", "at": 0, "count": 0,
                "user": "", "path": target}
    signed, why, user = _verify(header, force=force)
    return {"signed": signed, "why": why, "at": at, "count": len(names),
            "user": user, "path": target}


def _cookie_header():
    """The header to send upstream, or the sentence that explains why not."""
    header, names, _at = _jar()
    if not header:
        raise OnlineError("还没有登录。点「登录账号」，登录完再回来。")
    signed, why, _user = _verify(header)
    if signed:
        # The session cookie is domain-wide, so it belongs in the api jar -- but
        # the jar split comes from two separate `cookies_for_url` reads, and a
        # host-only Set-Cookie lands only in the jar of the host that sent it.
        # Both jars are already joined here for that reason.
        return header
    if why == "offline":
        raise OnlineError("连不上官方服务器，登录状态没法确认。")
    raise OnlineError("登录还没完成。在登录窗口里把账号和密码填完，再回来。")


def signout():
    """Forget the borrowed session, on this side of the boundary.

    Two things have to go and they live in different places:

      * the cookie jar in the shell's WebView2 profile -- that is
        `online_signout` in `desktop/src-tauri/src/online.rs`, because only the
        shell can reach it;
      * `online-session.json` plus this module's cache, which is what the engine
        reads on every call.

    Doing the second here rather than in Rust means the removal happens even
    when the page is open in a plain browser (no shell, no `invoke`), which is
    how the dev server is used.  Doing it here as well as there is deliberate:
    a file that survives a sign-out is exactly the thing a player would be
    right to complain about.

    The whole cache directory goes, not just the session: every `find-*.json`
    and `detail-*.json` in there was fetched with the account's cookie, and
    leaving a catalogue behind would preserve "what this account looked at"
    after the account is gone.
    """
    removed = {"file": False, "cache": 0}
    for path in (session_path(),):
        try:
            os.remove(path)
            removed["file"] = True
        except OSError:
            pass
    folder = cache_dir()
    try:
        for name in os.listdir(folder):
            if not name.endswith(".json"):
                continue
            try:
                os.remove(os.path.join(folder, name))
                removed["cache"] += 1
            except OSError:
                pass
    except OSError:
        pass
    # The in-memory verdict belongs to the cookie header that just went away;
    # keeping it would let a stale `signed: True` answer the next `peek`.
    _VERIFY.update({"header": None, "at": 0.0, "signed": False,
                    "why": "anon", "user": ""})
    return {"ok": True, **removed, "signed": False}


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


# `modDescription` is HTML, not text -- and not clean HTML either.
#
# Measured 2026-11-16 against seven real Detail responses: the field holds a
# fragment of the author's rich-text editor, so `<p>`, `<br />` and `&nbsp;`
# arrive intact, and two of the seven ALSO carry the editor's own formatting
# debris welded into the markup:
#
#   modId 408773  `<p>######## style="vertical-align: inherit;"&gt;<span style=
#                "vertical-align: inherit;"><span ...>` -- the tag name was eaten
#                by the editor, leaving `########` and ~40 nested spans
#   modId 211486  `## style="padding-left: 40px;">来自影之诗的黑暗贞德</p>`
#
# Rendering that as text produced exactly what the screenshot in the report
# showed: a wall of `style="vertical-align: inherit;"` with the actual sentence
# buried in the middle.  Tolerating it (rather than sanitising it) would mean
# shipping an HTML renderer that runs a stranger's markup, so the opposite is
# done here: every tag is dropped, entities are decoded, and the two kinds of
# debris are removed by pattern because no legitimate description needs a bare
# `style=` or a run of `####`.
_BREAK = re.compile(
    r"<\s*(?:br|hr)\s*/?\s*>|<\s*/?\s*(?:p|div|li|ul|ol|tr|td|h[1-6]|blockquote)\b[^>]*>",
    re.I)
_TAG = re.compile(r"<[^>]{0,600}>")
# A declaration left behind after its angle bracket vanished: `vertical-align:
# inherit;` / `padding-left: 40px;` / `color:#333`.
_DECL = re.compile(
    r"(?:vertical-align|text-align|text-decoration|font-size|font-family"
    r"|font-weight|font-style|line-height|letter-spacing|color|background"
    r"(?:-color|-image)?|margin(?:-left|-right|-top|-bottom)?|padding(?:-left"
    r"|-right|-top|-bottom)?|border(?:-[a-z]+)?|display|position|width|height"
    r"|float|clear|white-space|list-style(?:-type)?)"
    r"\s*:\s*[^;<>\"']{0,48};?", re.I)
# `style=` / `class=` whose tag name was eaten, plus the orphan `>` of that tag.
_ATTR = re.compile(r"\b(?:style|class|dir|lang|align)\s*=\s*[\"']{0,2}", re.I)
_DEBRIS = re.compile(r"#{2,}\s*")            # the eaten tag name above
_STRAY_GT = re.compile(r"[\"']\s*>")


def _plain(raw):
    """The description as readable paragraphs, or "" when there is nothing.

    Blank lines are preserved (the page renders them with `white-space:
    pre-wrap`), but runs of them collapse to one and leading/trailing ones go:
    modId 408773 has nine consecutive `&nbsp;` paragraphs, which as text would
    be twenty empty lines before the first sentence.
    """
    text = raw or ""
    if not text:
        return ""
    # CRLF arrives as `\r\n` and leaves a lone `\r` behind once the newline is
    # split on, which shows up as a line holding one invisible character -- a
    # "blank" line the trim below cannot recognise.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _BREAK.sub("\n", text)
    text = _TAG.sub("", text)
    text = _html.unescape(text)
    text = _DECL.sub("", text)
    text = _ATTR.sub("", text)
    text = _DEBRIS.sub("", text)
    text = _STRAY_GT.sub("", text)
    text = text.replace("\xa0", " ").replace("\u200b", "")
    lines = []
    blank = 0
    for line in text.split("\n"):
        line = re.sub(r"[ \t]{2,}", " ", line).strip(" \t\"'>")
        if not line:
            blank += 1
            if blank > 1 or not lines:
                continue
            lines.append("")
            continue
        blank = 0
        lines.append(line)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


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
        # The API's own names are `lastUpdate` and `createDate` (ISO 8601 with no
        # timezone suffix, e.g. "2025-08-13T14:31:28.84").  This line used to read
        # `lastUpdatedOn` / `creationDate`, which do not exist on any response --
        # the cards carried an empty date for weeks because of it.  The official
        # detail template uses the same two keys under the label "Created On".
        "updated": item.get("lastUpdate") or item.get("createDate") or "",
        "created": item.get("createDate") or "",
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
        # `start` is NOT a row offset: the catalogue server multiplies it by
        # `count` itself.  Measured against the live service (2026-11-16):
        # start=2, count=24 returns rows 25..48, and the highest start that
        # still answers at count=24 is 1722 == ceil(total / 24).  So `start`
        # carries the 1-based page number, and the offset the server uses is
        # exactly (start - 1) * count.
        "start": page,
        "count": PAGE_SIZE,
    }
    path = _cache_path("find", _query_key(payload))
    if not fresh:
        hit = _cache_read(path)
        if hit is not None:
            return hit

    doc = _call("Find", payload)
    total = doc.get("totalCount")
    if total is None and page > 1:
        # Past the last page the catalogue answers `totalCount: null` rather than
        # an empty page, so the screen would fall back to "第 1 / 1 页" over an
        # empty grid.  One extra call to page 1 is the only way the server tells
        # us how big the catalogue actually is, and only an out-of-range page
        # ever pays for it.
        probe = _call("Find", dict(payload, start=1))
        total = probe.get("totalCount")
        doc = {"modList": []}
    total = total or 0
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
            # Cleaned again on the way out, not only on the way in: entries
            # written before `_plain` existed still hold the raw HTML, and a
            # cache that outlives a fix is how the same bug gets reported twice.
            card = hit.get("mod")
            if isinstance(card, dict):
                card["description"] = _plain(card.get("description") or "")
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
    card["description"] = _plain(
        body.get("modDescription") or body.get("description") or "")
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
        "tags": [{"id": r.get("modTypeId"), "name": r.get("modTypeName"),
                  # The Chinese for the tag travels with the tag.  There are
                  # seventeen of them and they never change, so this is a table
                  # lookup, not a request to the translator: sending "Data Mod"
                  # off to be machine-translated on every page load would cost
                  # the free daily allowance for an answer we already know.
                  "zh": tag_zh(r.get("modTypeName"))}
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
        "why": status["why"],
        "at": status["at"],
        "count": status["count"],
        "user": status["user"],
        "tags": available,
        # The name -> Chinese table for the pills on the cards.  The tag list
        # above only holds what `/Tags` returns; a listing also carries
        # "Official" and the occasional singular "Scenario", and those have to
        # read in Chinese too.
        "tagZh": tag_zh_table(),
        "pageSize": PAGE_SIZE,
    }
