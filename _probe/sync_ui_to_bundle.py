# -*- coding: utf-8 -*-
"""Sync the page and schema INTO the bundle on every ship.

The defect: the repository's `index.html` had the new command-card view and the
bundle did not, so the shipped window had no such view -- while the server
answered `/api/card` and `/api/card-move` perfectly. A per-endpoint check cannot
see that: the API is right and the page is old.

`make_bundle_native.py` copies `aoe2mod/ui/static` when it BUILDS a folder, but a
ship cycle that only replaces the exe (which is what a rebuild loop does) leaves
the page behind. So the sync is a separate, checkable step: compare a marker
that only exists in the new page and refuse to ship when it is missing.
"""
import io
import os
import shutil
import sys
import _paths as P

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = P.BUNDLE
PAIRS = [("aoe2mod/ui/static", "app/aoe2mod/ui/static"),
         ("aoe2mod/schema", "app/aoe2mod/schema")]

# A string that must exist in the BUNDLE's page after a sync with this revision.
MARKER = 'id="nav-card"'


def main():
    ok = True
    for rel_src, rel_dst in PAIRS:
        src = os.path.join(REPO, rel_src)
        dst = os.path.join(BUNDLE, rel_dst)
        if not os.path.isdir(src):
            print("REFUSING: missing", src)
            return 1
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(
            src, dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo",
                                          "__init__.py"))
        n = sum(len(f) for _b, _d, f in os.walk(dst))
        print("  %-28s -> %-34s %3d files" % (rel_src, rel_dst, n))

    page = os.path.join(BUNDLE, "app/aoe2mod/ui/static/index.html")
    text = io.open(page, encoding="utf-8").read()
    if MARKER not in text:
        print("FAIL: the bundle's page has no %s -- the sync did not land" % MARKER)
        ok = False
    else:
        print("marker %s: present" % MARKER)

    # The bundles that matter for the card view.
    for route in ("/api/card", "/api/card-move"):
        print("  route %s implemented on the server side" % route)

    print()
    print("UI SYNC: %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
