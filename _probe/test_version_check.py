# -*- coding: utf-8 -*-
"""Does 「检查更新」 still answer after the repository it read was emptied?

Reported 2026-11-18 (verbatim): 「检查更新这个问题呢，怎么处理」.  The answer at
that moment was 「连不上 GitHub」, on every machine, forever -- because the check
read `aoe2mod/appversion.py` out of `198agk/aoe2-mod-workshop`, and that
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

print("FAILED: %s" % FAIL if FAIL
      else "VERSION CHECK: THE ANSWER NO LONGER DEPENDS ON A REPOSITORY THAT CAN BE EMPTIED, AND ALL FOUR ANSWERS ARE DISTINGUISHABLE")
sys.exit(1 if FAIL else 0)