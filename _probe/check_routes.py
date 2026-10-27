# -*- coding: utf-8 -*-
"""Cross-check: every route the page calls must exist in server.rs, and vice versa.

The meta rewrite replaced a range that turned out to contain `/api/mods`, so a
working route vanished and only the gate caught it. A range replace is exactly
the kind of edit that silently eats its neighbours; this check makes the loss
visible without waiting for a test to fail.
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SERVER = os.path.join(ROOT, "desktop", "aoe2mod-serve", "src", "server.rs")
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")

src = io.open(SERVER, encoding="utf-8").read()
page = io.open(PAGE, encoding="utf-8").read()

implemented = set(re.findall(r'^\s*"(/api/[a-z-]+)"\s*=>', src, re.M))
implemented |= {"/" , "/loading"} if '"/loading" =>' in src else set()

called = set(re.findall(r'"(/api/[a-z-]+)"', page))

missing = sorted(called - implemented)
# Some URLs are assembled by concatenation in the page ("/api/icon?kind=..."),
# so a literal scan cannot see them; those are not "unused".
CONCATENATED = {"/", "/api/browse", "/api/describe", "/api/icon",
                "/api/progress", "/api/stat"}
extra = sorted(implemented - called - {"/loading"} - CONCATENATED)

print("page calls %d routes, server implements %d" % (len(called), len(implemented)))
print()
if missing:
    print("MISSING (page calls, server does not answer):")
    for m in missing:
        print("   ", m)
else:
    print("MISSING: none")
print()
if extra:
    print("EXTRA (server answers, page never calls):")
    for m in extra:
        print("   ", m)
else:
    print("EXTRA: none")

# The three that are known and deliberate.
KNOWN_DELIBERATE = {"/api/ai-sentences", "/api/repair-check", "/api/repair-apply"}
unexplained = [m for m in missing if m not in KNOWN_DELIBERATE]
print()
if unexplained:
    print("UNEXPLAINED MISSING: %s" % unexplained)
    raise SystemExit(1)
print("route cross-check: OK (%d deliberately absent: %s)"
      % (len(KNOWN_DELIBERATE), ", ".join(sorted(KNOWN_DELIBERATE))))
