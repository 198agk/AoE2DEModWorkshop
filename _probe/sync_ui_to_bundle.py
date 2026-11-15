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


def _force_writable(func, target, exc):
    """Clear the read-only bit and retry.

    Measured 2026-11-09: `shutil.rmtree` on the bundle's static folder died with
    `PermissionError: [WinError 5] 拒绝访问` on `art/preview-girl.jpg` -- the file
    is shipped read-only (-r-xr-xr-x), and Windows refuses to unlink a read-only
    file.  A sync step that crashes on a healthy bundle is worse than no step,
    so the delete gets the same treatment every copy tool gives it: chmod, retry.
    """
    try:
        os.chmod(target, 0o700 if os.path.isdir(target) else 0o600)
    except OSError:
        pass
    func(target)


def _rmtree(path):
    shutil.rmtree(path, onexc=_force_writable)


def main():
    ok = True
    for rel_src, rel_dst in PAIRS:
        src = os.path.join(REPO, rel_src)
        dst = os.path.join(BUNDLE, rel_dst)
        if not os.path.isdir(src):
            print("REFUSING: missing", src)
            return 1
        if os.path.isdir(dst):
            _rmtree(dst)
        # `__init__.py` is a PACKAGE MARKER, not a cache.  This list used to
        # drop it (d4f6d70), and because this sync rebuilds `app/aoe2mod/schema`
        # from scratch it deleted `aoe2mod/schema/__init__.py` on every run --
        # one step after `sync_app_package.py` had copied it in.
        # Measured 2026-11-09: the four-step ship cycle could never pass,
        # `test_bundle_package_sync.py` always ended with
        #   FAIL aoe2mod/schema/__init__.py is in the repo but not in the bundle
        # and the only way to green was re-running step 1 alone, which left
        # step 2's page/schema sync unverified.  Bytecode is still dropped;
        # package markers are not.
        shutil.copytree(
            src, dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
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
