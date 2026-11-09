# -*- coding: utf-8 -*-
"""Copy the engine sources from the repo into a built bundle's `app\\`.

WHY THIS EXISTS
---------------
`_probe/test_*_shipped.py` start the REAL release exe.  That exe's shell prefers
`<bundle>\\app\\tools\\run_ui.py` over its built-in engine (see
`desktop/src-tauri/src/main.rs::engine_root`), so the bundle's Python copy is
what those suites actually exercise.  When the copy goes stale, a hundred passing
suites in the repo and a hundred red suites against the exe describe the same
code, one day apart, and the reds are all "defects" that were already fixed.

Measured: after `aoe2mod/ui/nl.py` grew by 2 KB in one evening, every shipped
suite still failed the sentences that change had fixed.

USAGE
    python -X utf8 _probe/sync_app_package.py [--bundle DIR] [--dry]

Exit 0 when the bundle matches the repo afterwards, 1 when a copy failed.  A
missing bundle is not an error -- it prints one line and exits 0, because a
developer without a built bundle should not be blocked.
"""
import argparse
import filecmp
import os
import shutil
import sys
import _paths as P

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_BUNDLE = P.BUNDLE

# What `make_bundle.py::copy_app` puts in `app\`, minus the files that only make
# sense in a checkout (`tests/out`, caches).
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")


def files_under(root, drop_test_out=True):
    out = {}
    for base, dirs, names in os.walk(root):
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        if drop_test_out and os.path.basename(base) == "tests" and "out" in dirs:
            dirs.remove("out")
        for n in names:
            if n.endswith((".pyc", ".pyo")):
                continue
            p = os.path.join(base, n)
            out[os.path.relpath(p, root).replace(os.sep, "/")] = p
    return out


def sync_tree(src, dst, dry):
    """Copy every file in `src` to the same relative path under `dst`."""
    copied = 0
    for rel, p in sorted(files_under(src).items()):
        q = os.path.join(dst, rel.replace("/", os.sep))
        if os.path.isfile(q) and filecmp.cmp(p, q, shallow=False):
            continue
        print("  %-6s %s" % ("would" if dry else "copy", rel))
        if not dry:
            os.makedirs(os.path.dirname(q), exist_ok=True)
            shutil.copy2(p, q)
        copied += 1
    return copied


def compare(src, dst):
    """Relative paths that differ or are missing on either side."""
    a = files_under(src)
    b = files_under(dst)
    bad = []
    for rel in sorted(set(a) | set(b)):
        if rel not in a or rel not in b:
            bad.append(rel)
        elif not filecmp.cmp(a[rel], b[rel], shallow=False):
            bad.append(rel)
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description="sync engine sources into a bundle")
    ap.add_argument("--bundle", default=DEFAULT_BUNDLE)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args(argv)

    app = os.path.join(os.path.abspath(args.bundle), "app")
    if not os.path.isdir(app):
        print("no bundle at %s  (nothing to sync)" % app)
        return 0

    total = 0
    for name in ("tools", "aoe2mod"):
        src = os.path.join(ROOT, name)
        dst = os.path.join(app, name)
        if not os.path.isdir(src):
            print("REFUSING: the repo has no %s\\" % name)
            return 1
        n = sync_tree(src, dst, args.dry)
        total += n
        if not args.dry:
            diff = compare(src, dst)
            if diff:
                print("FAILED: %s\\ still differs after the copy: %s"
                      % (name, diff[:12]))
                return 1
    print("SYNC APP PACKAGE: %d copied%s -- %s matches the repo"
          % (total, " (dry run)" if args.dry else "", app))
    return 0


if __name__ == "__main__":
    sys.exit(main())
