# -*- coding: utf-8 -*-
"""Every `self.x()` inside the HTTP handler must be a method that exists.

This pins a real bug, not a style rule.  Measured 2026-11-03: the
`/api/mod-move` branch called `self._body()`.  `_body` was never defined --
`do_POST` parses the body into a local named `payload` at the top -- so every
"move mod up/down" request raised `AttributeError` *after* the request had been
matched but *before* any response was written.  The socket closed with no
answer, the browser raised `TypeError: Failed to fetch`, and the screen said
「移不动：Failed to fetch」.  A missing attribute on a code path with no test is
invisible until a player clicks the button, and then it reads as a network
problem rather than as a typo in this file.

The check is structural: parse `aoe2mod/ui/server.py`, find the class defined
inside `make_handler`, and compare the set of `self.<name>(...)` calls against
the methods that class actually defines plus the ones `BaseHTTPRequestHandler`
provides.  It never imports the module, so it can not be fooled by a name that
resolves at runtime through `__getattr__`.
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")

# Provided by `http.server.BaseHTTPRequestHandler`, which the handler subclasses.
BASE = frozenset((
    "send_response", "send_header", "end_headers", "send_error", "log_message",
    "log_request", "log_error", "handle", "handle_one_request", "finish",
    "do_GET", "do_POST", "do_PUT", "do_DELETE", "do_HEAD", "do_OPTIONS",
))


def handler_class(tree):
    for node in tree.body:
        if not (isinstance(node, ast.FunctionDef) and node.name == "make_handler"):
            continue
        for sub in node.body:
            if isinstance(sub, ast.ClassDef) and sub.name == "Handler":
                return sub
    return None


def main():
    fails = []

    def check(ok, what, detail=""):
        print("  %s  %s%s" % ("ok  " if ok else "FAIL", what,
                              "" if not detail else " :: " + detail))
        if not ok:
            fails.append(what)

    src = io.open(SERVER, encoding="utf-8").read()
    tree = ast.parse(src)
    cls = handler_class(tree)
    check(cls is not None, "make_handler defines a Handler class")
    if cls is None:
        print("HANDLER METHODS: THE HANDLER CALLS ONLY METHODS IT HAS")
        return 1

    defined = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
    check("do_GET" in defined and "do_POST" in defined,
          "the handler answers both GET and POST")

    called = set()
    for node in ast.walk(cls):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name)
                and fn.value.id == "self"):
            called.add(fn.attr)
    missing = sorted(called - defined - BASE)
    check(not missing, "every self.<name>() the handler calls is defined",
          "missing: %s" % (missing,))
    check(len(called) >= 3, "the walk actually found the handler's calls",
          "found %d" % len(called))

    # The specific call that broke it must never come back.
    check("_body" not in called,
          "the handler does not call the never-defined self._body()")

    # `_guard` is how a failure becomes a Chinese sentence instead of a dead
    # socket; every app.* route should be wrapped in it.
    at = src.index("class Handler")
    tail = src[at:]
    posts = tail[tail.index("def do_POST"):] if "def do_POST" in tail else ""
    bare = [ln.strip() for ln in posts.splitlines()
            if "return app." in ln and "_guard" not in ln]
    check(not bare, "no route returns an unguarded app.* call",
          "bare: %s" % (bare[:3],))

    if fails:
        print("\nHANDLER METHODS: %d CHECK(S) FAILED -> %s" % (len(fails), fails))
        return 1
    print("\nHANDLER METHODS: THE HANDLER CALLS ONLY METHODS IT HAS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
