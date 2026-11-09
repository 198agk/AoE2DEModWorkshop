# -*- coding: utf-8 -*-
"""The bundle's Python copy must be the repository's Python.

WHY THIS EXISTS
---------------
The shipped exe prefers a Python engine when it can find one: `engine_root()` in
`desktop/src-tauri/src/main.rs` looks for `tools/run_ui.py` beside the exe and
runs it with `--serve-only --parent-pid`.  Every `_probe/test_*_shipped.py`
therefore talks to `<bundle>/app/aoe2mod/`, not to the repository.

That makes a STALE COPY the most expensive kind of red in this project: the
repository is green, the exe answers with last week's reader, and a hundred
suites report bugs that were fixed days ago.  It has happened -- `ui/nl.py`
was 2 KB behind, and it was found by accident while chasing something else.

`_probe/sync_app_package.py` copies the tree; this suite is the pin that says
somebody ran it.  Both directions are checked, because a file that exists only
in the bundle is just as much a lie about what ships.

Run:  python -X utf8 _probe/test_bundle_package_sync.py
"""
import filecmp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import _paths as P  # noqa: E402

IGNORE_DIRS = {"__pycache__", ".mypy_cache", ".pytest_cache"}
IGNORE_EXT = {".pyc", ".pyo"}


def walk(root):
    """Relative posix paths of every shipped file under `root`.

    `aoe2mod/tests/out/` is skipped exactly as `sync_app_package.py` skips it:
    it is where the test suites write their own mod folders (each with a 93 MB
    `.dat`), so it holds test OUTPUT, not shipped source.  Comparing it would
    fail every time a suite runs and teach people to ignore this pin.
    """
    out = set()
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        rel_base = os.path.relpath(base, root).replace(os.sep, "/")
        if rel_base == "tests" and "out" in dirs:
            dirs.remove("out")
        for f in files:
            if os.path.splitext(f)[1] in IGNORE_EXT:
                continue
            full = os.path.join(base, f)
            out.add(os.path.relpath(full, root).replace(os.sep, "/"))
    return out


def main():
    app = os.path.join(P.BUNDLE, "app")
    if not os.path.isdir(app):
        print("SKIP: no bundle at %s (nothing has been packaged here yet)"
              % P.BUNDLE)
        return 0

    fails = []
    checked = 0
    for name in ("aoe2mod", "tools"):
        src = os.path.join(ROOT, name)
        dst = os.path.join(app, name)
        if not os.path.isdir(dst):
            fails.append("%s is missing from the bundle" % name)
            continue
        a, b = walk(src), walk(dst)
        only_src = sorted(a - b)
        only_dst = sorted(b - a)
        for rel in only_src[:12]:
            fails.append("%s/%s is in the repo but not in the bundle" % (name, rel))
        for rel in only_dst[:12]:
            fails.append("%s/%s is in the bundle but not in the repo" % (name, rel))
        for rel in sorted(a & b):
            sa = os.path.join(src, rel.replace("/", os.sep))
            sb = os.path.join(dst, rel.replace("/", os.sep))
            checked += 1
            # `shallow=False`: same size and same mtime is not the same file, and
            # a copied tree keeps mtimes.
            if not filecmp.cmp(sa, sb, shallow=False):
                fails.append("%s/%s differs" % (name, rel))

    # The package must not carry build OUTPUT.  A suite that runs the shipped
    # exe without `AOE2MOD_BUILD_OUT` writes `<bundle>/app/_mods_out/<title>/`
    # (93 MB each), and on 2026-11-02 the 50.9 MB package had grown to 1.7 GB
    # with 77 test runs inside it.  Nobody notices, because the exe still works.
    import make_bundle as MB
    strays = MB.stray_output(app)
    if strays:
        for rel, n in strays[:8]:
            fails.append("%s is build output, not source (%.1f MB)"
                         % (rel, n / (1024.0 ** 2)))

    print("  %d files compared under %s" % (checked, app))
    if fails:
        print()
        for f in fails[:20]:
            print("  FAIL " + f)
        print()
        print("BUNDLE PACKAGE SYNC: %d DIFFERENCE(S) -- run "
              "`python -X utf8 _probe/sync_app_package.py`" % len(fails))
        return 1
    print()
    print("BUNDLE PACKAGE SYNC: THE SHIPPED PYTHON IS THE REPOSITORY'S PYTHON "
          "(%d files)" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
