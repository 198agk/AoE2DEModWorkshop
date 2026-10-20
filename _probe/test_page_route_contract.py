# -*- coding: utf-8 -*-
"""The page and the server must agree on every request body, in both directions.

Why this exists
---------------
`_probe/ui_page_harness.js` stubs `fetch`, so it proves the page SENDS a request
but never that the request means anything to the real server.  `_probe/
test_ui_server.py` calls the `App` methods directly for install / uninstall, so
it proves the method works but not that the ROUTE passes the right keys through.
Between those two suites there is a hole exactly the shape of a renamed key: the
page posts `{name: ...}`, the route reads `payload["title"]`, the button throws
`KeyError`, and both suites stay green.

The holes are not hypothetical.  `/api/install`, `/api/mod` and `/api/uninstall`
write the player's real mod list, so an HTTP-level test of them cannot be run
safely -- which is precisely why they were the three routes with no assertion
behind them until `profile_root` was threaded through.

So this file asserts the CONTRACT instead of the traffic: read the page's request
literals and the route's `payload` accesses out of the two source files, and
require that they name the same keys.

Rules
-----
1. Every key the page sends must be a key the route reads.  A key nobody reads is
   dead weight that looks like it does something.
2. Every key the route REQUIRES (`payload["k"]`, bracket form) must be sent by
   the page.  A required key the page omits is a 500 on the first click.
3. Every POST route the page calls must exist on the server, and every POST route
   that exists must be reachable from the page or listed as internal.

Parsing the page by regex is ugly; the alternative is a JS parser, and the two
shapes it must understand (object literals in argument position) are simple.  The
one trap is a TERNARY's colon looking like an object key (`man.info.Title ? a :
b`), which is why a key only counts when the character before it is `{` or `,`.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

HTML_PATH = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER_PATH = os.path.join(ROOT, "aoe2mod", "ui", "server.py")

FAILS = []


def check(name, ok, detail=""):
    if ok:
        print("  ok %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s :: %s" % (name, detail))


def _object_at(text, brace):
    """The balanced `{...}` literal that starts at or after `brace`."""
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace:i + 1]
    return ""


def _member_keys(obj):
    """Object-literal member names, ignoring ternaries and dotted lookups."""
    keys = set()
    for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*:", obj):
        before = obj[:m.start()].rstrip()
        if not before or before[-1] not in "{,":
            continue                      # `man.info.Title ? ... : ...` lands here
        keys.add(m.group(1))
    # Shorthand members: `{name, enabled}` names a key without a colon.
    for m in re.finditer(r"[{,]\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?=[,}])", obj):
        keys.add(m.group(1))
    return keys


def page_bodies(html):
    """{route: set(keys)} for every `api("/api/...", { ... })` call."""
    out = {}
    for m in re.finditer(r'api\(\s*"(/api/[a-z\-]+)"\s*,\s*\{', html):
        route = m.group(1)
        obj = _object_at(html, m.end() - 1)
        keys = _member_keys(obj)
        if not keys:
            print("  .. (no literal members found for %s)" % route)
        out.setdefault(route, set()).update(keys)
    return out


def server_reads(src):
    """{route: (required, optional)} for every POST handler.

    Bracket access is required (`payload["mod_dir"]`), `.get` is optional.  The
    GET routes are ignored: they read the query string, not a body.
    """
    out = {}
    posts = src.split("def do_POST(self):", 1)[1]
    # Each branch runs from `if path == "..."` to the next branch or the fallback.
    # The split consumes the newline before the next `if`, so the header has to be
    # cut off by pattern rather than by splitting on the shared prefix: splitting
    # on `"\n            if path =="` left an empty head, and every route then
    # looked like it read nothing (five false failures, all the same cause).
    parts = re.split(r'(?=\n\s*if path == ")', posts)
    for part in parts:
        m = re.match(r'\n\s*if path == "(/api/[a-z\-]+)"\s*:', part)
        if not m:
            continue
        head = part[m.end():]
        required = set(re.findall(r'payload\[\s*"([A-Za-z_]+)"\s*\]', head))
        optional = set(re.findall(r'payload\.get\(\s*"([A-Za-z_]+)"', head))
        out[m.group(1)] = (required, optional)
    return out


def main():
    html = io.open(HTML_PATH, encoding="utf-8").read()
    src = io.open(SERVER_PATH, encoding="utf-8").read()

    sent = page_bodies(html)
    read = server_reads(src)

    print("page posts to %d routes; the server handles %d POST routes"
          % (len(sent), len(read)))

    # ---- rule 3: the route exists ---------------------------------------
    for route in sorted(sent):
        check("the page posts to %s and the server handles it" % route,
              route in read, sorted(read))

    # ---- rule 1: nothing the page sends is ignored ----------------------
    for route, keys in sorted(sent.items()):
        if route not in read:
            continue
        required, optional = read[route]
        stray = sorted(keys - required - optional)
        check("%s reads every key the page sends" % route, not stray,
              "ignored: %s" % stray)

    # ---- rule 2: nothing the route requires is omitted ------------------
    for route, keys in sorted(sent.items()):
        if route not in read:
            continue
        required, _optional = read[route]
        missing = sorted(required - keys)
        check("%s needs no key the page omits" % route, not missing,
              "missing: %s" % missing)

    # ---- the routes with no screen must be named, not forgotten ---------
    # `/api/plan` and `/api/search` are used by `tools/` and by hand, and
    # `/api/uninstall` has no button yet.  Listing them here is the difference
    # between "no screen yet" and "someone forgot the button".
    no_screen = {"uninstall": "no button on the page yet",
                 "plan": "the page reads previews out of /api/parse",
                 "search": "the page browses by picture instead"}
    unsent = sorted(r for r in read if r not in sent)
    unexpected = [r for r in unsent if r.rsplit("/", 1)[-1] not in no_screen]
    check("every POST route the page never calls is a declared decision",
          not unexpected, "unexplained: %s" % unexpected)

    # ---- the parse of the page is not vacuous ---------------------------
    check("the page really does send bodies (not an empty parse)",
          len(sent) >= 4, sorted(sent))
    check("the route side really does read bodies (not an empty parse)",
          len(read) >= 4 and any(r or o for r, o in read.values()),
          sorted(read))
    check("the install call sends the folder it just built",
          "mod_dir" in sent.get("/api/install", set()),
          sorted(sent.get("/api/install", ())))

    print()
    if FAILS:
        print("PAGE/ROUTE CONTRACT: %d CHECK(S) FAILED" % len(FAILS))
        return 1
    print("PAGE/ROUTE CONTRACT: THE PAGE AND THE ROUTES NAME THE SAME KEYS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
