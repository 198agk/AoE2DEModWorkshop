"""Turning the workshop's English into Chinese, without a key or an account.

Two different problems live here and they get two different answers:

  * **Tag names.**  There are exactly seventeen of them in Age of Empires II
    (ids 9-30), they never change, and the official `Tags` endpoint already
    hands back their ids.  A local table is instant, exact, and costs nothing --
    machine-translating "Data Mod" on every page load would be worse in every
    way.

  * **Everything else.**  A mod's name and description are written by its
    author, in whatever language and with whatever typos.  That needs a real
    translator, and there is no key on this machine, so the backend is
    `api.mymemory.translated.net` -- measured 2026-11-16 as the only endpoint
    that answers from here (`translate.googleapis.com` returns nothing at all,
    youdao's legacy route returns an empty body, `cn.bing.com/ttranslatev3`
    wants a token it will not give out).

MyMemory's free tier counts **bytes**, not characters, and refuses a single
query of about 500 bytes.  So long text is split on sentence boundaries first
and reassembled, which also keeps a half-translated paragraph from happening
when one chunk is rejected.

Nothing here raises on a network problem.  A translator that can take the
workshop page down with it would be worse than no translator, so every entry
point returns the original text when it has nothing better.
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.mymemory.translated.net/get"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
# The documented ceiling is 500 bytes; staying under it keeps us out of the
# "QUERY LENGTH LIMIT EXCEEDED" branch entirely.
LIMIT = 460
TIMEOUT = 12
# One request per chunk would be a crawl for a long description, and the free
# tier has a daily word budget.  A translated paragraph is worth keeping for a
# week: re-typing a description is a rare event, and a stale translation of a
# mod nobody has edited is still the right answer.
CACHE_DAYS = 7

# Age of Empires II's mod tags, from `GET /api/v4/mods/Tags` filtered to
# `gameTitleId == 2` (read 2026-11-16: 17 rows).  Kept as a table rather than
# fetched because the mapping is a translation, not a datum: the ids are stable,
# and the Chinese word for "Taunt" will not arrive over the wire.
TAG_ZH = {
    9: "人工智能",
    10: "战役",
    11: "数据模组",
    12: "图像",
    13: "影片",
    14: "音乐",
    15: "随机地图",
    16: "场景",
    17: "音效",
    18: "语音",
    19: "嘲讽语音",
    20: "地形",
    21: "菜单背景",
    22: "用户界面",
    23: "文本",
    26: "其他",
    30: "罗马复兴",
}

# The same table read the other way, for the strings the listing carries: a
# card's `tags` field is tag *names*, not ids, so the name is the only handle
# there is.  Written out rather than derived from `TAG_ZH`, because that table
# is keyed by id and maps English to Chinese -- inverting it would only ever
# match Chinese input, which is the one case that never needs a lookup.
# Lowercased because one stray capital is not a different tag.
TAG_ZH_BY_NAME = {
    "artificial intelligence": "人工智能",
    "campaign": "战役",
    "data mod": "数据模组",
    "graphics": "图像",
    "movie": "影片",
    "music": "音乐",
    "random maps": "随机地图",
    "scenarios": "场景",
    "sounds": "音效",
    "speech": "语音",
    "taunt": "嘲讽语音",
    "terrain": "地形",
    "menu background": "菜单背景",
    "user interface": "用户界面",
    "text": "文本",
    "other": "其他",
    "return of rome": "罗马复兴",
    # Two names the listing carries that the tag endpoint does not: "Official"
    # is stamped on entries the studio published itself, and a few mods come
    # back with the singular "Scenario".  Both are still our vocabulary, so
    # they belong in this table rather than on a card in English.
    "official": "官方",
    "scenario": "场景",
}


class TranslateError(Exception):
    """Carries a sentence meant to be read by the player."""


def tag_zh(name):
    """The Chinese for a tag name, or "" when the tag is not one of ours."""
    return TAG_ZH_BY_NAME.get((name or "").strip().lower(), "")


def tag_zh_table():
    """The whole name table, for the page.

    A card's tag pills are drawn from the listing, and the listing carries a
    couple of names the `/Tags` endpoint never returns ("Official" is stamped
    on the studio's own mods, and some entries say "Scenario").  Sending the
    table down with `peek` means those still read in Chinese instead of leaving
    one English word in a row of Chinese ones -- and it costs a few hundred
    bytes once, against a translator request per page.
    """
    return dict(TAG_ZH_BY_NAME)


def cache_dir():
    root = os.environ.get("AOE2MOD_STATE_DIR")
    if not root:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        root = os.path.join(base, "aoe2de-mod-workshop")
    path = os.path.join(root, "zh")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


def _key(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]


def _read(key):
    path = os.path.join(cache_dir(), key + ".json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return ""
    if not isinstance(doc, dict):
        return ""
    # A cache with no expiry would pin a machine translation forever, and the
    # upstream does correct bad ones.
    at = doc.get("at") or 0
    if CACHE_DAYS and time.time() - at > CACHE_DAYS * 86400:
        return ""
    return doc.get("zh") or ""


def _write(key, text, zh):
    path = os.path.join(cache_dir(), key + ".json")
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"at": int(time.time()), "en": text[:400], "zh": zh}, fh)
        os.replace(tmp, path)
    except OSError:
        pass


# Sentence-ish boundaries, longest first.  Split AFTER the marker so the
# punctuation survives into the Chinese ("。" is dropped by the joiner below,
# which is deliberate: two chunks that each end in a comma read wrong when
# concatenated with a period in between).
_SPLIT = re.compile(r"(?<=[。！？；])|(?<=[.!?;])\s+|\n{2,}")


def _chunks(text, limit=LIMIT):
    """Break on sentence ends, then on words, so no chunk exceeds `limit` bytes."""
    out = []
    for piece in _SPLIT.split(text):
        piece = (piece or "").strip()
        if not piece:
            continue
        while len(piece.encode("utf-8")) > limit:
            # No sentence end in reach: fall back to the last space that fits.
            cut = limit
            while cut > 0 and len(piece[:cut].encode("utf-8")) > limit:
                cut -= 1
            space = piece.rfind(" ", 0, cut)
            if space <= 0:
                space = cut
            out.append(piece[:space].strip())
            piece = piece[space:].strip()
        if piece:
            out.append(piece)
    return out


def _one(text):
    """One chunk through the API, or "" when it declined."""
    url = API + "?" + urllib.parse.urlencode({"q": text, "langpair": "en|zh-CN"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as fh:
            doc = json.loads(fh.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError):
        return ""
    if not isinstance(doc, dict):
        return ""
    # `quotaFinished` goes true at the end of the day's free allowance, and the
    # body then holds an apology in `translatedText` rather than a translation.
    if doc.get("quotaFinished"):
        return ""
    body = doc.get("responseData")
    if not isinstance(body, dict):
        return ""
    zh = body.get("translatedText") or ""
    if not isinstance(zh, str):
        return ""
    if "MYMEMORY WARNING" in zh.upper() or "QUERY LENGTH LIMIT" in zh.upper():
        return ""
    return zh.strip()


def to_zh(text, fresh=False):
    """Chinese for `text`.  Returns the input unchanged when nothing works.

    The `unchanged` flag travels with the answer so the page can say "this one
    could not be translated" instead of silently showing English under a button
    labelled 译成中文.
    """
    text = (text or "").strip()
    if not text:
        return {"zh": "", "cached": False, "translated": True}
    # Nothing to do for text that is already mostly Chinese -- and asking the
    # API to "translate" Chinese wastes the whole daily budget on it.
    han = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    if han >= max(4, len(text) // 5):
        return {"zh": text, "cached": False, "translated": True}

    key = _key(text)
    if not fresh:
        hit = _read(key)
        if hit:
            return {"zh": hit, "cached": True, "translated": True}

    parts = []
    for chunk in _chunks(text):
        one = _one(chunk)
        # A declined chunk keeps its English rather than dropping out: losing a
        # sentence of the description is worse than leaving it untranslated.
        parts.append(one or chunk)
    zh = ""
    for part in parts:
        if not part:
            continue
        if not zh:
            zh = part
        elif zh[-1:] in "。！？；：）」" or part[:1] in "。！？；：，、）":
            zh += part
        elif re.match(r"[A-Za-z0-9]", part[:1]) and re.search(r"[A-Za-z0-9]$", zh[-1:]):
            zh += " " + part
        else:
            zh += part
    zh = zh.strip()
    translated = zh != text
    if translated:
        _write(key, text, zh)
    return {"zh": zh, "cached": False, "translated": translated}


def blurb(text, fresh=False):
    """`to_zh` with the failure spelled out, for the page to show as-is."""
    try:
        return to_zh(text, fresh=fresh)
    except TranslateError as exc:
        return {"zh": text or "", "cached": False, "translated": False,
                "why": str(exc)}
