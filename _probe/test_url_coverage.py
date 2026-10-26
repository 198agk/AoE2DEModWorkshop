# -*- coding: utf-8 -*-
"""Every URL the page fetches must exist on the server, and every panel must load.

Why this is separate from `_probe/test_page_route_contract.py`: that file compares
the *keys inside request bodies*.  This one compares the *URLs themselves*.  A
panel whose URL nobody implemented stays silently empty, and the page's own
`catch` -- the same one that handles "no recipes yet" -- swallows the rejection,
so the screen looks like a feature that has no content rather than a feature that
does not exist.

Static text only: no server, no `.dat`, no game.  Cheap enough to run after any
edit to the page or the routes.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")

# `api("/api/forms")` and `api(`/api/icon?...`)` -- the leading slash matters:
# a relative call would resolve against whatever the window's base is.
CALL = re.compile(r"""api\(\s*[`"](/api/[a-z0-9\-]+)""")
# `if path == "/api/meta":` -- the exact-match branches, which is how every route
# in this server is written.
ROUTE = re.compile(r'''if path ==\s*"(/api/[a-z0-9\-]+)"''')

# Panels that load themselves on boot or on a chip.  Each one is a thing a player
# sees; a missing route means a visible empty box, so these are named rather than
# inferred (an inferred set would shrink silently the day a panel is rewritten).
PANELS = ("/api/forms", "/api/recipes", "/api/locale", "/api/update-check",
          "/api/meta", "/api/mods", "/api/ai-meta")


def main():
    page = io.open(PAGE, encoding="utf-8").read()
    server = io.open(SERVER, encoding="utf-8").read()

    called = sorted(set(CALL.findall(page)))
    served = sorted(set(ROUTE.findall(server)))
    fails = []

    def check(name, ok, detail=""):
        if not ok:
            fails.append("%s :: %s" % (name, detail))
        print("%-4s %s%s" % ("ok" if ok else "FAIL", name,
                             "" if ok else "  :: " + str(detail)))

    # A gate over two empty sets passes for the wrong reason.
    check("the page calls a real number of urls", len(called) >= 15, len(called))
    check("the server serves a real number of urls", len(served) >= 20, len(served))

    missing = [u for u in called if u not in served]
    check("every url the page calls is served", not missing, missing)

    for url in PANELS:
        check("the server serves the %s panel" % url, url in served)
        check("the page loads the %s panel" % url, url in called)

    # A route branch that is spelled correctly and answers nothing is the other
    # half of the same failure: the URL resolves, the page renders an empty box.
    #
    # The rule is derived from the 24 routes that exist, not guessed: every one of
    # them either calls into the app object (`app.meta()`, `app.forms(...)`) or
    # builds an inline answer carrying `"ok"`.  A body of
    # `return self._guard(lambda: None)` satisfies a length threshold and answers
    # nothing, so length is the wrong measure -- "does it reach a producer" is.
    for url in served:
        idx = server.index('if path == "%s"' % url)
        nxt = server.find('if path == "/api/', idx + 10)
        body = server[idx:nxt if nxt > 0 else len(server)]
        reaches = ("app." in body) or ('"ok"' in body)
        check("the %s route reaches a producer" % url, reaches,
              body.strip()[:80])

    print()
    if fails:
        print("URL COVERAGE: %d CHECK(S) FAILED -> %s" % (len(fails), fails))
        return 1
    print("URL COVERAGE: EVERY URL THE PAGE CALLS IS SERVED, EVERY PANEL IS LOADED, "
          "AND NO ROUTE IS EMPTY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
