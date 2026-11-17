# -*- coding: utf-8 -*-
"""Is there a newer release of the workshop itself?

Why this is NOT ``Toolkit.update_check``
---------------------------------------
The route next door (``/api/update-check``) answers a local question: has the
GAME's data moved under a mod we installed, so that the mod's own copy of the
.dat now shadows a patch?  It costs a file hash and never touches the network.

This module answers the other question a player asks on the 关于 page: is there
a newer build of the TOOL?  The two are independent -- the game can patch while
no new build exists, and a new build can ship the day after a patch -- so they
are two routes and two answers.  Merging them would make one screen lie about
the other.

Why a gist and not the repository
---------------------------------
The check used to read ``aoe2mod/appversion.py`` out of the repository.  On
2026-11-17 that repository was emptied on request, so both spellings of the raw
URL started answering 404 and the only reachable answer became 「连不上」 --
technically true, useless to a player.

A gist is its own object with its own URL.  It is not a file in a source tree,
so it does not disappear when the tree does, and it does not require the
repository to be public or to exist at all for the check to work.  The file it
serves is ``version.json``:

    {"version": "1.0", "url": "https://github.com/..."}

The number is the one the screen prints (``aoe2mod.appversion.VERSION`` on this
side, ``version`` in the gist on the other).  Publishing a build means bumping
both; a release that forgets makes the check say "已经是最新的" rather than
inventing a second answer, which is the failure this project prefers.

``parse_version`` still understands the old ``VERSION = "1.0"`` source form, so
a tree that reinstates ``appversion.py`` keeps working without another edit.

Never raises
------------
``check()`` returns a dict on every path, including a dead network.  A version
check that throws would either take the 关于 page down or force the caller to
wrap it in try/except and invent its own wording; both are worse than an answer
that says 「连不上」.
"""
import json
import os
import re
import time

#: The repository this project is published from.  The number itself does not
#: live here any more (see GIST below); this is only where a player is sent when
#: there is something newer, and the last two SOURCES spellings keep working if
#: the plain repo file ever comes back.
REPO = "198agk/AoE2ModWorkshop"
BRANCH = "main"

#: The number now lives in a gist, not in the repository.
#:
#: Why: on 2026-11-17 the repository was emptied on request, so every
#: ``raw.githubusercontent.com`` URL below started answering 404 and the check
#: could only ever say 连不上.  A gist is a separate object with its own URL
#: that survives the repository it used to sit in, so the answer no longer
#: depends on what a source tree happens to contain today.
GIST = "8826376f54bf41d00d62a6bec6650b27"
GIST_FILE = "version.json"

SOURCES = (
    ("gist.githubusercontent.com",
     "https://gist.githubusercontent.com/198agk/%s/raw/%s" % (GIST, GIST_FILE)),
    ("gh-proxy.com (gist)",
     "https://gh-proxy.com/https://gist.githubusercontent.com/198agk/%s/raw/%s"
     % (GIST, GIST_FILE)),
    ("raw.githubusercontent.com",
     "https://raw.githubusercontent.com/%s/%s/aoe2mod/appversion.py"
     % (REPO, BRANCH)),
    ("cdn.jsdelivr.net",
     "https://cdn.jsdelivr.net/gh/%s@%s/aoe2mod/appversion.py" % (REPO, BRANCH)),
)

#: The page a player goes to when there IS something newer.  Printed, not
#: followed: the check never downloads or installs anything.
PROJECT_URL = "https://github.com/%s" % REPO

UA = "aoe2mod-updater/1 (+https://github.com/%s)" % REPO
TIMEOUT = 6.0

CACHE_FILE = "update.json"
#: Six hours.  The switch on the 设置 page is called 「每次启动检查更新」, and a
#: player who restarts the tool six times in a minute should not make six
#: requests; the manual chip bypasses this cache, because a press of 检查更新
#: means "now", not "whenever you last looked".
CACHE_SECONDS = 6 * 3600

STATE_DIR_ENV = "AOE2MOD_STATE_DIR"
STATE_DIR_ENV_NATIVE = "AOE2MOD_STATE"

#: ``VERSION = "1.0"`` on its own line, quoted with either kind of quote.
_VERSION_RE = re.compile("(?m)^[ \t]*VERSION[ \t]*=[ \t]*(.+?)[ \t]*$")
_NUM_RE = re.compile("([0-9]+)(?:[.]([0-9]+))?")


