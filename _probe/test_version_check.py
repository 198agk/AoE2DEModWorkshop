# -*- coding: utf-8 -*-
"""Does 「检查更新」 still answer after the repository it read was emptied?

Reported 2026-11-18 (verbatim): 「检查更新这个问题呢，怎么处理」.  The answer at
that moment was 「连不上 GitHub」, on every machine, forever -- because the check
read `aoe2mod/appversion.py` out of the project's own repository, and that
repository had been emptied on request the day before.  Every raw URL 404ed.

Two things had to change, and this nail holds both:

1. the number now lives in a gist, whose URL does not disappear when a source
   tree does.  The first two sources must be that gist (direct and proxied), and
   no source may be the repository raw path first -- otherwise the check is back
   to depending on a tree that is empty today.
2. `parse_version` must read the gist JSON (`{"version": "1.0"}`) and still read
   the old Python form (`VERSION = "1.0"`), because a reinstated tree should not
   need a second parser.

No network in this file.  `check()` takes an `opener`, which is exactly the seam
that makes the four answers testable without asking GitHub anything: behind /
same / ahead / unreachable.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from aoe2mod import appversion as AV                      # noqa: E402
from aoe2mod import updates as U                          # noqa: E402

FAIL = []


def check(name, ok, detail=None):
    if ok:
        print("  ok   %s" % name)
        return
    FAIL.append(name + ("" if detail is None else " :: %s" % (detail,)))
    print("  FAIL %s%s" % (name, "" if detail is None else " :: %s" % (detail,)))


def opener_for(body):
    """An `opener` that answers `body` for every URL, and records them."""
    seen = []

    def fetch(url, timeout=None):
        seen.append(url)
        if isinstance(body, Exception):
            raise body
        return body

    return fetch, seen


# The cache is a file next to the state records, so a nail that did not move it
# would read (and then rewrite) the real player's folder.
CACHE = tempfile.mkdtemp(prefix="aoe2mod-vc-")
os.environ["AOE2MOD_STATE_DIR"] = CACHE

# ---- 1. where the number comes from ----
first_name, first_url = U.SOURCES[0]
proxy_name, proxy_url = U.SOURCES[1]
check("the first source is the gist, not a repository file",
      "gist" in first_url, first_url)
check("and it is spelled as the raw gist host",
      first_url.startswith("https://gist.githubusercontent.com/"), first_url)
check("the second source is the same gist through the proxy this machine needs",
      "gh-proxy.com" in proxy_url and "gist.githubusercontent.com" in proxy_url,
      proxy_url)
check("no repository raw URL is tried before the gist any more",
      not any("raw.githubusercontent.com" in u for n, u in U.SOURCES[:2]),
      [u for n, u in U.SOURCES[:2]])
check("every source is https",
      all(u.startswith("https://") for n, u in U.SOURCES),
      [u for n, u in U.SOURCES if not u.startswith("https://")])

# ---- 2. the two shapes the parser has to read ----
check("the gist JSON shape parses",
      U.parse_version('{"version": "1.2", "url": "x"}') == "1.2",
      U.parse_version('{"version": "1.2"}'))
check("and the indented form a gist actually serves parses too",
      U.parse_version('{\n "version": "2.7"\n}') == "2.7",
      U.parse_version('{\n "version": "2.7"\n}'))
check("the old appversion.py source shape still parses",
      U.parse_version('VERSION = "0.9"') == "0.9",
      U.parse_version('VERSION = "0.9"'))
check("an empty body or a JSON without a version says so instead of guessing",
      U.parse_version("") == "" and U.parse_version("{}") == "",
      (U.parse_version(""), U.parse_version("{}")))
check("a bare number in the JSON is read, not dropped",
      U.parse_version('{"version": 3}') == "3",
      U.parse_version('{"version": 3}'))

# ---- 3. the four answers, from the seam the tests get ----
fetch, seen = opener_for('{"version": "1.4"}')
got = U.check(current="1.0", force=True, opener=fetch, sources=U.SOURCES)
check("a reachable gist is reported reachable",
      got["ok"] and got["reachable"], got)
check("and the remote number is the gist's",
      got["remote"] == "1.4", got["remote"])
check("a newer gist says behind",
      got["behind"] is True and got["same"] is False,
      (got["behind"], got["same"]))
check("and it names which source answered",
      got["source"] == first_name, got["source"])
check("the first source answering ends the search", len(seen) == 1, len(seen))

fetch, seen = opener_for('{"version": "1.0"}')
got = U.check(current="1.0", force=True, opener=fetch, sources=U.SOURCES)
check("the same number says same, not behind",
      got["same"] is True and got["behind"] is False,
      (got["same"], got["behind"]))

fetch, seen = opener_for('{"version": "0.8"}')
got = U.check(current="1.0", force=True, opener=fetch, sources=U.SOURCES)
check("an older gist is neither behind nor same, it is ahead",
      got["behind"] is False and got["same"] is False,
      (got["behind"], got["same"]))

fetch, seen = opener_for(OSError("no route to host"))
got = U.check(current="1.0", force=True, opener=fetch, sources=U.SOURCES)
check("a dead network is still an answer, not an exception", got["ok"] is True, got)
check("and it says it does not know",
      got["reachable"] is False and got["remote"] is None,
      (got["reachable"], got["remote"]))
check("every source was tried before giving up",
      len(seen) == len(U.SOURCES), "%d of %d" % (len(seen), len(U.SOURCES)))
check("and each failure is named, so a bug report says which host failed",
      len(got["notes"]) == len(U.SOURCES), got["notes"])

# A source that answers with something unreadable must not end the search: a
# proxy serving an HTML error page is the common shape of that.
calls = []


def flaky(url, timeout=None):
    calls.append(url)
    if len(calls) == 1:
        return "<html>404</html>"
    return '{"version": "1.1"}'


got = U.check(current="1.0", force=True, opener=flaky, sources=U.SOURCES)
check("an unreadable first answer falls through to the next source",
      got["reachable"] and got["remote"] == "1.1", got.get("remote"))
check("and it took exactly two requests", len(calls) == 2, len(calls))

# ---- 4. the number the screen prints is the number it compares ----
got = U.check(force=True, opener=opener_for('{"version": "%s"}' % AV.VERSION)[0],
              sources=U.SOURCES)
check("with no argument it compares against the shipped version",
      got["current"] == AV.VERSION, got["current"])
check("so a gist that agrees with this build reads as newest",
      got["same"] is True, got["same"])
check("the cache honours the state-dir override, so a test cannot touch the real one",
      U.cache_path().startswith(CACHE), U.cache_path())

# ---- 5. the player's numbering is decimal, so the compare must be too ----
# 「我每产生新改动，版本号就增加0.0001」 (2026-11-18).  The old `ver_tuple` kept
# two integers and threw the rest away, so 1.0001 and 1.0002 were the same
# number and a freshly published build read as 「已经是最新的」 on every machine.
check("a 0.0001 step compares GREATER than the build before it",
      U.ver_tuple("1.0002") > U.ver_tuple("1.0001"),
      (U.ver_tuple("1.0001"), U.ver_tuple("1.0002")))
check("...and the step below compares LESS",
      U.ver_tuple("1.0001") < U.ver_tuple("1.0002"),
      (U.ver_tuple("1.0002"), U.ver_tuple("1.0001")))
check("a whole minor still outranks every decimal step under it",
      U.ver_tuple("1.1") > U.ver_tuple("1.0999"),
      (U.ver_tuple("1.1"), U.ver_tuple("1.0999")))
check("1.10 is 1.1, not 1.01",
      U.ver_tuple("1.10") == U.ver_tuple("1.1"),
      (U.ver_tuple("1.10"), U.ver_tuple("1.1")))
check("1.0 and 1.0000 are the same build",
      U.ver_tuple("1.0") == U.ver_tuple("1.0000"),
      (U.ver_tuple("1.0"), U.ver_tuple("1.0000")))
check("junk sorts last instead of raising",
      U.ver_tuple("") == (-1, -1) and U.ver_tuple("x") == (-1, -1),
      (U.ver_tuple(""), U.ver_tuple("x")))
check("one decimal step past this build reads as behind",
      U.check(current="1.0001", force=True,
              opener=opener_for('{"version": "1.0002"}')[0],
              sources=U.SOURCES)["behind"] is True, "")

# ---- 6. a version number alone asks the player to download 286 MB blind ----
check("a gist that lists what changed is read",
      U.parse_changes('{"version": "1.0002", "changes": ["a", " b ", ""]}')
      == ["a", "b"],
      U.parse_changes('{"version": "1.0002", "changes": ["a", " b ", ""]}'))
check("the older key name is understood too, so a gist need not be rewritten",
      U.parse_changes('{"version": "1.0002", "notes": ["a"]}') == ["a"],
      U.parse_changes('{"version": "1.0002", "notes": ["a"]}'))
check("one bare sentence is accepted as a one-line list",
      U.parse_changes('{"changes": "只改了一行"}') == ["只改了一行"],
      U.parse_changes('{"changes": "只改了一行"}'))
check("a gist with no changes says so instead of inventing one",
      U.parse_changes('{"version": "1.0002"}') == []
      and U.parse_changes("VERSION = \"1.0\"") == []
      and U.parse_changes("<html>404</html>") == [], "")
check("this build ships its own list, so the page has something to show offline",
      U.local_changes() == [str(x) for x in AV.CHANGES] and len(AV.CHANGES) >= 1,
      U.local_changes())
check("the answer carries the changes next to the number",
      U.check(current="1.0", force=True,
              opener=opener_for('{"version": "1.0002", "changes": ["新东西"]}')[0],
              sources=U.SOURCES)["changes"] == ["新东西"], "")
check("...and falls back to this build's own list when the gist has none",
      U.check(current="1.0", force=True,
              opener=opener_for('{"version": "1.0002"}')[0],
              sources=U.SOURCES)["changes"] == U.local_changes(), "")
check("the local list is reported even when nothing answers",
      U.check(current="1.0", force=True,
              opener=opener_for(OSError("down"))[0],
              sources=U.SOURCES)["changes"] == U.local_changes(), "")

# ---- 6b. 更新日志：关于页要能翻到以前每一版，而不只是手上这一份 ------
# 发布记录是 JSON 数组，每项带 tag_name / name / body / published_at / html_url。
# 这里钉三件事：名字与日期读得出来、正文里的「怎么做的」不会被当成改动、
# 顺序是新的在上（屏幕上第一眼看到的是刚发的这一版）。
RELEASES = json.dumps([
    {"tag_name": "v1.0003", "name": "模组工坊 1.0003", "draft": False,
     "published_at": "2026-11-17T09:12:00Z", "html_url": "https://github.com/x/r/releases/tag/v1.0003",
     "body": "## 这一版改了什么\n\n- 下载新版快多了\n- 装完自己重新打开\n\n版本号规则：每有一轮改动就加 0.0001。\n"},
    {"tag_name": "v1.0002", "name": "模组工坊 1.0002", "draft": False,
     "published_at": "2026-11-16T03:40:00Z", "html_url": "https://github.com/x/r/releases/tag/v1.0002",
     "body": "## 这一版改了什么\n\n* 有新版时可以直接按按钮装好\n"},
    {"tag_name": "v9.9.9", "name": "draft", "draft": True,
     "published_at": "2026-11-18T00:00:00Z", "body": "- 还没发的一版\n"},
], ensure_ascii=False)
rows = U.parse_releases(RELEASES)
check("the release list is read as versions, newest first",
      [r["version"] for r in rows] == ["1.0003", "1.0002"],
      [r["version"] for r in rows])
check("a draft is not a version the player can read",
      "9.9.9" not in [r["version"] for r in rows], [r["version"] for r in rows])
check("each row keeps the date the release was published",
      rows[0]["date"] == "2026-11-17", rows[0]["date"])
check("the bullets are the changes, and the trailing explanation is not",
      rows[0]["notes"] == ["下载新版快多了", "装完自己重新打开"], rows[0]["notes"])
check("a body that uses * instead of - is read the same way",
      rows[1]["notes"] == ["有新版时可以直接按按钮装好"], rows[1]["notes"])
check("a table row or a fenced block is not a change",
      U.parse_releases(json.dumps([{"tag_name": "v2.0", "body":
          "- 真改动\n| 文件 | 大小 |\n```\ncode\n```\n"}]))[0]["notes"] == ["真改动"],
      U.parse_releases(json.dumps([{"tag_name": "v2.0", "body":
          "- 真改动\n| 文件 | 大小 |\n```\ncode\n```\n"}]))[0]["notes"])
check("a body with no bullets falls back to its plain lines",
      U.parse_releases(json.dumps([{"tag_name": "v2.0", "body":
          "## 标题\n只改了一行\n"}]))[0]["notes"] == ["只改了一行"],
      U.parse_releases(json.dumps([{"tag_name": "v2.0", "body":
          "## 标题\n只改了一行\n"}]))[0]["notes"])
check("a wrapper object around the array is accepted too",
      len(U.parse_releases(json.dumps({"releases": [{"tag_name": "v3.0",
          "body": "- 一行"}]}))) == 1, "")
check("garbage is not a changelog",
      U.parse_releases("<html>404</html>") == []
      and U.parse_releases("") == [], "")

fetch, seen = opener_for(RELEASES)
got = U.changelog(force=True, opener=fetch, sources=U.RELEASES_SOURCES)
check("a reachable release list comes back as the whole log",
      got["ok"] and got["reachable"] and len(got["rows"]) == 2, len(got.get("rows") or []))
check("...and it names which address answered",
      got["source"] == U.RELEASES_SOURCES[0][0], got["source"])
check("...with the changes already split into lines",
      got["rows"][0]["notes"][0] == "下载新版快多了", got["rows"][0]["notes"])
got = U.changelog(force=True, opener=opener_for(OSError("down"))[0],
                  sources=U.RELEASES_SOURCES)
check("nothing answering is said out loud, not faked into a list",
      got["reachable"] is False and got["rows"] == U.local_changelog(),
      got.get("notes"))
check("and the fallback is what this copy says about itself",
      U.local_changelog()[0]["version"] == AV.VERSION
      and U.local_changelog()[0]["notes"] == U.local_changes(),
      U.local_changelog())

# ---- 7. the three-part spelling the manifests need, derived not typed ----
check("SEMVER is a three-part version a manifest accepts",
      AV._semver("1.0001") == "1.0.1" and AV._semver("1.0") == "1.0.0"
      and AV._semver("1.1") == "1.0.1000",
      (AV._semver("1.0001"), AV._semver("1.0"), AV._semver("1.1")))
check("...and it agrees with the number this build carries",
      AV.SEMVER == AV._semver(AV.VERSION), (AV.SEMVER, AV.VERSION))


print("FAILED: %s" % FAIL if FAIL
      else "VERSION CHECK: THE ANSWER NO LONGER DEPENDS ON A REPOSITORY THAT CAN BE EMPTIED, AND ALL FOUR ANSWERS ARE DISTINGUISHABLE")
sys.exit(1 if FAIL else 0)