def state_dir():
    """Where the cache goes: the same folder the build records use.

    Spelled out here rather than imported from ``aoe2mod.mod.provenance``
    because that module pulls in the emitter chain, and this one is read on the
    about page before anything is built.  The two env names are the same two
    overrides, for the same reason: a test that isolated its build records with
    ``AOE2MOD_STATE`` must not have this check write into the player's real
    folder.
    """
    override = (os.environ.get(STATE_DIR_ENV)
                or os.environ.get(STATE_DIR_ENV_NATIVE))
    if override:
        return os.path.abspath(override)
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "aoe2de-mod-workshop")


def cache_path():
    return os.path.join(state_dir(), CACHE_FILE)


def ver_tuple(text):
    """``"1.10"`` -> ``(1, 10)``.  Unparseable sorts last, never raises.

    A string compare puts 1.10 before 1.9 and would report a newer build as
    older, which is the one wrong answer that makes a player stop pressing the
    button.
    """
    m = _NUM_RE.search(str(text or ""))
    if not m:
        return (-1, -1)
    return (int(m.group(1)), int(m.group(2) or 0))


def parse_version(text):
    """The version in the fetched body, whichever shape it arrived in.

    Two shapes because two upstreams exist.  The gist serves JSON
    (``{"version": "1.0", ...}``); a repository tree would serve Python
    (``VERSION = "1.0"``).  Reading both here means the source list can gain
    either one without a second parser, and a test can feed it either.
    """
    body = (text or "").strip()
    if body.startswith("{"):
        try:
            doc = json.loads(body)
        except ValueError:
            doc = None
        if isinstance(doc, dict):
            value = doc.get("version")
            if value is None:
                return ""
            return str(value).strip().strip("\"'").strip()
    m = _VERSION_RE.search(body)
    if not m:
        return ""
    value = m.group(0).split("=", 1)[-1].strip()
    return value.strip("\"'").strip()


def _fetch(url, timeout=TIMEOUT):
    """One GET, decoded as UTF-8.  Raises; ``check()`` is where it is caught."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(65536)
    return raw.decode("utf-8-sig", "replace")


def _read_cache():
    try:
        with open(cache_path(), "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _write_cache(doc):
    """Best effort.  A read-only folder must not break the check."""
    path = cache_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        pass


def _answer(current, reachable, source=None, url=None, remote="",
            notes=None, cached=False):
    cur = str(current or "")
    behind = bool(reachable and remote and ver_tuple(remote) > ver_tuple(cur))
    same = bool(reachable and remote and ver_tuple(remote) == ver_tuple(cur))
    return {
        "ok": True,
        "reachable": bool(reachable),
        "cached": bool(cached),
        "current": cur,
        "remote": remote or None,
        "behind": behind,
        "same": same,
        "source": source,
        "url": url,
        "project_url": PROJECT_URL,
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "notes": list(notes or []),
    }


def check(current=None, force=False, timeout=TIMEOUT, opener=None,
          sources=None, cache_dir=None):
    """Is there a newer build upstream than ``current``?

    ``current`` defaults to ``aoe2mod.appversion.VERSION`` -- the same constant
    the screen prints -- so the two can never disagree.

    ``opener`` is a callable ``(url, timeout) -> text``; tests use it so this
    file needs no network and no monkeypatching of ``urllib``.
    """
    if current is None:
        from . import appversion as AV
        current = AV.VERSION
    fetch = opener or _fetch

    if not force:
        doc = _read_cache()
        if doc and str(doc.get("current") or "") == str(current):
            age = time.time() - float(doc.get("at") or 0)
            if 0 <= age < CACHE_SECONDS and doc.get("reachable"):
                return _answer(current, True, source=doc.get("source"),
                               url=doc.get("url"),
                               remote=doc.get("remote") or "",
                               notes=["来自本机缓存（%d 分钟前）" % int(age // 60)],
                               cached=True)

    notes = []
    for name, url in (sources or SOURCES):
        try:
            text = fetch(url, timeout)
        except Exception as exc:
            notes.append("%s 连不上：%s" % (name, str(exc)[:120]))
            continue
        remote = parse_version(text)
        if not remote:
            notes.append("%s 读到了内容，里面没有版本号" % name)
            continue
        _write_cache({"at": time.time(), "current": str(current),
                      "remote": remote, "source": name, "url": url,
                      "reachable": True})
        return _answer(current, True, source=name, url=url, remote=remote,
                       notes=notes)

    _write_cache({"at": time.time(), "current": str(current),
                  "reachable": False})
    return _answer(current, False, notes=notes or ["没有一个地址连得上"])
